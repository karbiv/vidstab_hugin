### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

import os
from os import path
import sys
import signal
from argparse import ArgumentParser
import config
import out_frames
import utils
import args
import datetime as dt
from inp_frames import InFrames
from vidstab import Vidstab
from conveyor import Conveyor, Step


def signal_handler(signalnum, frame):
    exit(0)
signal.signal(signal.SIGINT, signal_handler)

parser = ArgumentParser(description="Stabilizes videos using libvidstab(FFMPEG) and Hugin lens transforms.")
args.init_cmd_args(parser)


def main():
    cmd_args, unknown_args = parser.parse_known_args()
    cfg = config.cfg = config.Configuration(cmd_args)

    inframes = cfg.inframes = InFrames(cfg)
    vs = cfg.vidstab = Vidstab(cfg)
    convey = cfg.convey = Conveyor(cfg)
    out_frms = cfg.out_frms = out_frames.OutFrames(cfg)

    ## Cached previous command arguments
    if not path.exists(cfg.cmd_args):
        cmd_args.force_upd = True
        open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:]))

    args_list = open(cfg.cmd_args, 'r').read().splitlines()
    prev_parser = ArgumentParser(description='Previous arguments')
    args.init_cmd_args(prev_parser)
    cfg.prev_args, unknown_args_prev = prev_parser.parse_known_args(args=args_list)
    open(cfg.cmd_args, 'w').write('\n'.join(sys.argv[1:])) # update prev args

    add_step = convey.add_step
    
    step_arg = int(cmd_args.step)
    print('Videofile:  ', cfg.args.videofile)
    print('Workdir:    ', cfg.args.workdir)
    print('PTO(Hugin): ', cfg.args.pto_name)


    add_step(
        'STEP_1: input frames and split audio.',
        convey.to_upd_input_frames,
        inframes.store_input_frames)

    add_step(
        'STEP_2: analyze cam motions in input video.',
        convey.to_upd_analyze,
        vs.analyze)

    add_step(
        "STEP_3: parse vidstab's trf file.",
        convey.to_upd_trf_parse,
        out_frms.parseTransforms)

    if utils.args_rolling_shutter():
        msg = 'STEP_4: create corrected rolling shutter frames.'
    else:
        msg = "STEP_4: create PTO files for Hugin."
    add_step(
        msg,
        convey.to_upd_camera_rotations,
        out_frms.compute_hugin_camera_rotations)
    
    add_step(
        'STEP_5: create stabilized frames, Hugin.',
        convey.to_upd_out_frames,
        out_frms.frames)

    add_step(
        'STEP_6: create video from stabilized frames.',
        convey.to_upd_out_video,
        out_frms.video)
    
    s = dt.datetime.now()

    convey.execute(step_arg)

    e = dt.datetime.now() - s
    print()
    print()
    utils.print_time(e.total_seconds(), prefix='Total time')


if __name__ == '__main__':
    main()
