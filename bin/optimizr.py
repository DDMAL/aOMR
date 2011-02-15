# a script for optimizing all of the glyphs for all of the pages.
#  - reads a directory of images and merges all page_glyph files into a single classifier
#  - optimizes the weights for a day (or another predetermined timeout)
#  - prunes the new classifier to a more lightweight version
#  - tests to make sure the new classifier recognition rate is the same as the old one
#  - spits out a new set of classifier glyphs and weights.
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


def process_directory(directory):
    glyphs = None
    filename = "page_glyphs.xml"
    # create a super-classifier
    for dirpath, dirnames, filenames in os.walk(directory):
        if os.path.abspath(dirpath) == os.path.abspath(directory):
            continue
        if not glyphs:
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, filename))
        else:
            glyphs.extend(gamera_xml.glyphs_from_xml(os.path.join(dirpath, filename)))
    
    searchstr = r'(\'|\\\\)'
    
    gg1 = [g for g in glyphs if not re.search(searchstr, g.get_main_id())]
    glyphs = [g for g in gg1 if not g.get_main_id() == "UNCLASSIFIED"]
    
    return glyphs

def build_classifier(gly):
    k = knn.kNNNonInteractive(gly, 'all', True, 8)
    k.start_optimizing()
    return k

def process_axz_directory(directory, class_glyphs, class_weights):
    for dirpath, dirnames, filenames in os.walk(directory):
        if os.path.abspath(directory) == os.path.abspath(dirpath):
            continue
        for f in filenames:
            axzfile = os.path.join(dirpath, f)
            ax = AxFile(axzfile, "")
            axtmp = ax.tmpdir
            staves = ax.get_img0().extract(0)
            # grab and remove the staves
            aomr_opts = {
                'number_of_stafflines': 4,
                'staff_finder': 0,
                'staff_removal': 0,
                'binarization': 0,
                'glyphs': "optimized_classifier.xml",
                'weights': "classifier_weights.xml",
                'discard_size': 6
            }
            
            aomr_obj = AomrObject(staves, **aomr_opts)
            aomr_obj.find_staves()
            aomr_obj.remove_stafflines()
            aomr_obj.glyph_classification()
            
            
if __name__ == "__main__":
    usage = "usage: %prog [options] input_directory axz_directory output_directory"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.error("You need to supply a directory of pages.")
    
    if not os.path.isdir(args[0]):
        parser.error("The supplied input directory is not a directory.")
    
    if not os.path.isdir(args[1]):
        parser.error("The supplied axz directory is not a directory.")
    
    init_gamera()
    
    classifiers = []
    glyphs = process_directory(args[0])
    for x in xrange(4):
        print "Starting optimizer {0}".format(x)
        classifiers.append(build_classifier(glyphs))
    
    starttime = datetime.datetime.now()
    endtime = starttime + datetime.timedelta(minutes=2)
    while endtime > datetime.datetime.now():
        time.sleep(10)
        print "I'm still alive."
    
    # once it's done, kill off the threads and get the results
    best_result = 0
    best_classifier = None
    print "Checking for the best results"
    for c,clsfr in enumerate(classifiers):
        print "Checking classifier {0}".format(c)
        res = clsfr.stop_optimizing()
        
        print "Classifier {0} was {1}".format(c, res)
        if res > best_result:
            best_class_num = c
            best_result = res
            best_classifier = clsfr
    
    print "The Best classifier was: {0} with result {1}".format(best_class_num, best_result)
    print "Editing and optimizing"
    edited_classifier = edit_mnn_cnn(best_classifier)
    
    print "Saving results"
    edited_classifier.to_xml_filename("optimized_classifier.xml")
    print "Saving weights"
    edited_classifier.save_settings("classifier_weights.xml")
    
    ##### finished creating a classifier.
    
    ##### Load up the AXZ Files
    axz = process_axz_directory(args[1])
    
    
    
    
    print "Done!"
    
    
        
        
    