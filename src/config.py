import os
from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import configparser
import argparse
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

        self.vidstab_hugin_cfg = path.join(path.abspath(args.project), 'vidstab_hugin.cfg')
        if not path.isfile(self.vidstab_hugin_cfg):
            print('\nvidstab_hugin.cfg doesn\'t exist: {}'.format(self.vidstab_hugin_cfg))
            print('A template vidstab_hugin.ini in can be created using "-cp"(--create-project) option\n')
            exit()

        self.project_pto = path.join(path.abspath(args.project), self.hugin_project_dirname, 'project.pto')
        ## TODO autogeneration
        # if not path.isfile(self.project_pto):
        #     print('\nrectilinear.pto doesn\'t exist: {}'.format(self.project_pto))
        #     print('Should be a Hugin project with rectilinear projection.\n')
        #     exit()

        if not args.videofile:
            print('PROBLEM: videofile argument is missing'); print()
            parser.print_help()
            exit()
        elif not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(utils.get_fps(args.videofile)))

        cfg = configparser.ConfigParser(strict=True)
        cfg.read(self.vidstab_hugin_cfg)
        self.params = cfg['parameters']

        ## Image format
        jpeg_quality = self.params.get('jpeg_quality', None)
        if jpeg_quality:
            self.jpeg_quality = jpeg_quality
        img_format = self.params.get('img_format', None)
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
        data_dir = path.join(path.abspath(args.project), self.renders_dirname, data_dir_name)
        data_path = Path(data_dir)
        self.datapath = data_path

        self.hugin_projects = Path(path.join(data_path, 'hugin_projects'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.frames_input = Path(path.join(data_path, 'frames_input'))
        self.frames_input.mkdir(parents=True, exist_ok=True)
        self.frames_stabilized = Path(path.join(data_path, 'frames_stabilized'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(data_path, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        # self.vidstab_dir = Path(path.join(data_path, 'vidstab'))
        # self.vidstab_dir.mkdir(parents=True, exist_ok=True)
        # self.input_video = path.join(self.vidstab_dir, "input.mkv")
        self.vidstab_orig_dir = Path(path.join(data_path, 'vidstab_orig'))
        self.vidstab_orig_dir.mkdir(parents=True, exist_ok=True)

        self.output_dir = Path(path.join(data_path, 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.crops_file = path.join(self.output_dir, 'crop_margins.txt')

        self.out_video = path.join(self.output_dir, 'out_video_input_projection.mkv')
        self.out_video_orig = path.join(self.output_dir, 'out_video.mkv')
        self.out_video_filtered = path.join(self.output_dir, 'filtered_input_projection.mkv')
        self.out_video_filtered_orig = path.join(self.output_dir, 'filtered.mkv')

        self.rectilinear_pto_path = path.join(data_path, 'rectilinear.pto')
        self.processed_video = path.join(self.vidstab_orig_dir, "input_processed.mkv")

        self.frames_rectilinear = Path(path.join(data_path, 'frames_rectilinear'))
        self.frames_rectilinear.mkdir(parents=True, exist_ok=True)

        self.frames_input_processed = Path(path.join(data_path, 'frames_input_processed'))
        self.frames_input_processed.mkdir(parents=True, exist_ok=True)


cfg: Configuration = None
