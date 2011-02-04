from gamera.core import *
from gamera.toolkits import musicstaves
from gamera.toolkits.musicstaves import stafffinder_miyao

import zipfile
import os
import warnings
import tempfile

import logging
lg = logging.getLogger('aomr')

class AomrObject:
    """
    Manipulates an Aomr file and stores its information
    """
    def __init__(self, filename, **kwargs):
        """
            Constructs and returns an AOMR object
        """
        self.filename = filename
        
        self.neume_type = kwargs['neume_type']
        self.display_image = kwargs['display_image']
        self.staff_position = kwargs['staff_position']
        self.staff_removal = kwargs['staff_removal']
        self.number_of_staves = kwargs['number_of_staves']
        
        self.tmpdir = tempfile.mkdtemp()
        
        # cache this once so we don't have to constantly load it
        self.image = load_image(self.filename)
        self.image_size = [self.image.ncols, self.image.nrows]
        
    def staff_position(self):
        s = stafffinder_miyao.StaffFinder_miyao(self.image)
        s.find_staves()
        staves = s.get_average()
        stavelines = []
        
        lg.debug("{0}".format(s))
        lg.debug('Staffspace height is {0}'.format(s.staffspace_height))
        #no_of_staves = 4            # convert to a variable in the module
        
        for i, staff in enumerate(staves):
            for j in range(self.no_of_staves - 1):
                stavelines.append([i+1, (j+1)*2+1, staff[j].average_y])
                stavelines.append([i+1, (j+1)*2+2, (staff[j].average_y + staff[j+1].average_y)/2])
            p3 = staves[i][0].average_y
            p5 = staves[i][1].average_y
            p7 = staves[i][2].average_y
            p9 = staves[i][3].average_y
            stavelines.append([i+1, 0, (3 * p3 - p5)/2 - (p5 - p3)])
            stavelines.append([i+1, 1, (2 * p3 - p5)])
            stavelines.append([i+1, 2, (3 * p3 - p5)/2])
            stavelines.append([i+1, 9, p9])
            stavelines.append([i+1,10, (3 * p9 - p7)/2])
            stavelines.append([i+1,11, (2 * p9 - p7)])
            stavelines.append([i+1,12, (5 * p9 - 3 * p7)/2])
        stavelines.sort
        return stavelines

    def staff_removal(self):
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