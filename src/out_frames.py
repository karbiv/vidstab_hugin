import os
from os import path
import sys
import hugin
from multiprocessing import Pool, Queue, Process
from subprocess import run, DEVNULL, check_output, STDOUT
import math
import config
from datatypes import *
import numpy as np
import matplotlib.pyplot as plt
import utils


motions_abs = [] # in absolute form between frames


def frames_2():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    input_frames = cfg.frames_in

    ## create cfg.stab_pto_path file
    run(['pto_gen', '-o', cfg.stab_pto_path,
         path.join(input_frames, os.listdir(input_frames)[0])],
        stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', cfg.stab_pto_path, '--template='+cfg.pto.filepath,
         cfg.stab_pto_path], stdout=DEVNULL)

    run(['pano_modify', '--output='+cfg.stab_pto_path, '--crop=AUTO',
         '--projection='+str(cfg.params['out_projection']),
         cfg.stab_pto_path], stdout=DEVNULL)

    pto = HuginPTO(cfg.stab_pto_path)

    utils.delete_files_in_dir(cfg.frames_stabilized_2)
    rotations = []
    f = open(path.join(cfg.output_dir, 'combined_rotations.txt'))
    lines = f.read().splitlines()
    for line in lines:
        if not line[0] == '#': 
            data = line.split()
            rotations.append((float(data[0]), float(data[1]), float(data[2])))
    
    imgs = sorted(os.listdir(cfg.frames_in))
    tasks = []
    for i, img in enumerate(imgs):
        rot = rotations[i]
        filepath = 'frame_{}.pto'.format(i+1)
        task = hugin_task(rot[0], rot[1], rot[2], img, filepath)
        tasks.append(task)

    ## multiprocessing
    hugin.frame_crop_widths = []
    hugin.frame_crop_heights = []
    hugin.frames_crop_q = Queue()

    ## Prepare pto file with output projection to calculate crops
    base_pto_path = path.join(cfg.hugin_projects, 'base_crop.pto')
    run(['pto_gen', '-o', base_pto_path, path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
        stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', base_pto_path, '--template='+cfg.stab_pto_path, base_pto_path],
        stdout=DEVNULL)
    ## set projection
    run(['pano_modify', '-o', base_pto_path, '--crop=AUTO',
         '--projection='+cfg.params['out_projection'], base_pto_path], stdout=DEVNULL)
    base_pto = HuginPTO(base_pto_path)
    crop_collector = Process(target=hugin.collect_frame_crop_data,
                             args=(hugin.frames_crop_q, base_pto))
    crop_collector.start()

    utils.delete_files_in_dir(cfg.hugin_projects)
    cfg.current_output_path = cfg.frames_stabilized_2
    cfg.current_pto_path = cfg.stab_pto_path
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.frames_output, tasks)

    hugin.frames_crop_q.put(None, True)
    utils.delete_filepath(base_pto_path)    


def frames_1():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    imgs = sorted(os.listdir(cfg.frames_in))
    #pto_projection = HuginPTO(cfg.projection_pto_path)
    pto_projection = cfg.pto
    horizont_tan = math.tan(math.radians(pto_projection.canv_half_hfov))
    tan_pix = horizont_tan/(pto_projection.canvas_w/2)

    utils.delete_files_in_dir(cfg.frames_stabilized)
    motions_rel = utils.get_global_motions(cfg.vidstab_dir)
    motions_abs_filtered = utils.gauss_filter(utils.convert_relative_motions_to_absolute(motions_rel), cfg.params['smoothing_1'])
    tasks = []
    for i, img in enumerate(imgs):
        try:
            x, y, roll = motions_abs_filtered[i].__dict__.values()
        except Exception as e:
            print(e)
            x, y, roll = 0, 0, 0

        roll = 0-math.degrees(roll)

        ## get original coords from projection
        _coords = '{} {}'.format(pto_projection.canvas_w/2+x, pto_projection.canvas_h/2-y)
        orig_coords = check_output(['pano_trafo', '-r', cfg.projection_pto_path, '0'],
                                   input=_coords.encode('utf-8')).strip().split()
        ox, oy = float(orig_coords[0]), float(orig_coords[1])
        
        ## get rectilinear projection coords from original
        _coords = '{} {}'.format(ox, oy)
        rectil_coords = check_output(['pano_trafo', cfg.pto.filepath, '0'],
                                     input=_coords.encode('utf-8')).strip().split()

        rx, ry = float(rectil_coords[0]), float(rectil_coords[1])
        x, y = rx-(cfg.pto.canvas_w/2), (cfg.pto.canvas_h/2)-ry

        yaw_rads = math.atan(x*tan_pix)
        yaw = math.degrees(yaw_rads)

        pitch_rads = math.atan(y*tan_pix)
        pitch = 0-math.degrees(pitch_rads)

        filepath = 'frame_{}.pto_projection'.format(i+1)
        task = hugin_task(roll, yaw, pitch, img, filepath)
        tasks.append(task)

        print('Calc camera rotations for frame {}: x {}, y {}, yaw {}, pitch {}'.format(i, x, y, yaw, pitch))

    ## save camera rotations of a first vidstab stage
    rotations_1_filepath = path.join(cfg.output_dir, 'rotations_1.txt')
    utils.delete_filepath(rotations_1_filepath)
    f = open(rotations_1_filepath, 'w')
    for t in tasks:
        f.write('{} {} {}\n'.format(t.roll, t.yaw, t.pitch))
    f.close()
        
    utils.delete_files_in_dir(cfg.hugin_projects)
    cfg.current_output_path = cfg.frames_stabilized
    ## create cfg.out_1_pto_path
    run(['pto_gen', '-o', cfg.out_1_pto_path,
         path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
        stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', cfg.out_1_pto_path, '--template='+cfg.pto.filepath,
         cfg.out_1_pto_path], stdout=DEVNULL)
    run(['pano_modify', '-o', cfg.out_1_pto_path, '--crop=AUTO', cfg.out_1_pto_path,
         '--projection='+str(cfg.params['vidstab_projection_2']) ],
        stdout=DEVNULL)
    
    #cfg.current_pto_path = cfg.pto.filepath
    cfg.current_pto_path = cfg.out_1_pto_path
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.frames_output, tasks)


def out_video_1():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '16'
    ivid = path.join(cfg.frames_stabilized, '%06d.jpg')
    iaud = path.join(cfg.audio_dir, 'audio.ogg')

    output = cfg.out_video_1

    # ## 4:3 aspect for rectilinear projection
    # cropf = 'crop=w=floor(ih*1.3333):h=ih'

    # ## 16:9 aspect for rectilinear projection
    # cropf = 'crop=w=floor((ih*1.7777)/2)*2:h=floor(ih/2)*2'

    cropf = 'crop=w=floor(iw/2)*2:h=floor(ih/2)*2'

    if path.isfile(iaud):
        cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-i', iaud,
               '-c:v', 'libx264', '-vf', cropf, '-crf', crf, '-c:a', 'copy',
               '-loglevel', 'error', '-stats', '-y', output]
    else:
        cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-vf', cropf, '-crf', crf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

    # ## test drawbox
    # box = ',drawbox=w=(iw/2.185):x=iw/2-(iw/2.185)/2:y=0:h=ih:color=black@1:t=fill'
    # f2 = ',crop=floor(iw/2.2)*2:floor(ih/2)*2'
    # pad = ',pad=w=iw+floor(iw/7.45):x=floor(iw/7.45)/2:h=ih+floor(ih/2.35):y=floor(ih/2.35)/2'
    # #pad = ',pad=w=iw+floor(iw/8):x=floor(iw/8)/2'
    # sharpen = ',unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=2.5'
    # cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-i', iaud,
    #        '-c:v', 'libx264', '-vf', f+box+f2+pad+sharpen, '-crf', crf, '-c:a', 'copy',
    #        '-loglevel', 'error', '-stats', '-y', output]

    # crop = 'crop=floor(iw/8)*2:floor(ih/4)*2'
    # cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-i', iaud,
    #        '-c:v', 'libx264', '-vf', crop, '-crf', crf, '-c:a', 'copy',
    #        '-loglevel', 'error', '-stats', '-y', output]

    run(cmd)


def out_video_2():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '16'
    f = 'crop=floor(iw/2)*2:floor(ih/2)*2'
    ivid = path.join(cfg.frames_stabilized_2, '%06d.jpg')
    iaud = path.join(cfg.audio_dir, 'audio.ogg')

    if path.isfile(iaud):
        cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-i', iaud,
               '-c:v', 'libx264', '-vf', f, '-crf', crf, '-c:a', 'copy',
               '-loglevel', 'error', '-stats', '-y', cfg.out_video_2]
    else:
        cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-vf', f, '-crf', crf,
               '-loglevel', 'error', '-stats', '-an', '-y', cfg.out_video_2]
    run(cmd)


def show_graph(motions):
    y_vals = []
    for m in motions:
        y_vals.append(m.x)
    xx = np.arange(len(y_vals))
    yy = np.array(y_vals)
    #plt.plot(xx, yy)
    plt.bar(xx, yy)
    plt.show()
