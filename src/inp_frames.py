import utils
import datatypes

import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL
import functools
import re


class InFrames():

    prjn_pto_txt: str = ''


    def __init__(self, cfg):
        self.cfg = cfg


    def create_original_frames_and_audio(self):
        '''Creates frame image files from a video'''
        cfg = self.cfg

        ## check if input videofile was modified
        frames_dir = cfg.frames_input
        imgs = sorted(os.listdir(frames_dir))
        if os.path.exists(cfg.args.videofile) and len(imgs) \
           and not cfg.args.force_upd:
            path_img = path.join(frames_dir, imgs[0])
            video_mtime = os.path.getmtime(cfg.args.videofile)
            frame_mtime = os.path.getmtime(path_img)
            if (video_mtime < frame_mtime):
                return

        utils.delete_files_in_dir(cfg.frames_input)

        inp = cfg.args.videofile
        oaud = path.join(cfg.audio_dir, "audio.ogg")

        ## audio
        cmd1 = ['ffmpeg',
                '-loglevel', 'error',
                '-stats',
                '-i', cfg.args.videofile,
                '-vn', '-aq', str(3), '-y', oaud
        ]

        ## video
        cmd2 = ['ffmpeg',
                '-loglevel', 'error',
                '-stats',
                '-i', inp,
                '-qscale:v', '1',
                path.join(cfg.frames_input, '%06d.jpg'), '-y'
        ]

        print(oaud)
        print(cfg.frames_input)
        run(cmd1)
        run(cmd2)


    def create_projection_frames(self, frames_src_dir, frames_dst_dir, hugin_ptos_dir):
        cfg = self.cfg

        if not utils.to_upd_prjn_frames(frames_src_dir, frames_dst_dir, hugin_ptos_dir):
            return

        utils.create_vidstab_projection_pto_file(cfg.projection_pto_path)
        self.prjn_pto_txt = utils.create_pto_txt_one_image(cfg.projection_pto_path)

        imgs = sorted(os.listdir(frames_src_dir))
        tasks = []
        for i, img in enumerate(imgs):
            tasks.append((img,))

        utils.delete_files_in_dir(hugin_ptos_dir)
        utils.delete_files_in_dir(frames_dst_dir)

        with Pool(int(cfg.args.num_cpus)) as p:
            results = [p.apply_async(self.projection_frames_worker,
                                     args=(t, frames_src_dir, frames_dst_dir, hugin_ptos_dir),
                                     callback=self.prjn_worker_callback)
                       for t in tasks]
            self.prjn_frames_total = len(results)
            self.prjn_frames_cnt = 0
            print(f'Create projection frames for vidstab input video, {self.prjn_frames_total} frames total.\n')
            for r in results:
                r.get()
            self.prjn_frames_total = 0
            self.prjn_frames_cnt = 0


    def prjn_worker_callback(self, r):
        self.prjn_frames_cnt += 1
        utils.print_progress(self.prjn_frames_cnt, self.prjn_frames_total, length=80)


    def projection_frames_worker(self, task, frames_src_dir, dest_dir, hugin_ptos_dir):
        img = task[0]

        src_img = path.join(frames_src_dir, img)

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(src_img),
                              self.prjn_pto_txt)

        pto_name = 'prjn_{}.pto'.format(img)
        with open(path.join(hugin_ptos_dir, pto_name), 'w') as f:
            f.write(curr_pto_txt)

        img_name = img.split('.')[:-1]
        out_img = path.join(dest_dir, f'{img_name[0]}.jpg')
        ## run pto render
        task_pto_path = path.join(hugin_ptos_dir, pto_name)
        run(['nona', '-g', '-i', '0', '-r', 'ldr', '-m', 'JPEG', '-z', '100',
             '-o', out_img, task_pto_path],
            stdout=DEVNULL
        )

        return out_img


    def create_input_video_for_vidstab(self, inp_frames_dir, vidstab_dir):
        cfg = self.cfg

        crf = '16'
        ## projection frames are for libvidstab, in JPEG
        ivid = path.join(inp_frames_dir, '%06d.jpg')
        output_file = path.join(vidstab_dir, cfg.prjn_video_name)

        ## check if cached data needs update
        if os.path.exists(output_file):
            imgs = sorted(os.listdir(inp_frames_dir))
            path_img = path.join(inp_frames_dir, imgs[0])
            video_mtime = os.path.getmtime(output_file)
            frame_mtime = os.path.getmtime(path_img)
            if (video_mtime > frame_mtime):
                return output_file

        ## divisable by 2, video size required by libvidstab and other FFMPEG filters
        cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'

        cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               '-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output_file]

        print('Create input video for vidstab')
        print('FFMPEG output:')
        run(cmd)
        print()    

        return output_file
