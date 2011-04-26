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
import simplejson
from operator import itemgetter, attrgetter
from pymei.Export import meitoxml


import logging
lg = logging.getLogger('pitch_find_965')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

def process_axz_directory(axz_directory, outputdir):
    print "Processing AXZ Folder"
    for dirpath, dirnames, filenames in os.walk(axz_directory):            
        for f in filenames:
            print f
            if f == ".DS_Store":
                continue
            pagenum = f.split("_")[2].split('.')[0]
            print "Loading page ", str(pagenum)
            
            # create an output directory
            outdir = os.path.join(outputdir, pagenum)
            os.mkdir(outdir)
            
            axzfile = os.path.join(dirpath, f)
            
            # if Caylin hasn't corrected this file yet...
            if not os.path.getmtime(axzfile) > time.mktime(time.strptime("08 Jan 2011", "%d %b %Y")):
                lg.debug("I haven't been touched.")
                os.rmdir(outdir)
                continue
                
            ax = AxFile(axzfile, "")
            axtmp = ax.tmpdir
            staves = ax.get_img0().extract(0)
            sfile = os.path.join(outdir, "original_image.tiff")
            save_image(staves, sfile)
            


def process_glyphs_directory(glyphs_directory, output_dir):
    print "Processing glyphs directory"
    for dirpath, dirnames, filenames in os.walk(glyphs_directory):  
        for f in filenames:
            if f == 'page_glyphs.xml':
                input_filename = os.path.join(dirpath, f)
    
                folder_no = dirpath.split('/')[-1]
                output_folder = os.path.join(folder_no, f)
                output_filename = os.path.join(output_dir, output_folder)
                # lg.debug("output_filename:{0}".format(output_filename))
                shutil.copy(input_filename, output_filename)
    
                lg.debug ("input filename: {0}".format(input_filename))
    
                original_image = os.path.join(output_dir, (os.path.join(folder_no, 'original_image.tiff')))
                mei_file_write = os.path.join(output_dir, (os.path.join(folder_no, 'page_glyphs.mei')))
                glyphs = gamera_xml.glyphs_from_xml(output_filename)
                aomr_obj = AomrObject(original_image, **aomr_opts)
                st_position = aomr_obj.find_staves() # staves position
                staff_coords = aomr_obj.staff_coords() # staves coordinates
                pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
                sorted_glyphs = sorted(pitch_find, key=itemgetter(1, 2))
    
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
                                        'strt_pitch': sg[3],
                                        'strt_pos': sg[4]}
                            contents.append(glyph)  
                    data[s] = {'coord':stave, 'content':contents}    
                print data
                print
                mei_file = AomrMeiOutput.AomrMeiOutput(data, original_image.split('/')[-2])
                meitoxml.meitoxml(mei_file.md, mei_file_write)


if __name__ == "__main__":
    # usage = "usage: %prog [options] input_directory axz_directory output_directory"
    usage = "usage: %prog [options] axz_directory page_glyphs_directory outputdir "
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()

    # if len(args) < 1:
    #     parser.error("You need to supply a directory of pages.")
    # 
    # if not os.path.isdir(args[0]):
    #     parser.error("The supplied input directory is not a directory.")
    # 
    # if not os.path.isdir(args[1]):
    #     parser.error("The supplied axz directory is not a directory.")
    
    init_gamera()

    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': 0, # 0: Miyao
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }

    axz = process_axz_directory(args[0], args[2])
    glyphs = process_glyphs_directory(args[1], args[2])


    

    # #DDMAL
    # original_file = "/Users/gabriel/Documents/1_CODE/2_aOMR/imgs/1000/1_all.tiff"
    # glyphs = gamera_xml.glyphs_from_xml(r"/Users/gabriel/Documents/1_CODE/2_aOMR/imgs/1000/page_glyphs.xml")
    # 
    # aomr_obj = AomrObject(original_file, **aomr_opts)
    # st_position = aomr_obj.find_staves() # staves position
    # pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
    # 
    # print len(pitch_find)
    # sorted_glyphs = sorted(pitch_find, key=itemgetter(1, 2))
    # for s in sorted_glyphs:
    #     print s

    

    print "Done!"




