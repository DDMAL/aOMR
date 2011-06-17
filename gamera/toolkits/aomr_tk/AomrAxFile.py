from gamera.core import *
from gamera.toolkits.aomr_tk.AomrExceptions import *

import zipfile
import os
import warnings
import tempfile
import shutil

class AomrAxFile(object):
    """
        Manipulates an Aruspix file and stores its information.    
        An object of this class provides the following functionality:
        - Read (unzip) the file
        - Write (zip) the file
        .. note:: 
        A *AxFile* object has several public properties, that can be manipulated by
        the user. The following table gives a detailed view on this.
        +-----------------------+---------------------------------------------------+
        | TODO                  | TODO                                              |
        +-----------------------+---------------------------------------------------+
        .. _constructor: gamera.toolkits.aruspix.ax_page.AxFile.html#init
        :Authors: Laurent Pugin and Jason Hockman (1.0); Andrew Hankinson and Gabriel Vigliensoni (2.0)
    """
    def __init__(self, filename):
        if os.path.splitext(filename)[-1] != ".axz":
            raise AomrNotAnAruspixFileError("The supplied file is not an Aruspix file.")
        self.filename = filename
        self.tmpdir = tempfile.mkdtemp()
        
        # unzip the AXZ file.
        zip = zipfile.ZipFile(self.filename, 'r')
        for name in zip.namelist():
            f = file(os.path.join(self.tmpdir, name), 'wb')
            f.write(zip.read(name))
            f.close()
        zip.close()
        
        if not os.path.exists(os.path.join(self.tmpdir, "img0.tif")):
            raise AomrAruspixPackageError("The img0.tif file is not in this package")
        if not os.path.exists(os.path.join(self.tmpdir, "img1.tif")):
            raise AomrAruspixPackageError("The img1.tif file is not in this package")
        if not os.path.exists(os.path.join(self.tmpdir, "index.xml")):
            raise AomrAruspixPackageError("The index.xml file is not in this package")
    
    def __del__(self):
        # clean up the tempdir.
        shutil.rmtree(self.tmpdir)
    
    def save(self, filename=None):
        if not filename:
            filename = self.filename
        
        zip = zipfile.ZipFile(filename, 'w')
        for name in os.listdir(self.tmpdir):
            zip.write(os.path.join(self.tmpdir, name), name)
        zip.close()
    
    def add_comment(self, text):
        """ Adds a simple comment to the gamera.txt file in the aruspix file."""
        f = open(os.path.join(self.tmpdir, "gamera.txt"), "a")
        f.write(text)
        f.close()
    
    def get_img0(self):
        """ Returns the path to img0.tif. These differ from their implementation
            in v.1.0, since they do not explicitly load the image into gamera...
            We'll leave that up to the calling function to do.
        """
        return os.path.join(self.tmpdir, "img0.tif")
        
    def get_img1(self):
        return os.path.join(self.tmpdir, "img1.tif")
    
    def get_index(self):
        return os.path.join(self.tmpdir, "index.xml")