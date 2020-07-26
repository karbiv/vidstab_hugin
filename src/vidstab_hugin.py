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

    rectilinear_pto = utils.create_rectilinear_pto()
    out_frms = out_frames.OutFrames(cfg, rectilinear_pto)
    
    ps = utils.print_step
    step = int(cmd_args.step)
    print()

    if step in (1, 0):
        ps('STEP 1, original frames and audio.')
        inpt_frames.create_original_frames_and_audio()

    if step in (2, 0):
        ps('STEP 2, analyze cam motions in input video.')
        vs.analyze()

    if step in (3, 0):
        ps('STEP 3, camera rotations in Hugin.')
        out_frms.compute_hugin_camera_rotations()

    if step in (4, 0):
        if utils.args_rolling_shutter():
            ps('STEP 4, analyze cam motions in video with corrected Rolling Shutter.')
            vs.analyze2()
            out_frms.compute_hugin_camera_rotations_processed()
        else:
            ps('STEP 4, SKIP(analyze cam motions in video with corrected Rolling Shutter).')

    if step in (5, 0):
        ps('STEP 5, create stabilized frames, Hugin')
        out_frms.frames()

    if step in (6, 0):
        ps('STEP 6, create video from stabilized frames, FFMPEG')
        out_frms.video()

    if step in (7, 0) and cfg.args.filter:
        ps('STEP 7, FFMPEG filter for output video')
        out_frms.ffmpeg_filter()


if __name__ == '__main__':
    conveyor()

