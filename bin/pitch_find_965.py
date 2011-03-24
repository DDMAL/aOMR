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
    'staff_finder': 0,
    'staff_removal': 0,
    'binarization': 0,
    'discard_size': 6
}


original_file = "/Users/gabriel/Documents/8_CODE/aOMR/imgs/965/PC_0965/original_image.tiff"
glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Documents/8_CODE/aOMR/imgs/965/PC_0965/page_glyphs.xml")


aomr_obj = AomrObject(original_file, **aomr_opts)
s = aomr_obj.find_staves()
print s
# tree = etree.parse(glyph_file)
# print etree.tostring(tree)

for g in glyphs:
    if g.get_main_id().split('.')[0] != '_group':
        print g.get_main_id().split('.'), g.offset_x, g.offset_y, g.ncols, g.nrows