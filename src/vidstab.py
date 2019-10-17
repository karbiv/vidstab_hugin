from os import path
import sys
from subprocess import run, DEVNULL, check_output
import math
import config
import utils
import datatypes


def detect_1():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.frames_projection_video

    step = 'stepsize='+str(cfg.params['stepsize_pass_1'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    #cropf = 'crop=floor((ih*1.777)/2)*2:floor(ih/2)*2,' # 16x9
    cropf = 'crop=floor((ih*1.333)/2)*2:floor(ih/2)*2,' # 4x3
    #cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2,'
    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=2'
    filts = cropf+detect.format(step, mincontrast, trf)

    # cmd = ['ffmpeg', '-i', inp, '-vf', filts, '-an', '-f', 'null',
    #        '-loglevel', 'error', '-stats', '-']
    cmd = ['ffmpeg', '-i', inp, '-vf', filts, '-an', '-y',
           '-loglevel', 'error', '-stats', '-c:v', 'libx264', '-crf', '24','show.mkv']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir)


def transform_1():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.frames_projection_video
    out = path.join(cfg.vidstab_dir, 'stabilized.mkv')

    crf = '16'
    smoothing_percent = int(cfg.params['smoothing_1'])
    smoothing = round((int(cfg.fps)/100)*smoothing_percent)
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'format=yuv444p'
    f2 = 'vidstabtransform=debug=1:input={0}:interpol=bicubic:{1}:optzoom=0:crop=black'.format(trf, sm)

    # frame_scale = float(cfg.params['first_stage_frame_scale'])
    # divider = round(float((1/frame_scale)*2), 4)
    cropf = 'crop=floor((ih*1.333)/2)*2:floor(ih/2)*2' # 4x3
    #cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'

    f = "{},{},{}".format(cropf, f1, f2)

    #duration = '00:00:00.250'
    cmd = ['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf,
           #'-t', duration,
           '-an', '-y', '-loglevel', 'error', '-stats', out]
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir)


def detect_2():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.out_video_1

    step = 'stepsize='+str(cfg.params['stepsize_pass_1'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    cropf = 'crop=floor((ih*1.333)/2)*2:floor(ih/2)*2,' # 4x3
    #cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2,'
    detect = cropf+'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=2'
    filts = detect.format(step, mincontrast, trf)

    # cmd = ['ffmpeg', '-i', inp, '-vf', filts, '-an', '-f', 'null',
    #        '-loglevel', 'error', '-stats', '-']
    cmd = ['ffmpeg', '-i', inp, '-vf', filts, '-an', '-y',
           '-loglevel', 'error', '-stats', '-c:v', 'libx264', '-crf', '24', 'show.mkv']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir_2)


def transform_2():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.out_video_1
    out = path.join(cfg.vidstab_dir_2, 'stabilized.mkv')

    crf = '16'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing_2']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'format=yuv444p'
    f2 = 'vidstabtransform=debug=1:input={0}:interpol=bicubic:{1}:optzoom=0:crop=black'.format(trf, sm)

    cropf = 'crop=floor((ih*1.333)/2)*2:floor(ih/2)*2' # 4x3
    f = "{},{},{}".format(cropf, f1, f2)

    #duration = '00:00:00.250'
    cmd = ['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf,
           #'-t', duration,
           '-an', '-y', '-loglevel', 'error', '-stats', out]
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir_2)


def combine_global_transforms():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg

    ## get first vidstab stage camera rotations
    f = open(path.join(cfg.output_dir, 'rotations_1.txt'))
    lines = f.read().splitlines()
    rotations_1 = []
    for l in lines:
        rotations_1.append((l.strip().split()))

    # first_rel = utils.get_global_motions(cfg.vidstab_dir)
    # # first_abs_filtered = utils.gauss_filter(utils.convert_relative_motions_to_absolute(first_rel),
    # #                                         cfg.params['smoothing_1'])
        
    second_rel = utils.get_global_motions(cfg.vidstab_dir_2)
    second_abs_filtered = utils.gauss_filter(utils.convert_relative_motions_to_absolute(second_rel),
                                             cfg.params['smoothing_2'])

    # combined_rel = []
    # for a, b in zip(first_rel, second_rel):
    #     combined_rel.append(datatypes.motion(a.x+b.x, a.y+b.y, a.roll+b.roll))
    # combined_abs_filtered = utils.gauss_filter(utils.convert_relative_motions_to_absolute(combined_rel),
    #                                            cfg.params['smoothing_2'])

    pto_projection = datatypes.HuginPTO(cfg.out_1_pto_path)
    horizont_tan = math.tan(math.radians(cfg.pto.canv_half_hfov))
    tan_pix = horizont_tan/(cfg.pto.canvas_w/2)
    combined_rotations = []

    #for i, m in enumerate(first_rel):
    for i, rot in enumerate(rotations_1):
        x, y, roll = second_abs_filtered[i].__dict__.values()
        #x, y, roll = combined_abs_filtered[i].__dict__.values()

        roll = 0-math.degrees(roll)

        ## get original coords from projection
        _coords = '{} {}'.format(pto_projection.canvas_w/2+x, pto_projection.canvas_h/2-y)
        orig_coords = check_output(['pano_trafo', '-r', cfg.out_1_pto_path, '0'],
                                   input=_coords.encode('utf-8')).strip().split()
        ox, oy = float(orig_coords[0]), float(orig_coords[1])

        ## get rectilinear projection coords from original
        _coords = '{} {}'.format(ox, oy)
        rectil_coords = check_output(['pano_trafo', cfg.pto.filepath, '0'],
                                     input=_coords.encode('utf-8')).strip().split()

        rx, ry = float(rectil_coords[0]), float(rectil_coords[1])
        x, y = rx-(cfg.pto.canvas_w/2), (cfg.pto.canvas_h/2)-ry

        yaw_rads = math.atan(x*tan_pix)
        yaw = math.degrees(yaw_rads)

        pitch_rads = math.atan(y*tan_pix)
        pitch = 0-math.degrees(pitch_rads)

        roll = float(rot[0]) + roll
        yaw = float(rot[1]) + yaw
        pitch = float(rot[2]) + pitch

        combined_rotations.append((roll, yaw, pitch))
        print('Combined camera rotations for frame {}: yaw {}, pitch {}'.format(i, yaw, pitch))

    motions_filepath = path.join(cfg.output_dir, 'combined_rotations.txt')
    utils.delete_filepath(motions_filepath)
    f = open(motions_filepath, 'w')
    for cm in combined_rotations:
        f.write('{} {} {}\n'.format(cm[0], cm[1], cm[2]))
    f.close()
