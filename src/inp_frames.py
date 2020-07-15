import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL
import functools
import re
import utils
import datatypes


def input_vidstab_projection_wrap(instance, frames_src_dir,
                                  dest_dir, hugin_projects_dir, task):
    return instance.projection_frames_worker(task, frames_src_dir,
                                             dest_dir, hugin_projects_dir)


class InFrames():

    prjn_pto_txt: str = ''
    prjn_pto: datatypes.HuginPTO = None


    def __init__(self, cfg):
        self.cfg = cfg


    def create_original_frames_and_audio(self):
        '''Creates frame image files from a video'''
        print('\n {} \n'.format(sys._getframe().f_code.co_name))
        
        ## check if input videofile was modified
        frames_dir = self.cfg.frames_input
        imgs = sorted(os.listdir(frames_dir))
        if os.path.exists(self.cfg.args.videofile) and len(imgs) \
           and not self.cfg.args.force_upd:
            path_img = path.join(frames_dir, imgs[0])
            video_mtime = os.path.getmtime(self.cfg.args.videofile)
            frame_mtime = os.path.getmtime(path_img)
            if (video_mtime < frame_mtime):
                print("Input frames don't need to be updated.")
                return
        
        utils.delete_files_in_dir(self.cfg.frames_input)

        inp = self.cfg.args.videofile
        oaud = path.join(self.cfg.audio_dir, "audio.ogg")

        ## audio
        cmd1 = ['ffmpeg',
                '-loglevel', 'error',
                '-stats',
                '-i', self.cfg.args.videofile,
                '-vn', '-aq', str(3), '-y', oaud
        ]

        ## video
        cmd2 = ['ffmpeg',
                '-loglevel', 'error',
                '-stats',
                '-i', inp,
                '-qscale:v', '1',
                path.join(self.cfg.frames_input, '%06d.jpg'), '-y'
        ]

        print(oaud)
        print(self.cfg.frames_input)
        run(cmd1)
        run(cmd2)


    def create_projection_frames(self, frames_src_dir, frames_dst_dir, hugin_projects_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        if not utils.vidstab_projection_frames_need_update(frames_dst_dir.parent):
            print('Projection frames for libvidstab don\'t need to be updated.')
            return
        
        utils.create_vidstab_projection_pto_file(self.cfg.projection_pto_path)
        self.prjn_pto_txt = utils.create_pto_txt_one_image(self.cfg.projection_pto_path)

        imgs = sorted(os.listdir(frames_src_dir))
        tasks = []
        for i, img in enumerate(imgs):
            tasks.append((img,))

        utils.delete_files_in_dir(hugin_projects_dir)
        utils.delete_files_in_dir(frames_dst_dir)
        frames_worker = functools.partial(input_vidstab_projection_wrap, self,
                                          frames_src_dir, frames_dst_dir, hugin_projects_dir)
        with Pool(int(self.cfg.args.num_cpus)) as p:
            p.map(frames_worker, tasks)


    def projection_frames_worker(self, task, frames_src_dir, dest_dir, hugin_projects_dir):
        img = task[0]

        src_img = path.join(frames_src_dir, img)

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(src_img), self.prjn_pto_txt)

        pto_name = 'prjn_{}.pto'.format(img)
        with open(path.join(hugin_projects_dir, pto_name), 'w') as f:
            f.write(curr_pto_txt)

        img_name = img.split('.')[:-1]
        out_img = path.join(dest_dir, f'{img_name[0]}.jpg')
        ## run pto render
        task_pto_path = path.join(hugin_projects_dir, pto_name)
        run(['nona', '-g', '-i', '0', '-r', 'ldr', '-m', 'JPEG', '-z', '100',
             '-o', out_img, task_pto_path],
            stdout=DEVNULL
        )

        print(out_img)


    def create_input_video_for_vidstab(self, inp_frames_dir, vidstab_dir) -> str:
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '16'
        ## projection frames are for libvidstab, in JPEG
        ivid = path.join(inp_frames_dir, '%06d.jpg')
        output_file = path.join(vidstab_dir, self.cfg.projection_video_name)

        ## check if cached data needs update
        if os.path.exists(output_file):
            imgs = sorted(os.listdir(inp_frames_dir))
            path_img = path.join(inp_frames_dir, imgs[0])
            video_mtime = os.path.getmtime(output_file)
            frame_mtime = os.path.getmtime(path_img)
            if (video_mtime > frame_mtime):
                print('Input video for vidstab doesn\'t need to be updated.')
                return output_file
        
        ## divisable by 2, video size required by libvidstab and other FFMPEG filters
        cropf = 'crop=floor(iw/2)*2:floor(ih/2)*2'

        cmd = ['ffmpeg', '-framerate', self.cfg.fps, '-i', ivid,
               '-c:v', 'libx264', '-crf', crf,
               '-vf', cropf,
               '-loglevel', 'error', '-stats', '-an', '-y', output_file]

        run(cmd)

        return output_file
