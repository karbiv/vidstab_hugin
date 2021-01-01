# ;;; Hugin projection numbers used
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

from os import path, cpu_count
from argparse import ArgumentParser, Action, SUPPRESS

class VideoFileAction(Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if '.pto' in value[0]:
            print('First positional option must be a Hugin project file path(*.pto), with rectilinear projection.')
            print('Second option must be a file path of video to stabilize;')
            exit()
        setattr(namespace, self.dest, path.abspath(value[0]))


max_cpus = 32
max_smoothing = 150
default_smoothing_percent_of_fps = 71
stepsize = 6
xy_dflt, roll_dflt = 0, 0

if cpu_count() == 2:
    num_cpus_default = 1
elif cpu_count() == 4:
    num_cpus_default = 3
else:
    num_cpus_default = cpu_count() - 2


def init_cmd_args(parser):
    pos_group = parser.add_argument_group('positional arguments')

    pos_group.add_argument('videofile', type=str, nargs=1,
                           metavar='input_video_file',
                           action=VideoFileAction,
                           help='A path to video file to stabilize;')

    parser.add_argument('--workdir', type=str, nargs='?', required=True,
                        help='Path to where video render work is done;')

    parser.add_argument('--num-cpus', type=int, nargs='?', required=False,
                        default=num_cpus_default,
                        choices=range(1, max_cpus),
                        metavar=f'1-{max_cpus}',
                        help='Number of CPUs(processes) to use')

    parser.add_argument('--smoothing', type=int, nargs='?', required=False,
                        default=default_smoothing_percent_of_fps,
                        choices=range(1, max_smoothing),
                        metavar=f'1-{max_smoothing}',
                        help='smoothing in percents, 100%% means FPS of the input video')

    vidstab_group = parser.add_argument_group('libvidstab arguments')

    vidstab_group.add_argument('--vs-mincontrast', type=float, nargs='?', required=False,
                               default=0.4,
                               metavar=f'0.1 ... 1.0',
                               help='Libvidstab mincontrast')

    vidstab_group.add_argument('--vs-stepsize', type=int, nargs='?', required=False,
                               default=stepsize, choices=range(1, 32),
                               metavar=f'1-32',
                               help='Libvidstab stepsize')

    rs_group = parser.add_argument_group('rolling shutter')

    rs_group.add_argument('--rs-topdown', required=False,
                          action='store_true',
                          default=False,
                          help='Scanning direction of lines in the CMOS image sensor: 0=bottom-up, 1=top-down.'
                          'Depends on how the camera was held when shooting.')

    rs_group.add_argument('--rs-xy', type=float, nargs='?', required=False,
                          default=xy_dflt,
                          help='Rolling shutter correction coefficient for translation x and y.')
    rs_group.add_argument('--rs-roll', type=float, nargs='?', required=False,
                          default=roll_dflt,
                          help='Rolling shutter correction coefficient for camera roll.')
    rs_group.add_argument('--rs-interpolation', type=int, nargs='?', required=False,
                          default=1, choices=range(0, 5),
                          metavar=f'1-5',
                          help='Interpolation in rolling shutter correction.')

    '''Hugin projection number'''
    ## if set, create frames with other projection for a video to vidstab
    parser.add_argument('--vidstab-prjn', type=int, nargs='?', required=False,
                        default=-1,
                        choices=range(-1, 21),
                        metavar=f'0-21',
                        help='Hugin projection number.')

    parser.add_argument('--force-upd', required=False,
                        action='store_true',
                        help='Flush cached files.')

    parser.add_argument('--outfilter', type=str, nargs='?', required=False,
                        default='',
                        metavar="'w_crop_coeff:h_crop_coeff:width_pixels'",
                        help="""FFMPEG crop/scale filtering of a rendered video.
String of 3 numbers separated by colon(':').
'width_crop_coeff:height_crop_coeff:width_pixels'
Crop multipliers are equal or less than 1.0, width and height are multiplied by coeffs to define inner rectangle to crop.
'width_pixels' defines pixel width an out video is scaled to.""")

    ## dev arguments
    parser.add_argument('--step', required=False, type=int, help=SUPPRESS, default=0)

    parser.add_argument('-v', '--verbose', required=False,
                        default=False, action='store_true',
                        help='Show info message, FFMPEG option')

    parser.add_argument('--with-audio', required=False, default=False,
                        action='store_true',
                        help='Copy audio stream(if exists) from input video to output video.')
