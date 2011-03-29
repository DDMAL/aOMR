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

def process_axz_directory(directory, outputdir):
    print "Processing AXZ Folder"
    for dirpath, dirnames, filenames in os.walk(directory):            
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
            
            # shutil.move(tfile[1], os.path.join(outdir, "original_image.tiff"))
            
            sfile = os.path.join(outdir, "original_image.tiff")

            save_image(staves, sfile)
            
            # lg.debug("Tempfile is: {0}".format(tfile[1]))
            
            # grab and remove the staves
            # aomr_opts = {
            #     'lines_per_staff': 4,
            #     'staff_finder': 0,
            #     'staff_removal': 0,
            #     'binarization': 0,
            #     'discard_size': 12 # GVM, was 6 
            # }
            # 
            # aomr_obj = AomrObject(sfile, **aomr_opts)

            
            # try:
            #     lg.debug("Finding Staves")
            #     s = aomr_obj.find_staves()
            # except:
            #     lg.debug("CAAAANNNNOOOT PARRSSSEEEE: {0}".format(pagenum))
            #     os.remove(sfile)
            #     os.rmdir(outdir)
            #     continue
            # 
            # lg.debug("S is: {0}".format(s))
            # if not s:
            #     lg.debug("no staves were found")
            #     os.remove(sfile)
            #     os.rmdir(outdir)
            #     continue
            # 
            # try:
            #     aomr_obj.remove_stafflines()
            # except:
            #     lg.debug("CAAAANNNNOOOT PARRSSSEEEE: {0}".format(pagenum))
            #     os.remove(sfile)
            #     os.rmdir(outdir)
            #     continue
            
            # gamera_xml.WriteXMLFile(glyphs=classified_image, with_features=True).write_filename(os.path.join(outdir, "page_glyphs.xml"))
            # gamera_xml.WriteXMLFile(symbol_table=s).write_filename(os.path.join(outdir, "symbol_table.xml"))
            # cknn.to_xml_filename(os.path.join(outdir, "classifier_glyphs.xml"), with_features=True)
            # save_image(aomr_obj.img_no_st, os.path.join(outdir, "source_image.tiff"))
            
            # clean up
            # del aomr_obj.img_no_st
            # del aomr_obj
            # del classified_image
            # del ax
            # del cknn
            
            
            # done!

if __name__ == "__main__":
    # usage = "usage: %prog [options] input_directory axz_directory output_directory"
    usage = "usage: %prog [options] axz_directory output_director"
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


    axz = process_axz_directory(args[0], args[1])

    print "Done!"




