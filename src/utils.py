import os
from os import path
import math
from subprocess import run, check_output, DEVNULL
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


def lens_shift():
    cfg = config.cfg

    inp_coords = '{} {}'.format(round(cfg.pto.orig_w/2+cfg.pto.lens_d),
                                round(cfg.pto.orig_h/2+cfg.pto.lens_e))
    ret = check_output(['pano_trafo', cfg.pto.filepath, '0'],
                       input=inp_coords.encode('utf-8'))
    ret_coords = ret.strip().split()
    rectilinear_coords = (round(float(ret_coords[0])), round(float(ret_coords[1])))
    return rectilinear_coords


def projection_to_original_coord(x, y, lens_center_x, lens_center_y):
    cfg = config.cfg

    filename = 'pixel_to_angle.pto'
    project_pto = cfg.pto.filepath # rectilinear
    tmp_pto = path.join(cfg.hugin_projects, filename)
    run(['pto_gen', '-o', tmp_pto, path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
        stderr=DEVNULL, stdout=DEVNULL)
    run(['pto_template', '-o', tmp_pto, '--template='+project_pto, tmp_pto],
        stdout=DEVNULL)

    ## set stabdetect projection
    run(['pano_modify', '-o', tmp_pto, '--crop=AUTO',
         '--projection='+cfg.params['stabdetect_projection'], tmp_pto], stdout=DEVNULL)

    ## get pix coord in original
    projection_coords = '{} {}'.format(cfg.pto.canvas_w/2+x, cfg.pto.canvas_h/2-y)
    ret = check_output(['pano_trafo', '-r', tmp_pto, '0'],
                       input=projection_coords.encode('utf-8'))
    ret_coords = ret.strip().split()
    inp_coords = (round(float(ret_coords[0])), round(float(ret_coords[1])))

    ## get pix coord in rectilinear projection
    inp_coords = '{} {}'.format(*inp_coords)
    ret = check_output(['pano_trafo', cfg.pto.filepath, '0'],
                       input=projection_coords.encode('utf-8'))
    ret_coords = ret.strip().split()
    rectilinear_coords = (round(float(ret_coords[0])), round(float(ret_coords[1])))
    

    proj_crop_x = lens_center_x-cfg.pto.crop_l
    proj_crop_y = lens_center_y-cfg.pto.crop_t
    half_crop_w = round(cfg.pto.crop_w/2)
    half_crop_h = round(cfg.pto.crop_h/2)
    delta_x = proj_crop_x-half_crop_w
    delta_y = proj_crop_y-half_crop_h

    left_tan = tan(radians(float(cfg.params['left_fov'])))
    right_tan = tan(radians(float(cfg.params['right_fov'])))
    up_tan = tan(radians(float(cfg.params['up_fov'])))
    down_tan = tan(radians(float(cfg.params['down_fov'])))

    left_pix = half_crop_w + delta_x
    right_pix = half_crop_w - delta_x
    up_pix = half_crop_h + delta_y
    down_pix = half_crop_h - delta_y

    left_tan_pix = left_tan/left_pix
    right_tan_pix = right_tan/right_pix


    if x < 0:
        yaw_rads = atan(x*left_tan_pix)
    else:
        yaw_rads = atan(x*right_tan_pix)

    if y < 0:
        pitch_rads = atan(y*up_tan_pix)
    else:
        pitch_rads = atan(y*down_tan_pix)
