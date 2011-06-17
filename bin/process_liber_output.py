##############
# This script will perform the following tasks:
#   0. Create the LU-final output structure.
#   0a. Copy Aruspix files
#   0b. Unzip and extract the images
#   1. Merge existing page_glyphs.xml and pitch recognition files for the hand-corrected LU pages
#   2. Perform AOMR on non-hand-corrected LU pages.
#   2a. Should we convert to another format to avoid TIFF issues?
#   3. Perform OCR on all pages with text.
#   4. Create the output MEI files
#
#
#

from optparse import OptionParser
import ConfigParser

import os
from gamera.core import *
from gamera import gamera_xml, knn, classify, plugin
from gamera.symbol_table import SymbolTable
from gamera.toolkits.aomr_tk.AomrAxFile import AomrAxFile
from gamera.toolkits.aomr_tk import AomrObject
from gamera.toolkits.aomr_tk import AomrMeiOutput

import PIL, os
from pymei.Import import xmltomei
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

def process_aruspix_directory(axdir, outputdir):
    for dirpath, dirnames, filenames in os.walk(axdir):
        for f in filenames:
            if f.startswith("."):
                lg.debug("Continuing.")
                continue
            lg.debug("Processing file: {0}".format(f))
            
            pagenum = f.split("_")[2].split('.')[0]
            # create an output directory
            
            lg.debug(int(pagenum))
            
            # if int(pagenum) <= 50:
            #     lg.debug("Skipping")
            #     continue
            
            outdir = os.path.join(outputdir, pagenum)
            if not os.path.exists(outdir):
                os.mkdir(outdir)
            axzfile = os.path.join(dirpath, f)

            ax = AomrAxFile(axzfile)
            axtmp = ax.tmpdir

            shutil.move(ax.get_img1(), os.path.join(outdir, "{0}_original_image.tiff".format(pagenum)))

            img0 = load_image(ax.get_img0())
            staves = img0.extract(0)
            staff_text = img0.extract(3)
            lyrics = img0.extract(4)
            titles = img0.extract(5)
            ornate_letters = img0.extract(2)

            sfile = os.path.join(outdir, "{0}_staves_only.tiff".format(pagenum))
            save_image(staves, sfile)

            save_image(lyrics, os.path.join(outdir, "{0}_lyrics_only.tiff".format(pagenum)))

            staff_text.or_image(titles, True)
            save_image(staff_text, os.path.join(outdir, "{0}_text_only.tiff".format(pagenum)))

            or_image = staff_text.or_image(lyrics, False)
            or_image2 = or_image.or_image(ornate_letters, False)
            # now merge in the titles, but do it in place on the new images.
            or_image2.or_image(titles, True)
            all_layers = os.path.join(outdir, "{0}_all_text_layers.tiff".format(pagenum))
            lg.debug("Saving {0}".format(all_layers))
            save_image(or_image, all_layers)
            
    lg.debug("Done processing Aruspix files.")

def process_pageglyphs_directory(pgdir, outdir):
    import all_glyphs
    glyph_corrections = dict(all_glyphs.g)
    total_glyphs = 0
    total_error = 0
    
    
    for dirpath, dirnames, filenames in os.walk(pgdir):
        for f in filenames:
            if f == 'page_glyphs.xml':
                folder_no = os.path.basename(dirpath)
                pnum = int(folder_no)
                
                outputdirectory = os.path.join(outdir, folder_no.zfill(4))
                
                if not os.path.exists(outputdirectory):
                    os.mkdir(outputdirectory)
                
                input_filename = os.path.join(dirpath, f)
                lg.debug("Input filename is {0}".format(input_filename))
                
                (corr_page_glyphs, total, error) = fix_spelling_mistakes(input_filename, glyph_corrections)
                
                output_filename = os.path.join(outputdirectory, "{0}_corr_page_glyphs.xml".format(folder_no.zfill(4)))
                lg.debug("Output filename is {0}".format(output_filename))
                gamera_xml.WriteXMLFile(glyphs=corr_page_glyphs, with_features=True).write_filename(output_filename)
                
                total_glyphs += total
                total_error += error
    
    lg.debug("There were {0} total glyphs.".format(total_glyphs))
    lg.debug("There were {0} total errors.".format(total_error))
    lg.debug("The misspelled error rate was {0}".format((total_error / total_glyphs)))
    
    
def fix_spelling_mistakes(page_glyphs_file, glyph_corrections):
    errno = 0.
    numglyphs = 0.
    numpages = 0
    
    glyphs = gamera_xml.glyphs_from_xml(page_glyphs_file)
    k = glyph_corrections.keys()
    
    for i,g in enumerate(glyphs):
        numglyphs += 1
        if g.get_main_id() in k:
            errno += 1
            # this glyph needs correcting.
            action = glyph_corrections[g.get_main_id()]
            if action == "warn":
                lg.warn("=====> Problem detected with {0} on page {1} <=====".format(g.get_main_id(), os.path.basename(page_glyphs_file)))
            elif action == "":
                # lg.warn("Deleting {0} from page {1}".format(g.get_main_id(), dirpath))
                glyphs.pop(i)
            else:
                # lg.warn("Replacing {0} with {1} on page {2}".format(g.get_main_id(), action, dirpath))
                g.classify_manual(action)
                
    return (glyphs, numglyphs, errno)
    
def aomr_remaining_pages(outdir, classifier):
    aomr_opts = {
        'staff_finder': 0,
        'lines_per_staff': 4,
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 14
    }
    for dirpath, dirnames, filenames in os.walk(outdir):
        if dirpath == outdir:
            continue
            
        if ".git" in dirpath.split("/"):
            continue
            
        folder_no = os.path.basename(dirpath)
        pnum = int(folder_no)
        
        lg.debug("Processing page {0}".format(pnum))
        
        # these files give us problems.
        if pnum in [41, 87, 100]:
            lg.debug("Skipping page {0}".format(pnum))
            continue
        
        corrpg = "{0}_corr_page_glyphs.xml".format(folder_no.zfill(4))
        # badpg = "bad_{0}_corr_page_glyphs.xml".format(folder_no.zfill(4))
        if not corrpg in filenames:
            # we need to perform aomr.
            original_image = os.path.join(dirpath, "{0}_staves_only.tiff".format(folder_no.zfill(4)))
            aomr_obj = AomrObject(original_image, **aomr_opts)
            
            try:
                lg.debug("Finding Staves")
                s = aomr_obj.find_staves()
            except Exception, e:
                lg.debug("Cannot find staves: {0} because {1}".format(pnum, e))
                continue
                
            if not s:
                lg.debug("No staves were found on page {0}".format(pnum))
                continue
                
            try:
                aomr_obj.remove_stafflines()
            except Exception, e:
                lg.debug("Cannot remove stafflines: {0} because {1}".format(pnum, e))
                continue
            
            cknn = knn.kNNNonInteractive(classifier, 'all', True, 1)
            ccs = aomr_obj.img_no_st.cc_analysis()
            func = classify.BoundingBoxGroupingFunction(4)
            classified_image = cknn.group_and_update_list_automatic(
                ccs,
                grouping_function=func,
                max_parts_per_group=4,
                max_graph_size=16
            )
            
            lg.debug("save all the files from page {0}".format(pnum))
            cknn.generate_features_on_glyphs(classified_image)
            
            s = SymbolTable()
            for split in plugin.methods_flat_category("Segmentation", ONEBIT):
               s.add("_split." + split[0])
            s.add("_group")
            s.add("_group._part")
            
            gamera_xml.WriteXMLFile(glyphs=classified_image, with_features=True).write_filename(os.path.join(dirpath, "{0}_uncorr_page_glyphs.xml".format(folder_no.zfill(4))))
            
            del aomr_obj
            del classified_image
            del cknn
            
def ocr_pages(outdir):
    pass

def create_mei_files(outdir):
    aomr_opts = {
        'staff_finder': 0,
        'lines_per_staff': 4,
        'staff_removal': 0,
        'binarization': 0,
        'discard_size': 12
    }
    for dirpath, dirnames, filenames in os.walk(outdir):
        if dirpath == outdir:
            continue
            
        if ".git" in dirpath.split("/"):
            continue
        
        folder_no = os.path.basename(dirpath)
        pnum = int(folder_no)
        
        # if not "bad_{0}_corr_page_glyphs.xml".format(folder_no.zfill(4)) in filenames:
        #     continue
        
        lg.debug("Generating MEI file for {0}".format(pnum))
        
        if "{0}_corr_page_glyphs.xml".format(folder_no.zfill(4)) in filenames:
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, "{0}_corr_page_glyphs.xml".format(folder_no.zfill(4))))
        elif "{0}_uncorr_page_glyphs.xml".format(folder_no.zfill(4)) in filenames:
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, "{0}_uncorr_page_glyphs.xml".format(folder_no.zfill(4))))
        else:
            lg.debug("There was no page glyphs file for page {0}".format(pnum))
            continue
            
        original_image = os.path.join(dirpath, "{0}_staves_only.tiff".format(folder_no.zfill(4)))
        mei_file_write = os.path.join(dirpath, '{0}_uncorr.mei'.format(folder_no.zfill(4)))
        
        aomr_obj = AomrObject(original_image, **aomr_opts)
        try:
            data = aomr_obj.run(glyphs)
        except OverflowError, e:
            lg.debug("Could not do detection on {0} because {1}".format(pnum, e))
            continue
        
        if not data:
            # no data was returned.
            lg.debug("No data was found for {0}".format(pnum))
            continue
        
        mei_file = AomrMeiOutput.AomrMeiOutput(data, "{0}_original_image.tiff".format(pnum), page_number = pnum)
        meitoxml.meitoxml(mei_file.md, mei_file_write)
        
def highlight_for_testing(outdir, testingdir):
    for dirpath, dirnames, filenames in os.walk(outdir):
        if dirpath == outdir:
            continue
            
        lg.debug(dirpath)
        if ".git" in dirpath.split("/"):
            continue
        
        folder_no = os.path.basename(dirpath)
        pnum = int(folder_no)
        
        lg.debug("Highlighting {0}".format(pnum))
        
        if "{0}_corr.mei".format(folder_no.zfill(4)) in filenames:
            mfile = "{0}_corr.mei".format(folder_no.zfill(4))
        elif "{0}_uncorr.mei".format(folder_no.zfill(4)) in filenames:
            mfile = "{0}_uncorr.mei".format(folder_no.zfill(4))
        else:
            lg.debug("No mei file found. Continue.")
            continue
        
        mdoc = xmltomei.xmltomei(os.path.join(dirpath, mfile))
        
        neumes = mdoc.search('neume')
        clefs = mdoc.search('clef')
        divisions = mdoc.search('division')
        custos = mdoc.search('custos')
        systems = mdoc.search('system')
        
        img = load_image(os.path.join(dirpath, "{0}_original_image.tiff".format(folder_no.zfill(4))))
        
        if img.pixel_type_name != "OneBit":
            img = img.to_onebit()
            
        rgb = Image(img, RGB)
        
        neumecolour = RGBPixel(255, 0, 0)
        clefcolour = RGBPixel(0, 255, 0)
        divisioncolour = RGBPixel(0, 0, 255)
        custoscolour = RGBPixel(128, 128, 0)
        systemscolour = RGBPixel(200, 200, 200)
        
        for system in systems:
                facs = mdoc.get_by_facs(system.facs)[0]
                rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), systemscolour)
                
        for neume in neumes:
            facs = mdoc.get_by_facs(neume.facs)[0]
            rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), neumecolour)
            
            # note_string = '-'.join([note.pitchname for note in neume.children_by_name('note')])
            # rgb.draw_text((int(facs.ulx) - 0, int(facs.uly) - 20), note_string, RGBPixel(0,0,0), size=10, bold=True, halign="left")
            # rgb.draw_text((int(facs.ulx) - 20, int(facs.uly) - 50), neume.attribute_by_name('name').value, RGBPixel(0,0,0), size=10, bold=True, halign="left")
            
        for clef in clefs:
            facs = mdoc.get_by_facs(clef.facs)[0]
            rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), clefcolour)
            
        for division in divisions:
            facs = mdoc.get_by_facs(division.facs)[0]
            rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), divisioncolour)
            
        for custo in custos:
            facs = mdoc.get_by_facs(custo.facs)[0]
            rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), custoscolour)
            
        rgb.highlight(img, RGBPixel(0,0,0))

        rgb.save_PNG(os.path.join(testingdir, '{0}_highlight.png'.format(folder_no.zfill(4))))
        
        

def main(config):
    init_gamera()
    
    axdir = config.get('input', 'aruspix_files_directory')
    pgdir = config.get('input', 'corrected_glyphs_directory')
    outdir = config.get('output', 'final_output_directory')
    testdir = config.get('output', 'testing_output_directory')
    
    lg.debug("Processing aruspix directory {0}.".format(axdir))
    # process_aruspix_directory(axdir, outdir)
    
    # process_pageglyphs_directory(pgdir, outdir)
    
    classifier = config.get('gamera', 'classifier')
    aomr_remaining_pages(outdir, classifier)
    
    # ocr_pages(outdir)
    
    create_mei_files(outdir)
    # highlight_for_testing(outdir, testdir)
    
if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-c", "--config", action="store", dest="config_file")
    (options, args) = parser.parse_args()
    
    if not options.config_file:
        parser.error('you must supply a config file.')
    
    config = ConfigParser.SafeConfigParser()
    config.read(options.config_file)
    
    main(config)
    
    print "Done!"