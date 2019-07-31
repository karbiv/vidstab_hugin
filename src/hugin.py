## uses Hugin Panorama Stitcher project template file

import os
from os import path
from math import tan, atan, radians, degrees
from subprocess import run, DEVNULL
from multiprocessing import Queue
import config
from utils import *
from datatypes import HuginPTO

'''
Some Hugin projections are supported only by CPU mode, no GPU:
BIPLANE, TRIPLANE, PANINI, EQUI_PANINI, GENERAL_PANINI
'''

frame_crop_widths = None
frame_crop_heights = None
frames_crop_q: Queue = None


def frames_output(task):
    '''pto is a file extension of Hugin project files'''
    cfg = config.cfg

    out_img = path.join(cfg.frames_stabilized, task.img)
    task_pto = path.join(cfg.hugin_projects, task.pto_file)
    run(['pto_gen', '-o', task_pto, path.join(cfg.frames_in, task.img)],
        stderr=DEVNULL, # supress msg about failed reading of EXIF data
        stdout=DEVNULL)
    run(['pto_template', '-o', task_pto, '--template='+cfg.pto.filepath, task_pto],
        stdout=DEVNULL)

    ## set projection
    run(['pano_modify', '--output='+task_pto, '--crop=AUTO',
         '--projection='+str(cfg.params['output_projection']), task_pto],
        stdout=DEVNULL)

    ## camera Euler rotations
    ## interpolation index 0 is bicubic
    run(['pano_modify', '--output='+task_pto,
         '--rotate={0},{1},{2}'.format(task.yaw, task.pitch, task.roll), task_pto],
        stdout=DEVNULL)

    print('Frame: ', out_img)

    ## '-g' option, GPU, for Nona to be able to run in parallel in processes
    run(['nona', '-g', '-i', '0', '-m', 'JPEG', '-r', 'ldr', '-z', '95', '-o', out_img, task_pto],
        stdout=DEVNULL)

    ## Apply crop to a pto
    run(['pano_modify', '-o', task_pto, '--crop=AUTO', task_pto], stdout=DEVNULL)
    tmp_hugp = HuginPTO(task_pto)
    frames_crop_q.put((tmp_hugp.crop_l, tmp_hugp.crop_r,
                       tmp_hugp.crop_t, tmp_hugp.crop_b), True)

    delete_filepath(task_pto)


def collect_frame_crop_data(crop_queue, base_pto):
    '''Crop doesn't require sorting, save directly to a file.'''
    cfg = config.cfg
    out_file = cfg.crops_file
    
    with open(out_file, 'a') as f:
        f.seek(0)
        f.truncate()
        half_crop_w = base_pto.crop_w/2
        half_crop_h = base_pto.crop_h/2
        while True:
            crops = crop_queue.get(True)
            if not crops:
                break
            pad_l = max(crops[0]-base_pto.crop_l, 0)
            pad_r = max(base_pto.crop_r-crops[1], 0)
            pad_w = max(pad_l, pad_r)

            pad_t = max(crops[2]-base_pto.crop_t, 0)
            pad_b = max(base_pto.crop_b-crops[3], 0)
            pad_h = max(pad_t, pad_b)

            crop_w = round((half_crop_w-pad_w)*2)
            crop_h = round((half_crop_h-pad_h)*2)

            f.write('{0} {1}\n'.format(crop_w, crop_h))
