import os
from os import path
import math
import re
from subprocess import run, check_output, DEVNULL
from math import radians as rads
from math import degrees as degs
from glob import glob
import numpy as np
import config
import datatypes


def create_pto_txt_one_image(pto_path):
    cfg = config.cfg
    pto_txt = ''
    first_img_found = False
    with open(pto_path, 'r') as proj_pto:
        for line in proj_pto:
            if line.startswith('#') or not line.strip():
                continue
            if line.startswith('i') and not first_img_found:
                pto_txt += line
                first_img_found = True
            elif not line.startswith('i'):
                pto_txt += line
    return pto_txt


def create_vidstab_projection_pto_file(pto_path):
    ''' Hugin projections:
    0   rectilinear
    1   cylindrical
    2   equirectangular
    3   fisheye (equidistant)
    4   stereographic
    5   mercator
    6   trans mercator
    7   sinusoidal
    8   lambert cylindrical equal area
    9   lambert equal area azimuthal
    10  albers equal area conic
    11  miller cylindrical
    12  panini
    13  architectural
    14  orthographic
    15  equisolid
    16  equirectangular panini
    17  biplane
    18  triplane
    19  panini general
    20  thoby
    21  hammer-aitoff equal area
    '''
    cfg = config.cfg
    pto_txt = create_pto_txt_one_image(cfg.pto.filepath)
    with open(pto_path, 'w') as f:
        f.write(pto_txt)
    projection = cfg.args.vidstab_projection
    run(['pano_modify', '-o', pto_path,
         #'--canvas={}x{}'.format(cfg.pto.canvas_w*3, cfg.pto.canvas_h*3),
         '--crop=AUTO', pto_path, '--projection='+str(projection) ], stdout=DEVNULL)


def create_rectilinear_pto():
    '''rectilinear pto to calculate camera rotations'''
    cfg = config.cfg
    pto_path = cfg.rectilinear_pto_path
    pto_txt = create_pto_txt_one_image(cfg.pto.filepath)
    ## change to rectilinear projection
    pto_txt = re.sub(r'p f[^\n\t ]+', 'p f0 ', pto_txt)
    with open(pto_path, 'w') as f:
        f.write(pto_txt)

    return datatypes.HuginPTO(pto_path)


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


def gauss_filter(fps, transforms_abs, smooth_percent):
        smoothing = round((int(fps)/100)*int(smooth_percent))
        mu = smoothing
        s = mu*2+1

        sigma2 = (mu/2)**2

        kernel = np.exp(-(np.arange(s)-mu)**2/sigma2)

        transforms_filtered = [0]*len(transforms_abs)
        tlen = len(transforms_abs)
        for i in range(tlen):
            ## make a convolution:
            weightsum, avg = 0.0, datatypes.transform(0, 0, 0)
            for k in range(s):
                idx = i+k-mu
                if idx >= 0 and idx < tlen:
                    weightsum += kernel[k]
                    avg = add_transforms(avg, mult_transforms(transforms_abs[idx], kernel[k]))

            if weightsum > 0:
                avg = mult_transforms(avg, 1.0/weightsum)
                ## high frequency must be transformed away
                transforms_filtered[i] = sub_transforms(transforms_abs[i], avg)

        return transforms_filtered
    

def convert_relative_transforms_to_absolute(transforms_rel):
    '''Relative to absolute (integrate transformations)'''
    transforms_abs = [0]*len(transforms_rel)
    transforms_abs[0] = datatypes.transform(0, 0, 0)
    t = transforms_rel[0]
    for i in range(1, len(transforms_rel)):
        transforms_abs[i] = add_transforms(transforms_rel[i], t)
        t = transforms_abs[i]

    return transforms_abs


# def convert_absolute_motions_to_relative(motions_abs):
#     '''Absolute motions to relative'''
#     motions_rel = []
#     motions_abs_r = motions_abs[:]
#     motions_abs_r.reverse()
#     currm = motions_abs_r[0] # last
#     for nextm in motions_abs_r[1:]:
#         motions_rel.append(sub_transforms(currm, nextm))
#         currm = nextm
#     motions_rel.append(datatypes.transform(0, 0, 0))
#     motions_rel.reverse()
#     return motions_rel


def get_global_motions(from_dir, filename='global_motions.trf'):
    cfg = config.cfg

    motions = []
    f = open(path.join(from_dir, filename))

    lines = f.read().splitlines()
    for line in lines:
        if not line[0] == '#':
            data = line.split()
            motions.append(datatypes.transform(float(data[1]), float(data[2]), float(data[3])))

    return motions


def sub_transforms(m1, m2):
    return datatypes.transform(m1.x-m2.x, m1.y-m2.y, m1.roll-m2.roll)


def add_transforms(m1, m2):
    return datatypes.transform(m1.x+m2.x, m1.y+m2.y, m1.roll+m2.roll)


def mult_transforms(t, s):
    return datatypes.transform(t.x*s, t.y*s, t.roll*s)


def get_fps(filepath):
    ''' ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate infile '''

    out = check_output(['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0',
                        '-show_entries', 'stream=r_frame_rate', filepath])
    out = out.strip().split(b'/')
    if len(out) == 1:
        return float(out[0])
    elif len(out) == 2:
        return float(out[0])/float(out[1])

    
def vidstab_projection_frames_need_update(info_dir):
    cfg = config.cfg

    
    pathname_prefix = f'{info_dir}/{cfg.vidstab_projection_prefix}'
    curr_info = f'{pathname_prefix}{cfg.args.vidstab_projection}.info'
    info_files = glob(path.join(info_dir, '*.info'))
    
    if not info_files:
        open(curr_info, 'a').close()
        return True

    if curr_info != info_files[0]:
        for info_file in info_files:
            os.remove(info_file)
        open(curr_info, 'a').close()
        return True

    inp_frames_num = len(os.listdir(cfg.frames_input))
    pjn_frames_num = len(os.listdir(cfg.projection_dir1_frames))
    if pjn_frames_num != inp_frames_num:
        for info_file in info_files:
            os.remove(info_file)
        open(curr_info, 'a').close()
        return True
