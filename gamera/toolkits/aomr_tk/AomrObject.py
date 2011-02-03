"""
The main function for the Aomr_tk Gamera toolkit

This is a good place for top-level functions, such as things
that would be called from the command line.

This module is not strictly necessary.
"""
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
    def __init__(self, filename, neume_type=None, display_image=None, staff_position=None, staff_removal=None, number_of_staves=4, tmpdir=None):
        """
        Constructs and returns an *Aomr* object
        """
        self.filename = filename
        self.deletedir = False

        if not tmpdir:
            self.tmpdir = tempfile.mkdtemp()
            self.deletedir = True        
        else:
            self.tmpdir = tmpdir
            
        self.no_of_staves = number_of_staves
        print "__init__"
        
    def image_size(self):
        i = load_image(self.filename)
        img_size = []
        img_size.append(i.ncols)
        img_size.append(i.nrows)
        print 'Image size is', img_size[0], '*', img_size[1]  
        return img_size
        
    def get_img(self):
        return load_image(self.filename)

    def staff_position(self):
        stavelines = []
        i = load_image(self.filename)
        s = stafffinder_miyao.StaffFinder_miyao(i)
        s.find_staves()
        print s
        print 'Staffspace height is', s.staffspace_height
        staves = s.get_average()
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
        i = load_image(self.filename)
        musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(i, 0, 0)
        musicstaves_no_staves.remove_staves(u'all', self.no_of_staves)
        img_no_st = musicstaves_no_staves.image   
        
        #mkstemp returns a tuple with (filedescriptor, path)
        tmpfile = tempfile.mkstemp()
        tf = os.fdopen(tmpfile[0], 'wb')
        save_image(musicstaves_no_staves.image, tf)
        tf.close()
        
        # now we return just the path to be re-opened on the other end.
        return tmpfile[1]
        
        
        # print img_no_st 
        # save_image(musicstaves_no_staves.image, self.filename+'_test')
        # return img_no_st
        
        
    # def save(self, filename):
    #     f = open(os.path.join(self.tmpdir, "test_img.tif"), 'w')
    #     f.write(filename)
    #     f.close