### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

import sys
import signal
from argparse import ArgumentParser, Action, RawTextHelpFormatter
from os import path
import config
from inp_frames import *
from vidstab import *
from out_frames import *
from crop_scale import *


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


class ProjectAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(namespace, self.dest, path.abspath(value[0]))


class CreateProjectAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(namespace, self.dest, path.abspath(value[0]))


num_of_stages = 7
parser = ArgumentParser(description="Stabilize video.",
                        formatter_class=RawTextHelpFormatter)

parser.add_argument('-p', '--project', type=str, nargs=1,
                    action=ProjectAction,
                    help='Path to outputs directory containing project.ini')
parser.add_argument('-v', '--videofile', type=str, nargs=1,
                    metavar='VideoFile',
                    action=VideoFileAction,
                    help='A path to video file to stabilize;')
parser.add_argument('-s', '--stage', type=int, nargs='?', required=False,
                    choices=range(1, num_of_stages+1), default=0,
                    help='Stage number. 3 stages overall:'+
                    '\n\t 1) input frames\n\t 2) vidstab\n\t 3) output frames\n\n')
parser.add_argument('-ss', dest='seek_start', type=str, nargs='?', required=False,
                    default='00:00:00.000',
                    help='Seek start, FFMPEG time format.')
parser.add_argument('-t', dest='duration', type=str, nargs='?', required=False,
                    default=None,
                    help='Duration from seek start(-ss), FFMPEG time format.')


if __name__ == '__main__':

    args = parser.parse_args()
    config.cfg = config.Configuration(args)

    if args.stage == 0: # all stages
        ## start pipeline
        input_frames_and_audio()
        
        libvidstab_detect()
        libvidstab_transform()
        libvidstab_detect_pass_2()
        libvidstab_transform_pass_2()
        libvidstab_detect_pass_3()
        libvidstab_transform_pass_3()
        libvidstab_detect_pass_4()
        libvidstab_transform_pass_4()
        combine_global_transforms()
        
        output_frames()
        
        output_video()
        crop_scale_output()
        ## end pipeline
    elif args.stage == 1:
        input_frames_and_audio()
    elif args.stage == 2:
        libvidstab_detect()
        libvidstab_transform()
        libvidstab_detect_pass_2()
        libvidstab_transform_pass_2()
        libvidstab_detect_pass_3()
        libvidstab_transform_pass_3()
        libvidstab_detect_pass_4()
        libvidstab_transform_pass_4()
        combine_global_transforms()
    elif args.stage == 3:
        output_frames()
    elif args.stage == 4:
        output_video()
        crop_scale_output()
