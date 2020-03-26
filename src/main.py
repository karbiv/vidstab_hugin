### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

import sys
import signal
from argparse import ArgumentParser, Action, RawTextHelpFormatter
from os import path
import config
import inp_frames
import vidstab
import out_frames


def signal_handler(signalnum, frame):
    exit(0)
signal.signal(signal.SIGINT, signal_handler)


class VideoFileAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if '.pto' in value[0]:
            print('First positional option must be a Hugin project file path(*.pto), with rectilinear projection.')
            print('Second option must be a file path of video to stabilize;')
            exit()
        setattr(namespace, self.dest, path.abspath(value[0]))


num_of_stages = 5
num_of_projections = 21 # Hugin projections
max_cpus = 16
max_smoothing = 200

num_cpus_default = 7

parser = ArgumentParser(description="Stabilize video.",
                        formatter_class=RawTextHelpFormatter)
## positional argument
parser.add_argument('videofile', type=str, nargs=1,
                    metavar='VideoFile',
                    action=VideoFileAction,
                    help='A path to video file to stabilize;')
parser.add_argument('-s', '--stage', type=int, nargs='?', required=False,
                    choices=range(1, num_of_stages+1), default=0,
                    help='Rendering stage number. '+str(num_of_stages)+' stages in total:'+
                    '\n\t 1) input frames\n\t 2) vidstab\n\t 3) output frames\n\n')
parser.add_argument('-c', '--num_cpus', type=int, nargs='?', required=False,
                    default=num_cpus_default, choices=range(1, max_cpus),
                    help='Number of CPUs(processes) to use')
parser.add_argument('--smoothing', type=int, nargs='?', required=False,
                    default=128, choices=range(1, max_smoothing),
                    help='smoothing in percents, 100% means FPS of the input video')
parser.add_argument('--scantop', type=int, nargs='?', required=False,
                    default=0, choices=[0, 1],
                    help='Scanning of lines of CMOS sensor in a video frame: 0=bottom-up, 1=top-down.\n'+
                    'Depends on how the camera was held when shooting.')


if __name__ == '__main__':

    args = parser.parse_args()
    config.cfg = config.Configuration(parser)

    if args.stage == 0: # all stages
        ## start pipeline

        inp_frames.input_frames_and_audio()

        vidstab.detect_original(config.cfg.args.videofile)
        vidstab.transform_original(config.cfg.args.videofile)

        out_frames.camera_transforms()
        vidstab.create_processed_vidstab_input()
        vidstab.detect_original(config.cfg.processed_video)
        vidstab.transform_original(config.cfg.processed_video)
        out_frames.frames()

        out_frames.video()

        out_frames.out_filter()

        ## end pipeline
    elif args.stage == 1:
        inp_frames.input_frames_and_audio()
    elif args.stage == 2:
        vidstab.detect_original(config.cfg.args.videofile)
        vidstab.transform_original(config.cfg.args.videofile)
    elif args.stage == 3:

        vidstab.detect_original(config.cfg.args.videofile)
        vidstab.transform_original(config.cfg.args.videofile)

        out_frames.camera_transforms()

        if int(config.cfg.params['do_roll_lines']) > 0 or \
           int(config.cfg.params['do_along_lines']) > 0 or \
           int(config.cfg.params['do_across_lines']) > 0:

            ## first pass
            vidstab.create_processed_vidstab_input()
            vidstab.detect_original(config.cfg.processed_video)
            vidstab.transform_original(config.cfg.processed_video)
            out_frames.camera_transforms_processed()

            ## second pass
            out_frames.camera_transforms()
            vidstab.create_processed_vidstab_input()
            vidstab.detect_original(config.cfg.processed_video)
            vidstab.transform_original(config.cfg.processed_video)
            out_frames.camera_transforms_processed()

        out_frames.frames()

        out_frames.video()
        out_frames.out_filter()

    elif args.stage == 4:
        out_frames.video()
    elif args.stage == 5:
        out_frames.out_filter()
    # elif args.stage == 6:
    #     out_frames.cleanup()
