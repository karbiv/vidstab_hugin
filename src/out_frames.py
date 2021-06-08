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

import datetime as dt

class OutFrames:

    pto_txt: str = ''
    rectilinear_pto: datatypes.HuginPTO = None
    projection_pto: datatypes.HuginPTO = None
    tan_pix: float = 0
    canv_half_hfov: float = 0
    optical_center = None


    def __init__(self, cfg):
        self.cfg = cfg
        self.rectilinear_pto = utils.create_rectilinear_pto()


    def compute_hugin_camera_rotations(self):
        """if rolling shutter cmd_args, corrects orig frames and
        saves to cfg.frames_input_processed"""
        cfg = self.cfg

        if cfg.args.vidstab_prjn > -1:
            self.curr_vidstab_dir = cfg.prjn_dir1_vidstab_prjn
        else:
            self.curr_vidstab_dir = cfg.prjn_dir1_vidstab_orig

        vidstab_dir = self.curr_vidstab_dir

        imgs = sorted(os.listdir(cfg.input_dir))
        self.canv_half_hfov = math.radians(self.rectilinear_pto.canv_half_hfov)

        max_horizont_tan = math.tan(self.canv_half_hfov)
        self.tan_pix = max_horizont_tan/(self.rectilinear_pto.canvas_w/2)

        ###
        # f_motions = open(path.join(vidstab_dir, 'global_motions.trf'))
        # transforms_rel = utils.get_global_motions(f_motions)

        s = dt.datetime.now()
        transforms_rel = utils.parseTransformsTrf(path.join(vidstab_dir, 'transforms.trf'))
        # for i in range(len(transforms_rel)):
        #     print(i+1, transforms_rel[i])
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds(), fps=True)
        ###

        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = utils.gauss_filter(cfg.fps, transforms_abs,
                                                     cfg.args.smoothing)

        ## set center coords to lens' optical axis
        path_img = path.join(cfg.input_dir, imgs[0])
        sk_img = skio.imread(path_img)
        cx, cy = np.array(sk_img.shape)[:2][::-1] / 2

        #self.optical_center = cx, cy
        self.optical_center = cx+cfg.pto.lens_d, cy+cfg.pto.lens_e

        if cfg.args.vidstab_prjn != -1:
            self.projection_pto = datatypes.HuginPTO(cfg.projection_pto_path)

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(cfg.input_dir, imgs[i])
            tasks.append((t[0], path_img, t[1], i))

        self.pto_txt = utils.create_pto_txt_one_image(cfg.pto.filepath)

        ## breaks cache checks
        # if not utils.args_rolling_shutter():
        #     utils.delete_files_in_dir(cfg.hugin_projects)
        # utils.delete_files_in_dir(cfg.frames_input_processed)

        if utils.args_rolling_shutter():
            print('Create images with corrected Rolling Shutter.')

        self.prjn_frames_total = len(tasks)
        self.prjn_frames_cnt = 0

        s = dt.datetime.now()
        with Pool(int(cfg.args.num_cpus)) as p:
            if not utils.args_rolling_shutter():
                print(f'Create Hugin pto files with camera moves.')
            results = [p.apply_async(self.camera_moves_worker, args=(t,),
                                     callback=self.prjn_worker_callback
                                     )
                       for t in tasks]
            for r in results:
                r.get()
        # for t in tasks:
        #     self.camera_moves_worker(t)

        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds(), fps=True)


    def prjn_worker_callback(self, task):
        utils.print_progress(self.prjn_frames_cnt, self.prjn_frames_total)
        self.prjn_frames_cnt += 1


    def camera_moves_worker(self, task):
        cfg = self.cfg
        t, img, t_rel = task[0], task[1], task[2]

        if cfg.args.vidstab_prjn == -1:
            ## compensate camera pre-rotation in each frame
            ## caused by optical center displacement on sensor
            orig_coords = '{} {}'.format(cfg.pto.orig_w/2 + t.x + cfg.pto.lens_d,
                                         cfg.pto.orig_h/2 - t.y + cfg.pto.lens_e)
            ## get rectilinear coords from original
            rcoords = check_output(['pano_trafo', self.rectilinear_pto.filepath, '0'],
                                   input=orig_coords.encode()).strip().split()
        else:
            ## get original coords from projection
            projection_coords = '{} {}'.format(
                self.projection_pto.canvas_w/2 + t.x,
                self.projection_pto.canvas_h/2 - t.y)
            ## from projection to original image coords
            orig_coords = check_output(['pano_trafo', '-r', cfg.projection_pto_path, '0'],
                                       input=projection_coords.encode('utf-8'))
            ## get rectilinear coords from original
            rcoords = check_output(['pano_trafo', self.rectilinear_pto.filepath, '0'],
                                   input=orig_coords).strip().split()
        # filter out possible preceding WARNING message
        rcoords = rcoords[-2:]

        x = float(rcoords[0])-(self.rectilinear_pto.canvas_w/2)
        y = (self.rectilinear_pto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        #roll = math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))

        dest_img = img
        if utils.args_rolling_shutter():
            #### Rolling Shutter start
            sk_img = skio.imread(img)

            # tx, ty = orig_coords.strip().split()
            # orig_tx, orig_ty = float(tx) - cfg.pto.orig_w/2, cfg.pto.orig_h/2 - float(ty)
            # warp_args = {'roll': t_rel.roll, 'y_move': orig_ty, 'along_move': orig_tx,
            #              'frame': task[3]}

            warp_args = {'roll': t_rel.roll, 'y_move': t_rel.y, 'along_move': t_rel.x,
                         'frame': task[3]}

            interpolation = int(cfg.args.rs_interpolation)
            modified_orig_frame = sktf.warp(sk_img,
                                            self.rolling_shutter_mappings,
                                            map_args=warp_args, order=interpolation)

            ## Save corrected original frame
            dest_img = path.join(cfg.frames_input_processed, path.basename(img))
            ## 100, best quality for JPEG in skimage
            skio.imsave(dest_img, img_as_ubyte(modified_orig_frame), quality=100)
            ## PNG
            #skio.imsave(dest_img, img_as_ubyte(modified_orig_frame))
            #### Rolling Shutter end

        else: # not utils.args_rolling_shutter()
            ## set input image path for frame PTO
            curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
            curr_pto_txt = re.sub(r' y[^\n\t ]+ ', ' y{} '.format(round(yaw_deg, 3)), curr_pto_txt)
            curr_pto_txt = re.sub(r' p[^\n\t ]+ ', ' p{} '.format(round(pitch_deg, 3)), curr_pto_txt)
            curr_pto_txt = re.sub(r' r[^\n\t ]+ ', ' r{} '.format(round(roll, 3)), curr_pto_txt)

            ### Write PTO project file for this frame
            filepath = '{}.pto'.format(path.basename(dest_img))
            with open(path.join(cfg.hugin_projects, filepath), 'w') as f:
                f.write(curr_pto_txt)


    def rolling_shutter_mappings(self, xy, **kwargs):
        '''Inverse map function'''

        #print(xy.shape)
        # xy shape (2073600, 2)

        cfg = self.cfg
        num_lines = cfg.pto.orig_h
        y_move = kwargs['y_move']
        along_move = kwargs['along_move']

        if not cfg.args.rs_scan_up:
            line_idxs = tuple(range(num_lines))
            #roll = 0 - kwargs['roll']
        else:
            line_idxs = tuple(reversed(range(num_lines)))
            #roll = kwargs['roll']

        roll = 0 - kwargs['roll']

        #### ACROSS and ALONG lines
        if float(cfg.args.rs_along) > 0.0 \
           or float(cfg.args.rs_across) > 0.0 \
           or float(cfg.args.rs_roll) > 0.0:



            



            
            max_shift_across = y_move * float(cfg.args.rs_across)
            if abs(y_move) > 1.0:
                across_delta = max_shift_across / num_lines
                across_line_shift = 0

                ## across
                if not cfg.args.rs_scan_up:
                    for i in line_idxs:
                        y = xy[i::num_lines, 1]
                        xy[i::num_lines, 1] = y - across_line_shift
                        across_line_shift += across_delta
                else:
                    for i in line_idxs:
                        y = xy[i::num_lines, 1]
                        xy[i::num_lines, 1] = y + across_line_shift
                        across_line_shift += across_delta

                # xy2 = np.copy(xy)
                # s = dt.datetime.now()
                # deltas = np.arange(0, across_delta*num_lines, across_delta)
                # deltas = np.dstack((np.zeros_like(deltas), deltas))
                # xy2.shape = (1920, 1080, 2)
                # xy2 = np.add(xy2, deltas)
                # e = dt.datetime.now() - s
                # print(e.total_seconds())

            if abs(along_move) > 1.0:
                last_line_along = along_move * float(cfg.args.rs_along)
                ## compensate number of lines after across lines correction
                along_delta = last_line_along / (num_lines + round(max_shift_across))
                along_line_shift = 0

                ## along
                if not cfg.args.rs_scan_up:
                    for i in line_idxs:
                        x = xy[i::num_lines, 0]
                        xy[i::num_lines, 0] = x - along_line_shift
                        along_line_shift += along_delta
                else:
                    for i in line_idxs:
                        x = xy[i::num_lines, 0]
                        xy[i::num_lines, 0] = x + along_line_shift
                        along_line_shift += along_delta

        #### ROLL lines
        if float(cfg.args.rs_roll) > 0 \
           and abs(roll) > 0.003:

            #print(kwargs["frame"]+1, roll)

            # max_shift_across = y_move * float(cfg.args.rs_across)
            # across_delta = max_shift_across / num_lines
            # across_line_shift = 0

            # last_line_along = along_move * float(cfg.args.rs_along)
            # along_delta = last_line_along / (num_lines + round(max_shift_across))
            # along_line_shift = 0

            roll_coeff = float(cfg.args.rs_roll)
            last_line_roll = roll * roll_coeff
            roll_delta = last_line_roll / num_lines
            #roll_delta = last_line_roll / (num_lines + round(max_shift_across))

            x0, y0 = self.optical_center

            x, y = xy.T
            cx, cy = x-x0, y-y0
            cxy = np.column_stack((cx, cy))

            theta = 0

            # along_delta = along_move / num_lines
            # along_shift = 0

            for i in line_idxs:
                # cx = x-x0+along_shift
                # cxy = np.column_stack((cx, cy))
                # along_shift += along_delta

                x, y = cxy[i::num_lines].T

                # x = x + along_shift
                # along_shift += along_delta

                ox = math.cos(theta)*x - math.sin(theta)*y
                oy = math.sin(theta)*x + math.cos(theta)*y
                cxy[i::num_lines] = np.dstack((ox, oy)).squeeze()
                theta -= roll_delta

            ## convert to pixel coords around center
            xy = cxy+self.optical_center

        return xy


    def compute_hugin_camera_rotations_processed(self):
        cfg = self.cfg

        if cfg.args.vidstab_prjn > -1:
            vidstab_dir = cfg.prjn_dir2_vidstab_prjn
        else:
            vidstab_dir = cfg.prjn_dir2_vidstab_orig

        if not utils.to_upd_camera_rotations_processed(vidstab_dir):
            return

        frames_dir = cfg.frames_input_processed
        imgs = sorted(os.listdir(frames_dir))
        self.canv_half_hfov = math.radians(self.rectilinear_pto.canv_half_hfov)
        max_horizont_tan = math.tan(self.canv_half_hfov)
        self.tan_pix = max_horizont_tan/(self.rectilinear_pto.canvas_w/2)

        ##
        # f_motions = open(path.join(vidstab_dir, 'global_motions.trf'))
        # transforms_rel = utils.get_global_motions(f_motions)

        s = dt.datetime.now()
        transforms_rel = utils.parseTransformsTrf(path.join(vidstab_dir, 'transforms.trf'))
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds(), fps=True)
        ##

        transforms_abs = utils.convert_relative_transforms_to_absolute(transforms_rel)
        transforms_abs_filtered = utils.gauss_filter(cfg.fps, transforms_abs, cfg.args.smoothing)

        self.pto_txt = utils.create_pto_txt_one_image(cfg.pto.filepath)

        tasks = []
        for i, t in enumerate(zip(transforms_abs_filtered, transforms_rel)):
            path_img = path.join(frames_dir, imgs[i])
            tasks.append((t[0], path_img, t[1]))

        utils.delete_files_in_dir(cfg.hugin_projects_processed)

        self.prjn_frames_total = len(tasks)
        self.prjn_frames_cnt = 0

        s = dt.datetime.now()
        with Pool(int(cfg.args.num_cpus)) as p:
            print('Rolling shutter, create Hugin pto files with camera moves.')
            results = [p.apply_async(self.camera_moves_processed_worker, args=(t,),
                                     callback=self.prjn_worker_callback)
                       for t in tasks]
            for r in results:
                r.get()

        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds(), fps=True)


    def camera_moves_processed_worker(self, task):
        cfg = self.cfg
        t, img = task[0], task[1]

        if cfg.args.vidstab_prjn == -1:
            orig_coords = '{} {}'.format(cfg.pto.orig_w/2 + t.x + cfg.pto.lens_d,
                                         cfg.pto.orig_h/2 - t.y + cfg.pto.lens_e)
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

        # filter out possible preceding WARNING message
        rcoords = rcoords[-2:]
        x = float(rcoords[0])-(self.rectilinear_pto.canvas_w/2)
        y = (self.rectilinear_pto.canvas_h/2)-float(rcoords[1])

        roll = 0-math.degrees(t.roll)
        yaw_deg = math.degrees(math.atan(x*self.tan_pix))
        pitch_deg = 0-math.degrees(math.atan(y*self.tan_pix))
        dest_img = path.join(cfg.frames_input_processed, path.basename(img))

        ## set input image path for frame PTO
        curr_pto_txt = re.sub(r'n".+\.(png|jpg|jpeg|tif)"', 'n"{}"'.format(dest_img), self.pto_txt)
        curr_pto_txt = re.sub(r' y[^\n\t ]+ ', ' y{} '.format(round(yaw_deg, 3)), curr_pto_txt)
        curr_pto_txt = re.sub(r' p[^\n\t ]+ ', ' p{} '.format(round(pitch_deg, 3)), curr_pto_txt)
        curr_pto_txt = re.sub(r' r[^\n\t ]+ ', ' r{} '.format(round(roll, 3)), curr_pto_txt)

        ### Write PTO project file for this frame
        filepath = '{}.pto'.format(path.basename(dest_img))
        with open(path.join(cfg.hugin_projects_processed, filepath), 'w') as f:
            f.write(curr_pto_txt)


    def frames(self):
        cfg = self.cfg

        pto_files = sorted(os.listdir(cfg.convey.curr_hugin_ptos_dir))
        all_out_frames = cfg.convey.all_out_frames

        tasks = []
        for i, pto in enumerate(pto_files):
            tasks.append(datatypes.hugin_task(str(i+1).zfill(6)+'.jpg', pto))

        self.prjn_frames_total = len(tasks)
        self.prjn_frames_cnt = 0

        s = dt.datetime.now()
        with Pool(int(cfg.args.num_cpus)) as p:
            print(f'Create stabilized frames for output video.')
            results = [p.apply_async(hugin.frames_output,
                                     args=(t, all_out_frames, cfg.frames_stabilized),
                                     callback=self.prjn_worker_callback)
                       for t in tasks]
            for r in results:
                r.get()

        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds(), fps=True)


    def video(self):
        cfg = self.cfg
        output = path.join(cfg.out_video_dir, cfg.convey.out_video_path)

        crf = '11'
        ivid = path.join(cfg.frames_stabilized, '%06d.jpg')

        audio_filepath = path.join(cfg.out_video_dir, 'sound.ogg')
        if cfg.args.with_audio:
            cmd_aud = ['ffmpeg',
                       '-loglevel', 'error',
                       '-stats',
                       '-i', cfg.args.videofile,
                       '-vn', '-aq', str(3), '-y', audio_filepath
            ]
            run(cmd_aud, #check=True,
                capture_output=True)

        if path.isfile(audio_filepath):
            cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-i', audio_filepath, '-c:v', 'libx264',
                   '-preset', 'fast', '-crf', crf, '-c:a', 'copy',
                   '-loglevel', 'error',
                   '-stats',
                   '-y', output]
        else:
            cmd = ['ffmpeg', '-framerate', cfg.fps, '-i', ivid, '-c:v', 'libx264',
                   '-preset', 'fast', '-crf', crf,
                   '-loglevel', 'error',
                   '-stats',
                   '-an', '-y', output]

        if cfg.args.verbose:
            print(' '.join(cmd))

        s = dt.datetime.now()
        run(cmd)
        e = dt.datetime.now() - s
        utils.print_time(e.total_seconds())
