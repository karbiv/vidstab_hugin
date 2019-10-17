import os
from os import path
import sys
import hugin
from multiprocessing import Pool, Queue, Process
from subprocess import run, DEVNULL, check_output, STDOUT
import numpy as np
import math
import pickle
import re
import config
import datatypes
import utils


pto_txt: str = ''
rpto: datatypes.HuginPTO = None
pto: datatypes.HuginPTO = None
tan_pix: float = 0

def calc_camera_transforms():
    global pto_txt, rpto, pto, tan_pix
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    # create rectilinear pto to calculate camera rotations
    pto_path = cfg.rectilinear_pto_path
    run(['pto_gen', '-o', pto_path, path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])], stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', pto_path, '--template='+cfg.pto.filepath, pto_path], stdout=DEVNULL)
    run(['pano_modify', '-o', pto_path,
         '--canvas={}x{}'.format(cfg.pto.canvas_w*3, cfg.pto.canvas_h*3),
         '--crop=AUTO', pto_path, '--projection='+str(0) ], stdout=DEVNULL)
    rpto = datatypes.HuginPTO(pto_path)

    pto = datatypes.HuginPTO(cfg.projection_pto_path)

    imgs = sorted(os.listdir(cfg.frames_in))
    horizont_tan = math.tan(math.radians(rpto.canv_half_hfov))
    tan_pix = horizont_tan/(rpto.canvas_w/2)

    if not cfg.args.original_input:
        transforms_rel = utils.get_global_motions(cfg.vidstab_dir)
    else:
        transforms_rel = utils.get_global_motions(cfg.vidstab_orig_dir)
    transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
    transforms_abs_filtered = gauss_filter(transforms_abs, cfg.params['smoothing'])

    with open(cfg.pto.filepath, 'r') as proj_pto:
        for line in proj_pto:
            if line.startswith('#') or not line.strip():
                continue
            else:
                pto_txt += line

    utils.delete_files_in_dir(cfg.hugin_projects)

    tasks = []
    for i, t in enumerate(transforms_abs_filtered):
        tasks.append((t, imgs[i]))

    with Pool(int(cfg.params['num_cpus'])) as p:
        p.map(cam_transforms, tasks)


def cam_transforms(task):
    cfg = config.cfg
    t, img = task

    if not cfg.args.original_input:
        ## get original coords from projection
        _coords = '{} {}'.format(pto.canvas_w/2+t.x, pto.canvas_h/2-t.y)
        orig_coords = check_output(['pano_trafo', '-r', pto.filepath, '0'], input=_coords.encode('utf-8'))
        ## get rectilinear coords from original
        rcoords = check_output(['pano_trafo', rpto.filepath, '0'], input=orig_coords).strip().split()
    else:
        ## without input projection video
        orig_coords = '{} {}'.format(cfg.pto.orig_w/2+t.x, cfg.pto.orig_h/2-t.y)
        rcoords = check_output(['pano_trafo', rpto.filepath, '0'], input=orig_coords.encode('utf-8')).strip().split()

    x, y = float(rcoords[0])-(rpto.canvas_w/2), (rpto.canvas_h/2)-float(rcoords[1])

    roll = 0-math.degrees(t.roll)

    yaw_rads = math.atan(x*tan_pix)
    yaw = math.degrees(yaw_rads)

    pitch_rads = math.atan(y*tan_pix)
    pitch = 0-math.degrees(pitch_rads)

    filepath = '{}.pto'.format(img)
    curr_pto_txt = re.sub(r'n".+\.jpg"', 'n"{}"'.format(path.join(cfg.frames_in, img)), pto_txt)
    curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

    with open(path.join(cfg.hugin_projects, filepath), 'w') as f:
        f.write(curr_pto_txt)

    txt = 'Camera rotations for frame {}: yaw {}, pitch {}, roll {}'
    print(txt.format(filepath, str(round(yaw, 5)).rjust(10), str(round(pitch, 5)).rjust(10), str(round(roll, 5)).rjust(10)))


def frames():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    ptos = sorted(os.listdir(cfg.hugin_projects))
    tasks = []
    for i, pto in enumerate(ptos):
        tasks.append(datatypes.hugin_task(str(i+1).zfill(6)+'.jpg', pto))

    utils.delete_files_in_dir(cfg.frames_stabilized)
    cfg.current_output_path = cfg.frames_stabilized
    cfg.current_pto_path = cfg.pto.filepath
    with Pool(int(cfg.params['num_cpus'])) as p:
        p.map(hugin.frames_output, tasks)


def gauss_filter(transforms, smooth_percent):
    cfg = config.cfg

    transforms_copy = transforms.copy()
    smoothing = round((int(cfg.fps)/100)*int(smooth_percent))
    mu = smoothing
    s = mu*2+1

    sigma2 = (mu/2)**2

    kernel = np.exp(-(np.arange(s)-mu)**2/sigma2)

    tlen = len(transforms)
    for i in range(tlen):
        ## make a convolution:
        weightsum, avg = 0.0, datatypes.transform(0, 0, 0)
        for k in range(s):
            idx = i+k-mu
            if idx >= 0 and idx < tlen:
                weightsum += kernel[k]
                avg = utils.add_transforms(avg, utils.mult_transforms(transforms_copy[idx], kernel[k]))

        if weightsum > 0:
            avg = utils.mult_transforms(avg, 1.0/weightsum)
            ## high frequency must be transformed away
            transforms[i] = utils.sub_transforms(transforms[i], avg)

    return transforms


def video():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '17'
    ivid = path.join(cfg.frames_stabilized, '%06d.jpg')
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
    if not cfg.args.original_input:
        output = cfg.out_video
    else:
        output = cfg.out_video_orig

    fps = cfg.fps
    if path.isfile(iaud):
        cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-i', iaud, '-c:v', 'libx264',
               '-preset', 'veryfast', '-crf', crf, '-c:a', 'copy',
               '-loglevel', 'error', '-stats', '-y', output]
    else:
        cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-c:v', 'libx264',
                '-preset', 'veryfast', '-crf', crf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

    run(cmd)


def out_filter():
    cfg = config.cfg

    filts = cfg.params['out_filter']
    crf = '18'
    if not cfg.args.original_input:
        ivid = cfg.out_video
        output = path.join(cfg.output_dir, cfg.out_video_filtered)
    else:
        ivid = cfg.out_video_orig
        output = path.join(cfg.output_dir, cfg.out_video_filtered_orig)
    cmd = ['ffmpeg', '-i', ivid, '-c:v', 'libx264', '-vf', filts, '-crf', crf,
           '-c:a', 'copy', '-loglevel', 'error', '-stats', '-y', output]

    print('\n', cmd, '\n')

    run(cmd)


def cleanup():
    cfg = config.cfg

    utils.delete_files_in_dir(cfg.frames_in)
    utils.delete_files_in_dir(cfg.frames_projection_path)
    utils.delete_files_in_dir(cfg.frames_stabilized)
    utils.delete_files_in_dir(cfg.hugin_projects)
    utils.delete_filepath(cfg.detect_show_video)
