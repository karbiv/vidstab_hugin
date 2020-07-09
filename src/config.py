import os
from os import path
import re
from pathlib import Path
from datatypes import HuginPTO
import utils


class Configuration:

    def __init__(self, parser):

        args = parser.parse_args()
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
        self.rectilinear_pto_path = path.join(self.workdir, 'rectilinear.pto')
        self.projection_pto_path = path.join(self.workdir, 'vidstab_projection.pto')


        self.input_dir = Path(path.join(self.data_dir, '1__input_frames'))
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.frames_input = Path(path.join(self.input_dir, 'original_frames'))
        self.frames_input.mkdir(parents=True, exist_ok=True)
        self.audio_dir = Path(path.join(self.input_dir, 'audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)


        ### Lens projections
        self.projection_video_name = "input_projection.mkv"
        ## pass 1
        self.projection_basedir1 = Path(path.join(self.data_dir, '2__lens_projection_frames_for_vidstab'))
        self.projection_basedir1.mkdir(parents=True, exist_ok=True)
        self.projection_dir1_frames = Path(path.join(self.projection_basedir1, 'frames'))
        self.projection_dir1_frames.mkdir(parents=True, exist_ok=True)
        self.projection_dir1_vidstab = Path(path.join(self.projection_basedir1, 'vidstab_pass'))
        self.projection_dir1_vidstab.mkdir(parents=True, exist_ok=True)

        self.frames_input_processed = Path(path.join(self.data_dir, '3__original_frames_rolling_shutter'))
        self.frames_input_processed.mkdir(parents=True, exist_ok=True)

        ## pass 2
        self.projection_basedir2 = Path(path.join(self.data_dir, '4__lens_projection_frames_for_vidstab'))
        self.projection_basedir2.mkdir(parents=True, exist_ok=True)

        self.projection_dir2_frames = Path(path.join(self.projection_basedir2, 'frames'))
        self.projection_dir2_frames.mkdir(parents=True, exist_ok=True)
        self.projection_dir2_vidstab = Path(path.join(self.projection_basedir2, 'vidstab_pass'))
        self.projection_dir2_vidstab.mkdir(parents=True, exist_ok=True)


        self.frames_stabilized = Path(path.join(self.data_dir, '5__stabilized_frames'))
        self.frames_stabilized.mkdir(parents=True, exist_ok=True)


        self.out_video_name = 'out_video.mkv'
        self.out_video_dir = Path(path.join(self.data_dir, '6__output_video'))
        self.out_video_dir.mkdir(parents=True, exist_ok=True)
        self.out_video = path.join(self.out_video_dir, self.out_video_name)

        self.ffmpeg_filtered_name = 'filtered.mkv'
        self.ffmpeg_filtered_dir = Path(path.join(self.data_dir, '7__ffmpeg_filtered_video'))
        self.ffmpeg_filtered_dir.mkdir(parents=True, exist_ok=True)

        ### cache info files, data in filenames
        self.vidstab_projection_prefix = 'vidstab_projection_'


cfg: Configuration = None
