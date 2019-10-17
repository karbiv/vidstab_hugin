from subprocess import run
import os
from os import path
import sys
import math
import config
import hugin
from multiprocessing import Pool
from subprocess import run, DEVNULL
from datatypes import *
import utils


def input_frames_and_audio():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    ## scaled down frames for the first stage of stabilization
    frame_scale = float(cfg.params['first_stage_frame_scale'])
    if frame_scale > 1:
        print('cfg.first_stage_frame_scale should be less than 1;')
        exit()
    divider = float(1/frame_scale)*2
    scale = 'scale=floor(iw/{})*2:floor(ih/{})*2'.format(divider, divider)

    utils.delete_files_in_dir(cfg.frames_in)
    ## input file
    oaud = path.join(cfg.audio_dir, "audio.ogg")

    if cfg.args.duration:
        cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats',
                '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
                '-t', cfg.args.duration,
                '-vf', scale,
                path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y']
        cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats',
                '-ss', cfg.args.seek_start, '-i', cfg.args.videofile,
                '-t', cfg.args.duration,
                '-vn', '-aq', str(3), '-y', oaud]
    else:
        cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats',
                '-ss', cfg.args.seek_start, '-i', cfg.args.videofile, '-qscale:v', "2",
                '-vf', scale,
                path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y']
        cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats',
                '-i', cfg.args.videofile,
                '-vn', '-aq', str(3), '-y', oaud]

    run(cmd1)
    run(cmd2)


def frames_projection():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    imgs = sorted(os.listdir(cfg.frames_in))
    tasks = []
    for i, img in enumerate(imgs):
        filepath = 'frame_{}.pto'.format(i+1)

        task = hugin_task(0, 0, 0, img, filepath)
        tasks.append(task)

    utils.delete_filepath(cfg.projection_pto_path)

    run(['pto_gen', '-o', cfg.projection_pto_path,
         path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
        stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', cfg.projection_pto_path, '--template='+cfg.pto.filepath,
         cfg.projection_pto_path], stdout=DEVNULL)
    run(['pano_modify', '-o', cfg.projection_pto_path, '--crop=AUTO', cfg.projection_pto_path,
         '--projection='+str(cfg.params['vidstab_projection_1']) ],
        stdout=DEVNULL)

    utils.delete_files_in_dir(cfg.frames_projection_path)
    cfg.current_output_path = cfg.frames_projection_path
    #cfg.current_pto_path = cfg.pto.filepath
    cfg.current_pto_path = cfg.projection_pto_path
    with Pool(int(cfg.params['num_processes'])) as p:
        p.map(hugin.frames_projection, tasks)


def create_video_for_vidstab():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '16'
    ivid = path.join(cfg.frames_projection_path, '%06d.jpg')
    output = cfg.frames_projection_video

    # ## 4:3 aspect for rectilinear projection
    # cropf = 'crop=w=floor(ih*1.3333):h=ih'

    # ## 16:9 aspect for rectilinear projection
    # cropf = 'crop=w=floor((ih*1.7777)/2)*2:h=floor(ih/2)*2'

    ## Some projection, just make size divisible by 2
    cropf = 'crop=w=floor(iw/2)*2:h=floor(ih/2)*2'

    cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
           '-c:v', 'libx264', '-crf', crf,
           '-vf', cropf,
           '-loglevel', 'error', '-stats', '-an', '-y', output]

    run(cmd)

# def write_full_input_frames():
#     print('\n {} \n'.format(sys._getframe().f_code.co_name))
#     cfg = config.cfg

#     utils.delete_files_in_dir(cfg.full_input_frames)

#     frame_scale = float(cfg.params['first_stage_frame_scale'])
#     if frame_scale == 1:
#         return
#     else:
#         print('\n write_full_input_frames() \n')

#     cmd = ['ffmpeg', '-i', cfg.args.videofile, '-qscale:v', "2",
#            path.join(cfg.full_input_frames, '%06d.jpg'),
#            '-loglevel', 'error', '-stats', '-y']
#     run(cmd)
