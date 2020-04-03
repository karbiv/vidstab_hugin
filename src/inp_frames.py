import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL
import functools
import re
import utils
import datatypes


def input_vidstab_projection_wrap(instance, frames_input_dir, task):
    return instance.frames_input_projection_worker(frames_input_dir, task)


class InFrames():

    prjn_pto_txt: str = ''
    prjn_pto: datatypes.HuginPTO = None


    def __init__(self, cfg):
        self.cfg = cfg


    def input_frames_and_audio(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        utils.delete_files_in_dir(self.cfg.frames_input)

        inp = self.cfg.args.videofile
        oaud = path.join(self.cfg.audio_dir, "audio.ogg")

        ## video
        # cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp, '-qscale:v', '1',
        #         path.join(self.cfg.datapath, self.cfg.frames_input, '%06d.'+self.cfg.img_ext), '-y']
        cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp,
                path.join(self.cfg.datapath, self.cfg.frames_input, '%06d.'+self.cfg.img_ext), '-y']

        ## audio
        cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', self.cfg.args.videofile,
                '-vn', '-aq', str(3), '-y', oaud]

        run(cmd1)
        run(cmd2)


    def input_frames_vidstab_projection(self, frames_input_dir=None):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        utils.create_vidstab_projection_pto_file(self.cfg.projection_pto_path)
        self.prjn_pto_txt = utils.create_pto_txt_one_image(self.cfg.projection_pto_path)

        imgs = sorted(os.listdir(frames_input_dir))
        tasks = []
        for i, img in enumerate(imgs):
            tasks.append((img,))

        utils.delete_files_in_dir(self.cfg.hugin_projects)
        utils.delete_files_in_dir(self.cfg.frames_projection_dir)
        frames_worker = functools.partial(input_vidstab_projection_wrap, self, frames_input_dir)
        with Pool(int(self.cfg.args.num_cpus)) as p:
            p.map(frames_worker, tasks)


    def frames_input_projection_worker(self, frames_input_dir, task):
        img = task[0]
        src_img = path.join(frames_input_dir, img)

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(src_img), self.prjn_pto_txt)

        ### Write PTO project
        pto_name = 'prjn_{}.pto'.format(path.basename(src_img))
        with open(path.join(self.cfg.hugin_projects, pto_name), 'w') as f:
            f.write(curr_pto_txt)

        ## run pto render
        out_img = path.join(self.cfg.frames_projection_dir, img)
        task_pto_path = path.join(self.cfg.hugin_projects, pto_name)
        run(self.cfg.nona_opts + ['-o', out_img, task_pto_path], stdout=DEVNULL)

        print(task_pto_path)


    def create_input_projection_video(self, output):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_projection_dir, '%06d.'+self.cfg.img_ext)

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               #'-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
