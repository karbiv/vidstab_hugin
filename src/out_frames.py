
import os
from os import path
import hugin
from multiprocessing import Pool, Queue, Process
from subprocess import run, DEVNULL
from math import tan, atan, radians, degrees
import config
from datatypes import *
import numpy as np
import matplotlib.pyplot as plt
from utils import *


motions_abs = [] # in absolute form between frames


def output_frames():
    global motions_abs
    cfg = config.cfg

    motions_rel = get_motions()

    motions_abs = convert_relative_motions_to_absolute(motions_rel)
    delete_files_in_dir(cfg.frames_stabilized)
    create_tasks_and_transform()


def output_video():
    cfg = config.cfg
    
    crf = '16'
    f = 'pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p'
    ivid = path.join(cfg.frames_stabilized, '%06d.jpg')
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
    output = path.join(cfg.output_dir, 'output.mkv')
    if path.isfile(iaud):
        run(['ffmpeg', '-loglevel', 'info', '-framerate', cfg.fps,
             '-thread_queue_size', '2048',
             '-i', ivid, '-i', iaud, '-c:v', 'libx264',
             '-vf', f, '-crf', crf, '-c:a', 'copy', '-y', output])
    else:
        run(['ffmpeg', '-loglevel', 'info', '-framerate', cfg.fps,
             '-thread_queue_size', '2048',
             '-i', ivid, '-c:v', 'libx264',
             '-vf', f, '-crf', crf, '-an', '-y', output])


def get_motions():
    cfg = config.cfg
    
    motions = []
    f = open(path.join(cfg.datapath, 'vidstab', 'global_motions.trf'))
    lines = f.read().splitlines()
    for line in lines:
        if not line[0] == '#':
            data = line.split()
            motions.append(motion(float(data[1]), float(data[2]), float(data[3])))

    return motions


def convert_relative_motions_to_absolute(motions_rel):
    '''Relative to absolute (integrate transformations)'''
    motions_abs = []
    currm = motions_rel[0]
    motions_abs.append(currm)
    for nextm in motions_rel[1:]:
        currm = add_motions(currm, nextm)
        motions_abs.append(currm)
    return motions_abs


def create_tasks_and_transform(only_show_graph=False):
    cfg = config.cfg

    if False:
        show_graph(motions_abs)
        show_graph(gauss_filter(motions_abs))
        exit()
    else:
        motions = gauss_filter(motions_abs)
        
        tasks = []
        imgs = sorted(os.listdir(cfg.frames_in))

        ## calculate FOVs from optical center
        
        proj_x, proj_y = hugin.pano_trafo()
        proj_crop_x = proj_x-cfg.pto.crop_l
        proj_crop_y = proj_y-cfg.pto.crop_t        
        half_crop_w = round(cfg.pto.crop_w/2)
        half_crop_h = round(cfg.pto.crop_h/2)
        delta_x = proj_crop_x-half_crop_w
        delta_y = proj_crop_y-half_crop_h

        left_tan = tan(radians(float(cfg.params['left_fov'])))
        right_tan = tan(radians(float(cfg.params['right_fov'])))
        up_tan = tan(radians(float(cfg.params['up_fov'])))
        down_tan = tan(radians(float(cfg.params['down_fov'])))

        left_pix = half_crop_w + delta_x
        right_pix = half_crop_w - delta_x
        up_pix = half_crop_h + delta_y
        down_pix = half_crop_h - delta_y
        
        left_tan_pix = left_tan/left_pix
        right_tan_pix = right_tan/right_pix
        up_tan_pix = up_tan/up_pix
        down_tan_pix = down_tan/down_pix

        for i, img in enumerate(imgs):
            try:
                x, y, roll = motions[i].__dict__.values()
            except Exception as e:
                print(e)
                x, y, roll = 0, 0, 0
            filepath = 'frame_{}.pto'.format(i+1)

            roll = round(0-degrees(roll), 5)

            if x < 0:
                yaw_rads = atan(x*left_tan_pix)
            else:
                yaw_rads = atan(x*right_tan_pix)
            yaw = round(degrees(yaw_rads), 5)

            if y < 0:
                pitch_rads = atan(y*up_tan_pix)
            else:
                pitch_rads = atan(y*down_tan_pix)
            pitch = round(0-degrees(pitch_rads), 5)

            task = hugin_task(roll, yaw, pitch, img, filepath)
            tasks.append(task)

        ## multiprocessing
        hugin.frame_crop_widths = []
        hugin.frame_crop_heights = []
        hugin.frames_crop_q = Queue()

        ## Prepare pto file with output projection to calculate crops
        base_pto_path = path.join(cfg.hugin_projects, 'base_crop.pto')
        run(['pto_gen', '-o', base_pto_path, path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
            stderr=DEVNULL, stdout=DEVNULL)
        run(['pto_template', '-o', base_pto_path, '--template='+cfg.pto.filepath, base_pto_path],
            stdout=DEVNULL)
        ## set projection
        run(['pano_modify', '-o', base_pto_path, '--crop=AUTO',
             '--projection='+cfg.params['output_projection'], base_pto_path], stdout=DEVNULL)
        base_pto = HuginPTO(base_pto_path)
        crop_collector = Process(target=hugin.collect_frame_crop_data,
                                 args=(hugin.frames_crop_q, base_pto))
        crop_collector.start()

        delete_files_in_dir(cfg.hugin_projects)
        with Pool(int(cfg.params['num_processes'])) as p:
            p.map(hugin.frames_output, tasks)

        hugin.frames_crop_q.put(None, True)
        delete_filepath(base_pto_path)


def create_cam_rotations():
    pass


def gauss_filter(motions):
    cfg = config.cfg
    
    motions_copy = motions.copy()
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    mu = smoothing
    s = mu*2+1
    sigma2 = (mu/2.0)**2
    kernel = np.exp(-(np.arange(s)-mu)**2/sigma2)

    mlength = len(motions)
    for i in range(mlength):
        ## make a convolution:
        weightsum, avg = 0.0, motion(0, 0, 0)
        for k in range(s):
            idx = i+k-mu
            if idx >= 0 and idx < mlength:
                weightsum += kernel[k]
                avg = add_motions(avg, mult_motion(motions_copy[idx], kernel[k]))

        if weightsum > 0:
            avg = mult_motion(avg, 1.0/weightsum)
            ## high frequency must be transformed away
            motions[i] = sub_motions(motions[i], avg)

    return motions


def sub_motions(m1, m2):
    return motion(m1.x-m2.x, m1.y-m2.y, m1.roll-m2.roll)


def add_motions(m1, m2):
    return motion(m1.x+m2.x, m1.y+m2.y, m1.roll+m2.roll)


def mult_motion(m, s):
    return motion(m.x*s, m.y*s, m.roll*s)


def show_graph(motions):
    y_vals = []
    for m in motions:
        y_vals.append(m.x)
    xx = np.arange(len(y_vals))
    yy = np.array(y_vals)
    #plt.plot(xx, yy)
    plt.bar(xx, yy)
    plt.show()
