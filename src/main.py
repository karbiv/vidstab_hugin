### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

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
max_smoothing = 128
default_smoothing_percent_of_fps = 73

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
                    '\t 1) input frames\n\t 2) vidstab\t 3) output frames')
parser.add_argument('-c', '--num_cpus', type=int, nargs='?', required=False,
                    default=num_cpus_default, choices=range(1, max_cpus),
                    help='Number of CPUs(processes) to use')
parser.add_argument('--smoothing', type=int, nargs='?', required=False,
                    default=default_smoothing_percent_of_fps, choices=range(1, max_smoothing),
                    help='smoothing in percents, 100% means FPS of the input video')
parser.add_argument('--scantop', type=int, nargs='?', required=False,
                    default=0, choices=[0, 1],
                    help='Scanning of lines of CMOS sensor in a video frame: 0=bottom-up, 1=top-down.'+
                    'Depends on how the camera was held when shooting.')
parser.add_argument('--use-projection', type=int, nargs='?', required=False,
                    default=1, choices=[0, 1],
                    help='Create and use frames with other Hugin projection for second pass of vidstab.\
                    Projection is set by "input_vidstab_projection" parameter in config.')


if __name__ == '__main__':

    args = parser.parse_args()
    cfg = config.cfg = config.Configuration(parser)
    out_frms = out_frames.OutFrames(cfg)
    in_frms = inp_frames.InFrames(cfg)
    vs = vidstab.Vidstab(cfg)

    if args.stage == 0: # all stages
        ## start pipeline
        in_frms.input_frames_and_audio()
        in_frms.input_frames_vidstab_projection(frames_input_dir=cfg.frames_input)
        in_frms.create_input_projection_video(cfg.projection_video_1)

        vs.detect_projection(cfg.projection_video_1)
        vs.transform_projection(cfg.projection_video_1)

        out_frms.camera_rotations_projection()
        if float(cfg.params['xy_lines']) > 0 or \
           float(cfg.params['roll_lines']) > 0:

            in_frms.input_frames_vidstab_projection(frames_input_dir=cfg.frames_input_processed)
            in_frms.create_input_projection_video(cfg.projection_video_2)

            vs.detect_projection(cfg.projection_video_2)
            vs.transform_projection(cfg.projection_video_2)

            out_frms.camera_rotations_processed(cfg.vidstab_projection_dir)

        out_frms.frames()
        out_frms.video()
        out_frms.out_filter()
        ## end pipeline

    elif args.stage == 1:
        in_frms.input_frames_and_audio()
        in_frms.input_frames_vidstab_projection(frames_input_dir=cfg.frames_input)
        in_frms.create_input_projection_video(cfg.projection_video_1)
    elif args.stage == 2:
        ## TODO skimage image registration and rotation
        vs.detect_projection(cfg.projection_video_1)
        vs.transform_projection(cfg.projection_video_1)
    elif args.stage == 3:
        out_frms.camera_rotations_projection()

        if float(cfg.params['xy_lines']) > 0 or \
           float(cfg.params['roll_lines']) > 0:

            in_frms.input_frames_vidstab_projection(frames_input_dir=cfg.frames_input_processed)
            in_frms.create_input_projection_video(cfg.projection_video_2)

            vs.detect_projection(cfg.projection_video_2)
            vs.transform_projection(cfg.projection_video_2)

            out_frms.camera_rotations_processed(cfg.vidstab_projection_dir)

        out_frms.frames()

    elif args.stage == 4:
        out_frms.video()
    elif args.stage == 5:
        out_frms.out_filter()
    # elif args.stage == 6:
    #     utils.delete_filepath(cfg.projection_video_1)
    #     out_frms.cleanup()
