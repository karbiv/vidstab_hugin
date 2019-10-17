import os
from os import path
import math
from subprocess import run, check_output, DEVNULL
from math import radians as rads
from math import degrees as degs
import numpy as np
import matplotlib.pyplot as plt
import config
from datatypes import *


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


def lens_shift(pto):
    inp_coords = '{} {}'.format(pto.orig_w/2+pto.lens_d,
                                pto.orig_h/2+pto.lens_e)
    ret = check_output(['pano_trafo', pto.filepath, '0'],
                       input=inp_coords.encode('utf-8'))
    ret_coords = ret.strip().split()
    rectilinear_coords = (float(ret_coords[0]), float(ret_coords[1]))
    return rectilinear_coords


def convert_relative_motions_to_absolute(motions_rel):
    '''Relative to absolute (integrate transformations)'''
    motions_abs = []
    currm = motions_rel[0]
    motions_abs.append(currm)
    for nextm in motions_rel[1:]:
        currm = add_motions(currm, nextm)
        motions_abs.append(currm)
    return motions_abs


def convert_absolute_motions_to_relative(motions_abs):
    '''Absolute motions to relative'''
    motions_rel = []
    motions_abs_r = motions_abs[:]
    motions_abs_r.reverse()
    currm = motions_abs_r[0] # last
    for nextm in motions_abs_r[1:]:
        motions_rel.append(sub_motions(currm, nextm))
        currm = nextm
    motions_rel.append(motion(0, 0, 0))
    motions_rel.reverse()
    return motions_rel


def gauss_filter(motions, smooth_percent, graph=False):
    cfg = config.cfg

    motions_copy = motions.copy()
    smoothing = round((int(cfg.fps)/100)*int(smooth_percent))
    mu = smoothing
    s = mu*2+1

    sigma2 = (mu/2)**2
    #sigma2 = (mu)**2

    kernel = np.exp(-(np.arange(s)-mu)**2/sigma2)
    ## higher order Gauss function
    #kernel = np.exp(-((np.arange(s)-mu)**2/sigma2)**2)

    ## dev show Gauss kernel graph
    if graph:
        y_vals = []
        for v in kernel:
            y_vals.append(v)
        xx = np.arange(len(y_vals))
        yy = np.array(y_vals)
        #plt.plot(xx, yy)
        plt.bar(xx, yy)
        plt.show()
        exit()

    mlength = len(motions)
    for i in range(mlength):
        ## make a convolution:
        weightsum, avg = 0.0, motion(0, 0, 0)
        for k in range(s):
            idx = i+k-mu
            if idx >= 0 and idx < mlength:
                weightsum += kernel[k]
                avg = add_motions(avg, mult_motion(motions_copy[idx], kernel[k]))

        if weightsum > 0:
            avg = mult_motion(avg, 1.0/weightsum)
            ## high frequency must be transformed away
            motions[i] = sub_motions(motions[i], avg)

    return motions


def get_global_motions(from_dir, filename='global_motions.trf'):
    cfg = config.cfg

    motions = []
    f = open(path.join(from_dir, filename))
    
    lines = f.read().splitlines()
    for line in lines:
        if not line[0] == '#':
            data = line.split()
            motions.append(motion(float(data[1]), float(data[2]), float(data[3])))

    return motions


def sub_motions(m1, m2):
    return motion(m1.x-m2.x, m1.y-m2.y, m1.roll-m2.roll)


def add_motions(m1, m2):
    return motion(m1.x+m2.x, m1.y+m2.y, m1.roll+m2.roll)


def mult_motion(m, s):
    return motion(m.x*s, m.y*s, m.roll*s)
