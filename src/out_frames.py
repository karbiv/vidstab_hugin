import os
from os import path
import hugin
from multiprocessing import Pool, Queue, Process
from subprocess import run, DEVNULL, check_output
from math import tan, atan, radians, degrees
import config
from datatypes import *
import numpy as np
import utils


motions_abs = [] # in absolute form between frames


def output_frames():
    global motions_abs
    cfg = config.cfg

    #motions_rel = utils.get_global_motions(cfg.vidstab_dir)
    motions_rel = utils.get_global_motions(cfg.output_dir)

    #motions_abs = utils.convert_relative_motions_to_absolute(motions_rel)
    motions_abs = motions_rel
    utils.delete_files_in_dir(cfg.frames_stabilized)
    create_tasks_and_transform()


def output_video():
    cfg = config.cfg

    crf = '16'
    f = 'pad=ceil(iw/2)*2:ceil(ih/2)*2'
    ivid = path.join(cfg.frames_stabilized, '%06d.jpg')
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
    output = path.join(cfg.output_dir, 'output.mkv')
    if path.isfile(iaud):
        run(['ffmpeg', '-loglevel', 'error', '-stats', '-framerate', cfg.fps,
             '-i', ivid, '-i', iaud, '-c:v', 'libx264',
             '-vf', f, '-crf', crf, '-c:a', 'copy', '-y', output])
    else:
        run(['ffmpeg', '-loglevel', 'error', '-stats', '-framerate', cfg.fps,
             '-i', ivid, '-c:v', 'libx264',
             '-vf', f, '-crf', crf, '-an', '-y', output])


def create_tasks_and_transform():
    cfg = config.cfg

    #motions = utils.gauss_filter(motions_abs)
    motions = motions_abs

    tasks = []
    imgs = sorted(os.listdir(cfg.frames_in))

    lens_center_x, lens_center_y = utils.lens_shift()
    proj_crop_x = lens_center_x-cfg.pto.crop_l
    proj_crop_y = lens_center_y-cfg.pto.crop_t
    half_crop_w = cfg.pto.crop_w/2
    half_crop_h = cfg.pto.crop_h/2
    delta_x = proj_crop_x-half_crop_w
    delta_y = proj_crop_y-half_crop_h

    left_pix = half_crop_w + delta_x
    right_pix = half_crop_w - delta_x
    up_pix = half_crop_h + delta_y
    down_pix = half_crop_h - delta_y

    horizont_half_fov = min(float(cfg.params['left_fov']), float(cfg.params['right_fov']))
    vertical_half_fov = min(float(cfg.params['up_fov']), float(cfg.params['down_fov']))
    horizont_tan = tan(radians(horizont_half_fov))
    vertical_tan = tan(radians(vertical_half_fov))

    width_half_pix = min(left_pix, right_pix)
    height_half_pix = min(up_pix, down_pix)

    width_tan_pix = horizont_tan/width_half_pix
    height_tan_pix = vertical_tan/height_half_pix

    for i, img in enumerate(imgs):
        try:
            x, y, roll = motions[i].__dict__.values()
        except Exception as e:
            print(e)
            x, y, roll = 0, 0, 0
        filepath = 'frame_{}.pto'.format(i+1)

        roll = 0-degrees(roll)

        orig_coords = '{} {}'.format(cfg.pto.orig_w/2+x+cfg.pto.lens_d,
                                     cfg.pto.orig_h/2-y+cfg.pto.lens_e)
        ret = check_output(['pano_trafo', cfg.pto.filepath, '0'],
                           input=orig_coords.encode('utf-8')).strip().split()

        rx, ry = float(ret[0]), float(ret[1])
        x, y = rx-(cfg.pto.canvas_w/2), (cfg.pto.canvas_h/2)-ry

        yaw_rads = atan(x*width_tan_pix)
        yaw = degrees(yaw_rads)

        pitch_rads = atan(y*height_tan_pix)
        pitch = 0-degrees(pitch_rads)

        task = hugin_task(roll, yaw, pitch, img, filepath)
        tasks.append(task)

        print('Calc camera rotations for frame {}: yaw {}, pitch {}'.format(i, yaw, pitch))

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

    utils.delete_files_in_dir(cfg.hugin_projects)
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.frames_output, tasks)

    hugin.frames_crop_q.put(None, True)
    utils.delete_filepath(base_pto_path)
