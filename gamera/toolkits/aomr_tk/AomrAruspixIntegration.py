import os
import time
import subprocess

import logging
lg = logging.getLogger('aomr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

class AomrAruspixIntegration(object):
    def __init__(self, **kwargs):
        self.path_to_ax = kwargs['path_to_ax']
        self.input_dir = kwargs['input_dir']
        self.output_dir = kwargs['output_dir']
    
    def run(self):
        # starts the aruspix preprocessing script.
        lg.debug("Starting to process.")
        self.path_to_ax_bin = os.path.join(self.path_to_ax, "Contents", "MacOS", "Aruspix")
        for dirpath, dirname, filenames in os.walk(self.input_dir):
            lg.debug("Processing {0}".format(dirpath))
            if not filenames:
                continue
            for f in filenames:
                if os.path.splitext(f)[-1] not in ('.tif', '.tiff'):
                    # the file is not a TIFF file
                    lg.debug("{0} is not a TIFF file".format(f))
                    continue
                    
                lg.debug("Infile {0}".format(os.path.join(dirpath, f)))
                
                outfile = os.path.splitext(f)[0] + ".axz"
                lg.debug("Outfile: {0}".format(outfile))
                
                ax_args = [self.path_to_ax_bin, "-q", "-e", "Rec", "-p", os.path.join(dirpath, f), os.path.join(self.output_dir, outfile)]
                lg.debug("Arguments: {0}".format(ax_args))
                
                proc = subprocess.call(ax_args)
                # while proc.returncode is None:
                #     lg.debug("Polling...")
                #     time.sleep(0.5)
                #     proc.poll()
                
        
    