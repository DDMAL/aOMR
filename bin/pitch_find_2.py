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
original_file = "/Users/gabriel/Dropbox/OMR_LU/imgs/axz/1002/original_image.tiff"
glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Dropbox/OMR_LU/imgs/axz/1002/page_glyphs.xml")

aomr_obj = AomrObject(original_file, **aomr_opts)
st_position = aomr_obj.find_staves() # staves position
staff_coords = aomr_obj.staff_coords()

# FOR LINE POSITIONS
# for l in st_position[0]['line_positions']:
#     print l

# test_data = {
#     1: {
#         'coord': [1,2,3,4],
#         'content': [{
#             'type': 'neume',
#             'form': ['clivis', '4'],
#             'coord': [213, 179, 26, 35],
#             'strt_pitch': 'E',
#             'strt_pos': 5
#         }, {
#             'type': 'neume',
#             'form': ['torculus', '2', '4'],
#             'coord': [213, 179, 26, 35],
#             'strt_pitch': 'B',
#             'strt_pos': 5
#         }]
#     }, 2: {
#         'coord': [4,5,6,7],
#         'content': [{
#             'type': '',
#             'form': [],
#             'coord': [],
#             'strt_pitch': 'A',
#             'strt_pos': ''
#         }]
#     }
# }








# meitoxml.meitoxml(mei_file, 'testfile.mei')

# FOR PITCH FINDING
pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
print len(pitch_find)
sorted_glyphs = sorted(pitch_find, key=itemgetter(1, 2))


data = {}

for s, stave in enumerate(staff_coords):
    contents = []
    for sg in sorted_glyphs:
        # print sg
        # print ("sg[1]:{0} s:{1} sg{2}".format(sg[1], s+1, sg))
        if sg[1] == s+1: 
            glyph = {   'type': sg[0].get_main_id().split('.')[0],
                        'form': sg[0].get_main_id().split('.')[1:],
                        'coord': [sg[0].offset_x, sg[0].offset_y, \
                                sg[0].offset_x+sg[0].ncols, sg[0].offset_y+sg[0].nrows],
                        'strt_pitch': sg[2],
                        'strt_pos': sg[3]}
            contents.append(glyph)
        
    data[s] = {'coord':stave, 'content':[contents]}    
print data


# mei_file = AomrMeiOutput.AomrMeiOutput(data)
# print mei_file
# meitoxml.meitoxml(mei_file, 'testfile.mei')

# for s in sorted_glyphs:
#     print s
    
#     n.attributes = {'pname': s[0], 'pitch': s[3]}
#     # print s
# print n
# print n.as_xml_string()
