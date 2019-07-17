
from subprocess import run, check_output


def get_fps(filepath):
    ''' ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate infile '''
    
    out = check_output(['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0',
                        '-show_entries', 'stream=r_frame_rate', filepath])
    out = out.strip().split(b'/')
    if len(out) == 1:
        return float(out[0])
    elif len(out) == 2:
        return float(out[0])/float(out[1])
