from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import configparser
import argparse
import utils


class Configuration:

    def __init__(self, args):

        if not path.isdir(args.project):
            print('\nNot a directory: {}'.format(args.project))
            print('Should be a directory containing vidstab_hugin.ini and rectilinear.pto(Hugin project)')
            print('Output subdirs will be created in that dir.\n')
            exit()
        else:
            args.project = path.abspath(args.project)

        self.vidstab_hugin_ini = path.join(path.abspath(args.project), 'vidstab_hugin.ini')
        if not path.isfile(self.vidstab_hugin_ini):
            print('\nvidstab_hugin.ini doesn\'t exist: {}'.format(self.vidstab_hugin_ini))
            print('A template vidstab_hugin.ini in can be created using "-cp"(--create-project) option\n')
            exit()

        self.project_pto = path.join(path.abspath(args.project), 'project.pto')
        if not path.isfile(self.project_pto):
            print('\nrectilinear.pto doesn\'t exist: {}'.format(self.project_pto))
            print('Should be a Hugin project with rectilinear projection.\n')
            exit()

        if not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(utils.get_fps(args.videofile)))

        cfg = configparser.ConfigParser(strict=True)
        cfg.read(self.vidstab_hugin_ini)
        self.params = cfg['parameters']

        self.pto = HuginPTO(self.project_pto)
        self.args = args

        ## create output video subdir tree
        ##
        data_dir_name = re.sub(r'[/\\]+', '_', args.videofile).strip('_')
        data_dir = path.join(path.abspath(args.project), data_dir_name)
        data_path = Path(data_dir)
        self.datapath = data_path

        self.hugin_projects = Path(path.join(data_path, 'hugin_projects'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.frames_in = Path(path.join(data_path, 'frames_in'))
        self.frames_in.mkdir(parents=True, exist_ok=True)
        self.frames_stabilized = Path(path.join(data_path, 'frames_stabilized'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(data_path, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.vidstab_dir = Path(path.join(data_path, 'vidstab'))
        self.vidstab_dir.mkdir(parents=True, exist_ok=True)
        self.vidstab_orig_dir = Path(path.join(data_path, 'vidstab_orig'))
        self.vidstab_orig_dir.mkdir(parents=True, exist_ok=True)

        self.output_dir = Path(path.join(data_path, 'OUTPUT'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.out_video = path.join(self.output_dir, 'out_video.mkv')
        self.out_video_orig = path.join(self.output_dir, 'out_video_no_input_projection.mkv')
        self.out_video_filtered = path.join(self.output_dir, 'filtered.mkv')
        self.out_video_filtered_orig = path.join(self.output_dir, 'filtered_no_input_projection.mkv')
        self.crops_file = path.join(self.output_dir, 'crop_margins.txt')

        self.projection_pto_path = path.join(data_path, 'projection.pto')
        self.rectilinear_pto_path = path.join(data_path, 'rectilinear.pto')
        self.input_video = path.join(self.vidstab_dir, "input.mkv")

        self.frames_projection = Path(path.join(data_path, 'frames_projection'))
        self.frames_projection.mkdir(parents=True, exist_ok=True)


cfg: Configuration = None
