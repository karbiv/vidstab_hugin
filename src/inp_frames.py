from subprocess import run
import os
from os import path
import sys
import math
import config
#import hugin
from multiprocessing import Pool
from subprocess import run, DEVNULL, check_output
import datatypes
import utils

import numpy as np
import skimage.transform as sktf
from skimage import io as skio
from skimage.util import img_as_ubyte


def input_frames_and_audio():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    utils.delete_files_in_dir(cfg.frames_input)

    inp = cfg.args.videofile
    oaud = path.join(cfg.audio_dir, "audio.ogg")

    ## video
    # cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp, '-qscale:v', '1',
    #         path.join(cfg.datapath, cfg.frames_input, '%06d.png'), '-y']
    cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp,
            path.join(cfg.datapath, cfg.frames_input, '%06d.png'), '-y']
    ## audio
    cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', cfg.args.videofile,
            '-vn', '-aq', str(3), '-y', oaud]

    run(cmd1)
    run(cmd2)


def frames_projection():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    imgs = sorted(os.listdir(cfg.frames_input))
    tasks = []
    for i, img in enumerate(imgs):
        filepath = 'frame_{}.pto'.format(i+1)

        task = datatypes.hugin_task(img, filepath)
        tasks.append(task)

    print('Create rectilinear.pto in renders.')
    pto_path = cfg.projection_pto_path
    res = run(['pto_move', '--copy', '--overwrite', cfg.pto.filepath, pto_path], stdout=DEVNULL)

    input_video_scale = 1
    run(['pano_modify', '-o', pto_path,
         '--crop=AUTO', pto_path, '--projection='+str(cfg.args.input_projection),
         '--canvas={}x{}'.format(int(cfg.pto.canvas_w*float(input_video_scale)),
                                 int(cfg.pto.canvas_h*float(input_video_scale)))])

    utils.delete_files_in_dir(cfg.hugin_projects)
    ## Create projection pto template with one image only
    pto_lines = []
    with open(cfg.projection_pto_path) as f:
        lines = f.read().splitlines()
        first_image_found = False
        for line in lines:
            if line.startswith('i'):
                if not first_image_found:
                    pto_lines.append(line+'\n')
                    first_image_found = True
            else:
                pto_lines.append(line+'\n')
    with open(cfg.projection_pto_tmpl_path, 'w') as f:
        f.writelines(pto_lines)

    ## launch worker processes
    utils.delete_files_in_dir(cfg.frames_projection)
    with Pool(int(cfg.args.num_cpus)) as p:
        p.map(frames_projection_worker, tasks)


def frames_projection_worker(task):
    cfg = config.cfg

    out_img = path.join(cfg.frames_projection, task.img)
    task_pto = path.join(cfg.hugin_projects, task.pto_file)
    run(['pto_gen', '-o', task_pto, path.join(cfg.frames_input, task.img)],
        stderr=DEVNULL, # supress msg about failed reading of EXIF data
        stdout=DEVNULL)
    run(['pto_template', '-o', task_pto, '--template='+cfg.projection_pto_tmpl_path, task_pto],
        stdout=DEVNULL)

    print('Frame: {}'.format(out_img))

    # run(['nona', '-g', '-i', '0', '-m', 'JPEG', '-r', 'ldr', '-z', '99', '-o', out_img, task_pto],
    #     stdout=DEVNULL)
    run(['nona', '-g', '-i', '0', '-m', 'PNG', '-r', 'ldr', '-o', out_img, task_pto],
        stdout=DEVNULL)

    utils.delete_filepath(task_pto)


def create_video_for_vidstab():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    crf = '16'
    ivid = path.join(cfg.frames_projection, '%06d.png')
    output = cfg.input_video

    cropf = str(cfg.params['input_video_filter'])

    cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
           '-c:v', 'libx264', '-crf', crf,
           '-vf', cropf,
           '-loglevel', 'error', '-stats', '-an', '-y', output]

    run(cmd)
