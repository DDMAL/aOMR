from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
from gamera.toolkits.aruspix.ax_file import AxFile

import logging
lg = logging.getLogger('textextract')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)
lg.setLevel(logging.DEBUG)
lg.addHandler(h)


def main(options):
    init_gamera()
    for dirpath, dirnames, filenames in os.walk(options['axz']):
        for f in filenames:
            if f.startswith("."):
                continue
            lg.debug("Processing: {0}".format(f))
            
            pagenum = f.split("_")[2].split('.')[0]
            outdir = os.path.join(options['out'], pagenum)
            os.mkdir(outdir)
            
            axzfile = os.path.join(dirpath, f)
            ax = AxFile(axzfile, "")
            axtmp = ax.tmpdir
            
            img0 = ax.get_img0()
            staff_text = img0.extract(3)
            lyrics = img0.extract(4)
            titles = img0.extract(5)
            
            if options['all']:
                # store each in a separate file
                stfile = os.path.join(outdir, "{0}_staff_text.tiff".format(pagenum))
                lg.debug("Saving {0}".format(stfile))
                save_image(staff_text, stfile)
                
                lfile = os.path.join(outdir, "{0}_lyrics.tiff".format(pagenum))
                lg.debug("Saving {0}".format(lfile))
                save_image(lyrics, lfile)
                
                tfile = os.path.join(outdir, "{0}_titles.tiff".format(pagenum))
                lg.debug("Saving {0}".format(tfile))
                save_image(titles, tfile)
                
            if options['mga']:
                or_image = staff_text.or_image(lyrics, False)
                # now merge in the titles, but do it in place on the new images.
                or_image.or_image(titles, True)
                all_layers = os.path.join(outdir, "{0}_all_text_layers.tiff".format(pagenum))
                
                lg.debug("Saving {0}".format(all_layers))
                save_image(or_image, all_layers)
            
            elif options['mgs']:
                or_image == staff_text.or_image(titles, False)
                some_layers = os.path.join(outdir, "{0}_some_text_layers.tiff".format(pagenum))
                lg.debug("Saving {0}".format(some_layers))
                save_image(or_image, some_layers)
            
            lg.debug("====> Finished processing {0} <=====".format(f))
            
            

if __name__ == "__main__":
    usage = "%prog axz_directory output_directory"
    parser = OptionParser(usage)
    parser.add_option("-a", "--all", help="Extract every layer into different image files.", dest="all", action="store_true", default=False)
    parser.add_option("-m", "--merge-all", dest="mergeall", help="Merge all text layers in the resulting file (lyrics [orange], text in staff [lt green], titles [yellow]).", action="store_true", default=False)
    parser.add_option("-s", "--merge-some", dest="mergesome", help="(default) Merge some text layers (text in staff [lt green], titles [yellow])", action="store_true", default=True)
    (options, args) = parser.parse_args()
    
    if options.mergeall:
        options.mergesome = False
    
    if not os.path.isdir(args[0]):
        parser.error("You must supply a directory of axz files.")
    if not os.path.isdir(args[1]):
        parser.error("You must supply an output directory.")
    if options.mergeall and options.mergesome:
        parser.error("Merge all and Merge some are mutually exclusive.")
        
    lg.debug("All is : {0}".format(options.all))
    lg.debug("Merge all is : {0}".format(options.mergeall))
    lg.debug("Merge some is : {0}".format(options.mergesome))
    
    opts = {
        'axz': args[0],
        'out': args[1],
        'all': options.all,
        'mga': options.mergeall,
        'mgs': options.mergesome,
    }
    
    main(opts)
