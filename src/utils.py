import os
from os import path
import math
from subprocess import run, check_output, DEVNULL
from math import radians as rads
from math import degrees as degs
#import matplotlib.pyplot as plt
import config
import datatypes


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

def convert_relative_transforms_to_absolute(transforms_rel):
    '''Relative to absolute (integrate transformations)'''
    transforms_abs = [0]*len(transforms_rel)
    transforms_abs[0] = datatypes.transform(0, 0, 0)
    t = transforms_rel[0]
    for i in range(1, len(transforms_rel)):
        transforms_abs[i] = add_transforms(transforms_rel[i], t)
        t = transforms_abs[i]

    return transforms_abs


def convert_absolute_motions_to_relative(motions_abs):
    '''Absolute motions to relative'''
    motions_rel = []
    motions_abs_r = motions_abs[:]
    motions_abs_r.reverse()
    currm = motions_abs_r[0] # last
    for nextm in motions_abs_r[1:]:
        motions_rel.append(sub_transforms(currm, nextm))
        currm = nextm
    motions_rel.append(datatypes.transform(0, 0, 0))
    motions_rel.reverse()
    return motions_rel


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
