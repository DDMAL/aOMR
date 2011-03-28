from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
from gamera import knn
import threading
import datetime
import time
import re
from gamera.knn_editing import edit_mnn_cnn
from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aomr_tk import AomrObject
from gamera import knn, plugin
from gamera import classify
from gamera.symbol_table import SymbolTable
import tempfile
import shutil
import random
from lxml import etree

import logging
lg = logging.getLogger('pitch_find_965')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)


aomr_opts = {
    'lines_per_staff': 4,
    'staff_finder': 0, # 0: Miyao
    'staff_removal': 0,
    'binarization': 0,
    'discard_size': 12
}

# DDMAL
# original_file = "/Users/gabriel/Documents/1_CODE/2_aOMR/imgs/735/original_image.tiff"
# glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Documents/1_CODE/2_aOMR/imgs/735/page_glyphs.xml")

#CASA
original_file = "/Users/gabriel/Documents/8_CODE/aOMR/imgs/735/original_image.tiff"
glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Documents/8_CODE/aOMR/imgs/735/page_glyphs.xml")


aomr_obj = AomrObject(original_file, **aomr_opts)

st_position = aomr_obj.find_staves() # staves position

pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))



# av_punctum = aomr_obj.average_punctum(glyphs) # page average punctum size

# glyphs_center_of_mass = aomr_obj.x_projection_vector(glyphs, av_punctum, aomr_opts.get('discard_size'))






# for g in glyphs:
#     if g.get_main_id().split('.')[0] != '_group':
#         # print g.get_main_id().split('.'), g.offset_x, g.offset_y, g.ncols, g.nrows
#         pass
#         
