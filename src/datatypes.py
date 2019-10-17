from dataclasses import dataclass
from collections.abc import Mapping
import math


@dataclass
class transform:
    x: float
    y: float
    roll: float


@dataclass
class hugin_task:
    # roll: float
    # yaw: float
    # pitch: float
    img: str
    pto_file: str


class HuginPTO:
    '''Hugin project, PanoTools Optimizer, "pto".
    Collects parameters only for the first image in project,
    which represents a video frame in context of this program.'''
    
    filepath = None
    is_rectilinear = False
    pto_lines = []
    canvas_w, canvas_h = None, None
    crop_l = None # left
    crop_r = None # right
    crop_t = None # top
    crop_b = None # bottom
    crop_w, crop_h = None, None
    orig_w, orig_h = None, None
    half_hfov, half_vfov = None, None
    canv_half_hfov, canv_half_vfov = None, None
    lens_d, lens_e = None, None
    interpolation = 0

    def __init__(self, filepath):
        self.parse_pto(filepath)
    
    def parse_pto(self, filepath):
        crop_list = None
        f = open(filepath)
        self.filepath = filepath

        lines = f.read().splitlines()
        for line in lines:            
            line = str(line.strip())
            if line.startswith('#'):
                continue
            else:
                self.pto_lines.append(line)

        first_image_found = False
        for line in self.pto_lines:
            if line.startswith('m'):
                parts = line.split()[1:]
                for p in parts:
                    if p.startswith('i'):
                        self.interpolation = int(p[1:])
            if line.startswith('p'):
                parts = line.split()[1:]
                for p in parts:
                    if p.startswith('f'):
                        if p[1:] == '0':
                            self.is_rectilinear = True
                    elif p.startswith('w'):
                        self.canvas_w = int(p[1:])
                    elif p.startswith('h'):
                        self.canvas_h = int(p[1:])
                    elif p.startswith('S'):
                        crop_list = p[1:].split(',')
                    elif p.startswith('v'):
                        self.canv_half_hfov = float(p[1:])/2
            
            if not first_image_found and line.startswith('i'):
                parts = line.split()
                if parts:
                    parts = parts[1:]
                    for p in parts:
                        if p.startswith('w'):
                            self.orig_w = int(p[1:])
                        if p.startswith('h'):
                            self.orig_h = int(p[1:])
                        if p.startswith('v'):
                            self.half_hfov = float(p[1:])/2
                        if p.startswith('d'):
                            self.lens_d = float(p[1:])
                        if p.startswith('e'):
                            self.lens_e = float(p[1:])

        self.unpack_crop(crop_list)
        f.close()
        self.calculate_crop_vert_fov(self.half_hfov)

    def calculate_crop_vert_fov(self, half_hfov):
        horizontal_max_tan = math.tan(math.radians(half_hfov))
        tan_pix = horizontal_max_tan/(self.crop_w/2)
        vert_max_tan = (self.crop_h/2)*tan_pix
        self.half_vfov = math.degrees(math.atan(vert_max_tan))
    
    def unpack_crop(self, crop):
        self.crop_l = int(crop[0])
        self.crop_r = int(crop[1])
        self.crop_t = int(crop[2])
        self.crop_b = int(crop[3])
        self.crop_w = self.crop_r - self.crop_l
        self.crop_h = self.crop_b - self.crop_t
