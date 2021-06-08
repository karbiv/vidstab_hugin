import os
from os import path
import math
import re
from subprocess import run, check_output, DEVNULL
from math import radians as rads
from math import degrees as degs
import numpy as np
import config
import datatypes
import random

from dataclasses import dataclass
import typing
import statistics as stats
from array import array


def print_time(secs, fps=False, prefix=None):
    cfg = config.cfg
    round_secs = round(secs, 3)

    if round_secs < 60:
        time = f"{round_secs}"
    else:
        mins = int(round_secs // 60)
        subsecs = round(round_secs % 60, 3)
        time = f"{mins}:{subsecs}"

    if not prefix:
        prefix = 'time:'

    if fps:
        fps = round(cfg.frames_total / (secs + 0.0001), 1)
        print(f"{prefix} {time};  fps {fps};")
    else:
        print(f"{prefix} {time};")


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
            elif not line.startswith(('i', 'v', 'c')):
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
        projection = cfg.args.vidstab_prjn
        run(['pano_modify', '-o', pto_path,
             #'--canvas={}x{}'.format(cfg.pto.canvas_w*3, cfg.pto.canvas_h*3),
         '--crop=AUTO', pto_path, '--projection='+str(projection) ], stdout=DEVNULL)


def create_rectilinear_pto():
    '''rectilinear pto to calculate camera rotations'''
    cfg = config.cfg

    pto_path = cfg.rectilinear_pto_path
    pto_txt = create_pto_txt_one_image(cfg.pto.filepath)

    ## change to rectilinear projection
    pto_txt = re.sub(r'p f[^\n\t ]+', 'p f0', pto_txt)

    ## set horizontal view angle, otherwise rectilinear canvas too small
    horiz_canvas = int(round(cfg.pto.frame_half_hfov))*2
    hmargins = (horiz_canvas/100)*17
    pto_txt = re.sub(r' v[^\n\t ]+', r' v'+str(horiz_canvas+hmargins),
                     pto_txt, count=1)

    with open(pto_path, 'w') as f:
        f.write(pto_txt)

    return datatypes.HuginPTO(pto_path)
#return datatypes.HuginPTO(cfg.rectilinear_pto_path)


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


def get_global_motions(f):
    cfg = config.cfg

    motions = []

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


def to_upd_prjn_frames(frames_src_dir, frames_dst_dir, hugin_ptos_dir):
    cfg = config.cfg

    if cfg.args.vidstab_prjn != cfg.prev_args.vidstab_prjn:
        return True

    src_frames = os.listdir(frames_src_dir)
    if not src_frames:
        return True
    dst_frames = os.listdir(frames_dst_dir)
    if len(dst_frames) != len(src_frames):
        return True

    ptos = os.listdir(hugin_ptos_dir)
    pto_0 = path.join(hugin_ptos_dir, ptos[0])
    frame_0 = path.join(frames_src_dir, src_frames[0])
    frame_mtime = os.path.getmtime(frame_0)
    pto_mtime = os.path.getmtime(pto_0)
    if pto_mtime < frame_mtime:
        return True

    return False


def rolling_shutter_args_changed():
    cfg = config.cfg
    
    if cfg.args.rs_along != cfg.prev_args.rs_along \
       or cfg.args.rs_across != cfg.prev_args.rs_across \
           or cfg.args.rs_roll != cfg.prev_args.rs_roll \
               or cfg.args.rs_scan_up != cfg.prev_args.rs_scan_up:
        return True

    return False


def args_rolling_shutter():
    cfg = config.cfg

    if float(cfg.args.rs_along) > 0 \
       or float(cfg.args.rs_across) > 0 \
       or float(cfg.args.rs_roll) > 0:
        return True
    return False


def to_upd_camera_rotations_processed(vidstab_dir):
    cfg = config.cfg

    if not args_rolling_shutter():
        return False

    if cfg.args.force_upd:
        return True

    if cfg.args.smoothing != cfg.prev_args.smoothing:
        return True

    pto_files = sorted(os.listdir(cfg.hugin_projects_processed))
    num_inp_frames = len(os.listdir(cfg.frames_input_processed))
    if not pto_files or len(pto_files) != num_inp_frames:
        return True

    pto_0 = path.join(cfg.hugin_projects_processed, pto_files[0])
    pto_mtime = os.path.getmtime(pto_0)

    # global_motions = os.path.join(vidstab_dir, "global_motions.trf")
    # global_motions_mtime = os.path.getmtime(global_motions)
    # if pto_mtime < global_motions_mtime:
    #     return True

    transforms_trf = os.path.join(vidstab_dir, "transforms.trf")
    transforms_mtime = os.path.getmtime(transforms_trf)
    if pto_mtime < transforms_mtime:
        return True

    main_pto = cfg.args.pto
    main_pto_mtime = os.path.getmtime(main_pto)
    if pto_mtime < main_pto_mtime:
        return True

    return False


def print_progress(iteration, total, prefix = '', suffix = '', decimals = 1,
                   length = 80, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    import sys

    # iteration is zero-based

    percent = ("{0:." + str(decimals) + "f}").format(100 * ((iteration+1) / total))
    filled_length = int(length * (iteration+1) // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'{prefix} |{bar}| {percent}% {suffix}', end='')

    if iteration+1 < total:
        print('\r', end='')
    else:
        print()




@dataclass
class LM:
    vx: int = 0; vy: int = 0; fx: int = 0; fy: int = 0;
    fsize: int = 0; contrast: int = 0; match: int = 0


def parseTransformsTrf(fpath):
    cfg = config.cfg

    f = open(fpath)
    lines = f.read().splitlines()

    ver_line = lines[0]
    match = re.match(r'VID.STAB (.+)', ver_line)
    version = int(match.group(1).strip())
    if version < 1:
        exit("transforms.trf version error")
    if version > 1:
        exit("Version of VID.STAB file too large: got "+version)

    lines = lines[1:]
    trf_frames = []
    for line in lines:
        if not line.strip()[0] == "#":
            match = re.match(r'.*\[(.*)\]', line)
            lm_strs = match.group(1).split(",")
            lms = []
            if len(match.group(1)):
                for lm_str in lm_strs:
                    match = re.match(r'\(LM(.+)\)', lm_str.strip())
                    if match:
                        nums = match.group(1).split()
                        lms.append(LM(int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3]),
                                      int(nums[4]), float(nums[5]), float(nums[6])))

                trf_frames.append(lms)

    print("Compute frame transforms")

    frame_motions = [datatypes.transform(0.0, 0.0, 0.0)]
    for f_cnt, motions in enumerate(trf_frames):

        match_quals = []
        ## calculates means transform to initialise gradient descent
        if motions:
            xsum, ysum = 0.0, 0.0
            for ilm in range(len(motions)):
                match_quals.append(motions[ilm].match)
                xsum += motions[ilm].vx
                ysum += motions[ilm].vy
                t = array("f", [xsum/len(motions), ysum/len(motions), 0])
        else:
            t = array("f", [0.0]*3)

        mu = stats.fmean(match_quals)
        psd = stats.pstdev(match_quals, mu) # population standard distribution

        # first we throw away those fields that match badly (during motion detection)
        # filter fields by match quality
        disableFields(motions, mu, psd, 1.5)

        stepsizes = [0.2, 0.2, 0.00005] # x, y, roll
        residual = [0.0]
        for k in range(3):
            # optimize `t' to minimize transform quality (12 steps per dimension)
            resgd = gradientDescent(t, motions, stepsizes.copy(), residual)

            # now we need to ignore the fields that don't fit well (e.g. moving objects)
            # cut off everything above 1 std. dev. for skewed distributions
            # this will cut off the tail
            # do this only two times (3 gradient optimizations in total)
            if (k == 0 and residual[0] > 0.1) or (k==1 and residual[0] > 20):
                disableFields(motions, mu, psd, 1.0)
                t = resgd
            else:
                break

        frame_motions.append(datatypes.transform(resgd[0], resgd[1], resgd[2]))
        print_progress(f_cnt, len(trf_frames))

    return frame_motions


def disableFields(motions, mu, psd, stddevs):
    ''' Disables those fields whose (miss)quality is high.
    stddevs: x standard deviations to exclude
    '''
    #print(mu, stddevs * psd)
    thresh = mu + stddevs * psd
    for i in range(len(motions)):
        m = motions[i]
        if m and m.match > thresh: motions[i] = False


def gradientDescent(t, motions, stepsizes, residual):

    qual = calcTransformQuality
    dim = 3 # x, y, roll
    threshold = 0.01
    N = 16
    # stepsizes is [0.2, 0.2, 0.00005]

    # initial call
    v = qual(t, motions)

    x = array("f", t)
    i = 0
    while i < N*dim and v > threshold:
        k = i % dim

        x2 = array("f", x)
        if random.randrange(2**16) % 2: h = 1e-6
        else: h = -1e-6

        x2[k] += h
        v2 = qual(x2, motions)

        x2 = array("f", x)
        x2[k] = x[k] + ((v - v2)/h) * stepsizes[k]

        v2 = qual(x2, motions)
        if v2 < v: # lower average error
            x, v = x2, v2
            stepsizes[k] *= 1.2 # increase stepsize (4 successful steps will double it)
        else:
            stepsizes[k] /= 2.0

        i += 1

    residual[0] = v

    return x


def calcTransformQuality(t, motions):
    cfg = config.cfg
    error = 0.0
    tx, ty, roll = t[0], t[1], t[2]

    cos_a, sin_a = math.cos(roll), math.sin(roll)
    c_x, c_y = cfg.pto.orig_w/2, cfg.pto.orig_h/2

    num = 1 # start with 1 to avoid div by zero
    for m in motions:
        if m:
            # fx, fy: middle position of a field
            rx, ry = m.fx - c_x, m.fy - c_y
            vx = ( cos_a*rx + sin_a*ry + c_x + tx) - m.fx
            vy = (-sin_a*rx + cos_a*ry + c_y + ty) - m.fy

            # initial call
            # vx = ( rx + c_x + tx) - m.fx,  = tx
            # vy = ( ry + c_y + ty) - m.fy,  = ty

            # roll pass
            # vx = ( rx + 0.000001*ry + c_x + tx) - m.fx,  = tx
            # vy = ( ry + 0.000001*rx + c_y + ty) - m.fy,  = ty

            error += math.pow(vx-m.vx, 2) + math.pow(vy-m.vy, 2)
            num += 1

    # 1 pixel translation missmatch is roughly (with size 500):
    # roll=0.11 (degree)
    return error/num + abs(roll)/5.0
