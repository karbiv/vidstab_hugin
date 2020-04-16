### Video stabilization using "Hugin Panorama Stitcher" and "libvidstab"(ffmpeg)

# ;;; Hugin projection indexes
# ; 0   rectilinear
# ; 1   cylindrical
# ; 2   equirectangular
# ; 3   fisheye
# ; 4   stereographic
# ; 5   mercator
# ; 6   trans mercator
# ; 7   sinusoidal
# ; 8   lambert cylindrical equal area
# ; 9   lambert equal area azimuthal
# ; 10  albers equal area conic
# ; 11  miller cylindrical
# ; 12  panini
# ; 13  architectural
# ; 14  orthographic
# ; 15  equisolid
# ; 16  equirectangular panini
# ; 17  biplane
# ; 18  triplane
# ; 19  panini general
# ; 20  thoby
# ; 21  hammer-aitoff equal area

# ;;; Interpolation of Rolling Shutter corrected frames, 0 and 1 are faster
# ; 0: Nearest-neighbor
# ; 1: Bi-linear (default)
# ; 2: Bi-quadratic
# ; 3: Bi-cubic
# ; 4: Bi-quartic
# ; 5: Bi-quintic

import signal
from argparse import ArgumentParser, Action, RawTextHelpFormatter
from os import path
import config
import inp_frames
import vidstab as vs
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


num_of_stages = 7
num_of_projections = 21 # Hugin projections
max_cpus = 16
max_smoothing = 128

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
parser.add_argument('--scantop', type=int, nargs='?', required=False,
                    default=0, choices=[0, 1],
                    help='Scanning direction of lines in the CMOS image sensor: 0=bottom-up, 1=top-down.'+
                    'Depends on how the camera was held when shooting.')
parser.add_argument('--use-projection', type=int, nargs='?', required=False,
                    default=1, choices=[0, 1],
                    help='Create and use frames with other Hugin projection for second pass of vidstab.\
                    Projection is set by "input_vidstab_projection" parameter in config.')
parser.add_argument('--vidstab-projection', type=int, nargs='?', required=False,
                    default=3, choices=[0, 21],
                    help='Hugin projection number.')
parser.add_argument('--rolling_shutter_interpolation', type=int, nargs='?', required=False,
                    default=1, choices=[0, 5],
                    help='Interpolation in rolling shutter correction.')
default_smoothing_percent_of_fps = 83
parser.add_argument('--smoothing', type=int, nargs='?', required=False,
                    default=default_smoothing_percent_of_fps, choices=range(1, max_smoothing),
                    help='smoothing in percents, 100% means FPS of the input video')
## libvidstab options
parser.add_argument('--mincontrast', type=float, nargs='?', required=False,
                    default=0.3, #choices=range(0, 1.0),
                    help='Libvidstab mincontrast')
stepsize = 6
parser.add_argument('--stepsize', type=int, nargs='?', required=False,
                    default=stepsize, choices=range(1, 32),
                    help='Libvidstab stepsize')
## Rolling Shutter correction coeffs
# xy_dflt, roll_dflt = 0, 0
xy_dflt, roll_dflt = 0.45, 0.53
parser.add_argument('--xy_lines', type=float, nargs='?', required=False,
                    default=xy_dflt, #choices=range(0, 3.0),
                    help='Rolling shutter correction coefficient for translation x and y.')
parser.add_argument('--roll_lines', type=float, nargs='?', required=False,
                    default=roll_dflt, #choices=range(0, 3.0),
                    help='Rolling shutter correction coefficient for camera roll.')


if __name__ == '__main__':

    args = parser.parse_args()

    cfg = config.cfg = config.Configuration(parser)

    out_frms = out_frames.OutFrames(cfg)
    inframes = inp_frames.InFrames(cfg)
    vidstab = vs.Vidstab(cfg)
    xy_lines = cfg.args.xy_lines
    roll_lines = cfg.args.roll_lines

    if args.stage == 0: # all stages
        ## start pipeline

        inframes.create_original_frames_and_audio()

        inframes.create_projection_frames(cfg.frames_input, cfg.projection_dir1_frames)
        inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames, cfg.projection_dir1_vidstab)
        vidstab.analyze(cfg.projection_dir1_vidstab)

        out_frms.compute_hugin_camera_rotations(cfg.projection_dir1_vidstab)
        if float(xy_lines) > 0 or float(roll_lines) > 0:
            inframes.create_projection_frames(cfg.frames_input_processed, cfg.projection_dir2_frames)
            inframes.create_input_video_for_vidstab(cfg.projection_dir2_frames, cfg.projection_dir2_vidstab)
            vidstab.analyze(cfg.projection_dir2_vidstab)
            out_frms.compute_hugin_camera_rotations_processed(cfg.projection_dir2_vidstab)

        out_frms.frames()

        out_frms.video()
        out_frms.ffmpeg_filter()

        ## end pipeline

    elif args.stage == 1:
        inframes.create_original_frames_and_audio()
    elif args.stage == 2:
        inframes.create_projection_frames(cfg.frames_input, cfg.projection_dir1_frames)
        inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames, cfg.projection_dir1_vidstab)
        vidstab.analyze(cfg.projection_dir1_vidstab)
    elif args.stage == 3:
        ## saves original frames with corrected rolling shutter
        out_frms.compute_hugin_camera_rotations(cfg.projection_dir1_vidstab)
    elif args.stage == 4:
        if float(xy_lines) > 0 or float(roll_lines) > 0:
            inframes.create_projection_frames(cfg.frames_input_processed, cfg.projection_dir2_frames)
            inframes.create_input_video_for_vidstab(cfg.projection_dir2_frames, cfg.projection_dir2_vidstab)
            vidstab.analyze(cfg.projection_dir2_vidstab)
            ## fast operation, just computes hugin camera rotations and saves PTO files
            out_frms.compute_hugin_camera_rotations_processed(cfg.projection_dir2_vidstab)
    elif args.stage == 5:
        out_frms.frames()
    elif args.stage == 6:
        out_frms.video()
    elif args.stage == 7:
        out_frms.ffmpeg_filter()
