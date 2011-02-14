# a script for optimizing all of the glyphs for all of the pages.
#  - reads a directory of images and merges all page_glyph files into a single classifier
#  - optimizes the weights for a day (or another predetermined timeout)
#  - prunes the new classifier to a more lightweight version
#  - tests to make sure the new classifier recognition rate is the same as the old one
#  - spits out a new set of classifier glyphs and weights.
from optparse import OptionParser
import os
from gamera import gamera_xml
from gamera import knn
import threading
import datetime
import time
from gamera.knn_editing import edit_mnn_cnn

def process_directory(directory):
    features = ["area", 
    "aspect_ratio",
    "black_area", 
    "compactness", 
    "moments", 
    "ncols_feature",
    "nholes", 
    "nholes_extended", 
    "nrows_feature", 
    "skeleton_features", 
    "top_bottom", 
    "volume", 
    "volume16regions", 
    "volume64regions", 
    "zernike_moments"]
    
    filename = "page_glyphs.xml"
    glyphs = None
    
    # create a super-classifier
    for dirpath, dirnames, filenames in os.walk(directory):
        if os.path.abspath(dirpath) == os.path.abspath(directory):
            continue
        if not glyphs:
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, filename))
        else:
            glyphs.extend(gamera_xml.glyphs_from_xml(os.path.join(dirpath, filename)))
    # 
    return glyphs

def build_classifier(gly):
    k = knn.kNNNonInteractive(gly, 'all', True, 8)
    k.start_optimizing()
    # p = Pool()
    # result = p.map_async(__optimize, (glyphs,))
    # result.wait(5)
    # p.close()
    # p.terminate()
    return k

    
if __name__ == "__main__":
    usage = "usage: %prog [options] directory"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.error("You need to supply a directory of pages.")
    
    if not os.path.isdir(args[0]):
        parser.error("The supplied directory is not a directory.")
    
    classifiers = []
    for x in xrange(4):
        print "Starting optimizer {0}".format(x)
        glyphs = process_directory(args[0])
        classifiers.append(build_classifier(glyphs))
    
    starttime = datetime.datetime.now()
    endtime = starttime + datetime.timedelta(minutes=10)
    while endtime > datetime.datetime.now():
        time.sleep(10)
        print "I'm still alive."
    
    # once it's done, kill off the threads.
    best_result = 0
    best_classifier = None
    print "CHecking for the best results"
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
    
    print "Done!"
    
    
        
        
    