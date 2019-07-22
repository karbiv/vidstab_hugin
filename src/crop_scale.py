from os import path
from subprocess import run
import config
from utils import ff, delete_files_in_dir

def crop_scale_output():
    cfg = config.cfg
    
    ivid = path.join(cfg.output_dir, 'output.mkv')
    ovid = path.join(cfg.output_dir, 'scaled.mkv')

    min_cropw, min_croph = calculate_crop(cfg.crops_file)

    #exit()
    
    scalew = 1920
    coeff = scalew/min_cropw
    scaleh = ff(round(min_croph*coeff))

    crf = str(15)
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
    filts = 'crop={}:{},scale={}:{}'.format(min_cropw, min_croph, scalew, scaleh)
    
    if path.isfile(iaud):
        run(['ffmpeg', '-loglevel', 'info', '-i', ivid, '-i', iaud,
             '-vf', filts, '-c:v', 'libx264', '-crf', crf, '-c:a', 'copy', '-y', ovid])
    else:
        run(['ffmpeg', '-loglevel', 'info', '-i', ivid,
             '-vf', filts, '-c:v', 'libx264', '-crf', crf, '-an', '-y', ovid])


# TODO calculate zoom for each frame, instead of minimal crop
def calculate_crop(crops_filepath):
    f = open(crops_filepath, 'r')
    lines = f.read().splitlines()
    crop_widths = []
    crop_heights = []
    for line in lines:
        w, h = line.split()
        crop_widths.append(int(w))
        crop_heights.append(int(h))
    min_cw, min_ch = ff(min(crop_widths)), ff(min(crop_heights))
    #max_cw, max_ch = ff(max(crop_widths)), ff(max(crop_heights))

    #print(max_cw, max_ch)

    return min_cw, min_ch
