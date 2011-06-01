# checks page_glyph files for malformed neume names.
from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
import all_glyphs

import logging

lg = logging.getLogger("spell")
fh = logging.FileHandler("glyph-problems.log")
fh.setLevel(logging.WARN)
lg.addHandler(fh)


def main(options):
    init_gamera()
    glyph_corrections = dict(all_glyphs.g)
    errno = 0.
    numglyphs = 0.
    numpages = 0
    
    for dirpath, dirnames, filenames in os.walk(options['gam']):
        numpages += 1
        for f in filenames:
            if f == "page_glyphs_corr.xml":
                os.unlink(os.path.join(dirpath, f))
            if f != "page_glyphs.xml":
                continue
            # lg.debug("Processing: {0}".format(f))
            
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, f))
            
            for i,g in enumerate(glyphs):
                numglyphs += 1
                if g.get_main_id() in glyph_corrections.keys():
                    errno += 1
                    # this glyph needs correcting.
                    action = glyph_corrections[g.get_main_id()]
                    if action == "warn":
                        lg.warn("=====> Problem detected with {0} on page {1} <=====".format(g.get_main_id(), os.path.basename(dirpath)))
                    elif action == "":
                        # lg.warn("Deleting {0} from page {1}".format(g.get_main_id(), dirpath))
                        glyphs.pop(i)
                    else:
                        # lg.warn("Replacing {0} with {1} on page {2}".format(g.get_main_id(), action, dirpath))
                        g.classify_manual(action)
            
            os.rename(os.path.join(dirpath, f), os.path.join(dirpath, "page_glyphs_uncorr.xml"))
            gamera_xml.WriteXMLFile(glyphs=glyphs, with_features=True).write_filename(os.path.join(dirpath, "page_glyphs.xml"))
            # save out glyphs.
            # move on.
    
    print "Totals: {0} errors out of {1} glyphs; {2} total error rate".format(errno, numglyphs, (errno / numglyphs) * 100)
    print "Number of pages: {0}".format(numpages)
    print "Average glyphs per page: {0}".format(numglyphs / numpages)
    print "Average errors per page: {0}".format(errno / numpages)
    
            
if __name__ == "__main__":
    usage = "%prog gam_directory"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    
    opts = {
        'gam': args[0]
    }
    
    main(opts)
        
    