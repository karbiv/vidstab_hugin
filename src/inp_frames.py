from subprocess import run
from os import path
import os
import math
import config
import hugin
from multiprocessing import Pool
from datatypes import *
from utils import *


def input_frames_and_audio():
    cfg = config.cfg
    
    delete_files_in_dir(cfg.frames_in)
    ## input file
    oaud = path.join(cfg.audio_dir, "audio.ogg")
    if cfg.args.duration:
        run(['ffmpeg', '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
             '-t', cfg.args.duration,
             path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y'])
        run(['ffmpeg', '-ss', cfg.args.seek_start, '-i', cfg.args.videofile,
             '-t', cfg.args.duration,
             '-vn', '-aq', str(3), '-y', oaud])
    else:
        run(['ffmpeg', '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
             path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y'])
        run(['ffmpeg', '-i', cfg.args.videofile, '-vn', '-aq', str(3), '-y', oaud])


def create_rectilinear_frames():
    cfg = config.cfg
    
    imgs = sorted(os.listdir(cfg.frames_in))
    ## create rectilinear frame_tasks
    delete_files_in_dir(cfg.frames_rectilinear)
    frame_tasks = []
    for i, img in enumerate(imgs):
        tx, ty, roll = 0, 0, 0
        filename = 'frame_{}.pto'.format(i+1)
        task = hugin_task(tx, ty, roll, img, filename)
        frame_tasks.append(task)

    ## create rectilinear frames
    delete_files_in_dir(cfg.hugin_projects)
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.create_rectilinear_frames, frame_tasks)


def create_vid_for_vidstab():
    '''Create a video that will be analyzed by libvidstab'''
    cfg = config.cfg
    
    inp = path.join(cfg.datapath, cfg.frames_rectilinear, "%06d.jpg")
    out = path.join(cfg.datapath, "vidstab", "tostabilize.mkv")

    ## calculate crop for rectilinear frame, to pass to libvidstab analysis
    stab_half_fov = float(cfg.params['stab_crop_fov'])/2

    ## horizontal
    center_crop_w = ff(cfg.pto.crop_w)
    if cfg.pto.half_hfov > stab_half_fov:
        center_crop_w = get_center_crop(float(cfg.params['stab_crop_fov'])/2)

    ## vertical
    center_crop_h = ff(cfg.pto.crop_h)
    if cfg.pto.half_vfov > stab_half_fov:
        center_crop_h = get_center_crop(float(cfg.params['stab_crop_fov'])/2)

    cropf = 'crop={}:{}'.format(center_crop_w, center_crop_h)
    filts = cropf+',format=yuv444p,hqdn3d,unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=1.5'
    filts = 'format=yuv444p,hqdn3d,unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=1.5'
    #filts = filts+',normalize=blackpt=black:whitept=white:smoothing={}'.format(round(float(cfg.fps)/2))

    ## create video
    run(['ffmpeg', '-framerate', cfg.fps, '-i', inp, '-c:v', 'libx264', '-crf', '16', '-vf',
         filts, '-an', '-y', out])


def get_center_crop(stab_half_fov):
    return ff(degs_to_pix(stab_half_fov))*2
