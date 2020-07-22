import os
from os import path
import sys
from subprocess import run
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
            inpt_frames.create_projection_frames(cfg.frames_input,
                                                 cfg.prjn_dir1_frames,
                                                 cfg.hugin_projects)
            input_video = inpt_frames.create_input_video_for_vidstab(cfg.prjn_dir1_frames,
                                                                     cfg.prjn_dir1_vidstab_prjn)
            vidstab_dir = cfg.prjn_dir1_vidstab_prjn
            frames_dir = cfg.prjn_dir1_frames
        else:
            input_video = cfg.args.videofile
            vidstab_dir = cfg.prjn_dir1_vidstab_orig
            frames_dir = cfg.frames_input

        global_motions = os.path.join(vidstab_dir, "global_motions.trf")
        imgs = sorted(os.listdir(frames_dir))
        if os.path.exists(global_motions) \
           and not cfg.args.force_upd:
            path_img = path.join(frames_dir, imgs[0])
            global_motions_mtime = os.path.getmtime(global_motions)
            frame_mtime = os.path.getmtime(path_img)
            if frame_mtime < global_motions_mtime:
                return

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

        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)

        ## saves global_motions.trf
        self.save_global_motions_trf_file(input_video, vidstab_dir)


    def analyze2(self):   
        trf = 'transforms.trf'
        cfg = self.cfg

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
            input_video = cfg.args.videofile
            vidstab_dir = cfg.prjn_dir2_vidstab_orig
            frames_dir = cfg.frames_input_processed

        global_motions = os.path.join(vidstab_dir, "global_motions.trf")
        imgs = sorted(os.listdir(frames_dir))
        if os.path.exists(global_motions) \
           and not cfg.args.force_upd:
            path_img = path.join(frames_dir, imgs[0])
            global_motions_mtime = os.path.getmtime(global_motions)
            frame_mtime = os.path.getmtime(path_img)
            if frame_mtime < global_motions_mtime:
                return

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

        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)

        ## saves global_motions.trf
        self.save_global_motions_trf_file(input_video, vidstab_dir)

        return vidstab_dir


    def save_global_motions_trf_file(self, input_video, vidstab_dir):
        trf = 'transforms.trf'
        out = path.join(vidstab_dir, 'stabilized.mkv')

        crf = '18'
        smoothing_percent = int(self.cfg.args.smoothing)
        smoothing = round((int(self.cfg.fps)/100)*smoothing_percent)
        sm = 'smoothing={0}:relative=1'.format(smoothing)
        maxangle = 0.6 # radians
        f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black:maxangle={}'.\
            format(trf, sm, maxangle)

        cmd = ['ffmpeg', '-i', input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
               '-t', '00:00:00.150',
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               out]
        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)


    def create_processed_vidstab_input(self, output):
        print('\n {}'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_input_processed, '%06d.jpg')

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
