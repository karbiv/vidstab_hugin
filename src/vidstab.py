import os
from os import path
import sys
from subprocess import run, DEVNULL
import utils
import inp_frames
import out_frames


class Vidstab:


    def __init__(self, cfg):
        self.cfg = cfg


    def analyze(self):
        trf = 'transforms.trf'
        cfg = self.cfg

        if cfg.args.vidstab_prjn > -1:
            inpt_frames = inp_frames.InFrames(cfg)
            inpt_frames.create_projection_frames(cfg.input_dir,
                                                 cfg.prjn_dir1_frames,
                                                 cfg.hugin_projects)
            input_video = inpt_frames.create_input_video_for_vidstab(cfg.prjn_dir1_frames,
                                                                     cfg.prjn_dir1_vidstab_prjn)
            vidstab_dir = cfg.prjn_dir1_vidstab_prjn
            frames_dir = cfg.prjn_dir1_frames
        else:
            input_video = cfg.args.videofile
            vidstab_dir = cfg.prjn_dir1_vidstab_orig
            frames_dir = cfg.input_dir

        if not utils.to_upd_analyze(vidstab_dir, frames_dir):
            return

        step = 'stepsize='+str(cfg.args.vs_stepsize)
        mincontrast = float(cfg.args.vs_mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
        filts = detect.format(step, mincontrast, trf)

        show_detect = path.join(vidstab_dir, 'show.mkv')
        #skip_first = "select='gte(n,0)',"
        cmd = ['ffmpeg', '-i', input_video, '-c:v', 'libx264', '-crf', '18',
               '-vf', filts,
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               show_detect]

        print('Analyze cam motions in video (libvidstab)')
        if cfg.args.verbose:
            print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)
        print()

        ## saves global_motions.trf
        ## was needed before gradient descent impl in py from C
        #self.save_global_motions_trf_file(input_video, vidstab_dir)


    def analyze2(self):
        trf = 'transforms.trf'
        cfg = self.cfg

        if not utils.args_rolling_shutter():
            return

        if cfg.args.vidstab_prjn > -1:
            inpt_frames = inp_frames.InFrames(cfg)
            inpt_frames.create_projection_frames(cfg.frames_input_processed,
                                                 cfg.prjn_dir2_frames,
                                                 cfg.hugin_projects_processed)
            input_video = inpt_frames.create_input_video_for_vidstab(cfg.prjn_dir2_frames,
                                                                     cfg.prjn_dir2_vidstab_prjn)
            vidstab_dir = cfg.prjn_dir2_vidstab_prjn
            frames_dir = cfg.prjn_dir2_frames
        else:
            input_video = cfg.input_processed_video_path
            vidstab_dir = cfg.prjn_dir2_vidstab_orig
            frames_dir = cfg.frames_input_processed

        if not utils.to_upd_analyze(vidstab_dir, frames_dir):
            return

        if utils.args_rolling_shutter():
            self.create_processed_vidstab_input(cfg.input_processed_video_path)

        step = 'stepsize='+str(cfg.args.vs_stepsize)
        mincontrast = float(cfg.args.vs_mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
        filts = detect.format(step, mincontrast, trf)

        show_detect = path.join(vidstab_dir, 'show.mkv')
        cmd = ['ffmpeg', '-i', input_video, '-c:v', 'libx264', '-crf', '18',
               '-vf', filts,
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               show_detect]

        print('Vidstab analyze video after rolling shutter correction')
        if cfg.args.verbose:
            print(' '.join(cmd))
            print('FFMPEG output:')
            run(cmd, cwd=vidstab_dir)
        else:
            run(cmd, cwd=vidstab_dir, stdout=DEVNULL)
        print()

        ## saves global_motions.trf
        ## was needed before gradient descent impl in py from C
        #self.save_global_motions_trf_file(input_video, vidstab_dir)


    ## was needed before gradient descent impl in py from C
    def save_global_motions_trf_file(self, input_video, vidstab_dir):
        cfg = self.cfg
        trf = 'transforms.trf'
        out = path.join(vidstab_dir, 'stabilized.mkv')

        crf = '21'
        smoothing_percent = int(cfg.args.smoothing)
        smoothing = round((int(cfg.fps)/100)*smoothing_percent)
        sm = 'smoothing={0}:relative=1'.format(smoothing)
        maxangle = 0.6 # radians
        f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black:maxangle={}'.\
            format(trf, sm, maxangle)

        cmd = ['ffmpeg', '-i', input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
               '-t', '00:00:00.250',
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               out]

        print("Create global_motions.trf file, libvidstab's result")
        if cfg.args.verbose:
            print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir,
            #check=True,
            #capture_output=True
            )


    def create_processed_vidstab_input(self, output):
        print("Create corrected 'rolling shutter' video for vidstab")

        crf = '16'
        ivid = path.join(self.cfg.frames_input_processed, '%06d.jpg')

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
