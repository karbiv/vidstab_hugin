import os
from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import utils


class Configuration:

    def __init__(self, args):

        self.args = args

        self.project_pto = path.join(args.workdir, args.pto_name)
        args.pto = self.project_pto

        if not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(utils.get_fps(args.videofile)))

        self.frames_total = 0

        self.pto = HuginPTO(self.project_pto)

        ## create output video subdir tree
        self.data_dir_name = re.sub(r'[/\\.]+', '_', args.videofile).strip('_')
        self.data_dir = path.join(path.abspath(args.workdir), self.data_dir_name)

        # self.workdir = Path(path.join(self.data_dir, '0__workdir'))
        # self.workdir.mkdir(parents=True, exist_ok=True)

        ## saved command args file
        self.cmd_args = path.join(self.data_dir, 'cmd_args.txt')

        self.input_dir = Path(path.join(self.data_dir, '1__input_frames'))
        self.input_dir.mkdir(parents=True, exist_ok=True)

        self.vidstab1_dir = Path(path.join(self.data_dir, '2__vidstab_detect'))
        self.vidstab1_dir.mkdir(parents=True, exist_ok=True)

        self.camera_moves_path = Path(path.join(self.data_dir, '3__camera_moves'))
        self.camera_moves_path.mkdir(parents=True, exist_ok=True)

        self.trf_rel_path = path.join(self.camera_moves_path, 'trf_rel.pickle')
        self.trf_abs_filtered_path = path.join(self.camera_moves_path, 'trf_abs_filtered.pickle')

        self.projection_pto_path = path.join(self.camera_moves_path, 'vidstab_projection.pto')
        self.rectilinear_pto_path = path.join(self.camera_moves_path, 'rectilinear.pto')
        
        self.hugin_projects = Path(path.join(self.camera_moves_path, 'hugin_ptos'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.frames_processed = Path(path.join(self.camera_moves_path, 'frames_processed'))
        self.frames_processed.mkdir(parents=True, exist_ok=True)

        self.vidstab2_dir = Path(path.join(self.data_dir, '4__vidstab_detect'))
        self.vidstab2_dir.mkdir(parents=True, exist_ok=True)

        self.frames_stabilized = Path(path.join(self.data_dir, '5__stabilized_frames'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)

        self.out_video_name = 'out_video.mkv'
        self.out_video_dir = self.data_dir


cfg: Configuration = None
