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

import os
from os import path
import signal
from argparse import ArgumentParser, Action, RawTextHelpFormatter
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

num_of_steps = 7
num_of_projections = 21 # Hugin projections
max_cpus = 16
max_smoothing = 128
num_cpus_default = 4

parser = ArgumentParser(description="Stabilizes videos using libvidstab(FFMPEG) and Hugin lens transforms.")

pos_group = parser.add_argument_group('positional arguments')

pos_group.add_argument('videofile', type=str, nargs=1,
                    metavar='input_video_file',
                    action=VideoFileAction,
                    help='A path to video file to stabilize;')

parser.add_argument('--pto', type=str, nargs='?', required=True,
                    help='Path to a Hugin project file(*.pto);')

parser.add_argument('--workdir', type=str, nargs='?', required=True,
                    help='Path to where video render work is done;')

parser.add_argument('--step', type=int, nargs='?', required=False,
                    choices=range(1, num_of_steps),
                    metavar=f'1-{num_of_steps}',
                    default=0,
                    help='Step number. '+str(num_of_steps)+' steps in total:'+
                    '\t 1) input frames\n\t 2) vidstab\t 3) output frames')
parser.add_argument('--num-cpus', type=int, nargs='?', required=False,
                    default=num_cpus_default,
                    choices=range(1, max_cpus),
                    metavar=f'1-{max_cpus}',
                    help='Number of CPUs(processes) to use')

default_smoothing_percent_of_fps = 83
parser.add_argument('--smoothing', type=int, nargs='?', required=False,
                    default=default_smoothing_percent_of_fps,
                    choices=range(1, max_smoothing),
                    metavar=f'1-{max_smoothing}',
                    help='smoothing in percents, 100%% means FPS of the input video')

vidstab_group = parser.add_argument_group('libvidstab arguments')

vidstab_group.add_argument('--mincontrast', type=float, nargs='?', required=False,
                    default=0.3,
                    metavar=f'0.1 ... 1.0',
                    help='Libvidstab mincontrast')
stepsize = 6
vidstab_group.add_argument('--stepsize', type=int, nargs='?', required=False,
                    default=stepsize, choices=range(1, 32),
                    metavar=f'1-32',
                    help='Libvidstab stepsize')

rs_group = parser.add_argument_group('rolling shutter')

rs_group.add_argument('--scantop', type=int, nargs='?', required=False,
                    default=0, choices=[0, 1],
                    help='Scanning direction of lines in the CMOS image sensor: 0=bottom-up, 1=top-down.'
                    'Depends on how the camera was held when shooting.')
xy_dflt, roll_dflt = 0, 0
#xy_dflt, roll_dflt = 0.45, 0.64
rs_group.add_argument('--rs-lines', type=float, nargs='?', required=False,
                    default=xy_dflt,
                    help='Rolling shutter correction coefficient for translation x and y.')
rs_group.add_argument('--rs-roll', type=float, nargs='?', required=False,
                    default=roll_dflt,
                    help='Rolling shutter correction coefficient for camera roll.')
rs_group.add_argument('--rs-interpolation', type=int, nargs='?', required=False,
                    default=1, choices=range(0, 5),
                    metavar=f'1-5',
                    help='Interpolation in rolling shutter correction.')

''' Hugin projections:
    0   rectilinear
    1   cylindrical
    2   equirectangular
    3   fisheye (equidistant)
    4   stereographic
    5   mercator
    6   trans mercator
    7   sinusoidal
    8   lambert cylindrical equal area
    9   lambert equal area azimuthal
    10  albers equal area conic
    11  miller cylindrical
    12  panini
    13  architectural
    14  orthographic
    15  equisolid
    16  equirectangular panini
    17  biplane
    18  triplane
    19  panini general
    20  thoby
    21  hammer-aitoff equal area '''
## if set, create frames with other projection for a video to pass to vidstab
parser.add_argument('--vidstab-projection', type=int, nargs='?', required=False,
                    default=-1,
                    choices=range(-1, 21),
                    metavar=f'0-21',
                    help='Hugin projection number.')

parser.add_argument('-f', '--force', required=False,
                    action='store_true',
                    help='Flush cached files.')


if __name__ == '__main__':

    args = parser.parse_args()

    cfg = config.cfg = config.Configuration(parser)

    out_frms = out_frames.OutFrames(cfg)
    inframes = inp_frames.InFrames(cfg)
    vidstab = vs.Vidstab(cfg)
    rs_lines = cfg.args.rs_lines
    rs_roll = cfg.args.rs_roll

    if args.step == 0: # all stages
        ## start pipeline

        ### Step 1
        inframes.create_original_frames_and_audio()

        ### Step 2
        curr_vidstab_dir = None
        if args.vidstab_projection != -1: ## -1 is default when arg is not explicit
            inframes.create_projection_frames(cfg.frames_input, cfg.projection_dir1_frames,
                                              cfg.hugin_projects)
            videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames,
                                                                cfg.projection_dir1_vidstab_prjn)
            vidstab.analyze(videofile, cfg.projection_dir1_vidstab_prjn, cfg.projection_dir1_frames)
            curr_vidstab_dir = cfg.projection_dir1_vidstab_prjn
        else:
            vidstab.analyze(args.videofile, cfg.projection_dir1_vidstab_orig, cfg.frames_input)
            curr_vidstab_dir = cfg.projection_dir1_vidstab_orig

        ### Step 3
        ## if rolling shutter args, corrects orig frames and saves to cfg.frames_input_processed
        out_frms.compute_hugin_camera_rotations(curr_vidstab_dir)

        ### Step 4
        if float(rs_lines) > 0 or float(rs_roll) > 0: # if Rolling Shutter correction args
            curr_vidstab_dir = None
            if args.vidstab_projection != -1:
                inframes.create_projection_frames(cfg.frames_input_processed,
                                                  cfg.projection_dir2_frames,
                                                  cfg.hugin_projects_processed)
                videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir2_frames,
                                                                    cfg.projection_dir2_vidstab_prjn)
                vidstab.analyze(videofile, cfg.projection_dir2_vidstab_prjn, cfg.projection_dir2_frames)
                curr_vidstab_dir = cfg.projection_dir1_vidstab_prjn
            else:
                vidstab.analyze(args.videofile, cfg.projection_dir2_vidstab_orig, cfg.frames_input_processed)
                curr_vidstab_dir = cfg.projection_dir1_vidstab_orig

            out_frms.compute_hugin_camera_rotations_processed(curr_vidstab_dir)

        ### Step 5
        out_frms.frames()

        ### Step 6
        out_frms.video()

        ### Step 7
        out_frms.ffmpeg_filter()

        ## end pipeline




    ## TODO
        
    elif args.step == 1:
        inframes.create_original_frames_and_audio()
    elif args.step == 2:
        if args.vidstab_projection != -1: ## -1 is default when arg is not explicit
            inframes.create_projection_frames(cfg.frames_input, cfg.projection_dir1_frames)
            videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames,
                                                                cfg.projection_dir1_vidstab)
            vidstab.analyze(videofile, cfg.projection_dir1_vidstab)
        else:
            vidstab.analyze(args.videofile, cfg.projection_dir1_vidstab)
    elif args.step == 3:
        ## saves original frames with corrected rolling shutter
        out_frms.compute_hugin_camera_rotations(cfg.projection_dir1_vidstab)
    elif args.step == 4:
        if float(rs_lines) > 0 or float(rs_roll) > 0: ## if Rolling Shutter correction args
            if args.vidstab_projection != -1:
                inframes.create_projection_frames(cfg.frames_input_processed,
                                                  cfg.projection_dir2_frames)
                videofile = inframes.create_input_video_for_vidstab(cfg.projection_dir1_frames,
                                                                    cfg.projection_dir2_vidstab)
                vidstab.analyze(videofile, cfg.projection_dir2_vidstab)
            else:
                vidstab.analyze(args.videofile, cfg.projection_dir2_vidstab)

            out_frms.compute_hugin_camera_rotations_processed(cfg.projection_dir2_vidstab)
    elif args.step == 5:
        out_frms.frames()
    elif args.step == 6:
        out_frms.video()
    elif args.step == 7:
        out_frms.ffmpeg_filter()
