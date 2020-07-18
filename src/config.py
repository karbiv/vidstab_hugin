import os
from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import utils


class Configuration:

    def __init__(self, args):

        self.args = args
        self.project_pto = args.pto

        if not path.isfile(args.videofile):
            print('\nFilepath doesn\'t exist: {}\n'.format(args.videofile)); exit()
        else:
            self.fps = str(round(utils.get_fps(args.videofile)))
            
        self.pto = HuginPTO(self.project_pto)

        ## create output video subdir tree
        data_dir_name = re.sub(r'[/\\.]+', '_', args.videofile).strip('_')
        self.data_dir = path.join(path.abspath(args.workdir), data_dir_name)
        self.workdir = Path(path.join(self.data_dir, '0__workdir'))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.hugin_projects = Path(path.join(self.workdir, 'hugin_ptos'))
        self.hugin_projects.mkdir(parents=True, exist_ok=True)
        self.hugin_projects_processed = Path(path.join(self.workdir, 'hugin_ptos_processed'))
        self.hugin_projects_processed.mkdir(parents=True, exist_ok=True)
        self.projection_pto_path = path.join(self.workdir, 'vidstab_projection.pto')

        self.input_dir = Path(path.join(self.data_dir, '1__input_frames'))
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.frames_input = Path(path.join(self.input_dir, 'original_frames'))
        self.frames_input.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(self.input_dir, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        ### Lens projections
        self.projection_video_name = "input_projection.mkv"

        self.projection_basedir1 = Path(path.join(self.data_dir, '2__lens_projection_frames_for_vidstab'))
        self.projection_basedir1.mkdir(parents=True, exist_ok=True)
        self.prjn_dir1_frames = Path(path.join(self.projection_basedir1, 'frames'))
        self.prjn_dir1_frames.mkdir(parents=True, exist_ok=True)
        self.prjn_dir1_vidstab_orig = Path(path.join(self.projection_basedir1, 'vidstab_pass_orig'))
        self.prjn_dir1_vidstab_orig.mkdir(parents=True, exist_ok=True)
        self.prjn_dir1_vidstab_prjn = Path(path.join(self.projection_basedir1, 'vidstab_pass_prjn'))
        self.prjn_dir1_vidstab_prjn.mkdir(parents=True, exist_ok=True)

        self.rolling_shutter = Path(path.join(self.data_dir, '3__rolling_shutter'))
        self.rolling_shutter.mkdir(parents=True, exist_ok=True)
        self.frames_input_processed = Path(path.join(self.rolling_shutter, 'original_frames_processed'))
        self.frames_input_processed.mkdir(parents=True, exist_ok=True)
        self.rectilinear_pto_path = path.join(self.rolling_shutter, 'rectilinear.pto')

        self.projection_basedir2 = Path(path.join(self.data_dir, '4__lens_projection_frames_for_vidstab'))
        self.projection_basedir2.mkdir(parents=True, exist_ok=True)

        self.prjn_dir2_frames = Path(path.join(self.projection_basedir2, 'frames'))
        self.prjn_dir2_frames.mkdir(parents=True, exist_ok=True)
        self.projection_dir2_vidstab_orig = Path(path.join(self.projection_basedir2, 'vidstab_pass_orig'))
        self.projection_dir2_vidstab_orig.mkdir(parents=True, exist_ok=True)
        self.prjn_dir2_vidstab_prjn = Path(path.join(self.projection_basedir2, 'vidstab_pass_prjn'))
        self.prjn_dir2_vidstab_prjn.mkdir(parents=True, exist_ok=True)

        self.frames_stabilized = Path(path.join(self.data_dir, '5__stabilized_frames'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)

        self.out_video_name = 'out_video.mkv'
        self.out_video_dir = Path(path.join(self.data_dir, '6__output_video'))
        self.out_video_dir.mkdir(parents=True, exist_ok=True)
        self.out_video = path.join(self.out_video_dir, self.out_video_name)

        self.ffmpeg_filtered_name = 'filtered.mkv'
        self.ffmpeg_filtered_dir = Path(path.join(self.data_dir, '7__ffmpeg_filtered_video'))
        self.ffmpeg_filtered_dir.mkdir(parents=True, exist_ok=True)

        ## saved command args file
        self.cmd_args = path.join(self.workdir, 'cmd_args.txt')

cfg: Configuration = None
