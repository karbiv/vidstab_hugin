import os
from os import path
import sys
from multiprocessing import Pool
from subprocess import run, DEVNULL, check_output
import math
import re
import functools
import numpy as np
import skimage.transform as sktf
from skimage import io as skio
from skimage.util import img_as_ubyte

import hugin
import datatypes
import utils


def camera_rotations_wrap(instance, arg):
    return instance.camera_rotations_worker(arg)


def camera_rotations_projection_wrap(instance, arg):
    return instance.camera_rotations_projection_worker(arg)


def camera_rotations_processed_wrap(instance, arg):
    return instance.camera_rotations_processed_worker(arg)


class OutFrames:

    pto_txt: str = ''
    rectilinear_pto: datatypes.HuginPTO = None
    projection_pto: datatypes.HuginPTO = None
    tan_pix: float = 0
    half_hfov: float = 0
    optical_center = None


    def __init__(self, cfg, rectilinear_pto):
        self.cfg = cfg
        self.rectilinear_pto = rectilinear_pto


    def compute_hugin_camera_rotations(self):
        """if rolling shutter cmd_args, corrects orig frames and
        saves to cfg.frames_input_processed"""
        cfg = self.cfg

        if cfg.args.vidstab_prjn > -1:
            hugin_ptos_dir = cfg.hugin_projects_processed
            vidstab_dir = cfg.prjn_dir1_vidstab_prjn
        else:
            hugin_ptos_dir = cfg.hugin_projects
            vidstab_dir = cfg.prjn_dir1_vidstab_orig

        if not utils.to_upd_camera_rotations(vidstab_dir, hugin_ptos_dir):
            return

        frames_dir = cfg.frames_input
        imgs = sorted(os.listdir(frames_dir))
        self.half_hfov = math.radians(self.rectilinear_pto.canv_half_hfov)
        horizont_tan = math.tan(self.half_hfov)
        self.tan_pix = horizont_tan/(self.rectilinear_pto.canvas_w/2)

        transforms_rel = utils.get_global_motions(vidstab_dir)
        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = utils.gauss_filter(cfg.fps, transforms_abs,
                                                     cfg.args.smoothing)
        ## set center coords to lens' optical axis
        path_img = path.join(frames_dir, imgs[0])
        sk_img = skio.imread(path_img)
        cx, cy = np.array(sk_img.shape)[:2][::-1] / 2
        self.optical_center = cx+cfg.pto.lens_d, cy+cfg.pto.lens_e

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(frames_dir, imgs[i])
            tasks.append((t[0], path_img, t[1]))

        self.pto_txt = utils.create_pto_txt_one_image(cfg.pto.filepath)
        if cfg.args.vidstab_prjn != -1:
            self.projection_pto = datatypes.HuginPTO(cfg.projection_pto_path)

        utils.delete_files_in_dir(hugin_ptos_dir)
        utils.delete_files_in_dir(cfg.frames_input_processed)
        frames_worker = functools.partial(camera_rotations_projection_wrap, self)
        with Pool(int(cfg.args.num_cpus)) as p:
            print('Camera rotations in pto files and rolling shutter correction(if enabled):')
            p.map(frames_worker, tasks)


    def camera_rotations_projection_worker(self, task):
        cfg = self.cfg
        t, img, t_rel = task[0], task[1], task[2]

        if cfg.args.vidstab_prjn > -1:
            hugin_projects_dir = cfg.hugin_projects_processed
        else:
            hugin_projects_dir = cfg.hugin_projects

        if cfg.args.vidstab_prjn == -1:
            orig_coords = '{} {}'.format(cfg.pto.orig_w/2 + t.x, cfg.pto.orig_h/2 - t.y)
            ## get rectilinear coords from original
            rcoords = check_output(['pano_trafo', self.rectilinear_pto.filepath, '0'],
                                   input=orig_coords.encode()).strip().split()
        else:
            ## get original coords from projection
            projection_coords = '{} {}'.format(self.projection_pto.canvas_w/2 + t.x,
                                               self.projection_pto.canvas_h/2 - t.y)
            orig_coords = check_output(['pano_trafo', '-r', cfg.projection_pto_path, '0'],
                                       input=projection_coords.encode('utf-8'))
            ## get rectilinear coords from original
            rcoords = check_output(['pano_trafo', self.rectilinear_pto.filepath, '0'],
                                   input=orig_coords).strip().split()


        x = float(rcoords[0])-(self.rectilinear_pto.canvas_w/2)
        y = (self.rectilinear_pto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))
        dest_img = img

        if utils.args_rolling_shutter():
            #### Rolling Shutter start
            sk_img = skio.imread(img)

            if cfg.args.vidstab_prjn == -1:
                orig_coords = '{} {}'.format(cfg.pto.orig_w/2 + t_rel.x,
                                             cfg.pto.orig_h/2 - t_rel.y)
            else:
                projection_coords = '{} {}'.format(self.projection_pto.canvas_w/2+t_rel.x,
                                                   self.projection_pto.canvas_h/2-t_rel.y)
                orig_coords = check_output(['pano_trafo', '-r', cfg.projection_pto_path, '0'],
                                           input=projection_coords.encode('utf-8'))

            tx, ty = orig_coords.strip().split()
            orig_tx, orig_ty = float(tx) - cfg.pto.orig_w/2, cfg.pto.orig_h/2 - float(ty)
            warp_args = {'roll': t_rel.roll, 'y_move': orig_ty, 'along_move': orig_tx}
            interpolation = int(cfg.args.rs_interpolation)
            modified_orig_frame = sktf.warp(sk_img, self.rolling_shutter_mappings,
                                            map_args=warp_args, order=interpolation)

            ## Save corrected original frame
            dest_img = path.join(cfg.frames_input_processed, path.basename(img))
            ## 100, best quality for JPEG in skimage
            skio.imsave(dest_img, img_as_ubyte(modified_orig_frame), quality=100)
            #### Rolling Shutter end

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
        curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

        ### Write PTO project file for this frame
        filepath = '{}.pto'.format(path.basename(dest_img))
        with open(path.join(hugin_projects_dir, filepath), 'w') as f:
            f.write(curr_pto_txt)

        ## Show progress
        print(path.join(hugin_projects_dir, filepath))


    def rolling_shutter_mappings(self, xy, **kwargs):
        '''Inverse map function'''
        cfg = self.cfg
        num_lines = cfg.pto.orig_h

        if cfg.args.rs_scantop == 0:
            line_idxs = tuple(reversed(range(num_lines)))
        else:
            line_idxs = tuple(range(num_lines))

        #### ACROSS and ALONG lines
        if float(cfg.args.rs_xy) > 0:
            last_line_across = kwargs['y_move'] * float(cfg.args.rs_xy)
            across_delta = last_line_across / num_lines
            across_line_shift = 0

            last_line_along = kwargs['along_move'] * float(cfg.args.rs_xy)
            along_delta = last_line_along / num_lines
            along_line_shift = 0

            for i in line_idxs: # bottom-up
                ## across
                y = xy[i::num_lines, 1]
                xy[i::num_lines, 1] = y + across_line_shift
                across_line_shift += across_delta

                ## along
                x = xy[i::num_lines, 0]
                xy[i::num_lines, 0] = x + along_line_shift
                along_line_shift += along_delta

        #### ROLL lines
        if float(cfg.args.rs_roll) > 0:

            ## Roll is in degrees
            roll_coeff = float(cfg.args.rs_roll)
            last_line_roll = kwargs['roll'] * roll_coeff
            roll_delta = last_line_roll / num_lines

            x0, y0 = self.optical_center
            x, y = xy.T
            cx, cy = x-x0, y-y0

            theta = 0
            cxy = np.column_stack((cx, cy))

            for i in line_idxs:
                x, y = cxy[i::num_lines].T
                ox = math.cos(theta)*x - math.sin(theta)*y
                oy = math.sin(theta)*x + math.cos(theta)*y
                cxy[i::num_lines] = np.dstack((ox, oy)).squeeze()
                theta -= roll_delta

            xy = cxy+self.optical_center

        return xy


    def compute_hugin_camera_rotations_processed(self, vidstab_dir):
        print('\n {}'.format(sys._getframe().f_code.co_name))
        cfg = self.cfg

        ## check if Hugin pto files need to be updated
        to_update = False
        pto_files_dir = cfg.hugin_projects_processed
        pto_files = sorted(os.listdir(pto_files_dir))
        global_motions = os.path.join(vidstab_dir, "global_motions.trf")
        if len(pto_files) and os.path.exists(global_motions) \
           and not cfg.args.force_upd:
            path_pto = path.join(pto_files_dir, pto_files[0])
            frame_pto_mtime = os.path.getmtime(path_pto)
            global_motions_mtime = os.path.getmtime(global_motions)
            if frame_pto_mtime > global_motions_mtime:
                to_update = True
            num_inpt_frames = len(os.listdir(cfg.frames_input))
            num_inpt_frames_processed = len(os.listdir(cfg.frames_input_processed))
            if num_inpt_frames != num_inpt_frames_processed:
                to_update = True
        if not to_update:
            return

        frames_dir = cfg.frames_input_processed
        imgs = sorted(os.listdir(frames_dir))
        self.half_hfov = math.radians(self.rectilinear_pto.canv_half_hfov)
        horizont_tan = math.tan(self.half_hfov)
        self.tan_pix = horizont_tan/(self.rectilinear_pto.canvas_w/2)

        transforms_rel = utils.get_global_motions(vidstab_dir)
        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = utils.gauss_filter(cfg.fps, transforms_abs, cfg.args.smoothing)

        self.pto_txt = utils.create_pto_txt_one_image(cfg.pto.filepath)

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(frames_dir, imgs[i])
            tasks.append((t[0], path_img, t[1]))

        utils.delete_files_in_dir(cfg.hugin_projects_processed)
        frames_worker = functools.partial(camera_rotations_processed_wrap, self)
        with Pool(int(cfg.args.num_cpus)) as p:
            print('\nStart processes pool for creation of tasks.')
            print('Frames camera rotations:')
            p.map(frames_worker, tasks)


    def camera_rotations_processed_worker(self, task):
        cfg = self.cfg
        t, img = task[0], task[1]

        ## without input projection video
        orig_coords = '{} {}'.format(cfg.pto.orig_w/2+t.x+cfg.pto.lens_d,
                                     cfg.pto.orig_h/2-t.y+cfg.pto.lens_e)
        rcoords = check_output(['pano_trafo', self.rectilinear_pto.filepath, '0'],
                               input=orig_coords.encode('utf-8')).strip().split()

        x = float(rcoords[0])-(self.rectilinear_pto.canvas_w/2)
        y = (self.rectilinear_pto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))
        dest_img = path.join(cfg.frames_input_processed, path.basename(img))

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
        curr_pto_txt = re.sub(r' y0 ', ' y{} '.format(round(yaw_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' p0 ', ' p{} '.format(round(pitch_deg, 15)), curr_pto_txt)
        curr_pto_txt = re.sub(r' r0 ', ' r{} '.format(round(roll, 15)), curr_pto_txt)

        ### Write PTO project file for this frame
        filepath = '{}.pto'.format(path.basename(dest_img))
        with open(path.join(cfg.hugin_projects_processed, filepath), 'w') as f:
            f.write(curr_pto_txt)

        print(path.join(cfg.hugin_projects_processed, filepath))


    def frames(self):
        cfg = self.cfg

        if cfg.args.vidstab_prjn > -1:
            hugin_projects_dir = cfg.hugin_projects_processed
        else:
            hugin_projects_dir = cfg.hugin_projects

        ## check if update is needed
        pto_files = sorted(os.listdir(hugin_projects_dir))
        stabilized_imgs = sorted(os.listdir(cfg.frames_stabilized))
        if len(stabilized_imgs) \
           and not cfg.args.force_upd:
            path_img = path.join(cfg.frames_stabilized, stabilized_imgs[0])
            frame_mtime = os.path.getmtime(path_img)
            path_pto = path.join(hugin_projects_dir, pto_files[0])
            pto_mtime = os.path.getmtime(path_pto)
            if pto_mtime < frame_mtime:
                return

        pto_files = sorted(os.listdir(hugin_projects_dir))
        tasks = []
        for i, pto in enumerate(pto_files):
            tasks.append(datatypes.hugin_task(str(i+1).zfill(6)+'.jpg', pto))

        utils.delete_files_in_dir(cfg.frames_stabilized)
        cfg.current_output_path = cfg.frames_stabilized
        cfg.current_pto_path = cfg.pto.filepath
        with Pool(int(cfg.args.num_cpus)) as p:
            p.map(hugin.frames_output, tasks)


    def video(self):
        cfg = self.cfg

        output = path.join(cfg.out_video_dir, cfg.out_video)

        ## check if update needed
        stabilized_imgs = sorted(os.listdir(cfg.frames_stabilized))
        if os.path.exists(output) and len(stabilized_imgs) \
           and not cfg.args.force_upd:
            output_video_mtime = os.path.getmtime(output)
            path_img = path.join(cfg.frames_stabilized, stabilized_imgs[0])
            frame_mtime = os.path.getmtime(path_img)
            if (output_video_mtime > frame_mtime):
                return

        crf = '16'
        ivid = path.join(cfg.frames_stabilized, '%06d.jpg')
        iaud = path.join(cfg.audio_dir, 'audio.ogg')

        fps = cfg.fps
        rs_xy = cfg.args.rs_xy
        rs_roll = cfg.args.rs_roll

        if path.isfile(iaud):
            cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-i', iaud, '-c:v', 'libx264',
                   '-preset', 'veryfast', '-crf', crf, '-c:a', 'copy',
                   '-loglevel', 'error',
                   '-stats',
                   '-y', output]
        else:
            cmd = ['ffmpeg', '-framerate', fps, '-i', ivid, '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', crf,
                   '-loglevel', 'error',
                   '-stats',
                   '-an', '-y', output]

        run(cmd)


    def ffmpeg_filter(self):
        cfg = self.cfg

        w_crop = 0.91
        h_crop = 0.93
        w_scale = 1920

        cropf = f'crop=iw*{w_crop}:ih*{h_crop}:(iw-(iw*{w_crop}))/2:(ih-(ih*{h_crop}))/2'
        scalef = f'scale={w_scale}:-1,crop=floor(iw/2)*2:floor(ih/2)*2'
        pixel_format = f'yuv420p'
        filts = f'{cropf},{scalef},format={pixel_format}'

        crf = '16'
        ivid = path.join(cfg.out_video_dir, cfg.out_video)
        output = path.join(cfg.ffmpeg_filtered_dir, cfg.ffmpeg_filtered_name)

        cmd = ['ffmpeg', '-i', ivid, '-c:v', 'libx264', '-vf', filts, '-crf', crf,
               '-c:a', 'copy', '-loglevel', 'error', '-stats', '-y', output]

        print(output)

        run(cmd)


    def cleanup(self):
        print('\n {}'.format(sys._getframe().f_code.co_name))
        cfg = self.cfg

        utils.delete_files_in_dir(cfg.frames_input)
        utils.delete_files_in_dir(cfg.frames_projection)
        utils.delete_files_in_dir(cfg.frames_stabilized)
        utils.delete_files_in_dir(cfg.hugin_projects)

        utils.delete_filepath(cfg.out_video)
