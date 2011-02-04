"""
Toolkit setup

This file is run on importing anything within this directory.
Its purpose is only to help with the Gamera GUI shell,
and may be omitted if you are not concerned with that.
"""

import os
import math
import uuid
import sys
import re
from lxml import etree

from gamera.core import *
from gamera.args import *

from gamera import toolkit
from gamera.gui import gui, has_gui, var_name
from gamera.gui.matplotlib_support import *
from gamera import classify
from gamera import knn

from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aruspix.ax_page import AxPage
from gamera.toolkits.aruspix.ax_staff import AxStaff

from gamera.toolkits import musicstaves
from gamera.toolkits.musicstaves import stafffinder_miyao

from gamera.toolkits.aomr_tk import main
from gamera.toolkits.aomr_tk.AomrObject import AomrObject
from gamera.toolkits.aomr_tk.AomrExceptions import *
from gamera.toolkits.aomr_tk import aomr_module_icon

import wx

# development -- logging & debugging
import pdb
import logging
lg = logging.getLogger('aomr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)


if has_gui.has_gui:
    class AomrModuleIcon(toolkit.CustomIcon):
        def __init__(self, *args, **kwargs):
            toolkit.CustomIcon.__init__(self, *args, **kwargs)
            
            # list containing all classes derived from
            # AOMR, add your own class name to this list
            # and it will appear in the menu of the AOMR
            # icon
            #
            self.classes = ["AomrObject"]
            # menu id's for creating classes over popup menu

            self._menuids = []
            for c in self.classes:
                self._menuids.append(wx.NewId())
            
        def get_icon():
            return toolkit.CustomIcon.to_icon(aomr_module_icon.getBitmap())
        get_icon = staticmethod(get_icon)
        
        def check(data):
            import inspect
            return inspect.ismodule(data) and data.__name__.endswith("aomr_tk")
        check = staticmethod(check)
        
        def right_click(self, parent, event, shell):
            self._shell=shell
            x, y=event.GetPoint()
            menu=wx.Menu()
            
            # create the menu entry for each class listed in
            # 'classes' (they all point to the same method but
            # can be distinguished by their menu index)
            for index, entry in enumerate(self.classes):
                menu.Append(self._menuids[index],
                        "Create a {0} object".format(entry))
                wx.EVT_MENU(parent, self._menuids[index], self.createAOMRobj)
            parent.PopupMenu(menu, wx.Point(x, y))
            
        def double_click(self):
            pass
            
        def createAOMRobj(self, event):
            # find class belonging to menu entry
            # global swap
            tmpdir = None
            index = -1
            for i, m in enumerate(self._menuids):
                if m == event.GetId():
                    index = i
                    break
            if index < 0:
                return
            ms_module=self.classes[index]
            
            # ask for parameters
            dialog=Args([FileOpen("Image file", "", "*.*"),
                    Check("Printed Neume Style / Img_Size"),
                    Check("Display Original File", "", True),
                    Check("Retrieve Staff Position"),
                    Check("Staff Removal"),
                    Int("Number of staves")],
                    "Create an %s object" % ms_module)
            params=dialog.show()
            
            lg.debug("The Parameters returned were {0}".format(params))
            
            dialog_args = {
                "filename": params[0],
                "neume_type": params[1],
                "display_image": params[2],
                "staff_position": params[3],
                "staff_removal": params[4],
                "number_of_staves": params[5],
            }
            # this checks to see if the filename has been set.
            # we could also check here to see if the file is an image, if
            # it's a directory, blah blah blah.
            if dialog_args['filename'] == None:
                raise AomrFilePathNotSetError("You must supply a filename.")
            
            # create an Aruspix OMR object
            aomr_file = AomrObject(**dialog_args)
            
            lg.debug("Loaded AOMR File: {0}".format(aomr_file))
            
            # since we would have raised an exception if the 
            filename = dialog_args['filename']
            imagename = os.path.basename(os.path.splitext(filename)[0])
            lg.debug("Raw imagename: {0}".format(imagename))
            
            imagename = re.sub(r'[^a-zA-Z0-9]', "_", imagename)
            lg.debug("Imagename after formatting: {0}".format(imagename))
            
            # load the image into gamera
            image = load_image(filename)
            self._shell.run("{0} = load_image(r'{1}')".format(imagename, filename))
            
            if image.data.pixel_type != ONEBIT:
                self._shell.run("{0} = {0}.to_onebit()".format(imagename))
                
            self._shell.run("{0} = {1}.{2}({3}, {4})".format(imagename, self.label,
                                                        ms_module, imagename, dialog_args['neume_type']))
            
            if dialog_args['neume_type']:
                # process neume type stuff if the checkbox is set
                img_size = aomr_file.image_size()
                
            if dialog_args['display_image']:
                # display image if checkbox is set
                self._shell.run("{0} = load_image(r'{1}')".format(imagename, filename))
                # aomr_file.get_img()
                
            if dialog_args['staff_position']:
                # do processing with staff position if set
                staff_position = aomr_file.staff_position()
                lg.debug(staff_position)
                
            if dialog_args['staff_removal']:
                # process staff removal if set
                img_no_st = aomr_file.staff_removal()
                self._shell.run("{0}_no_st = load_image(r'{1}')".format(imagename, img_no_st))                    
    AomrModuleIcon.register()
