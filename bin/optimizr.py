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
from gamera import knn, plugin
from gamera import classify
from gamera.symbol_table import SymbolTable
import tempfile
import shutil
import random


import logging
lg = logging.getLogger('optimizr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

# def process_directory(directory):
#     kval = 1
#     searchstr = r'(\'|\\\\)'
#     first_glyphs = None
#     glyphs = []
#     filename = "page_glyphs.xml"
#     # create a super-classifier
#     for dirpath, dirnames, filenames in os.walk(directory):
#         print "Processing {0}".format(dirpath)
#         if os.path.abspath(dirpath) == os.path.abspath(directory):
#             continue
#         if not first_glyphs:
#             first_glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, filename))
#             # gg1 = [g for g in glyphs if not re.search(searchstr, g.get_main_id())]
#             # first_glyphs = [g for g in gg1 if not g.get_main_id() == "UNCLASSIFIED"]
#             # print "First Glyphs: {0}".format(first_glyphs)
#             k = knn.kNNNonInteractive(first_glyphs, 'all', True, kval)
#         else:
#             k.merge_from_xml_filename(os.path.join(dirpath, filename))
#     
#     # gg1 = [g for g in glyphs if not re.search(searchstr, g.get_main_id())]
#     # glyphs = [g for g in gg1 if not g.get_main_id() == "UNCLASSIFIED"]
#     # k.merge_glyphs(glyphs)
#     print "Number of Glyphs: {0}".format(len(k.get_glyphs()))
#     return k

# def build_classifier(gly):
    # kval = random.randint(1,3)
    # kval = 1
    # k = knn.kNNNonInteractive(gly, 'all', True, kval)
    # k.ga_population = 10
    # k.ga_crossover = 0.6
    # k.ga_mutation = 0.05
    # k.start_optimizing()
    # return (k, kval)

def process_axz_directory(directory, class_glyphs, class_weights, outputdir):
    print "Processing AXZ Folder"
    for dirpath, dirnames, filenames in os.walk(directory):
        
        # if os.path.abspath(directory) == os.path.abspath(dirpath):
        #     continue
            
        for f in filenames:
            if f == ".DS_Store":
                continue
            pagenum = f.split("_")[0]
            print "Loading page ", str(pagenum)
            
            # create an output directory
            outdir = os.path.join(outputdir, pagenum)
            os.mkdir(outdir)
            
            axzfile = os.path.join(dirpath, f)
            
            # if Caylin hasn't corrected this file yet...
            if not os.path.getmtime(axzfile) > time.mktime(time.strptime("08 Jan 2011", "%d %b %Y")):
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
            aomr_opts = {
                'lines_per_staff': 4,
                'staff_finder': 0,
                'staff_removal': 0,
                'binarization': 0,
                'discard_size': 6
            }
            
            aomr_obj = AomrObject(sfile, **aomr_opts)
            
            try:
                s = aomr_obj.find_staves()
            except:
                lg.debug("CAAAANNNNOOOT PARRSSSEEEE: {0}".format(pagenum))
                os.remove(sfile)
                os.rmdir(outdir)
                continue
            
            if not s:
                # no staves were found
                os.remove(sfile)
                os.rmdir(outdir)
                continue
            
            try:
                aomr_obj.remove_stafflines()
            except:
                lg.debug("CAAAANNNNOOOT PARRSSSEEEE: {0}".format(pagenum))
                os.remove(sfile)
                os.rmdir(outdir)
                continue
            
            cknn = knn.kNNNonInteractive(class_glyphs, 'all', 1)
            # cknn.load_settings(class_weights)
            ccs = aomr_obj.img_no_st.cc_analysis()
            func = classify.BoundingBoxGroupingFunction(4)
            # classified_image = cknn.group_and_update_list_automatic(ccs, grouping_function, max_parts_per_group=4, max_graph_size=16)
            classified_image = cknn.group_and_update_list_automatic(
                ccs,
                grouping_function=func,
                max_parts_per_group=4,
                max_graph_size=16
            )
            
            
            
            # save all the files into this directory
            cknn.save_settings(os.path.join(outdir, "classifier_settings.xml"))
            
            cknn.generate_features_on_glyphs(classified_image)
            s = SymbolTable()
            for split in plugin.methods_flat_category("Segmentation", ONEBIT):
               s.add("_split." + split[0])
            s.add("_group")
            s.add("_group._part")
            for g in cknn.get_glyphs():
                for idx in g.id_name:
                    s.add(idx[1])
                    
            gamera_xml.WriteXMLFile(glyphs=classified_image, with_features=True).write_filename(os.path.join(outdir, "page_glyphs.xml"))
            gamera_xml.WriteXMLFile(symbol_table=s).write_filename(os.path.join(outdir, "symbol_table.xml"))
            cknn.to_xml_filename(os.path.join(outdir, "classifier_glyphs.xml"), with_features=True)
            save_image(aomr_obj.img_no_st, os.path.join(outdir, "source_image.tiff"))
            
            # clean up
            del aomr_obj.img_no_st
            del aomr_obj
            del classified_image
            del ax
            del cknn
            
            
            # done!
            
            
if __name__ == "__main__":
    usage = "usage: %prog [options] input_directory axz_directory output_directory"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        parser.error("You need to supply a directory of pages.")
    
    if not os.path.isdir(args[0]):
        parser.error("The supplied input directory is not a directory.")
    
    if not os.path.isdir(args[1]):
        parser.error("The supplied axz directory is not a directory.")
    
    init_gamera()
    
    # classifiers = []
    # for x in xrange(5):
    #     print "Starting optimizer {0}".format(x)
    #     # clsf = process_directory(args[0])
    #     k = knn.kNNNonInteractive("/Volumes/Copland/Users/ahankins/Desktop/lutest/classifier_glyphs_587_18395.xml",'all', True, 1)
    #     k.ga_population = 10
    #     k.ga_crossover = 0.6
    #     k.ga_mutation = 0.05
    #     print "Number of Glyphs in {0}: {1}".format(x, len(k.get_glyphs()))
    #     classifiers.append(k)
    #     k.start_optimizing()
    # 
    # starttime = datetime.datetime.now()
    # endtime = starttime + datetime.timedelta(hours=10)
    # while endtime > datetime.datetime.now():
    #     time.sleep(1200)
    #     for c,clsf in enumerate(classifiers):
    #         print "{0} Generation: {1}".format(c, clsf.ga_generation)
    #         print "{0} Best: {1}".format(c, clsf.ga_best)
    # 
    # # once it's done, kill off the threads and get the results
    # best_result = 0
    # best_classifier = None
    # print "Checking for the best results"
    # for c,clsfr in enumerate(classifiers):
    #     print "Checking classifier {0}".format(c)
    #     res = clsfr.stop_optimizing()
    #     print "Initial rate was: {0}".format(clsfr.ga_initial)
    #     print "Best rate was: {0}".format(clsfr.ga_best)
    #     print "K value was: {0}".format(clsfr)        
    #     print "Classifier {0} was {1}".format(c, res)
    #     if res > best_result:
    #         best_class_num = c
    #         best_result = res
    #         best_classifier = clsfr
    # 
    # print "The Best classifier was: {0} with result {1}".format(best_class_num, best_result)
    # print "Editing and optimizing"
    # edited_classifier = edit_mnn_cnn(best_classifier)
    # 
    # print "Saving results"
    # edited_classifier.to_xml_filename(os.path.join(args[2], "optimized_classifier.xml"))
    # print "Saving weights"
    # edited_classifier.save_settings(os.path.join(args[2], "classifier_weights.xml"))
    # 
    ##### finished creating a classifier.
    
    ##### Load up the AXZ Files
    axz = process_axz_directory(args[1], os.path.join(args[2], "optimized_classifier_Feb16.xml"), os.path.join(args[2], "classifier_weights_Feb16.xml"), args[2])
    
    
    
    
    print "Done!"
    
    
        
        
    