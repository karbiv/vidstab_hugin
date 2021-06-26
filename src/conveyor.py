from collections.abc import Callable
import config
import os
from os import path
import traceback
import inp_frames
import utils


class StepUpd(Exception):


    def __init__(self, msg=''):
        self.msg = msg


class StepSkip(Exception):


    def __init__(self, msg=''):
        self.msg = msg


class StepBreak(Exception):


    def __init__(self, msg):
        self.msg = msg



class Step:


    def __init__(self,
                 msg,
                 check: Callable[[], None],
                 make:  Callable[[], None]):
        self.msg = msg
        self.check = check
        self.make = make


class Conveyor:


    steps = []


    def __init__(self, cfg):
        self.cfg = cfg


    def add_step(self,
                 msg,
                 check: Callable[[], None],
                 make:  Callable[[], None]):
        self.steps.append(Step(msg, check, make))


    def execute(self, step=0):
        cfg = config.cfg
        force_upd = False
        if cfg.args.force_upd:
            force_upd = True

        if step == 0:
            ## all steps
            for s in self.steps:
                print_step(s.msg, cfg.frames_total)
                self.try_step(s, force_upd)
        elif step > 1:
            ## check readiness of prev steps
            for si in range(step):
                s = self.steps[si]
                print_step(s.msg, cfg.frames_total)
                if force_upd and si+1 == step:
                    self.try_step(s, True)
                else:
                    self.try_step(s)


    def try_step(self, step, force_upd=False):
        cfg = config.cfg

        if force_upd:
            try:
                step.check() # for side effects
            except:
                step.make()
            else:
                step.make()
            return

        try:
            step.check()
        except StepUpd as supd:
            if cfg.args.debug:
                print('DEBUG INFO:')
                print(traceback.format_exc())

            if supd.msg:
                print(supd.msg)
            step.make()
        except StepSkip as skip:
            if cfg.args.debug:
                print('DEBUG INFO:')
                print(traceback.format_exc())

            if skip.msg:
                print('Skip; ', skip.msg)
            else:
                print('Skip;')
        except StepBreak as sb:
            if cfg.args.debug:
                print('DEBUG INFO:')
                print(traceback.format_exc())

            print(sb.msg)
            print('Execution stopped.')
            exit()
        else:
            print('Fresh;')


    def to_upd_input_frames(self):
        cfg = self.cfg
        frames_dir = cfg.input_dir
        imgs = sorted(os.listdir(frames_dir))
        ## important for other code, `utils.print_time'
        ## line is repeated in `store_input_frames'
        cfg.frames_total = len(imgs)

        ## TODO compare num of frames in dir with FFMPEG probe

        if not os.path.exists(cfg.args.videofile) and not len(imgs):
            msg = f"No videofile: {cfg.args.videofile}\n"
            msg += f"Frames folder is empty: {frames_dir}\n"
            raise StepBreak(msg)

        ## check if input videofile was updated
        if len(imgs):
            path_img = path.join(frames_dir, imgs[0])
            video_mtime = os.path.getmtime(cfg.args.videofile)
            frame_mtime = os.path.getmtime(path_img)
            if (video_mtime > frame_mtime):
                msg = f"Input videofile is newer than imported frames in {frames_dir}"
                msg += "\nUpdating all steps."
                raise StepUpd(msg)
        else:
            raise StepUpd()


    ## in progress, from utils module
    def to_upd_analyze(self):
        cfg = self.cfg

        frames_dir = cfg.input_dir
        transforms_trf = os.path.join(cfg.vidstab1_dir, "transforms.trf")
        if not os.path.exists(transforms_trf):
            raise StepUpd()

        imgs = sorted(os.listdir(frames_dir))
        path_img = path.join(frames_dir, imgs[0])
        transforms_mtime = os.path.getmtime(transforms_trf)
        frame_mtime = os.path.getmtime(path_img)
        if frame_mtime > transforms_mtime:
            raise StepUpd()

        if cfg.args.vs_mincontrast != cfg.prev_args.vs_mincontrast \
           or cfg.args.vs_stepsize != cfg.prev_args.vs_stepsize:
            raise StepUpd()


    def to_upd_trf_parse(self):
        cfg = self.cfg

        if cfg.args.smoothing != cfg.prev_args.smoothing:
            raise StepUpd()

        if not os.path.exists(cfg.trf_rel_path) \
           or not os.path.exists(cfg.trf_abs_filtered_path):
            raise StepUpd()

        trf_rel_path_mtime = os.path.getmtime(cfg.trf_rel_path)
        trf_abs_filtered_path_mtime = os.path.getmtime(cfg.trf_abs_filtered_path)
        transforms_trf = os.path.join(cfg.vidstab1_dir, "transforms.trf")
        transforms_mtime = os.path.getmtime(transforms_trf)

        if trf_rel_path_mtime < transforms_mtime \
           or trf_abs_filtered_path_mtime < transforms_mtime:
            raise StepUpd()



    def to_upd_camera_rotations(self):
        cfg = self.cfg

        if utils.rolling_shutter_args_changed():
            raise StepUpd()

        if cfg.args.smoothing != cfg.prev_args.smoothing:
            raise StepUpd()

        main_pto = cfg.args.pto
        main_pto_mtime = os.path.getmtime(main_pto)

        trf_rel_path_mtime = os.path.getmtime(cfg.trf_rel_path)
        trf_abs_filtered_path_mtime = os.path.getmtime(cfg.trf_abs_filtered_path)

        if utils.args_rolling_shutter():
            rs_frames = sorted(os.listdir(cfg.frames_processed))

            if len(rs_frames):
                path_img = path.join(cfg.frames_processed,
                                     rs_frames[0])
                rs_frame_mtime = os.path.getmtime(path_img)
                if rs_frame_mtime < trf_rel_path_mtime \
                   or rs_frame_mtime < trf_abs_filtered_path_mtime:
                    raise StepUpd()
            else:
                raise StepUpd()

            num_orig_frames = len(os.listdir(cfg.input_dir))
            if num_orig_frames > len(rs_frames):
                raise StepUpd()
            
        else:
            pto_files = sorted(os.listdir(cfg.hugin_projects))
            num_orig_frames = len(os.listdir(cfg.input_dir))
            if pto_files:
                if len(pto_files) != num_orig_frames:
                    raise StepUpd()
                pto_0 = path.join(cfg.hugin_projects, pto_files[0])
                pto_mtime = os.path.getmtime(pto_0)
                if pto_mtime < trf_rel_path_mtime \
                   or pto_mtime < trf_abs_filtered_path_mtime:
                    raise StepUpd()
                if pto_mtime < main_pto_mtime:
                    #msg = f'Result PTO updated, '
                    raise StepUpd()
            else:
                raise StepUpd()


    def to_upd_rs_analyze(self):
        cfg = self.cfg

        ## next code identical to `self.to_upd_analyze()'

        transforms_trf = os.path.join(cfg.vidstab2_dir, "transforms.trf")
        if not os.path.exists(transforms_trf):
            raise StepUpd()
        transforms_mtime = os.path.getmtime(transforms_trf)

        main_pto = cfg.args.pto
        main_pto_mtime = os.path.getmtime(main_pto)
        if main_pto_mtime > transforms_mtime:
            raise StepUpd()

        imgs = sorted(os.listdir(cfg.frames_processed))
        path_img = path.join(cfg.frames_processed, imgs[0])

        frame_mtime = os.path.getmtime(path_img)
        if frame_mtime > transforms_mtime:
            raise StepUpd()

        if cfg.args.vs_mincontrast != cfg.prev_args.vs_mincontrast \
           or cfg.args.vs_stepsize != cfg.prev_args.vs_stepsize:
            raise StepUpd()


    all_out_frames = True

    def to_upd_out_frames(self):
        cfg = self.cfg
        
        if utils.args_rolling_shutter():

            to_upd_vidstab = False
            try:
                transforms_trf = os.path.join(cfg.vidstab2_dir, "transforms.trf")
                if not os.path.exists(transforms_trf):
                    to_upd_vidstab = True
                    raise StepUpd()
                transforms_mtime = os.path.getmtime(transforms_trf)

                main_pto = cfg.args.pto
                main_pto_mtime = os.path.getmtime(main_pto)
                if main_pto_mtime > transforms_mtime:
                    raise StepUpd()

                imgs = sorted(os.listdir(cfg.frames_processed))
                path_img = path.join(cfg.frames_processed, imgs[0])

                frame_mtime = os.path.getmtime(path_img)
                if frame_mtime > transforms_mtime:
                    to_upd_vidstab = True
                    raise StepUpd()

                if cfg.args.vs_mincontrast != cfg.prev_args.vs_mincontrast \
                   or cfg.args.vs_stepsize != cfg.prev_args.vs_stepsize:
                    to_upd_vidstab = True
                    raise StepUpd()

                trf_rel_path_mtime = os.path.getmtime(cfg.trf_rel_path)
                trf_abs_filtered_path_mtime = os.path.getmtime(cfg.trf_abs_filtered_path)
                
                pto_files = sorted(os.listdir(cfg.hugin_projects))
                num_orig_frames = len(os.listdir(cfg.input_dir))
                if pto_files:
                    if len(pto_files) != num_orig_frames:
                        raise StepUpd()
                    pto_0 = path.join(cfg.hugin_projects, pto_files[0])
                    pto_mtime = os.path.getmtime(pto_0)
                    if pto_mtime < trf_rel_path_mtime \
                       or pto_mtime < trf_abs_filtered_path_mtime:
                        raise StepUpd()
                    if pto_mtime < main_pto_mtime:
                        #msg = f'Result PTO updated, '
                        raise StepUpd()
                else:
                    raise StepUpd()
                
            except StepUpd as supd:
                if to_upd_vidstab:
                    cfg.vidstab.analyze2()
                cfg.out_frms.compute_hugin_camera_rotations_processed()
            except Exception as e:
                raise e
        
        pto_files = sorted(os.listdir(cfg.hugin_projects))
        stabilized_imgs = sorted(os.listdir(cfg.frames_stabilized))

        ptos_len = len(pto_files)
        out_frames_len = len(stabilized_imgs)
        self.all_out_frames = True
        if out_frames_len != ptos_len:
            self.all_out_frames = False

        if out_frames_len:
            path_img = path.join(cfg.frames_stabilized, stabilized_imgs[0])
            frame_mtime = os.path.getmtime(path_img)
            path_pto = path.join(cfg.hugin_projects, pto_files[0])
            pto_mtime = os.path.getmtime(path_pto)
            if pto_mtime < frame_mtime and self.all_out_frames:
                return
            elif pto_mtime > frame_mtime:
                # delete all out frames
                utils.delete_files_in_dir(cfg.frames_stabilized)
                raise StepUpd()
        else:
            raise StepUpd()


    def to_upd_out_video(self):
        cfg = self.cfg

        self.out_video_path = path.join(cfg.out_video_dir, cfg.out_video_name)

        output = path.join(cfg.out_video_dir, self.out_video_path)
        if not os.path.exists(output):
            raise StepUpd()

        ## check if update needed
        stabilized_imgs = sorted(os.listdir(cfg.frames_stabilized))
        if len(stabilized_imgs):
            output_video_mtime = os.path.getmtime(output)
            path_img = path.join(cfg.frames_stabilized, stabilized_imgs[0])
            frame_mtime = os.path.getmtime(path_img)
            if output_video_mtime < frame_mtime:
                raise StepUpd()
        else:
            raise StepUpd()


def print_step(msg, frames_total=None):
    print()
    print('_______')
    if frames_total:
        print(msg, f'{frames_total} frames.')
    else:
        print(msg)
        print()
