from optparse import OptionParser
import os, sys
from gamera.core import *
from gamera import gamera_xml
from gamera.toolkits.aomr_tk import AomrObject
from gamera.toolkits.aomr_tk import AomrMeiOutput

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

def main(original_file, page_file, outdir):
    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': 0, # 0: Miyao
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }
    
    #FILES TO PROCESS
    glyphs = gamera_xml.glyphs_from_xml(page_file)
    file_name = (original_file.split('/')[-2] + '_' + original_file.split('/')[-1])


    # CREATING AOMR OBJECT, FINDING STAVES, AND RETRIEVING STAFF COORDINATES
    aomr_obj = AomrObject(original_file, **aomr_opts)
    st_position = aomr_obj.find_staves() # staves position
    staff_coords = aomr_obj.staff_coords()

    sorted_glyphs = aomr_obj.miyao_pitch_find(glyphs, aomr_opts['discard_size'])

    # PITCH FINDING
    # pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
    # print len(pitch_find)
    # sorted_glyphs = sorted(proc_glyphs, key=itemgetter(1, 2))



    # STRUCTURING THE DATA IN JSON
    data = {}
    for s, stave in enumerate(staff_coords):
        contents = []
        for glyph, staff, offset, strt_pos, note in sorted_glyphs:
            glyph_id = glyph.get_main_id()
            # lg.debug("Glyph ID: {0}".format(glyph_id))
            
            
            glyph_type = glyph_id.split(".")[0]
            glyph_form = glyph_id.split(".")[1:]
            # lg.debug("sg[1]:{0} s:{1} sg{2}".format(sg[1], s+1, sg))
            # structure: g, stave, g.offset_x, note, strt_pos
            if staff == s+1:
                j_glyph = { 'type': glyph_type,
                            'form': glyph_form,
                            'coord': [glyph.offset_x, glyph.offset_y, glyph.offset_x + glyph.ncols, glyph.offset_y + glyph.nrows],
                            'strt_pitch': note,
                            'strt_pos': strt_pos}
                contents.append(j_glyph)  
        data[s] = {'coord':stave, 'content':contents}    
    # print data
    # CREATING THE MEI FILE
    mei_file = AomrMeiOutput.AomrMeiOutput(data, file_name)

    meitoxml.meitoxml(mei_file.md, os.path.join(outdir, file_name.split('.')[0]+'.mei'))

if __name__ == "__main__":
    usage = "%prog path_to_image path_to_pagexml output_dir"
    opts = OptionParser(usage = usage)
    options, args = opts.parse_args()
    
    if not args:
        opts.error("You must supply arguments to this script.")
    
    if not args[0]:
        opts.error("You must supply a path to an image.")
    if not args[1]:
        opts.error("You must supply a pagexml file")
    if not args[2]:
        opts.error("You must supply an output directory.")
    
    main(args[0], args[1], args[2])
    
    
    













