import utils
import datatypes
import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL
import functools
import re
import datetime as dt


class InFrames():

    prjn_pto_txt: str = ''


    def __init__(self, cfg):
        self.cfg = cfg


    def store_input_frames(self):
        '''Creates frame image files from a video'''
        cfg = self.cfg

        utils.delete_files_in_dir(cfg.input_dir)
        inp = cfg.args.videofile

        ## "-src_range", "1", # src is full range, 0-255
        cmd = ['ffmpeg',
               '-loglevel', 'error',
               '-stats',
               '-i', inp,
               "-src_range", "1", # src is full range, 0-255
               "-vsync", "drop",  # important to avoid 1st and 2 frames duplicated
               '-q:v', '1',
               path.join(cfg.input_dir, '%6d.jpg'), '-y'
               ]

        print(f'Store frames of {cfg.args.videofile}')
        #print(cmd)
        s = dt.datetime.now()
        run(cmd, check=True)
        ## important for other code, `utils.print_time'
        cfg.frames_total = len(os.listdir(cfg.input_dir))
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds())

        ## remove first frame, can be a duplicate with the second in some cases
        # imgs = sorted(os.listdir(frames_dir))
        # try:
        #     file_path = path.join(frames_dir, imgs[0])
        #     os.unlink(file_path)
        # except Exception as e:
        #     raise("couldn't delete first frame")


    def prjn_worker_callback(self, r):
        self.prjn_frames_cnt += 1
        utils.print_progress(self.prjn_frames_cnt, self.prjn_frames_total, length=80)


    def projection_frames_worker(self, task, frames_src_dir, dest_dir, hugin_ptos_dir):
        img = task[0]

        src_img = path.join(frames_src_dir, img)

        ## set input image path for frame PTO
        pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(src_img),
                              self.prjn_pto_txt)

        pto_name = 'prjn_{}.pto'.format(img)
        with open(path.join(hugin_ptos_dir, pto_name), 'w') as f:
            f.write(pto_txt)

        img_name = img.split('.')[:-1]
        out_img = path.join(dest_dir, f'{img_name[0]}.jpg')
        ## run pto render
        task_pto_path = path.join(hugin_ptos_dir, pto_name)
        run(['nona', '-g', '-i', '0', '-r', 'ldr', '-m', 'JPEG', '-z', '100',
             '-o', out_img, task_pto_path],
            stdout=DEVNULL
        )

        return out_img
