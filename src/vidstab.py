from subprocess import run
from os import path
import config
import utils
import datatypes


filt_for_pass_2 = 'crop=floor(iw/2.1)*2:floor(ih/2.1)*2'
filt_for_pass_3 = 'crop=floor(iw/2.2)*2:floor(ih/2.2)*2'
filt_for_pass_4 = 'crop=floor(iw/2.5)*2:floor(ih/2.3)*2'

# filt_for_pass_1 = 'scale=floor(iw/4)*2:floor(ih/4)*2'
# filt_for_pass_2 = 'scale=floor(iw/2)*2:floor(ih/2)*2'

## pixels step size for detect phase in libvidstab
stepsize_pass_1 = 6
stepsize_pass_2 = 4
stepsize_pass_3 = 2
stepsize_pass_4 = 2


def libvidstab_detect():
    print('\n libvidstab_detect() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.args.videofile

    step = 'stepsize='+str(stepsize_pass_1)
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=2'
    detect = detect.format(step, mincontrast, trf)
    filts = detect

    cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
           '-i', inp, '-vf', filts, '-an', '-f', 'null', '-']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir)


def libvidstab_transform():
    print('\n libvidstab_transform() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = cfg.args.videofile
    out = path.join(cfg.vidstab_dir, 'stabilized.mkv')

    crf = '16'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'format=yuv444p'
    f2 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)

    f = "{},{},{}".format(filt_for_pass_2, f1, f2)
    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir)


def libvidstab_detect_pass_2():
    print('\n libvidstab_detect_pass_2() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')

    step = 'stepsize='+str(stepsize_pass_2)
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    filts = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
           '-i', inp, '-vf', filts, '-f', 'null', '-']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir_pass_2)


def libvidstab_transform_pass_2():
    print('\n libvidstab_transform_pass_2() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')
    out = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')

    crf = '16'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv444p'

    time = '00:00:00.150'
    f = "{},{},{}".format(filt_for_pass_3, f1, f2)
    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_2)

    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_2)


def libvidstab_detect_pass_3():
    print('\n libvidstab_detect_pass_3() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')

    step = 'stepsize='+str(stepsize_pass_3)
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    filts = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
           '-i', inp, '-vf', filts, '-f', 'null', '-']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir_pass_3)


def libvidstab_transform_pass_3():
    print('\n libvidstab_transform_pass_3() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')
    out = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')

    crf = '16'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv444p'

    f = "{},{}".format(f1, f2)

    #time = '00:00:00.150'
    # run(['ffmpeg', '-loglevel', 'error', '-stats',
    #      '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
    #     cwd=cfg.vidstab_dir_pass_3)

    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_3)


def libvidstab_detect_pass_4():
    print('\n libvidstab_detect_pass_4() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')

    step = 'stepsize='+str(stepsize_pass_4)
    mincontrast = float(cfg.params['motion_detection_mincontrast'])

    detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
    filts = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
           '-i', inp, '-vf', filts, '-f', 'null', '-']
    print(' '.join(cmd))
    run(cmd, cwd=cfg.vidstab_dir_pass_4)


def libvidstab_transform_pass_4():
    print('\n libvidstab_transform_pass_4() \n')
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')
    out = path.join(cfg.vidstab_dir_pass_4, 'stabilized.mkv')

    crf = '24'
    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv444p'

    time = '00:00:00.150'
    f = "{},{}".format(f1, f2)
    run(['ffmpeg', '-loglevel', 'error', '-stats',
         '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
        cwd=cfg.vidstab_dir_pass_4)


def combine_global_transforms():
    print('\n combine_global_transforms() \n')
    cfg = config.cfg

    first_pass_rel = utils.get_global_motions(cfg.vidstab_dir)
    second_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_2)
    third_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_3)
    forth_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_4)

    combined = []
    for (a, b, c, d) in zip(first_pass_rel, second_pass_rel, third_pass_rel, forth_pass_rel):
        combined.append(datatypes.motion(a.x+b.x+c.x+d.x, a.y+b.y+c.y+d.y,
                                         a.roll+b.roll))

    combined = utils.gauss_filter(utils.convert_relative_motions_to_absolute(combined))

    f = open(cfg.combined_global_motions, 'a')
    f.seek(0)
    f.truncate()
    for cm in combined:
        f.write('0 {} {} {}\n'.format(cm.x, cm.y, cm.roll))
    f.close()













# def libvidstab_detect():
#     print('libvidstab_detect()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     #inp = cfg.args.videofile
#     inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')

#     step = 'stepsize=3'
#     mincontrast = float(cfg.params['motion_detection_mincontrast'])

#     crop = 'crop=(floor(iw/3))*2:floor(ih/2)*2,'
#     detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=2'
#     detect = detect.format(step, mincontrast, trf)
#     filts = crop+detect

#     crf = '21'
#     cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
#            '-i', inp, '-vf', filts, '-c:v', 'libx264', '-crf', crf, '-an', '-y', 'show.mkv']
#     print(' '.join(cmd))
#     run(cmd, cwd=cfg.vidstab_dir)


# def libvidstab_transform():
#     print('libvidstab_transform()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')
#     out = path.join(cfg.vidstab_dir, 'stabilized.mkv')

#     crf = '16'
#     smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
#     sm = 'smoothing={0}:relative=1'.format(smoothing)
#     f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
#     f2 = 'format=yuv444p'

#     f = "crop=((floor(iw/5))*2):(floor(ih/3))*2,{0},{1}".format(f1, f2)
#     run(['ffmpeg', '-loglevel', 'error', '-stats',
#          '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
#         cwd=cfg.vidstab_dir)


# def libvidstab_detect_pass_2():
#     print('libvidstab_detect_pass_2')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')

#     step = 'stepsize=1'
#     mincontrast = float(cfg.params['motion_detection_mincontrast'])

#     detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
#     filts = detect.format(step, mincontrast, trf)

#     cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
#            '-i', inp, '-vf', filts, '-f', 'null', '-']
#     print(' '.join(cmd))
#     run(cmd, cwd=cfg.vidstab_dir_pass_2)


# def libvidstab_transform_pass_2():
#     print('libvidstab_transform_pass_2()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir, 'stabilized.mkv')
#     out = path.join(cfg.vidstab_dir_pass_2, 'stabilized.mkv')

#     crf = '21'
#     smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
#     sm = 'smoothing={0}:relative=1'.format(smoothing)
#     f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
#     f2 = 'format=yuv444p'

#     time = '00:00:00.150'

#     f = "{0},{1}".format(f1, f2)
#     run(['ffmpeg', '-loglevel', 'error', '-stats',
#          '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
#         cwd=cfg.vidstab_dir_pass_2)


# ## for rotation
# def libvidstab_detect_pass_3():
#     print('libvidstab_detect_pass_3()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')

#     step = 'stepsize=4'
#     mincontrast = float(cfg.params['motion_detection_mincontrast'])

#     #crop = 'crop=((floor(iw/2))*2):(floor(ih/2))*2,'
#     #scale = 'scale=floor(iw/1.7):(floor(ih/1.7)),'
#     detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
#     filts = detect.format(step, mincontrast, trf)

#     cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
#            '-i', inp, '-vf', filts, '-f', 'null', '-']
#     print(' '.join(cmd))
#     run(cmd, cwd=cfg.vidstab_dir_pass_3)


# def libvidstab_transform_pass_3():
#     print('libvidstab_transform_pass_3()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir, 'tostabilize.mkv')
#     out = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')

#     crf = '16'
#     smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
#     sm = 'smoothing={0}:relative=1'.format(smoothing)
#     #scale = 'scale=floor(iw/1.5):(floor(ih/1.5)),'
#     f = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)

#     run(['ffmpeg', '-loglevel', 'error', '-stats',
#          '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
#         cwd=cfg.vidstab_dir_pass_3)


# def libvidstab_detect_pass_4():
#     print('libvidstab_detect_pass_4()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')

#     step = 'stepsize=4'
#     mincontrast = float(cfg.params['motion_detection_mincontrast'])

#     detect = 'format=yuv444p,vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}'
#     filts = detect.format(step, mincontrast, trf)

#     cmd = ['ffmpeg', '-loglevel', 'error', '-stats',
#            '-i', inp, '-vf', filts, '-f', 'null', '-']
#     print(' '.join(cmd))
#     run(cmd, cwd=cfg.vidstab_dir_pass_4)


# def libvidstab_transform_pass_4():
#     print('libvidstab_transform_pass_4()')
#     cfg = config.cfg

#     trf = 'transforms.trf'
#     inp = path.join(cfg.vidstab_dir_pass_3, 'stabilized.mkv')
#     out = path.join(cfg.vidstab_dir_pass_4, 'stabilized.mkv')

#     crf = '16'
#     smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
#     sm = 'smoothing={0}:relative=1'.format(smoothing)
#     f = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)

#     time = '00:00:00.150'

#     run(['ffmpeg', '-loglevel', 'error', '-stats',
#          '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-crf', crf, '-an', '-y', out],
#         cwd=cfg.vidstab_dir_pass_4)


# def combine_global_transforms():
#     print('combine_global_transforms()')
#     cfg = config.cfg

#     first_pass_rel = utils.get_global_motions(cfg.vidstab_dir)
#     second_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_2)
#     third_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_3)
#     forth_pass_rel = utils.get_global_motions(cfg.vidstab_dir_pass_4)

#     combined = []
#     # for (a, b, c) in zip(first_pass_rel, second_pass_rel, third_pass_rel):
#     #     combined.append(datatypes.motion(a.x+b.x, a.y+b.y, c.roll))
#     for (a, b, c, d) in zip(first_pass_rel, second_pass_rel, third_pass_rel, forth_pass_rel):
#         combined.append(datatypes.motion(a.x+b.x, a.y+b.y, c.roll+d.roll))

#     combined = utils.gauss_filter(utils.convert_relative_motions_to_absolute(combined))

#     f = open(cfg.combined_global_motions, 'a')
#     f.seek(0)
#     f.truncate()
#     for cm in combined:
#         f.write('0 {} {} {}\n'.format(cm.x, cm.y, cm.roll))
#     f.close()
