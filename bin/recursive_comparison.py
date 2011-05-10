from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aomr_tk import AomrObject
from gamera.toolkits.aomr_tk import AomrMeiOutput
import simplejson

from operator import itemgetter
from pymei.Export import meitoxml
from pymei.Import import xmltomei
import time, shutil

import logging
lg = logging.getLogger('pitch_find')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

def process_directory(working_directory, ground_truth_directory, output_directory, staff_algorithm, exceptions):
    """
        Performs all the directory processing and methods
    """
    print "\nProcessing directory {0}".format(working_directory)
    
    aomr_opts = {
        'lines_per_staff': 4,
        'staff_finder': 0, # 0: Miyao
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }
    
    for dirpath, dirnames, filenames in os.walk(working_directory):
        for f in filenames:
            if f == 'page_glyphs.xml':
                page_number = dirpath.split('/')[-1]
                page_glyphs = os.path.join(dirpath, f)
                original_image = os.path.join(dirpath, 'original_image.tiff')
                mei_file_write = os.path.join(dirpath, page_number +'_original_image.mei')
                glyphs = gamera_xml.glyphs_from_xml(page_glyphs)
                aomr_obj = AomrObject(original_image, **aomr_opts)
                
                aomr_obj.extended_processing = True # set to false if you don't want to do extended processing (aka "exceptions").
                
                st_position = aomr_obj.find_staves()
                staff_coords = aomr_obj.staff_coords()
                if staff_algorithm == 'Miyao':
                    sorted_glyphs = aomr_obj.miyao_pitch_find(glyphs)
                elif staff_algorithm == 'AvLines':
                    sorted_glyphs = aomr_obj.pitch_find(glyphs, st_position)
                mei_document = jsontomei(sorted_glyphs, staff_coords, mei_file_write)
                
                precision, mei_no_notes, no_errors = ground_truth_comparison(ground_truth_directory, mei_file_write)
                
                print ("Page {0}".format(page_number))
                results.append([page_number, mei_no_notes, no_errors, precision])
            else:
                pass
        
def ground_truth_comparison(ground_truth_directory, mei_file):
    """
        Compares the pitches of the ground truth and the classifier
    """
    error = 0
    m = mei_file.split('/')[-1]
    n = m.split('.')[-2] + '_GT.mei'
    ground_truth = os.path.join(ground_truth_directory, n)
    ground_truth = xmltomei.xmltomei(ground_truth)
    pitch_mei_file = xmltomei.xmltomei(mei_file)
    
    g_t_notes = [n.pitchname for n in ground_truth.search('note')]
    mei_notes = [c.pitchname for c in pitch_mei_file.search('note')]
    
    g_t_no_notes = len(g_t_notes)
    mei_no_notes = len(mei_notes)
    
    if g_t_no_notes != mei_no_notes:
        print 'Different number of notes between the ground truth and the compared filed.'
        
    
    for i in range(g_t_no_notes):
        if g_t_notes[i] != mei_notes[i]:
            error = error + 1

    precision = 100.0 - ((100.0 * error) / (i + 1))
    return precision, mei_no_notes, error
    
    

def jsontomei(pitches_found, staff_coords, mei_file_write):
    """
        Sorts the glyphs, parses to json, and converts to MEI
    """
    sorted_glyphs = sorted(pitches_found, key=itemgetter(1, 2))
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
    mei_file = AomrMeiOutput.AomrMeiOutput(data, mei_file_write.split('/')[-1])
    meitoxml.meitoxml(mei_file.md, mei_file_write)

if __name__ == "__main__":
    usage = "usage: %prog [options] working_directory ground_truth_directory output_directory staff_algorithm"
    opts = OptionParser(usage = usage)
    options, args = opts.parse_args()
    init_gamera()

    
    if not args:
        opts.error("You must supply arguments to this script as \nworking_directory \nground_truth_directory \noutput_directory \nstaff_algorithm: *Miyao* or *AvLines* \nexceptions: *yes* or *no*")
    # if not args[0]:
    #     opts.error("You must supply a path to a working directory.")
    # if not args[1]:
    #     opts.error("You must supply a path to a ground truth directory")
    # if not args[2]:
    #     opts.error("You must supply path to an output directory.")
    # if not args[3]:
    #     opts.error("You must specify a staff linetracking algorithm: AvLines or Miyao")
    # if args[3] is not 'Miyao' or args[3] is not 'AvLines':
    #     opts.error("You must specify a staff linetracking algorithm: AvLines or Miyao")
    # if not args[4]:
    #     opts.error("You must say if you want or not to handle exceptions: *yes* or *no*")
        
    print
    # print args[0], args[1], args[2], args[3], args[4]
    
    results = []

    process_directory(args[0], args[1], args[2], args[3])

    no_glyphs = 0
    no_errors = 0
    
    for r in results:
        no_glyphs = no_glyphs + r[1]
        no_errors = no_errors + r[2]
        print r

    precision = 100.0 - (100.0 * no_errors)/(no_glyphs)
    print ("There are {0} glyphs and {1} errors in total. The precision is {2}".format(no_glyphs, no_errors, precision))

    print "\nDone!\n"