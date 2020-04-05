import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL
import functools
import re
import utils
import datatypes


def input_vidstab_projection_wrap(instance, dest_dir, task):
    return instance.projection_frames_worker(task, dest_dir)


class InFrames():

    prjn_pto_txt: str = ''
    prjn_pto: datatypes.HuginPTO = None


    def __init__(self, cfg):
        self.cfg = cfg


    def create_original_frames_and_audio(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        utils.delete_files_in_dir(self.cfg.frames_input)

        inp = self.cfg.args.videofile
        oaud = path.join(self.cfg.audio_dir, "audio.ogg")

        ## video
        # cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp, '-qscale:v', '1',
        #         path.join(self.cfg.datapath, self.cfg.frames_input, '%06d.'+self.cfg.img_ext), '-y']
        cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp,
                path.join(self.cfg.frames_input, '%06d.'+self.cfg.img_ext), '-y']

        ## audio
        cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', self.cfg.args.videofile,
                '-vn', '-aq', str(3), '-y', oaud]

        run(cmd1)
        run(cmd2)


    def create_projection_frames(self, dest_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        utils.create_vidstab_projection_pto_file(self.cfg.projection_pto_path)
        self.prjn_pto_txt = utils.create_pto_txt_one_image(self.cfg.projection_pto_path)

        imgs = sorted(os.listdir(self.cfg.frames_input))
        tasks = []
        for i, img in enumerate(imgs):
            tasks.append((img,))

        utils.delete_files_in_dir(self.cfg.hugin_projects)
        utils.delete_files_in_dir(dest_dir)
        frames_worker = functools.partial(input_vidstab_projection_wrap, self, dest_dir)
        with Pool(int(self.cfg.args.num_cpus)) as p:
            p.map(frames_worker, tasks)


    def projection_frames_worker(self, task, dest_dir):
        img = task[0]
        src_img = path.join(self.cfg.frames_input, img)

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(src_img), self.prjn_pto_txt)

        pto_name = 'prjn_{}.pto'.format(path.basename(src_img))
        with open(path.join(self.cfg.hugin_projects, pto_name), 'w') as f:
            f.write(curr_pto_txt)

        ## run pto render
        out_img = path.join(dest_dir, img)
        task_pto_path = path.join(self.cfg.hugin_projects, pto_name)
        run(self.cfg.nona_opts + ['-o', out_img, task_pto_path], stdout=DEVNULL)

        print(task_pto_path)


    def create_input_video_for_vidstab(self, inp_frames_dir, dest_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(inp_frames_dir, '%06d.'+self.cfg.img_ext)
        output = path.join(dest_dir, self.cfg.projection_video_name)
        ## divisable by 2, video size required by libvidstab
        cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               '-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)
