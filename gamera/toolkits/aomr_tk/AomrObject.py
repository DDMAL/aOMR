from gamera.core import *
from gamera.toolkits import musicstaves
from gamera.toolkits.aomr_tk.AomrExceptions import *

import zipfile
import os
import warnings
import tempfile

import logging
lg = logging.getLogger('aomr')
import pdb


class AomrObject(object):
    """
    Manipulates an Aomr file and stores its information
    """
    def __init__(self, filename, **kwargs):
        """
            Constructs and returns an AOMR object
        """
        self.filename = filename
        
        self.number_of_staves = kwargs['number_of_staves']
        self.sfnd_algorithm = kwargs['staff_finder']
        self.srmv_algorithm = kwargs['staff_removal']
        
        self.page_result = {}
        
        
        # cache this once so we don't have to constantly load it
        self.image = load_image(self.filename)
        self.image_size = [self.image.ncols, self.image.nrows]
        
        self.page_result = {
            'staves': {},
            'dimensions': self.image_size
        }
        
    def process_image(self):
        lg.debug(self.sfnd_algorithm)
        
        if self.sfnd_algorithm is 0:
            s = musicstaves.StaffFinder_miyao(self.image)
        elif self.sfnd_algorithm is 1:
            s = musicstaves.StaffFinder_dalitz(self.image)
        elif self.sfnd_algorithm is 2:
            s = musicstaves.StaffFinder_projections(self.image)
        else:
            raise AomrStaffFinderNotFoundError("The staff finding algorithm was not found.")
            
        s.find_staves()
        staves = s.get_average()
        
        for i, staff in enumerate(staves):
            lg.debug("Staff {0} ({1} lines)".format(i+1, len(staff)))
            yvals = [y.average_y for y in staff]
            leftx = [x.left_x for x in staff]
            rightx = [x.right_x for x in staff]
            
            # grab the staff coords with some extra padding to account for
            # staff curvature and some ledger lines.
            ulx,uly = min(leftx), min(yvals) - s.staffspace_height
            lrx,lry = max(rightx), max(yvals) + s.staffspace_height
            
            line_positions = [(leftx[j], rightx[j], yvals[j]) for j in xrange(len(staff))]
            
            # pdb.set_trace()
            lg.debug("I is : {0}".format(i))
            
            self.page_result['staves'][i] = {
                'coords': [ulx, uly, lrx, lry],
                'num_lines': len(staff),
                'line_pos': line_positions,
                'contents': []
            }
        
        lg.debug(self.page_result)
        
    def remove_staves(self):
        """ Removes staves. 
            Returns a file object of the image with staves removed.
        """
        musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(self.image, 0, 0)
        musicstaves_no_staves.remove_staves(u'all', self.number_of_staves)
        img_no_st = musicstaves_no_staves.image
        
        #mkstemp returns a tuple with (filedescriptor, path)
        tmpfile = tempfile.mkstemp()
        # tf = os.fdopen(tmpfile[0], 'wb')
        save_image(musicstaves_no_staves.image, tmpfile[1])
        # tf.close()
        
        # now we return just the path to be re-opened on the other end.
        return tmpfile[1]