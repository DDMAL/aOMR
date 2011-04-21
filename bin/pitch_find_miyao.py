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
from gamera.toolkits.aomr_tk import AomrMeiOutput
from gamera import knn, plugin
from gamera import classify
from gamera.symbol_table import SymbolTable
import tempfile
import shutil
import random
from lxml import etree
from operator import itemgetter, attrgetter
import pymei
from pymei.Components import Modules
from pymei.Helpers import template
from pymei.Export import meitoxml

import logging
lg = logging.getLogger('pitch_find_miyao')
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

#FILES TO PROCESS
original_file = "/Users/gabriel/Dropbox/OMR_LU/imgs/OK/1001/original_image.tiff"
glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Dropbox/OMR_LU/imgs/OK/1001/page_glyphs.xml")
file_name = (original_file.split('/')[-2] + '_' + original_file.split('/')[-1])


# CREATING AOMR OBJECT, FINDING STAVES, AND RETRIEVING STAFF COORDINATES
aomr_obj = AomrObject(original_file, **aomr_opts)
st_position = aomr_obj.find_staves() # staves position
staff_coords = aomr_obj.staff_coords()

sorted_glyphs = aomr_obj.miyao_pitch_find(glyphs, aomr_opts.get('discard_size'))

# PITCH FINDING
# pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
# print len(pitch_find)
# sorted_glyphs = sorted(proc_glyphs, key=itemgetter(1, 2))



# STRUCTURING THE DATA IN JSON
data = {}
for s, stave in enumerate(staff_coords):
    contents = []
    for sg in sorted_glyphs:
        # lg.debug("sg[1]:{0} s:{1} sg{2}".format(sg[1], s+1, sg))
        # structure: g, stave, g.offset_x, note, strt_pos
        if sg[1] == s+1: 
            glyph = {   'type': sg[0].get_main_id().split('.')[0],
                        'form': sg[0].get_main_id().split('.')[1:],
                        'coord': [sg[0].offset_x, sg[0].offset_y, \
                                sg[0].offset_x+sg[0].ncols, sg[0].offset_y+sg[0].nrows],
                        'strt_pitch': sg[4],
                        'strt_pos': sg[3]}
            contents.append(glyph)  
    data[s] = {'coord':stave, 'content':contents}    
print data
print

# CREATING THE MEI FILE
mei_file = AomrMeiOutput.AomrMeiOutput(data, file_name)
# print mei_file
# print


meitoxml.meitoxml(mei_file.md, '/Users/gabriel/Desktop/' + file_name.split('.')[0]+'.mei')













