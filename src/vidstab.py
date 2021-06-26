import os
from os import path
import sys
from subprocess import run, DEVNULL
import datetime as dt
import utils
import inp_frames
import out_frames


class Vidstab:


    def __init__(self, cfg):
        self.cfg = cfg


    def analyze(self):
        cfg = self.cfg

        trf = 'transforms.trf'
        step = 'stepsize='+str(cfg.args.vs_stepsize)
        mincontrast = float(cfg.args.vs_mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
        filts = detect.format(step, mincontrast, trf)
        show_detect = path.join(cfg.vidstab1_dir, 'show.mkv')

        input_video = path.join(cfg.input_dir, '%06d.jpg')
        cmd = ['ffmpeg', '-r', cfg.fps,
               '-i', input_video, '-c:v', 'libx264',
               '-vf', filts,
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               show_detect]

        print('Analyze cam motions in video (libvidstab)')
        if cfg.args.verbose:
            print(' '.join(cmd))

        s = dt.datetime.now()
        run(cmd, cwd=cfg.vidstab1_dir)
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds())

        ## saves global_motions.trf
        ## was needed before gradient descent impl in py from C
        #self.save_global_motions_trf_file(input_video, cfg.vidstab1_dir)


    def analyze2(self):
        trf = 'transforms.trf'
        cfg = self.cfg

        step = 'stepsize='+str(cfg.args.vs_stepsize)
        mincontrast = float(cfg.args.vs_mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
        filts = detect.format(step, mincontrast, trf)

        input_video = path.join(cfg.frames_processed, '%06d.jpg')

        show_detect = path.join(cfg.vidstab2_dir, 'show.mkv')
        cmd = ['ffmpeg', '-r', cfg.fps,
               '-i', input_video, '-c:v', 'libx264',
               '-vf', filts,
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               show_detect]

        s = dt.datetime.now()
        print('Vidstab analyze corrected frames')
        if cfg.args.verbose:
            print(' '.join(cmd))
            print('FFMPEG output:')
            run(cmd, cwd=cfg.vidstab2_dir)
        else:
            run(cmd, cwd=cfg.vidstab2_dir, stdout=DEVNULL)
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds())

        ## saves global_motions.trf
        ## was needed before gradient descent impl in py from C
        #self.save_global_motions_trf_file(input_video, cfg.vidstab2_dir)


    ## was needed before gradient descent impl in py from C
    # def save_global_motions_trf_file(self, input_video, vidstab_dir):
    #     cfg = self.cfg
    #     trf = 'transforms.trf'
    #     out = path.join(vidstab_dir, 'stabilized.mkv')

    #     crf = '21'
    #     smoothing_percent = int(cfg.args.smoothing)
    #     smoothing = round((int(cfg.fps)/100)*smoothing_percent)
    #     sm = 'smoothing={0}:relative=1'.format(smoothing)
    #     maxangle = 0.6 # radians
    #     f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black:maxangle={}'.\
    #         format(trf, sm, maxangle)

    #     cmd = ['ffmpeg', '-i', input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
    #            '-t', '00:00:00.250',
    #            '-an', '-y',
    #            '-loglevel', 'error',
    #            '-stats',
    #            out]

    #     print("Create global_motions.trf file, libvidstab's result")
    #     if cfg.args.verbose:
    #         print(' '.join(cmd))
    #     run(cmd, cwd=vidstab_dir,
    #         #check=True,
    #         #capture_output=True
    #         )
