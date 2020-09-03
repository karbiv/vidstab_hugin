import os
from os import path
from math import tan, atan, radians, degrees
from subprocess import run, DEVNULL
from multiprocessing import Queue
import config
import utils
from datatypes import HuginPTO

frame_crop_widths = None
frame_crop_heights = None
frames_crop_q: Queue = None


def frames_output(task):
    '''Used by multiprocessing.Pool'''
    cfg = config.cfg

    if utils.args_rolling_shutter():
        hugin_ptos_dir = cfg.hugin_projects_processed
    else:
        hugin_ptos_dir = cfg.hugin_projects
    
    out_img = path.join(cfg.current_output_path, task.img)
    task_pto_path = path.join(hugin_ptos_dir, task.pto_file)

    run(['nona', '-g', '-i', '0', '-r', 'ldr', '-m', 'JPEG', '-z', '100',
         '-o', out_img, task_pto_path], stdout=DEVNULL)

    if frames_crop_q:
        tmp_hugp = HuginPTO(task_pto_path)
        frames_crop_q.put((tmp_hugp.crop_l, tmp_hugp.crop_r,
                           tmp_hugp.crop_t, tmp_hugp.crop_b), True)


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
