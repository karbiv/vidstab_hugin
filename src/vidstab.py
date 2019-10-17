import os
from os import path
import sys
from subprocess import run, DEVNULL, check_output
import math
import config
import utils
import datatypes


def detect():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    trf = 'transforms.trf'
    dest = cfg.vidstab_dir

    step = 'stepsize='+str(cfg.params['stepsize'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'

    inp = cfg.input_video
    filts = detect.format(step, mincontrast, trf)

    show_detect = path.join(dest, 'show.mkv')
    cmd = ['ffmpeg', '-i', inp, '-c:v', 'libx264', '-crf', '18',
           '-vf', filts,
           '-an', '-y', '-loglevel', 'error', '-stats', show_detect]

    num_frames = len(os.listdir(cfg.frames_in))
    print('Total frames: {}'.format(num_frames))

    print(' '.join(cmd))
    run(cmd, cwd=dest)


def transform():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    trf = 'transforms.trf'
    dest = cfg.vidstab_dir
    out = os.path.join(dest, 'stabilized.mkv')

    crf = '18'
    smoothing_percent = int(cfg.params['smoothing'])
    smoothing = round((int(cfg.fps)/100)*smoothing_percent)
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black'.format(trf, sm)

    inp = cfg.input_video
    cmd = ['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf,
           '-t', '00:00:00.250',
           '-an', '-y', '-stats', out]
    print(' '.join(cmd))
    run(cmd, cwd=dest)


def detect_original():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    trf = 'transforms.trf'
    dest = cfg.vidstab_orig_dir

    step = 'stepsize='+str(cfg.params['stepsize'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'

    inp = cfg.args.videofile
    cropf = cfg.params['input_orig_video_filter']
    filts = '{},{}'.format(cropf, detect.format(step, mincontrast, trf))

    show_detect = path.join(dest, 'show.mkv')
    cmd = ['ffmpeg', '-i', inp, '-c:v', 'libx264', '-crf', '18',
           '-vf', filts,
           '-an', '-y', '-loglevel', 'error', '-stats', show_detect]

    num_frames = len(os.listdir(cfg.frames_in))
    print('Total frames: {}'.format(num_frames))

    print(' '.join(cmd))
    run(cmd, cwd=dest)


def transform_original():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    trf = 'transforms.trf'
    dest = cfg.vidstab_orig_dir
    out = os.path.join(dest, 'stabilized.mkv')

    crf = '18'
    smoothing_percent = int(cfg.params['smoothing'])
    smoothing = round((int(cfg.fps)/100)*smoothing_percent)
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    cropf = cfg.params['input_orig_video_filter']
    f = '{},vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black'.format(cropf, trf, sm)

    inp = cfg.args.videofile
    cmd = ['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf,
           '-t', '00:00:00.250',
           '-an', '-y', '-stats', out]
    print(' '.join(cmd))
    run(cmd, cwd=dest)
