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



def main(original_file, page_file, outdir, pitch_find_algorithm, exceptions, required_pos):
    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': 0, # 0: Miyao
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12,
        'exceptions': exceptions
    }

    # global las
    # las = []
    required_pos = int(required_pos)
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

    no_g = 0.0
    no_st = 0.0
    total = 0.0
    diff = 0.0

    for g in sorted_glyphs:
        # print g
        glyph = g[0]
        glyph_id = glyph.get_main_id()
        glyph_stave = g[1]
        glyph_position = g[3]
        glyph_com = g[5]
        glyph_projection = g[4]
        # print glyph_id, glyph_position, required_pos
        
        if glyph_id.split('.')[0] == 'neume' and glyph_position == required_pos:# and glyph_stave == 1:
            # print 'XXX'
            no_g += 1
            
            # lg.debug("GLYPH: {0} STAVE: {1} POSITION: {2} COM: {3} PROJECTION: {4}".format(glyph_id, glyph_stave, glyph_position, glyph_com, glyph_projection))
            adding_distribution(glyph.offset_y, glyph_projection)
            
    # lg.debug("DISTRIBUTION OF GLYPHS ACROSS THE PAGE:\n{0}".format(page_dist))
    # lg.debug("STAFF_COORDS: {0}".format(st_position))
    proc_st_pos(st_position)

    # center_of_mass = (aomr_obj.center_of_mass(page_dist))
    # for i, pd in enumerate(page_dist[151:213]):
    #     print i+151, pd
    # lg.debug("\nNUMBER OF GLYPHS: {0}\nCENTER OF MASS: {1}".format(no_g, center_of_mass))    
    # print center_of_mass

    for i, stave in enumerate(las):
        init = stave[0]
        end = stave[-1]
        proj_by_stave = page_dist[init:end]
        for p in proj_by_stave:
            if p != 0:
                center_of_mass = (aomr_obj.center_of_mass(proj_by_stave))
                diff = center_of_mass + init - las[i][required_pos]
                no_st += 1
                break
            else:
                diff = 0
        # print ('NOMINAL POSITION: {0}, ACTUAL POSITION: {1}'.format(center_of_mass + init, las[i][required_pos]))
        # print ('STAVE: {0} DIFF: {1}'.format(i, diff))
        # print
        total = total + diff
        if no_st == 0:
            no_st = 1
    print total, no_st, total/no_st
    avg_pos_page.append(total/no_st)
    total = 0
    
def adding_distribution(offset_y, glyph_projection):
    """Adds the projection of previous glyphs to make the peak and valleys for a given row
    """
    for i, a in enumerate(glyph_projection):
        page_dist[offset_y + i] = page_dist[offset_y + i] + a

def proc_st_pos(st_position):
    """Calculates and adds intermediate spaces
    """
    
    
    for j, st in enumerate(st_position):
        lines_and_spaces = []
        # print st['avg_lines']
        for i, s in enumerate(st['avg_lines'][1:]):
            lines_and_spaces.append(st['avg_lines'][i])
            lines_and_spaces.append(0.5*(st['avg_lines'][i+1] + st['avg_lines'][i]))
        lines_and_spaces.append(st['avg_lines'][i+1])
        # lg.debug("Line and Space: {0}\n{1}".format(j, lines_and_spaces))
        las.append(lines_and_spaces)
        
        
        
if __name__ == "__main__":
    usage = "usage: %prog [options] aruspix_directory page_glyphs_directory outputdir staff_algorithm(*AvLines* or *Miyao*) exceptions (*yes* or *no*) glyph_position"
    opts = OptionParser(usage)
    (options, args) = opts.parse_args()

    if not args:
        opts.error("You must supply arguments to this script.")
    if not args[0]:
        opts.error("You must supply a path to an image.")
    if not args[1]:
        opts.error("You must supply a pagexml file")
    if not args[2]:
        opts.error("You must supply an output directory.")
    page_dist = [0] * 3000
    avg_pos_page = []
    las = []
    for a in range(12):
        main(args[0], args[1], args[2], args[3], args[4], a)
        total = 0
        las = []
    print avg_pos_page
    
    main(args[0], args[1], args[2], args[3], args[4], args[5])
    print avg_pos_page
    print 'Done!'


