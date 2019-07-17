from subprocess import run
from os import path
import config
from utils import delete_filepath


def libvidstab_detect():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.datapath, 'vidstab', 'tostabilize.mkv')
    out = path.join(cfg.datapath, 'vidstab', 'stabilized.mkv')

    step = 'stepsize='+str(cfg.params['motion_detection_stepsize'])
    mincontrast = float(cfg.params['motion_detection_mincontrast'])
    detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
    detect = detect.format(step, mincontrast, trf)

    cmd = ['ffmpeg', '-i', inp, '-vf', detect, '-f', 'null', '-']
    print(' '.join(cmd)+'\n')
    run(cmd, cwd=cfg.vidstab_dir)


def libvidstab_transform():
    cfg = config.cfg

    trf = 'transforms.trf'
    inp = path.join(cfg.datapath, 'vidstab', 'tostabilize.mkv')
    out = path.join(cfg.datapath, 'vidstab', 'stabilized.mkv')

    ## min time, for libvidstab to just create global_motions.trf file
    time = '00:00:00.250'

    smoothing = round((int(cfg.fps)/100)*int(cfg.params['smoothing']))
    print(smoothing)
    sm = 'smoothing={0}:relative=1'.format(smoothing)
    f1 = 'vidstabtransform=debug=1:input={0}:interpol=linear:{1}:optzoom=0:crop=black'.format(trf, sm)
    f2 = 'format=yuv420p'
    f = "{0},{1}".format(f1, f2)
    run(['ffmpeg', '-t', time, '-i', inp, '-vf', f, '-c:v', 'libx264', '-an', '-y', out],
        cwd=cfg.vidstab_dir)
