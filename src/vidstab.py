from subprocess import run
from os import path
import config
import utils
import datatypes


def libvidstab_detect():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.args.videofile
    #inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')

    step = 'stepsize='+str(cfg.params['motion_detection_stepsize'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    detect = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-i', inp, '-vf', detect, '-f', 'null', '-']
    print(' '.join(cmd)+'\n')
    run(cmd, cwd=cfg.vidstab_dir)


def libvidstab_transform():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.args.videofile
    #inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')
    out = path.join(cfg.vidstab_dir, 'stabilized.mkv')

    ## min time, for libvidstab to just create global_motions.trf file
    time = '00:00:00.250'
    time = '00:00:30.250'

    crf = '15'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv420p'

    # f = "crop=(floor(iw/2))*2:(floor(ih/2))*2,{0},{1}".format(f1, f2)
    # run(['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
    #     cwd=cfg.vidstab_dir)
    
    f = "crop=((floor(iw/3))*2):(floor(ih/3))*2,{0},{1}".format(f1, f2)
    run(['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir)


def libvidstab_detect_pass_2():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')

    step = 'stepsize='+str(cfg.params['motion_detection_stepsize'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    detect = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-i', inp, '-vf', detect, '-f', 'null', '-']
    print(' '.join(cmd)+'\n')
    run(cmd, cwd=cfg.vidstab_dir_pass_2)


def libvidstab_transform_pass_2():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')
    out = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')

    ## min time, for libvidstab to just create global_motions.trf file
    time = '00:00:00.250'

    crf = '15'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv444p'
    
    # f = "crop=(floor(iw/2))*2:(floor(ih/2))*2,{0},{1}".format(f1, f2)
    # run(['ffmpeg', '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
    #     cwd=cfg.vidstab_dir_pass_2)

    ## crop center
    f = "crop=((floor(iw/3.7))*2):(floor(ih/3.7))*2,{0},{1}".format(f1, f2)
    run(['ffmpeg', '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_2)


def combine_global_transforms():
    cfg = config.cfg

    first_pass_rel = utils.get_global_motions(cfg.vidstab_dir)
    first_pass_abs = utils.convert_relative_motions_to_absolute(first_pass_rel)
    first_pass = utils.gauss_filter(first_pass_abs)
    
    second_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_2)
    second_pass_abs = utils.convert_relative_motions_to_absolute(second_pass_rel)
    second_pass = utils.gauss_filter(second_pass_abs)

    third_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_3)
    third_pass_abs = utils.convert_relative_motions_to_absolute(third_pass_rel)
    third_pass = utils.gauss_filter(third_pass_abs)

    combined = []
    # for (a, b) in zip(first_pass_rel, second_pass_rel):
    #     combined.append(datatypes.motion(a.x+b.x, a.y+b.y, a.roll+b.roll))

    for (a, b, c) in zip(first_pass_rel, second_pass_rel, third_pass_rel):
        combined.append(datatypes.motion(a.x+b.x+c.x, a.y+b.y+c.y, a.roll))

    combined = utils.gauss_filter(utils.convert_relative_motions_to_absolute(combined))

    f = open(cfg.combined_global_motions, 'a')
    f.seek(0)
    f.truncate()
    for cm in combined:
        f.write('0 {} {} {}\n'.format(cm.x, cm.y, cm.roll))
    f.close()


def libvidstab_detect_pass_3():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')

    #step = 'stepsize='+str(cfg.params['motion_detection_stepsize'])
    step = 'stepsize=1'
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    detect = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-i', inp, '-vf', detect, '-f', 'null', '-']
    print(' '.join(cmd)+'\n')
    run(cmd, cwd=cfg.vidstab_dir_pass_3)


def libvidstab_transform_pass_3():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')
    out = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')

    ## min time, for libvidstab to just create global_motions.trf file
    time = '00:00:00.250'

    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv420p'
    f = "crop=(floor(iw/2))*2:(floor(ih/2))*2,{0},{1}".format(f1, f2)
    run(['ffmpeg', '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_3)
