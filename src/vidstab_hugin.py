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
import datetime as dt


def signal_handler(signalnum, frame):
    exit(0)
signal.signal(signal.SIGINT, signal_handler)

parser = ArgumentParser(description="Stabilizes videos using libvidstab(FFMPEG) and Hugin lens transforms.")
args.init_cmd_args(parser)


def conveyor():
    cmd_args, unknown_args = parser.parse_known_args()
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
    cfg.prev_args, unknown_args_prev = prev_parser.parse_known_args(args=args_list)
    open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:])) # update prev args

    out_frms = out_frames.OutFrames(cfg, utils.create_rectilinear_pto())

    ps = utils.print_step
    step = int(cmd_args.step)
    print(cfg.args.videofile)

    frames_total = 0
    
    if step in (1, 0):
        ps('STEP 1, input frames and split audio.')
        s = dt.datetime.now()
        inpt_frames.store_input_frames()
        e = dt.datetime.now() - s
        #print("Time elapsed: ", e.total_seconds())
        frames_total = len(os.listdir(cfg.input_dir))

    if step in (2, 0):
        ps('STEP 2, analyze cam motions in input video.', frames_total)
        s = dt.datetime.now()
        vs.analyze()
        e = dt.datetime.now() - s
        #print("Time elapsed: ", e.total_seconds())

    if step in (3, 0):
        ps(f'STEP 3, camera rotations in Hugin.', frames_total)
        s = dt.datetime.now()
        out_frms.compute_hugin_camera_rotations()
        e = dt.datetime.now() - s
        #print("Time elapsed: ", e.total_seconds())

    ## step used only if Rolling Shutter correction is done
    if step in (4, 0):
        s = dt.datetime.now()
        if utils.args_rolling_shutter(): # cfg.args.rs_xy and cfg.args.rs_roll options
            ps('STEP 4, analyze cam motions in video with corrected Rolling Shutter.',
               frames_total)
            vs.analyze2()
            out_frms.compute_hugin_camera_rotations_processed()
        else:
            ps('SKIP STEP 4, (analyze cam motions in video with corrected Rolling Shutter).',
               frames_total)
        e = dt.datetime.now() - s
        #print("Time elapsed: ", e.total_seconds())

    if step in (5, 0):
        ps(f'STEP 5, create stabilized frames, Hugin.', frames_total)
        s = dt.datetime.now()
        out_frms.frames()
        e = dt.datetime.now() - s
        print("Time elapsed: ", e.total_seconds())

    if step in (6, 0):
        ps(f'STEP 6, create video from stabilized frames, FFMPEG.', frames_total)
        s = dt.datetime.now()
        out_frms.video()
        e = dt.datetime.now() - s
        #print("Time elapsed: ", e.total_seconds())


if __name__ == '__main__':
    conveyor()
