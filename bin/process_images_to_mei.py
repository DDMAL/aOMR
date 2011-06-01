from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aomr_tk import AomrObject
from gamera.toolkits.aomr_tk import AomrMeiOutput

try:
    import simplejson
except ImportError:
    # 2.7
    import json as simplejson

from operator import itemgetter
from pymei.Export import meitoxml
import time, shutil

import pdb
import logging
lg = logging.getLogger('pitch_find')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

def process_axz_directory(axz_directory, outputdir, skip=False):
    print "Processing AXZ Folder"
    axzfiles_processed = []
    for dirpath, dirnames, filenames in os.walk(axz_directory):            
        for f in filenames:
            lg.debug("Processing file: {0}".format(f))
            if f.startswith("."):
                continue
            pagenum = f.split("_")[2].split('.')[0]
            # create an output directory
            axzfiles_processed.append(pagenum)
            
            if not skip:
                outdir = os.path.join(outputdir, pagenum)
                os.mkdir(outdir)
                axzfile = os.path.join(dirpath, f)
                
                ax = AxFile(axzfile, "")
                axtmp = ax.tmpdir
                staves = ax.get_img0().extract(0)
                sfile = os.path.join(outdir, "original_image.tiff")
                save_image(staves, sfile)
            
    return axzfiles_processed
            


def process_glyphs_directory(glyphs_directory, output_dir):
    aomr_opts = {
        'staff_finder': 0,
        'lines_per_staff': 4,
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }
    print "Processing glyphs directory"
    for dirpath, dirnames, filenames in os.walk(glyphs_directory):
        for f in filenames:
            if f == 'page_glyphs.xml':
                folder_no = os.path.basename(dirpath)
                pnum = int(folder_no)
                input_filename = os.path.join(dirpath, f)
                lg.debug("Input filename is {0}".format(input_filename))
                
                output_filename = os.path.join(output_dir, folder_no.zfill(4), f)
                lg.debug("Output filename is {0}".format(output_filename))
                
                shutil.copy(input_filename, output_filename)
                
                original_image = os.path.join(output_dir, folder_no.zfill(4), 'original_image.tiff')
                mei_file_write = os.path.join(output_dir, folder_no.zfill(4), 'liber-usualis-{0}.mei'.format(folder_no.zfill(4)))
                glyphs = gamera_xml.glyphs_from_xml(output_filename)
                
                aomr_obj = AomrObject(original_image, **aomr_opts)
                data = aomr_obj.run(glyphs)
                
                mei_file = AomrMeiOutput.AomrMeiOutput(data, original_image.split('/')[-2], page_number = pnum)
                meitoxml.meitoxml(mei_file.md, mei_file_write)

def main(options):
    axz = process_axz_directory(options["axz_dir"], options['out_dir'], options['skip'])
    glyphs = process_glyphs_directory(options['glyphs_dir'], options['out_dir'])


if __name__ == "__main__":
    # usage = "usage: %prog [options] input_directory axz_directory output_directory"
    usage = "usage: %prog [options] axz_directory page_glyphs_directory output_directory"
    parser = OptionParser(usage)
    parser.add_option("-a", "--algorithm", help="The staff finding algorithm. 0 for miyao, 1 for avglines. Default is 0", dest="algorithm", type="int", default=0)
    parser.add_option("-s", "--skip", help="skip aruspix parsing stage (if it's already done.)", dest="skip", action="store_true", default=False)
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No arguments specified.")
    
    if not os.path.isdir(args[0]):
        parser.error("The supplied axz directory is not a directory.")
    if not os.path.isdir(args[1]):
        parser.error("The supplied glyphs directory is not a directory.")
    
    if options.skip:
        print "Skipping aruspix generation. "
    
    opts = {
        'axz_dir': args[0],
        'glyphs_dir': args[1],
        'out_dir': args[2],
        'stf_find': options.algorithm,
        'skip': options.skip
    }
    
    init_gamera()
    main(opts)
    print "Done!"




