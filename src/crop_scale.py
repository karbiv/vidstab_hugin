from os import path
from subprocess import run
import config
from utils import ff

def crop_scale_output():
    cfg = config.cfg
    
    ivid = path.join(cfg.output_dir, 'output.mkv')
    ovid = path.join(cfg.output_dir, 'scaled.mkv')

    cropw, croph = calculate_crop(cfg.crops_file)
    
    scalew = 1920
    coeff = scalew/cropw
    scaleh = ff(round(croph*coeff))

    crf = str(24)
    iaud = path.join(cfg.audio_dir, 'audio.ogg')
    filts = 'crop={}:{},scale={}:{}'.format(cropw, croph, scalew, scaleh)
    
    if path.isfile(iaud):
        run(['ffmpeg', '-loglevel', 'info', '-i', ivid, '-i', iaud,
             '-vf', filts, '-c:v', 'libx264', '-crf', crf, '-c:a', 'copy', '-y', ovid])
    else:
        run(['ffmpeg', '-loglevel', 'info', '-i', ivid,
             '-vf', filts, '-c:v', 'libx264', '-crf', crf, '-an', '-y', ovid])


def calculate_crop(crops_filepath):
    f = open(crops_filepath, 'r')
    lines = f.read().splitlines()
    crop_widths = []
    crop_heights = []
    for line in lines:
        w, h = line.split()
        crop_widths.append(int(w))
        crop_heights.append(int(h))
    cw, ch = ff(min(crop_widths)), ff(min(crop_heights))

    return cw, ch
