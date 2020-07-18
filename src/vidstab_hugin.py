### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

import os
from os import path
import sys
import signal
from argparse import ArgumentParser
import config
import inp_frames
import vidstab
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

    inpt_frames = inp_frames.InFrames(cfg)
    vs = vidstab.Vidstab(cfg)

    ## Cached previous command arguments
    if not path.exists(cfg.cmd_args):
        cmd_args.force_upd = True
        open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:]))
    args_list = open(cfg.cmd_args, 'r').read().splitlines()
    prev_parser = ArgumentParser(description='Previous arguments')
    args.init_cmd_args(prev_parser)
    cfg.prev_args = prev_parser.parse_args(args=args_list)
    open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:])) # update prev args
    ps = utils.print_step
    
    ps('step 1, create_original_frames_and_audio')
    inpt_frames.create_original_frames_and_audio()

    
    ps('step 2, analyze input video')
    vs.analyze()

    
    ps('step 3, compute_hugin_camera_rotations')
    rectilinear_pto = utils.create_rectilinear_pto()
    out_frms = out_frames.OutFrames(cfg, rectilinear_pto)
    out_frms.compute_hugin_camera_rotations()

    
    ps('step 4, rolling shutter; analyze2; compute_hugin_camera_rotations_processed')
    if utils.args_rolling_shutter() and utils.rolling_shutter_args_changed():
        vidstab_dir = vs.analyze2()
        out_frms.compute_hugin_camera_rotations_processed(vidstab_dir)

        
    ps('step 5, create stabilized frames, Hugin')
    out_frms.frames()

    
    ps('step 6, create video from stabilized frames, FFMPEG')
    out_frms.video()

    
    if cfg.args.filter:
        ps('step 7, FFMPEG filter for output video')
        out_frms.ffmpeg_filter()


if __name__ == '__main__':
    conveyor()
