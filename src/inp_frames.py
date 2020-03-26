from subprocess import run
from os import path
import sys
import config
import utils


def input_frames_and_audio():
    print('\n {} \n'.format(sys._getframe().f_code.co_name))
    cfg = config.cfg
    utils.delete_files_in_dir(cfg.frames_input)

    inp = cfg.args.videofile
    oaud = path.join(cfg.audio_dir, "audio.ogg")

    ## video
    # cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp, '-qscale:v', '1',
    #         path.join(cfg.datapath, cfg.frames_input, '%06d.'+cfg.img_ext), '-y']
    cmd1 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', inp,
            path.join(cfg.datapath, cfg.frames_input, '%06d.'+cfg.img_ext), '-y']

    ## audio
    cmd2 = ['ffmpeg', '-loglevel', 'error', '-stats', '-i', cfg.args.videofile,
            '-vn', '-aq', str(3), '-y', oaud]

    run(cmd1)
    run(cmd2)


# def frames_rectilinear():
#     print('\n {} \n'.format(sys._getframe().f_code.co_name))
#     cfg = config.cfg

#     imgs = sorted(os.listdir(cfg.frames_in))
#     tasks = []
#     for i, img in enumerate(imgs):
#         filepath = 'frame_{}.pto'.format(i+1)

#         task = hugin_task(0, 0, 0, img, filepath)
#         tasks.append(task)

#     utils.delete_filepath(cfg.rectilinear_pto_path)

#     run(['pto_gen', '-o', cfg.rectilinear_pto_path,
#          path.join(cfg.frames_in, os.listdir(cfg.frames_in)[0])],
#         stderr=DEVNULL, stdout=DEVNULL)
#     run(['pto_template', '-o', cfg.rectilinear_pto_path, '--template='+cfg.pto.filepath,
#          cfg.rectilinear_pto_path], stdout=DEVNULL)
#     run(['pano_modify', '-o', cfg.rectilinear_pto_path, '--crop=AUTO', cfg.rectilinear_pto_path,
#          '--projection='+str(cfg.params['vidstab_projection_1']) ],
#         stdout=DEVNULL)

#     utils.delete_files_in_dir(cfg.frames_rectilinear)
#     cfg.current_output_path = cfg.frames_rectilinear
#     cfg.current_pto_path = cfg.rectilinear_pto_path
#     with Pool(int(cfg.params['num_processes'])) as p:
#         p.map(hugin.frames_projection, tasks)
