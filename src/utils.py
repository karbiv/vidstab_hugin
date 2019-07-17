import os
from os import path
import math
from math import radians as rads
from math import degrees as degs
import config
from datatypes import HuginPTO


def delete_files_in_dir(dir_path):
    for f in os.listdir(dir_path):
        if not f == ".gitignore":
            file_path = path.join(dir_path, f)
            delete_filepath(file_path)


def delete_filepath(file_path):
    try:
        os.unlink(file_path)
    except Exception as e:
        pass


def ff(num):
    '''Make argument divisible by 2(even) and integer.
    Required for FFMPEG sizes.'''
    num = round(num)
    if num % 2:
        return int(num - 1)
    else:
        return int(num)


def degs_to_pix(degrees):
    cfg = config.cfg
    
    fov_tan = math.tan(rads(cfg.pto.half_hfov))
    tan_pix = fov_tan/(cfg.pto.crop_w/2)
    degs_tan = math.tan(rads(degrees))
    return round(degs_tan/tan_pix)


