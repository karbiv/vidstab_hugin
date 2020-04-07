import os
from os import path
import sys
from subprocess import run


class Vidstab:


    def __init__(self, cfg):
        self.cfg = cfg


    def analyze(self, vidstab_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'

        input_video = path.join(vidstab_dir, self.cfg.projection_video_name)
        step = 'stepsize='+str(self.cfg.args.stepsize)
        mincontrast = float(self.cfg.args.mincontrast)
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
        self.save_global_motions_trf_file(vidstab_dir)


    def save_global_motions_trf_file(self, vidstab_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'
        out = path.join(vidstab_dir, 'stabilized.mkv')

        input_video = path.join(vidstab_dir, self.cfg.projection_video_name)
        crf = '18'
        smoothing_percent = int(self.cfg.args.smoothing)
        smoothing = round((int(self.cfg.fps)/100)*smoothing_percent)
        sm = 'smoothing={0}:relative=1'.format(smoothing)
        f = 'vidstabtransform=debug=1:input={}:{}:optzoom=0:crop=black'.format(trf, sm)

        cmd = ['ffmpeg', '-i', input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
               '-t', '00:00:00.250',
               '-an', '-y',
               '-loglevel', 'error',
               '-stats',
               out]
        print(' '.join(cmd))
        run(cmd, cwd=vidstab_dir)


    def create_processed_vidstab_input(self, output):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_input_processed, '%06d.'+self.cfg.img_ext)

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
