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
from operator import itemgetter, attrgetter

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

#DDMAL
original_file = "/Users/gabriel/Dropbox/OMR_LU/imgs/axz/1000/original_image.tiff"
glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Dropbox/OMR_LU/imgs/axz/1000/page_glyphs.xml")

aomr_obj = AomrObject(original_file, **aomr_opts)
st_position = aomr_obj.find_staves() # staves position
pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))

print len(pitch_find)
sorted_glyphs = sorted(pitch_find, key=itemgetter(1, 2))
for s in sorted_glyphs:
    print s

