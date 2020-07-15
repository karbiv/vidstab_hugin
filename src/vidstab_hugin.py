### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

import os
from os import path
import sys
import signal
from argparse import ArgumentParser
import config
import inp_frames
import vidstab as vs
import out_frames
import utils
import args


def signal_handler(signalnum, frame):
    exit(0)
signal.signal(signal.SIGINT, signal_handler)

parser = ArgumentParser(description="Stabilizes videos using libvidstab(FFMPEG) and Hugin lens transforms.")
args.init_cmd_args(parser)


def conveyor():
    cmd_args = parser.parse_args()
    cfg = config.cfg = config.Configuration(cmd_args)

    out_frms = out_frames.OutFrames(cfg)
    inframes = inp_frames.InFrames(cfg)
    vidstab = vs.Vidstab(cfg)

    ## Cached previous command arguments
    if not path.exists(cfg.cmd_args):
        cmd_args.force_upd = True
        open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:]))
    args_list = open(cfg.cmd_args, 'r').read().splitlines()
    prev_parser = ArgumentParser(description='Previous arguments')
    args.init_cmd_args(prev_parser)
    cfg.prev_args = prev_parser.parse_args(args=args_list)
    open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:])) # update prev args

    ### Conveyor start
    ## Step 1
    inframes.create_original_frames_and_audio()

    ## Step 2
    curr_vidstab_dir = None
    if cmd_args.vidstab_projection > -1:
        inframes.create_projection_frames(cfg.frames_input, cfg.projection_dir1_frames,
                                          cfg.hugin_projects)
        videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames,
                                                            cfg.projection_dir1_vidstab_prjn)
        vidstab.analyze(videofile, cfg.projection_dir1_vidstab_prjn, cfg.projection_dir1_frames)
        curr_vidstab_dir = cfg.projection_dir1_vidstab_prjn
    else:
        vidstab.analyze(cmd_args.videofile, cfg.projection_dir1_vidstab_orig, cfg.frames_input)
        curr_vidstab_dir = cfg.projection_dir1_vidstab_orig

    ## Step 3
    ## if rolling shutter cmd_args, corrects orig frames and saves to cfg.frames_input_processed
    out_frms.compute_hugin_camera_rotations(curr_vidstab_dir)

    ## Step 4
    if utils.args_rolling_shutter() and utils.rolling_shutter_args_changed():
        curr_vidstab_dir = None
        if cmd_args.vidstab_projection > -1:
            inframes.create_projection_frames(cfg.frames_input_processed,
                                              cfg.projection_dir2_frames,
                                              cfg.hugin_projects_processed)
            videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir2_frames,
                                                                cfg.projection_dir2_vidstab_prjn)
            vidstab.analyze(videofile, cfg.projection_dir2_vidstab_prjn,
                            cfg.projection_dir2_frames)
            curr_vidstab_dir = cfg.projection_dir1_vidstab_prjn
        else:
            vidstab.analyze(cmd_args.videofile, cfg.projection_dir2_vidstab_orig,
                            cfg.frames_input_processed)
            curr_vidstab_dir = cfg.projection_dir1_vidstab_orig

        out_frms.compute_hugin_camera_rotations_processed(curr_vidstab_dir)

    ## Step 5
    out_frms.frames()

    ## Step 6
    out_frms.video()

    ## Step 7
    out_frms.ffmpeg_filter()


if __name__ == '__main__':
    conveyor()
