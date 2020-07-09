import os
from os import path
import sys
from subprocess import run
import utils


class Vidstab:


    def __init__(self, cfg):
        self.cfg = cfg
        #self.input_video = path.join(vidstab_dir, self.cfg.projection_video_name)
        self.input_video = self.cfg.args.videofile


    def analyze(self, vidstab_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'

        global_motions = os.path.join(vidstab_dir, "global_motions.trf")
        imgs = sorted(os.listdir(self.cfg.projection_dir1_frames))
        if os.path.exists(global_motions) \
           and not self.cfg.args.force:
            path_img = path.join(self.cfg.projection_dir1_frames, imgs[0])
            global_motions_mtime = os.path.getmtime(global_motions)
            frame_mtime = os.path.getmtime(path_img)
            if frame_mtime < global_motions_mtime:
                print("Video motions analysis doesn't need to be updated.")
                return

        step = 'stepsize='+str(self.cfg.args.stepsize)
        mincontrast = float(self.cfg.args.mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'
        filts = detect.format(step, mincontrast, trf)

        show_detect = path.join(vidstab_dir, 'show.mkv')
        cmd = ['ffmpeg', '-i', self.input_video, '-c:v', 'libx264', '-crf', '18',
               '-vf', filts,
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               show_detect]

        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)

        ## saves global_motions.trf
        self.save_global_motions_trf_file(vidstab_dir)


    def save_global_motions_trf_file(self, vidstab_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'
        out = path.join(vidstab_dir, 'stabilized.mkv')

        crf = '18'
        smoothing_percent = int(self.cfg.args.smoothing)
        smoothing = round((int(self.cfg.fps)/100)*smoothing_percent)
        sm = 'smoothing={0}:relative=1'.format(smoothing)
        maxangle = 0.6 # radians
        f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black:maxangle={}'.format(trf, sm, maxangle)

        cmd = ['ffmpeg', '-i', self.input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
               '-t', '00:00:00.150',
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               out]
        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)


    def create_processed_vidstab_input(self, output):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_input_processed, '%06d.jpg')

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
