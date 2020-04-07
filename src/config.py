import os
from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import utils


class Configuration:

    hugin_project_dirname = 'hugin_pto'
    renders_dirname = 'renders'
    img_ext = '' # extension important for video tools to detect format to save
    is_jpeg = False
    nona_opts = None
    jpeg_quality = 99

    def __init__(self, parser):

        args = parser.parse_args()
        args.project = os.getcwd()

        self.project_pto = path.join(path.abspath(args.project), self.hugin_project_dirname, 'project.pto')

        if not args.videofile:
            print('PROBLEM: videofile argument is missing'); print()
            parser.print_help()
            exit()
        elif not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(utils.get_fps(args.videofile)))

        ## Image format
        jpeg_quality = args.jpeg_quality
        if jpeg_quality:
            self.jpeg_quality = jpeg_quality
        img_format = args.img_format
        if img_format:
            self.img_ext = img_format.strip('.').lower()
            if self.img_ext.startswith('jp'):
                self.is_jpeg = True
                self.nona_opts = ['nona', '-g', '-i', '0', '-m', 'JPEG', '-r', 'ldr', '-z', self.jpeg_quality]
            elif self.img_ext.startswith('png'):
                self.nona_opts = ['nona', '-g', '-i', '0', '-m', 'PNG', '-r', 'ldr']
            elif self.img_ext.startswith('tif'):
                self.img_ext = 'tif'
                self.nona_opts = ['nona', '-g', '-i', '0', '-m', 'TIFF', '-r', 'ldr']
            else:
                print('Error: wrong image format for "img_format" parameter.')
                exit()
        else:
            self.img_ext = 'tif'
            self.nona_opts = ['nona', '-g', '-i', '0', '-m', 'TIFF', '-r', 'ldr']

        self.pto = HuginPTO(self.project_pto)
        self.args = args

        ## create output video subdir tree
        ##
        data_dir_name = re.sub(r'[/\\.]+', '_', args.videofile).strip('_')
        self.data_dir = path.join(path.abspath(args.project), self.renders_dirname, data_dir_name)
        self.workdir = Path(path.join(self.data_dir, 'workdir'))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.hugin_projects = Path(path.join(self.workdir, 'hugin_ptos'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.rectilinear_pto_path = path.join(self.workdir, 'rectilinear.pto')
        self.projection_pto_path = path.join(self.workdir, 'vidstab_projection.pto')


        self.input_dir = Path(path.join(self.data_dir, '1__original_frames_and_audio'))
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.frames_input = Path(path.join(self.input_dir, 'frames'))
        self.frames_input.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(self.input_dir, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        ### Lens projections
        self.projection_video_name = "input_projection.mkv"
        ## pass 1
        self.projection_basedir1 = Path(path.join(self.data_dir, '2__lens_projection_frames'))
        self.projection_basedir1.mkdir(parents=True, exist_ok=True)
        self.projection_dir1_frames = Path(path.join(self.projection_basedir1, 'projection_frames'))
        self.projection_dir1_frames.mkdir(parents=True, exist_ok=True)
        self.projection_dir1_vidstab = Path(path.join(self.projection_basedir1, 'vidstab_pass'))
        self.projection_dir1_vidstab.mkdir(parents=True, exist_ok=True)
        ## pass 2
        self.projection_basedir2 = Path(path.join(self.data_dir, '3__lens_projection_frames_corrected_rolling_shutter'))
        self.projection_basedir2.mkdir(parents=True, exist_ok=True)
        self.frames_input_processed = Path(path.join(self.projection_basedir2, 'original_frames_corrected_rolling_shutter'))
        self.frames_input_processed.mkdir(parents=True, exist_ok=True)
        self.projection_dir2_frames = Path(path.join(self.projection_basedir2, 'projection_frames'))
        self.projection_dir2_frames.mkdir(parents=True, exist_ok=True)
        self.projection_dir2_vidstab = Path(path.join(self.projection_basedir2, 'vidstab_pass'))
        self.projection_dir2_vidstab.mkdir(parents=True, exist_ok=True)

        self.frames_stabilized = Path(path.join(self.data_dir, '4__stabilized_lens_projection_frames'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)

        self.out_video_name = 'out_video.mkv'
        self.out_video_filtered_name = 'filtered.mkv'
        self.out_video_dir = Path(path.join(self.data_dir, '5__output'))
        self.out_video_dir.mkdir(parents=True, exist_ok=True)
        self.out_video = path.join(self.out_video_dir, self.out_video_name)


cfg: Configuration = None
