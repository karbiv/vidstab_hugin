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
    print('input_frames_and_audio()')
    cfg = config.cfg

    delete_files_in_dir(cfg.frames_in)
    ## input file
    oaud = path.join(cfg.audio_dir, "audio.ogg")
    if cfg.args.duration:
        run(['ffmpeg', '-loglevel', 'error', '-stats',
             '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
             '-t', cfg.args.duration,
             path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y'])
        run(['ffmpeg', '-loglevel', 'error', '-stats',
             '-ss', cfg.args.seek_start, '-i', cfg.args.videofile,
             '-t', cfg.args.duration,
             '-vn', '-aq', str(3), '-y', oaud])
    else:
        run(['ffmpeg', '-loglevel', 'error', '-stats',
             '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
             path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y'])
        run(['ffmpeg', '-loglevel', 'error', '-stats',
             '-i', cfg.args.videofile, '-vn', '-aq', str(3), '-y', oaud])


def create_projection_frames():
    print('create_projection_frames()')
    cfg = config.cfg
    
    imgs = sorted(os.listdir(cfg.frames_in))
    ## create rectilinear frame_tasks
    delete_files_in_dir(cfg.frames_projection)
    frame_tasks = []
    for i, img in enumerate(imgs):
        tx, ty, roll = 0, 0, 0
        filename = 'frame_{}.pto'.format(i+1)
        task = hugin_task(tx, ty, roll, img, filename)
        frame_tasks.append(task)

    ## create rectilinear frames
    delete_files_in_dir(cfg.hugin_projects)
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.create_projection_frames, frame_tasks)


def create_vid_for_vidstab():
    '''Create a video that will be analyzed by libvidstab'''
    print('create_vid_for_vidstab()')
    cfg = config.cfg
    
    inp = path.join(cfg.datapath, cfg.frames_projection, "%06d.jpg")
    out = path.join(cfg.datapath, "vidstab", "tostabilize.mkv")

    # filts = 'format=yuv444p,hqdn3d,unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount=1.4'
    # filts = filts+',normalize=blackpt=black:whitept=white:smoothing={}'.format(round(float(cfg.fps)/2))

    #filts = 'scale=floor(iw/2):(floor(ih/2)),'
    #filts = 'crop=((floor(iw/4))*2):(floor(ih/4))*2,'
    filts = 'normalize=blackpt=black:whitept=white:smoothing={}'.format(round(float(cfg.fps)/2))

    ## create video
    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-framerate', cfg.fps, '-i', inp, '-c:v', 'libx264', '-crf', '16', '-vf',
         filts, '-an', '-y', out])
