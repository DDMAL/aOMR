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

import logging
lg = logging.getLogger('pitch_find')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

def process_axz_directory(axz_directory, outputdir):
    print "Processing AXZ Folder"
    for dirpath, dirnames, filenames in os.walk(axz_directory):            
        for f in filenames:
            lg.debug("Processing file: {0}".format(f))
            if f.startswith("."):
                continue
            pagenum = f.split("_")[2].split('.')[0]
            # create an output directory
            outdir = os.path.join(outputdir, pagenum)
            os.mkdir(outdir)
            axzfile = os.path.join(dirpath, f)

            ax = AxFile(axzfile, "")
            axtmp = ax.tmpdir
            staves = ax.get_img0().extract(0)
            sfile = os.path.join(outdir, "original_image.tiff")
            save_image(staves, sfile)
            


def process_glyphs_directory(glyphs_directory, output_dir, stf_find):
    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': stf_find, # 0: Miyao, 1: avglines
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }
    print "Processing glyphs directory"
    for dirpath, dirnames, filenames in os.walk(glyphs_directory):
        lg.debug("Processing {0}".format(dirpath))
        for f in filenames:
            if f == 'page_glyphs.xml':
                input_filename = os.path.join(dirpath, f)
                folder_no = os.path.basename(dirpath)
                
                pnum = int(folder_no)
                
                output_filename = os.path.join(output_dir, folder_no, f)
                shutil.copy(input_filename, output_filename)
                
                original_image = os.path.join(output_dir, folder_no, 'original_image.tiff')
                mei_file_write = os.path.join(output_dir, folder_no, 'page_glyphs.mei')
                glyphs = gamera_xml.glyphs_from_xml(output_filename)
                
                aomr_obj = AomrObject(original_image, **aomr_opts)
                
                st_position = aomr_obj.find_staves() # staves position
                staff_coords = aomr_obj.staff_coords() # staves coordinates
                
                if stf_find == 1:
                    pitch_find = aomr_obj.pitch_find(glyphs, st_position)
                else:
                    pitch_find = aomr_obj.miyao_pitch_find(glyphs)
                    
                # pitch_find = aomr_obj.pitch_find(glyphs, st_position, aomr_opts.get('discard_size'))
                sorted_glyphs = sorted(pitch_find, key=itemgetter(1, 2))
                
                data = {}
                for s, stave in enumerate(staff_coords):
                    contents = []
                    for glyph, staff, offset, strt_pos, note in sorted_glyphs:
                        glyph_id = glyph.get_main_id()
                        glyph_type = glyph_id.split(".")[0]
                        glyph_form = glyph_id.split(".")[1:]

                        if staff == s+1: 
                            j_glyph = { 'type': glyph_type,
                                        'form': glyph_form,
                                        'coord': [glyph.offset_x, glyph.offset_y, glyph.offset_x + glyph.ncols, glyph.offset_y + glyph.nrows],
                                        'strt_pitch': note,
                                        'strt_pos': strt_pos}
                            contents.append(j_glyph)  
                    data[s] = {'coord':stave, 'content':contents}
                    
                mei_file = AomrMeiOutput.AomrMeiOutput(data, original_image.split('/')[-2], page_number = pnum)
                meitoxml.meitoxml(mei_file.md, mei_file_write)


def main(options):
    axz = process_axz_directory(options["axz_dir"], options['out_dir'])
    glyphs = process_glyphs_directory(options['glyphs_dir'], options['out_dir'], options['stf_find'])


if __name__ == "__main__":
    # usage = "usage: %prog [options] input_directory axz_directory output_directory"
    usage = "usage: %prog [options] axz_directory page_glyphs_directory output_directory"
    parser = OptionParser(usage)
    parser.add_option("-a", "--algorithm", help="The staff finding algorithm. 0 for miyao, 1 for avglines. Default is 0", dest="algorithm", type="int", default=0)
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("No arguments specified.")
    
    if not os.path.isdir(args[0]):
        parser.error("The supplied axz directory is not a directory.")
    if not os.path.isdir(args[1]):
        parser.error("The supplied glyphs directory is not a directory.")
    
    opts = {
        'axz_dir': args[0],
        'glyphs_dir': args[1],
        'out_dir': args[2],
        'stf_find': options.algorithm
    }
    
    init_gamera()
    main(opts)
    print "Done!"




