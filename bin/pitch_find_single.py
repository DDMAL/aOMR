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

def main(original_file, page_file, outdir, pitch_find_algorithm, exceptions):
    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': 0, # 0: Miyao
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12,
        'exceptions': exceptions
    }

    #FILES TO PROCESS
    glyphs = gamera_xml.glyphs_from_xml(page_file)
    file_name = (original_file.split('/')[-2] + '_' + original_file.split('/')[-1])


    # CREATING AOMR OBJECT, FINDING STAVES, AND RETRIEVING STAFF COORDINATES
    aomr_obj = AomrObject(original_file, **aomr_opts)
    st_position = aomr_obj.find_staves() # staves position
    staff_coords = aomr_obj.staff_coords()

    # staff_non_parallel = aomr_obj.staff_no_non_parallel(glyphs)
    # print staff_non_parallel


    if pitch_find_algorithm == 'Miyao':
        sorted_glyphs = aomr_obj.miyao_pitch_find(glyphs, aomr_opts['discard_size'])
    elif pitch_find_algorithm == 'AvLines':
        sorted_glyphs = aomr_obj.pitch_find(glyphs, st_position, aomr_opts['discard_size'])


    for g in sorted_glyphs:
        # print g
        glyph = g[0]
        glyph_id = glyph[0]
        glyph_staff = g[1]
        glyph_position = g[3]
        glyph_com = g[5]
        glyph_projection = g[4]
        
        if glyph_staff == 1 and glyph_position == 6:        
            lg.debug("\nGLYPH: {0} STAFF: {1} POSITION: {2} COM: {3} PROJECTION: {4}".format(glyph_id, glyph_staff, glyph_position, glyph_com, glyph_projection))
        
        
            
            
            
            
    #         
    #         
    #         
    # # STRUCTURING THE DATA IN JSON
    # data = {}
    # for s, stave in enumerate(staff_coords):
    #     contents = []
    #     for glyph, staff, offset, strt_pos, note, projection, center_of_mass in sorted_glyphs:
    #         glyph_id = glyph.get_main_id()
    #         if glyph_id[0] == 'neume':
    #             print glyph_id, center_of_mass, projection
    #         
            
            
            
            
    # CREATING THE MEI FILE
   #  mei_file = AomrMeiOutput.AomrMeiOutput(data, file_name)
    # meitoxml.meitoxml(mei_file.md, os.path.join(outdir, file_name.split('.')[0]+'.mei'))



if __name__ == "__main__":
    usage = "%prog path_to_image path_to_page_xml output_dir pitch_find_algorithm exceptions"
    opts = OptionParser(usage = usagek,
    options, args = opts.parse_args()
    
    if not args:
        opts.error("You must supply arguments to this script.")
    
    if not args[0]:
        opts.error("You must supply a path to an image.")
    if not args[1]:
        opts.error("You must supply a pagexml file")
    if not args[2]:
        opts.error("You must supply an output directory.")

    main(args[0], args[1], args[2], args[3], args[4])
    










