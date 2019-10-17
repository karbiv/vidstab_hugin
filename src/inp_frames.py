from subprocess import run
import os
from os import path
import sys
import math
import config
import hugin
from multiprocessing import Pool
from subprocess import run, DEVNULL, check_output
import datatypes
import utils


def input_frames_and_audio():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    utils.delete_files_in_dir(cfg.frames_in)

    #filts = 'fps='.format(cfg.params['fps'])

    inp = cfg.args.videofile
    oaud = path.join(cfg.audio_dir, "audio.ogg")

    ## video
    cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp, '-qscale:v', "2",
            path.join(cfg.datapath, cfg.frames_in, '%06d.jpg'), '-y']
    ## audio
    cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', cfg.args.videofile,
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

        task = datatypes.hugin_task(img, filepath)
        tasks.append(task)

    pto_path = cfg.projection_pto_path
    run(['pto_gen', '-o', pto_path, path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])], stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', pto_path, '--template='+cfg.pto.filepath, pto_path], stdout=DEVNULL)
    in_projection = cfg.params['input_projection']
    run(['pano_modify', '-o', pto_path,
         '--crop=AUTO', pto_path, '--projection='+str(in_projection),
         '--canvas={}x{}'.format(int(cfg.pto.canvas_w*float(cfg.params['input_video_scale'])),
                                 int(cfg.pto.canvas_h*float(cfg.params['input_video_scale'])))],
        stdout=DEVNULL)

    utils.delete_files_in_dir(cfg.frames_projection)
    cfg.current_output_path = cfg.frames_projection
    cfg.current_pto_path = cfg.projection_pto_path
    with Pool(int(cfg.params['num_cpus'])) as p:
        p.map(hugin.frames_projection, tasks)


def create_video_for_vidstab():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '16'
    ivid = path.join(cfg.frames_projection, '%06d.jpg')
    output = cfg.input_video

    cropf = str(cfg.params['input_video_filter'])

    cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
           '-c:v', 'libx264', '-crf', crf,
           '-vf', cropf,
           '-loglevel', 'error', '-stats', '-an', '-y', output]

    run(cmd)
