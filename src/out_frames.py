import os
from os import path
import sys
import hugin
from multiprocessing import Pool
from subprocess import run, DEVNULL, check_output
import math
import re
import datatypes
import utils
import functools

import numpy as np
import skimage.transform as sktf
from skimage import io as skio
from skimage.util import img_as_ubyte

#import timeit as tt


def camera_rotations_wrap(instance, arg):
    return instance.camera_rotations_worker(arg)


def camera_rotations_projection_wrap(instance, arg):
    return instance.camera_rotations_projection_worker(arg)


def camera_rotations_processed_wrap(instance, arg):
    return instance.camera_rotations_processed_worker(arg)


class OutFrames:

    pto_txt: str = ''
    rpto: datatypes.HuginPTO = None
    projection_pto: datatypes.HuginPTO = None
    tan_pix: float = 0
    half_hfov: float = 0
    optical_center = None


    def __init__(self, cfg):
        self.cfg = cfg
        self.rpto = utils.create_rectilinear_pto()


    def camera_rotations_projection(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        frames_dir = self.cfg.frames_input
        imgs = sorted(os.listdir(frames_dir))
        self.half_hfov = math.radians(self.rpto.canv_half_hfov)
        horizont_tan = math.tan(self.half_hfov)
        self.tan_pix = horizont_tan/(self.rpto.canvas_w/2)

        transforms_rel = utils.get_global_motions(self.cfg.vidstab_projection_dir)
        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = self.gauss_filter(transforms_abs, self.cfg.args.smoothing)

        ## set center coords to lens' optical axis
        path_img = path.join(frames_dir, imgs[0])
        sk_img = skio.imread(path_img, plugin='pil')
        cx, cy = np.array(sk_img.shape)[:2][::-1] / 2
        self.optical_center = cx+self.cfg.pto.lens_d, cy+self.cfg.pto.lens_e

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(frames_dir, imgs[i])
            tasks.append((t[0], path_img, t[1]))

        self.pto_txt = utils.create_pto_txt_one_image(self.cfg.pto.filepath)
        self.projection_pto = datatypes.HuginPTO(self.cfg.projection_pto_path)

        utils.delete_files_in_dir(self.cfg.hugin_projects)
        utils.delete_files_in_dir(self.cfg.frames_input_processed)
        frames_worker = functools.partial(camera_rotations_projection_wrap, self)
        with Pool(int(self.cfg.args.num_cpus)) as p:
            print('Frames camera rotations:')
            p.map(frames_worker, tasks)


    def camera_rotations_projection_worker(self, task):
        t, img, t_rel = task[0], task[1], task[2]

        ## get original coords from projection
        projection_coords = '{} {}'.format(self.projection_pto.canvas_w/2 + t.x,
                                           self.projection_pto.canvas_h/2 - t.y)
        orig_coords = check_output(['pano_trafo', '-r', self.cfg.projection_pto_path, '0'],
                                   input=projection_coords.encode('utf-8'))
        # _ox, _oy = orig_coords.strip().split()
        # ox, oy = float(_ox)+self.cfg.pto.lens_d, float(_oy)-self.cfg.pto.lens_e
        # orig_coords = f'{ox} {oy}'.encode('utf-8')
        ## get rectilinear coords from original
        rcoords = check_output(['pano_trafo', self.rpto.filepath, '0'], input=orig_coords).strip().split()

        x, y = float(rcoords[0])-(self.rpto.canvas_w/2), (self.rpto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))
        dest_img = img

        if float(self.cfg.args.xy_lines) > 0 or \
           float(self.cfg.args.roll_lines) > 0:
            #### Rolling Shutter start
            sk_img = skio.imread(img, plugin='pil')
            projection_coords = '{} {}'.format(self.projection_pto.canvas_w/2+t_rel.x,
                                               self.projection_pto.canvas_h/2-t_rel.y)
            orig_coords = check_output(['pano_trafo', '-r', self.cfg.projection_pto_path, '0'],
                                       input=projection_coords.encode('utf-8'))
            tx, ty = orig_coords.strip().split()
            orig_tx, orig_ty = float(tx) - self.cfg.pto.orig_w/2, self.cfg.pto.orig_h/2 - float(ty)
            warp_args = {'roll': t_rel.roll, 'y_move': orig_ty, 'along_move': orig_tx}
            interpolation = int(self.cfg.args.rolling_shutter_interpolation)
            modified = sktf.warp(sk_img, self.rolling_shutter_mappings, map_args=warp_args, order=interpolation)
            # def test(): sktf.warp(sk_img, self.rolling_shutter_mappings, map_args=warp_args, order=interpolation)
            # print(tt.timeit(test, number=1))

            dest_img = path.join(self.cfg.frames_input_processed, path.basename(img))
            if self.cfg.is_jpeg:
                skio.imsave(dest_img, img_as_ubyte(modified), quality=self.cfg.jpeg_quality)
            else:
                skio.imsave(dest_img, img_as_ubyte(modified), plugin='pil')
            #### Rolling Shutter end

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
        curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

        ### Write PTO project file for this frame
        filepath = '{}.pto'.format(path.basename(dest_img))
        with open(path.join(self.cfg.hugin_projects, filepath), 'w') as f:
            f.write(curr_pto_txt)

        print(path.join(self.cfg.hugin_projects, filepath))


    def rolling_shutter_mappings(self, xy, **kwargs):
        '''Inverse map function'''
        #num_lines = 1080
        num_lines = self.cfg.pto.orig_h

        #### ACROSS and ALONG lines
        if float(self.cfg.args.xy_lines) > 0:
            last_line_across = kwargs['y_move'] * float(self.cfg.args.xy_lines)
            across_delta = last_line_across / num_lines
            across_line_shift = 0

            last_line_along = kwargs['along_move'] * float(self.cfg.args.xy_lines)
            along_delta = last_line_along / num_lines
            along_line_shift = 0

            #for i in range(num_lines):
            for i in reversed(range(num_lines)): # bottom-up
                ## across
                y = xy[i::num_lines, 1]
                xy[i::num_lines, 1] = y + across_line_shift
                across_line_shift += across_delta

                ## along
                x = xy[i::num_lines, 0]
                xy[i::num_lines, 0] = x + along_line_shift
                along_line_shift += along_delta

        #### ROLL lines
        if float(self.cfg.args.roll_lines) > 0:

            ## Roll is in degrees
            roll_coeff = float(self.cfg.args.roll_lines)
            last_line_roll = kwargs['roll'] * roll_coeff
            roll_delta = last_line_roll / num_lines

            x0, y0 = self.optical_center
            x, y = xy.T
            cx, cy = x-x0, y-y0

            theta = 0
            cxy = np.column_stack((cx, cy))

            #for i in range(num_lines):
            for i in reversed(range(num_lines)):
                x, y = cxy[i::num_lines].T
                ox = math.cos(theta)*x - math.sin(theta)*y
                oy = math.sin(theta)*x + math.cos(theta)*y
                cxy[i::num_lines] = np.dstack((ox, oy)).squeeze()
                theta -= roll_delta

            xy = cxy+self.optical_center

        return xy


    def camera_rotations_processed(self, vidstab_dir):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        frames_dir = self.cfg.frames_input_processed
        imgs = sorted(os.listdir(frames_dir))
        self.half_hfov = math.radians(self.rpto.canv_half_hfov)
        horizont_tan = math.tan(self.half_hfov)
        self.tan_pix = horizont_tan/(self.rpto.canvas_w/2)

        transforms_rel = utils.get_global_motions(vidstab_dir)
        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = self.gauss_filter(transforms_abs, self.cfg.args.smoothing)

        self.pto_txt = utils.create_pto_txt_one_image(self.cfg.pto.filepath)

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(frames_dir, imgs[i])
            tasks.append((t[0], path_img, t[1]))

        utils.delete_files_in_dir(self.cfg.hugin_projects)
        frames_worker = functools.partial(camera_rotations_processed_wrap, self)
        with Pool(int(self.cfg.args.num_cpus)) as p:
            print('\nStart processes pool for creation of tasks.')
            print('Frames camera rotations:')
            p.map(frames_worker, tasks)


    def camera_rotations_processed_worker(self, task):
        t, img = task[0], task[1]

        ## without input projection video
        orig_coords = '{} {}'.format(self.cfg.pto.orig_w/2+t.x+self.cfg.pto.lens_d,
                                     self.cfg.pto.orig_h/2-t.y+self.cfg.pto.lens_e)
        rcoords = check_output(['pano_trafo', self.rpto.filepath, '0'], input=orig_coords.encode('utf-8')).strip().split()

        x, y = float(rcoords[0])-(self.rpto.canvas_w/2), (self.rpto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))
        dest_img = path.join(self.cfg.frames_input_processed, path.basename(img))

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
        curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

        ### Write PTO project file for this frame
        filepath = '{}.pto'.format(path.basename(dest_img))
        with open(path.join(self.cfg.hugin_projects, filepath), 'w') as f:
            f.write(curr_pto_txt)

        print(path.join(self.cfg.hugin_projects, filepath))


    def frames(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        ptos = sorted(os.listdir(self.cfg.hugin_projects))
        tasks = []
        for i, pto in enumerate(ptos):
            tasks.append(datatypes.hugin_task(str(i+1).zfill(6)+'.'+self.cfg.img_ext, pto))

        utils.delete_files_in_dir(self.cfg.frames_stabilized)
        self.cfg.current_output_path = self.cfg.frames_stabilized
        self.cfg.current_pto_path = self.cfg.pto.filepath
        with Pool(int(self.cfg.args.num_cpus)) as p:
            p.map(hugin.frames_output, tasks)


    def gauss_filter(self, transforms, smooth_percent):
        transforms_copy = transforms.copy()
        smoothing = round((int(self.cfg.fps)/100)*int(smooth_percent))
        mu = smoothing
        s = mu*2+1

        sigma2 = (mu/2)**2

        kernel = np.exp(-(np.arange(s)-mu)**2/sigma2)

        tlen = len(transforms)
        for i in range(tlen):
            ## make a convolution:
            weightsum, avg = 0.0, datatypes.transform(0, 0, 0)
            for k in range(s):
                idx = i+k-mu
                if idx >= 0 and idx < tlen:
                    weightsum += kernel[k]
                    avg = utils.add_transforms(avg, utils.mult_transforms(transforms_copy[idx], kernel[k]))

            if weightsum > 0:
                avg = utils.mult_transforms(avg, 1.0/weightsum)
                ## high frequency must be transformed away
                transforms[i] = utils.sub_transforms(transforms[i], avg)

        return transforms


    def video(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        crf = '14'
        ivid = path.join(self.cfg.frames_stabilized, '%06d.'+self.cfg.img_ext)
        iaud = path.join(self.cfg.audio_dir, 'audio.ogg')

        fps = self.cfg.fps
        xy_lines = self.cfg.args.xy_lines
        roll_lines = self.cfg.args.roll_lines

        if float(xy_lines) > 0 or float(roll_lines) > 0:
            xy = self.cfg.args.xy_lines
            roll = self.cfg.args.roll_lines
            smooth = self.cfg.args.smoothing
            lens_d = self.cfg.pto.lens_d or '0'
            lens_e = self.cfg.pto.lens_e or '0'
            fname = self.cfg.out_video_name
            name = f'xy{xy}_r{roll}_smooth{smooth}_d{lens_d}_e{lens_e}_{fname}'
        else:
            name = self.cfg.out_video
        output = path.join(self.cfg.output_dir, name)

        if path.isfile(iaud):
            cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-i', iaud, '-c:v', 'libx264',
                   '-preset', 'veryfast', '-crf', crf, '-c:a', 'copy',
                   '-loglevel', 'error', '-stats', '-y', output]
        else:
            cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', crf,
                   '-loglevel', 'error', '-stats', '-an', '-y', output]

        run(cmd)


    def out_filter(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        filts = 'crop=iw*0.945:ih*0.945:(iw-(iw*0.945))/2:(ih-(ih*0.945))/2,scale=1920:-1,crop=floor(iw/2)*2:floor(ih/2)*2,format=yuv420p'
        crf = '14'
        ivid = self.cfg.out_video

        if float(self.cfg.args.xy_lines) > 0 or \
           float(self.cfg.args.roll_lines) > 0:
            xy = self.cfg.args.xy_lines
            roll = self.cfg.args.roll_lines
            smooth = self.cfg.args.smoothing
            fname = self.cfg.out_video_filtered_name
            name = f'xy{xy}_r{roll}_smooth{smooth}_{fname}'
        else:
            name = self.cfg.out_video_filtered_name
        print(name)
        output = path.join(self.cfg.output_dir, name)

        cmd = ['ffmpeg', '-i', ivid, '-c:v', 'libx264', '-vf', filts, '-crf', crf,
               '-c:a', 'copy', '-loglevel', 'error', '-stats', '-y', output]

        print('\n', cmd, '\n')

        run(cmd)


    def cleanup(self):
        print('\n {} \n'.format(sys._getframe().f_code.co_name))

        utils.delete_files_in_dir(self.cfg.frames_input)
        utils.delete_files_in_dir(self.cfg.frames_projection)
        utils.delete_files_in_dir(self.cfg.frames_stabilized)
        utils.delete_files_in_dir(self.cfg.hugin_projects)

        utils.delete_filepath(self.cfg.out_video)
