# checks page_glyph files for malformed neume names.
from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml

def main(options):
    init_gamera()
    all_glyphs = []
    
    for dirpath, dirnames, filenames in os.walk(options['gam']):
        for f in filenames:
            if f != "page_glyphs.xml":
                continue
            # lg.debug("Processing: {0}".format(f))
            
            glyphs = gamera_xml.glyphs_from_xml(os.path.join(dirpath, f))
            
            def __glyphchecker(g):
                if "_group" in g.get_main_id().split("."):
                    return False
                elif "_split" in g.get_main_id().split("."):
                    return False
                else:
                    return True
            all_glyphs.extend([g.get_main_id() for g in glyphs if __glyphchecker(g)])
    
    all_glyphs.sort()
    all_glyph_set = set(all_glyphs)
    all_glyph_list = list(all_glyph_set)
    all_glyph_list.sort()
    for n in all_glyph_list:
        print n
        
if __name__ == "__main__":
    usage = "%prog gam_directory"
    parser = OptionParser(usage)
    (options, args) = parser.parse_args()
    
    opts = {
        'gam': args[0]
    }
    
    main(opts)
        
    