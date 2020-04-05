import os
from os import path
import sys
from subprocess import run


class Vidstab:


    def __init__(self, cfg):
        self.cfg = cfg


    def analyze(self, dest):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'

        step = 'stepsize='+str(self.cfg.args.stepsize)
        mincontrast = float(self.cfg.args.mincontrast)
        detect = 'vidstabdetect=shakiness=10:accuracy=15:{0}:mincontrast={1}:result={2}:show=1'

        #cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'
        #filts = '{},{}'.format(cropf, detect.format(step, mincontrast, trf))
        filts = detect.format(step, mincontrast, trf)

        show_detect = path.join(dest, 'show.mkv')
        cmd = ['ffmpeg', '-i', input_video, '-c:v', 'libx264', '-crf', '18',
               '-vf', filts,
               '-an', '-y', '-loglevel', 'error', '-stats', show_detect]

        num_frames = len(os.listdir(self.cfg.frames_projection_dir))
        print('Total frames: {}'.format(num_frames))

        print(' '.join(cmd))
        run(cmd, cwd=dest)

        ## saves global_motions.trf
        self.transform(dest)


    def transform(self, dest):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        trf = 'transforms.trf'
        #dest = self.cfg.vidstab_projection_dir
        out = os.path.join(dest, 'stabilized.mkv')

        crf = '18'
        smoothing_percent = int(self.cfg.args.smoothing)
        smoothing = round((int(self.cfg.fps)/100)*smoothing_percent)
        sm = 'smoothing={0}:relative=1'.format(smoothing)
        #cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'
        #f = '{},vidstabtransform=debug=0:input={}:{}:optzoom=0:crop=black'.format(cropf, trf, sm)
        f = 'vidstabtransform=debug=0:input={}:{}:optzoom=0:crop=black'.format(trf, sm)

        cmd = ['ffmpeg', '-i', input_video, '-vf', f, '-c:v', 'libx264', '-crf', crf,
               '-t', '00:00:00.250',
               '-an', '-y', '-stats', out]
        print(' '.join(cmd))
        run(cmd, cwd=dest)


    def create_processed_vidstab_input(self, output):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_input_processed, '%06d.'+self.cfg.img_ext)

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
