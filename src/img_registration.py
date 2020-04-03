import numpy as np
import matplotlib.pyplot as plt
import math

from skimage import data
from skimage.feature import register_translation
from skimage.feature.register_translation import _upsampled_dft
from scipy.ndimage import fourier_shift
from skimage import io as skio
import skimage.transform as sktf

img1 = skio.imread('./000004.png', plugin='pil')
img2 = skio.imread('./000005.png', plugin='pil')

# pixel precision first
shifts1, error, diffphase = register_translation(img1, img2, upsample_factor=10)
print(f"Detected pixel offset (y, x): {shifts1}")

shp = img1.shape
radius = round(shp[0]/2)
polar1 = sktf.warp_polar(img1, radius=radius, multichannel=True,
                         #scaling='log'
)

## translated frame to detect rotation
trf = sktf.SimilarityTransform(translation=(shifts1[1], 0-shifts1[0]))
tr_frm = sktf.warp(img2, trf)
polar2 = sktf.warp_polar(tr_frm, radius=radius, multichannel=True,
                         #scaling='log'
)

shifts2, error, phasediff = register_translation(polar1, polar2, upsample_factor=30)
print("Recovered value for counterclockwise rotation: " f"{shifts2[0]}")
print(shifts2)
#print(error, phasediff)
print(math.degrees(-0.009752))
