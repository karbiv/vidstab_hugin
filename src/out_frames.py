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

import numpy as np
import skimage.transform as sktf
from skimage import io as skio, data
from skimage.util import img_as_ubyte, img_as_float

import shutil as sh
import traceback

pto_txt: str = ''
rpto: datatypes.HuginPTO = None
tan_pix: float = 0
half_hfov: float = 0

def camera_transforms():
    global pto_txt, rpto, pto, tan_pix, half_hfov
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    frames_dir = cfg.frames_input

    ## create rectilinear pto to calculate camera rotations
    rpto_path = cfg.rectilinear_pto_path
    print('Create rectilinear.pto in renders:')
    res = run(['pto_move', '--copy', '--overwrite', cfg.pto.filepath, rpto_path])
    run(['pano_modify', '-o', rpto_path,
         '--canvas={}x{}'.format(cfg.pto.canvas_w*3, cfg.pto.canvas_h*3),
         '--crop=AUTO', rpto_path, '--projection='+str(0) ], stdout=DEVNULL)
    rpto = datatypes.HuginPTO(rpto_path)

    imgs = sorted(os.listdir(frames_dir))
    half_hfov = math.radians(rpto.canv_half_hfov)
    horizont_tan = math.tan(half_hfov)
    tan_pix = horizont_tan/(rpto.canvas_w/2)

    transforms_rel = utils.get_global_motions(cfg.vidstab_orig_dir)
    transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
    transforms_abs_filtered = gauss_filter(transforms_abs, cfg.args.smoothing)

    with open(cfg.pto.filepath, 'r') as proj_pto:
        for line in proj_pto:
            if line.startswith('#') or not line.strip():
                continue
            else:
                pto_txt += line

    tasks = []
    for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
        path_img = path.join(frames_dir, imgs[i])
        tasks.append((t[0], path_img, t[1]))

    utils.delete_files_in_dir(cfg.hugin_projects)
    utils.delete_files_in_dir(cfg.frames_input_processed)
    with Pool(int(cfg.args.num_cpus)) as p:
        print('\nStart processes pool for creation of tasks.')
        print('Frames camera rotations:')
        p.map(camera_transforms_worker, tasks)


def camera_transforms_worker(task):
    cfg = config.cfg
    t, img, t_rel = task[0], task[1], task[2]

    ## without input projection video
    orig_coords = '{} {}'.format(cfg.pto.orig_w/2+t.x, cfg.pto.orig_h/2-t.y)
    rcoords = check_output(['pano_trafo', rpto.filepath, '0'], input=orig_coords.encode('utf-8')).strip().split()

    x, y = float(rcoords[0])-(rpto.canvas_w/2), (rpto.canvas_h/2)-float(rcoords[1])

    roll = 0-math.degrees(t.roll)
    yaw_deg = math.degrees(math.atan(x*tan_pix))
    pitch_deg = 0-math.degrees(math.atan(y*tan_pix))
    dest_img = img

    #### Rolling Shutter start
    sk_img = skio.imread(img, plugin='pil')
    warp_args = {'center': np.array(sk_img.shape)[:2][::-1] / 2, 'roll': t_rel.roll,
                 'y_move': t_rel.y, 'along_move': t_rel.x}
    modified = sktf.warp(sk_img, rolling_shutter_mappings, map_args=warp_args, order=1)

    dest_img = path.join(cfg.frames_input_processed, path.basename(img))
    if cfg.is_jpeg:
        skio.imsave(dest_img, img_as_ubyte(modified), quality=cfg.jpeg_quality)
    else:
        skio.imsave(dest_img, img_as_ubyte(modified), plugin='pil')
    #### Rolling Shutter end

    ## set input image path for frame PTO
    curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), pto_txt)
    curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

    ### Write PTO project file for this frame
    filepath = '{}.pto'.format(path.basename(dest_img))
    with open(path.join(cfg.hugin_projects, filepath), 'w') as f:
        f.write(curr_pto_txt)

    print(path.join(cfg.hugin_projects, filepath))


def rolling_shutter_mappings(xy, **kwargs):
    '''Inverse map function'''
    cfg = config.cfg
    width, num_lines = 1920, 1080
    len_cxy = len(xy)
    orig_shape = xy.shape

    #### Order of corrections stages is important
    
    #### ACROSS lines
    if int(cfg.params['do_across_lines']) > 0:
        last_line = kwargs['y_move'] * float(cfg.params['across_lines'])
        across_delta = last_line / num_lines
        across_line_shift = 0
        
        #for i in range(num_lines):
        for i in reversed(range(num_lines)): # bottom-up
            y = xy[i::num_lines, 1]
            xy[i::num_lines, 1] = y + across_line_shift
            across_line_shift += across_delta

    #### ALONG lines
    ## TODO maybe combine with across
    if int(cfg.params['do_along_lines']) > 0:
        along_move = kwargs['along_move']
        along_coeff = float(cfg.params['along_lines'])
        last_line = along_move * along_coeff
        along_delta = last_line / num_lines
        along_line_shift = 0

        #for i in range(num_lines):
        for i in reversed(range(num_lines)): # bottom-up
            x = xy[i::num_lines, 0]
            xy[i::num_lines, 0] = x + along_line_shift
            along_line_shift += along_delta
    
    #### ROLL lines
    if int(cfg.params['do_roll_lines']) > 0:
        center, roll = kwargs['center'], kwargs['roll']

        ## Roll in degrees
        roll_coeff = float(cfg.params['roll_lines'])
        last_line_roll = roll * roll_coeff
        roll_delta = last_line_roll / num_lines

        x0, y0 = center
        x, y = xy.T
        cx, cy = x-x0, y-y0

        theta = 0
        cxy = np.column_stack((cx, cy))

        #for i in range(num_lines):
        for i in reversed(range(num_lines)):
            x, y = cxy[i::num_lines].T
            ox = math.cos(theta)*x - math.sin(theta)*y
            oy = math.sin(theta)*x + math.cos(theta)*y
            cxy[i::num_lines] = np.dstack((ox, oy)).squeeze()
            theta -= roll_delta
            #theta += roll_delta

        xy = cxy+center

    return xy
    

def camera_transforms_processed():
    global pto_txt, rpto, pto, tan_pix, half_hfov
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    frames_dir = cfg.frames_input_processed

    ## create rectilinear pto to calculate camera rotations
    rpto_path = cfg.rectilinear_pto_path
    print('Create rectilinear.pto in renders:')
    res = run(['pto_move', '--copy', '--overwrite', cfg.pto.filepath, rpto_path])
    run(['pano_modify', '-o', rpto_path,
         '--canvas={}x{}'.format(cfg.pto.canvas_w*3, cfg.pto.canvas_h*3),
         '--crop=AUTO', rpto_path, '--projection='+str(0) ], stdout=DEVNULL)
    rpto = datatypes.HuginPTO(rpto_path)

    imgs = sorted(os.listdir(frames_dir))
    half_hfov = math.radians(rpto.canv_half_hfov)
    horizont_tan = math.tan(half_hfov)
    tan_pix = horizont_tan/(rpto.canvas_w/2)

    transforms_rel = utils.get_global_motions(cfg.vidstab_orig_dir)
    transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
    transforms_abs_filtered = gauss_filter(transforms_abs, cfg.args.smoothing)

    with open(cfg.pto.filepath, 'r') as proj_pto:
        for line in proj_pto:
            if line.startswith('#') or not line.strip():
                continue
            else:
                pto_txt += line

    tasks = []
    for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
        path_img = path.join(frames_dir, imgs[i])
        tasks.append((t[0], path_img, t[1]))

    utils.delete_files_in_dir(cfg.hugin_projects)
    with Pool(int(cfg.args.num_cpus)) as p:
        print('\nStart processes pool for creation of tasks.')
        print('Frames camera rotations:')
        p.map(camera_transforms_processed_worker, tasks)


def camera_transforms_processed_worker(task):
    cfg = config.cfg
    t, img, t_rel = task[0], task[1], task[2]

    ## without input projection video
    orig_coords = '{} {}'.format(cfg.pto.orig_w/2+t.x, cfg.pto.orig_h/2-t.y)
    rcoords = check_output(['pano_trafo', rpto.filepath, '0'], input=orig_coords.encode('utf-8')).strip().split()

    x, y = float(rcoords[0])-(rpto.canvas_w/2), (rpto.canvas_h/2)-float(rcoords[1])

    roll = 0-math.degrees(t.roll)
    yaw_deg = math.degrees(math.atan(x*tan_pix))
    pitch_deg = 0-math.degrees(math.atan(y*tan_pix))
    dest_img = path.join(cfg.frames_input_processed, path.basename(img))

    ## set input image path for frame PTO
    curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), pto_txt)
    curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
    curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

    ### Write PTO project file for this frame
    filepath = '{}.pto'.format(path.basename(dest_img))
    with open(path.join(cfg.hugin_projects, filepath), 'w') as f:
        f.write(curr_pto_txt)

    print(path.join(cfg.hugin_projects, filepath))


def frames():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    ptos = sorted(os.listdir(cfg.hugin_projects))
    tasks = []
    for i, pto in enumerate(ptos):
        tasks.append(datatypes.hugin_task(str(i+1).zfill(6)+'.'+cfg.img_ext, pto))

    utils.delete_files_in_dir(cfg.frames_stabilized)
    cfg.current_output_path = cfg.frames_stabilized
    cfg.current_pto_path = cfg.pto.filepath
    with Pool(int(cfg.args.num_cpus)) as p:
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
    ivid = path.join(cfg.frames_stabilized, '%06d.'+cfg.img_ext)
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
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
    crf = '14'
    ivid = cfg.out_video_orig
    output = path.join(cfg.output_dir, cfg.out_video_filtered_orig)

    cmd = ['ffmpeg', '-i', ivid, '-c:v', 'libx264', '-vf', filts, '-crf', crf,
           '-c:a', 'copy', '-loglevel', 'error', '-stats', '-y', output]

    print('\n', cmd, '\n')

    run(cmd)


def cleanup():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    utils.delete_files_in_dir(cfg.frames_input)
    utils.delete_files_in_dir(cfg.frames_projection)
    utils.delete_files_in_dir(cfg.frames_stabilized)
    utils.delete_files_in_dir(cfg.hugin_projects)

    utils.delete_filepath(path.join(cfg.vidstab_orig_dir, 'show.mkv'))
    utils.delete_filepath(cfg.out_video_orig)
