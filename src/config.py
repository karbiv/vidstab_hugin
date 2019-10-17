from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import ffprobe
import configparser
import argparse


class Configuration:
    ## output video dir tree
    datapath: str = None
    ## subdirs inside self.datapath
    hugin_projects: str = None
    frames_in: str = None
    frames_stabilized: str = None
    frames_stabilized_2: str = None
    frames_projection_path: str = None
    audio_dir: str = None
    vidstab_dir: str = None
    vidstab_dir_2: str = None
    #full_input_frames: str = None
    out_video_1: str = None

    ## files
    crops_file: str = None
    vidstab_hugin_ini: str = None
    rectilinear_pto: str = None

    pto: HuginPTO = None
    first_stage_pto_path: str = None
    stab_pto_path: str = None

    fps: str = None # FPS of input video, by ffprobe
    params: configparser.SectionProxy = None # params from vidstab_hugin.ini
    args: argparse.Namespace = None

    current_pto_path = None
    current_output_projection = None


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

        self.rectilinear_pto = path.join(path.abspath(args.project), 'rectilinear.pto')
        if not path.isfile(self.rectilinear_pto):
            print('\nrectilinear.pto doesn\'t exist: {}'.format(self.rectilinear_pto))
            print('Should be a Hugin project with rectilinear projection.\n')
            exit()

        if not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(ffprobe.get_fps(args.videofile)))

        cfg = configparser.ConfigParser(strict=True)
        cfg.read(self.vidstab_hugin_ini)
        self.params = cfg['parameters']

        self.pto = HuginPTO(self.rectilinear_pto)

        if not self.pto.is_rectilinear:
            print('\nHugin project must be set to a "rectilinear" projection mode.\n')
            exit()

        self.args = args

        ## create output video subdir tree
        ##
        data_dir_name = re.sub(r'[/\\]+', '_', args.videofile).strip('_')
        data_dir = path.join(path.abspath(args.project), data_dir_name)
        data_dir = '{}_ss{}_t{}'.format(data_dir, args.seek_start or '', args.duration or '')
        data_path = Path(data_dir)
        self.datapath = data_path

        self.video_for_vidstab = path.join(self.datapath, "vidstab", "tostabilize.mkv")
        self.hugin_projects = Path(path.join(data_path, 'hugin_work_dir'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.frames_in = Path(path.join(data_path, 'frames_in'))
        self.frames_in.mkdir(parents=True, exist_ok=True)
        self.frames_stabilized = Path(path.join(data_path, 'frames_stabilized'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)
        self.frames_projection_path = Path(path.join(data_path, 'frames_projection'))
        self.frames_projection_path.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(data_path, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.vidstab_dir = Path(path.join(data_path, 'vidstab'))
        self.vidstab_dir.mkdir(parents=True, exist_ok=True)
        self.vidstab_dir_2 = Path(path.join(data_path, 'vidstab_2'))
        self.vidstab_dir_2.mkdir(parents=True, exist_ok=True)

        self.output_dir = Path(path.join(data_path, 'OUTPUT'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.crops_file = path.join(self.output_dir, 'crop_margins.txt')

        self.first_stage_pto_path = path.join(self.output_dir, 'first_stage.pto')
        self.stab_pto_path = path.join(self.output_dir, 'stab.pto')

        self.frames_stabilized_2 = Path(path.join(data_path, 'frames_stabilized_2'))
        self.frames_stabilized_2.mkdir(parents=True, exist_ok=True)

        self.projection_pto_path = path.join(data_path, 'projection.pto')
        self.frames_projection_video = path.join(self.vidstab_dir, 'projection.mkv')
        self.out_video_1 = path.join(self.output_dir, 'out_video_1.mkv')
        self.out_video_2 = path.join(self.output_dir, 'out_video_2.mkv')

        self.out_1_pto_path = path.join(data_path, 'out_1.pto')
        self.out_2_pto_path = path.join(data_path, 'out_2.pto')

        ########
        # self.vidstab_dir_3 = Path(path.join(data_path, 'vidstab_3'))
        # self.vidstab_dir_3.mkdir(parents=True, exist_ok=True)
        # self.frames_stabilized_3 = Path(path.join(data_path, 'frames_stabilized_3'))
        # self.frames_stabilized_3.mkdir(parents=True, exist_ok=True)
        # self.out_video_3 = path.join(self.output_dir, 'out_video_3.mkv')


cfg: Configuration = None
