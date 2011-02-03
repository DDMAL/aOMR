"""
Toolkit setup

This file is run on importing anything within this directory.
Its purpose is only to help with the Gamera GUI shell,
and may be omitted if you are not concerned with that.
"""

from gamera import toolkit
import wx
from gamera.toolkits.aomr_tk import main

# Let's import all our plugins here so that when this toolkit
# is imported using the "Toolkit" menu in the Gamera GUI
# everything works.

from gamera.toolkits.aomr_tk.plugins import clear

# You can inherit from toolkit.CustomMenu to create a menu
# for your toolkit.  Create a list of menu option in the
# member _items, and a series of callback functions that
# correspond to them.  The name of the callback function
# should be the same as the menu item, prefixed by '_On'
# and with all spaces converted to underscores.

from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aruspix.ax_page import AxPage
from gamera.toolkits.aruspix.ax_staff import AxStaff

from gamera.toolkits.aomr_tk.aomr_object import AomrObject
# from gamera.toolkits.aomr_tk.staff_removal import AOMR_Staff_Removal
# from gamera.toolkits.aomr_tk.classification import AOMR_Classification
# from gamera.toolkits.aomr_tk.pitchfinder import AOMR_Pitchfinder



from gamera.core import *
from gamera.args import *
from gamera.toolkits import musicstaves
from gamera.toolkits.musicstaves import stafffinder_miyao

from gamera.gui import gui
from gamera.gui import has_gui
from gamera.gui.matplotlib_support import *
from gamera import classify
from lxml import etree

from gamera import knn
import os
import math
import uuid
import sys

import re
from os import path

from gamera import toolkit


import pdb
import logging
lg = logging.getLogger('aomr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)





if has_gui.has_gui:
    from gamera.gui import var_name
    import wx 

    import aomr_module_icon
    
    # class Aomr_tkMenu(toolkit.CustomMenu):
    #     _items = ["Aomr_tk Toolkit",
    #               "Aomr_tk Toolkit 2"]
    #     def _OnAomr_tk_Toolkit(self, event):
    #         wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit!").ShowModal()
    #         main.main()
    #     def _OnAomr_tk_Toolkit_2(self, event):
    #         wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit 2!").ShowModal()
    #         main.main()
            
    class AomrModuleIcon(toolkit.CustomIcon):
        
        def __init__(self, *args, **kwargs):
            toolkit.CustomIcon.__init__(self, *args, **kwargs)

            #
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
            return inspect.ismodule(data) and\
                    data.__name__.endswith("aomr_tk")
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
                        "Create a %s object" % entry)
                wx.EVT_MENU(parent, self._menuids[index],\
                        self.createAOMRobj)
            parent.PopupMenu(menu, wx.Point(x, y))


        def double_click(self):
            pass
            

        def createAOMRobj(self, event):
            # find class belonging to menu entry
            # global swap
            tmpdir = ""
            
            index = -1
            for i, m in enumerate(self._menuids):
                if m == event.GetId():
                    index = i
                    break
            if index < 0:
                return
            ms_module=self.classes[index]

            # ask for parameters
            dialog=Args([FileOpen("Image file", "", "*.*"),\
                    Check("Printed Neume Style / Img_Size"), # Check("Printed Neume Style", "True"),
                    Check("Display Original File", "", True),
                    Check("Retrieve Staff Position"),
                    Check("Staff Removal"),
                    Int("Number of staves"),
                    Directory("Temporal directory (optional)", tmpdir)], # Int("Staffline height"),\ # Int("Staffspace height")],\
                    "Create an %s object" % ms_module)
            params=dialog.show()
            
            print str(params)
            
            dialog_args = {
                "filename": params[0],
                "neume_type": params[1],
                "display_image": params[2],
                "staff_position": params[3],
                "staff_removal": params[4],
                "number_of_staves": params[5],
                "tmpdir": params[6]
            }
            
            if dialog_args['filename'] == None:
                raise Exception("You must supply a filename.")
            
            
            aomr_file = AomrObject(**dialog_args)
            print aomr_file

            if params != None:
                if params[0] != None:
                    #
                    # load the image here and load it
                    # into the gamera shell, too. this is
                    # done because for checking whether
                    # it is a onebit image or not.
                    #
                    filename=params[0]
                    imagename = path.basename(params[0])
                    imagename=imagename.split('.')[0]
                    # substitute special characters
                    imagename=re.sub('[^a-zA-Z0-9]', '_',\
                            imagename)
                    imagename=re.sub('^[0-9]', '_',\
                            imagename)
                    # test = r"test\t"
                    # test2 = "test\t"
                    image=load_image(filename)
                    # self._shell.run(imagename + ' = load_image(r"' + filename + '") ') 
                    self._shell.run("%s = load_image(r'%s')"\
                                                % (imagename, filename))
                    if image.data.pixel_type != ONEBIT:
                        self._shell.run("%s = %s.to_onebit()"\
                                % (imagename,\
                                imagename))
                                
                    # self._shell.run("%s.display(%s)"\ GVM. It doesn't work. Check.
                    #             % (imagename,\
                    #             imagename))
                    
                    # still exists in the gamera shell
                    # del image

                    # choose a name for the variable in
                    # the GUI
                    # if ms_module.startswith("StaffFinder"):
                    #     name=var_name.get("stafffinder",\
                    #         self._shell.locals)
                    # else:
                    #     name=var_name.get("musicstaves",\
                    #         self._shell.locals)

                    # if name is "" or name is None:
                    #     return
                    

                    # create an instance of the specified
                    # AOMR_XXX class
                    self._shell.run("%s = %s.%s(%s, %d)"\
                            % (imagename,\
                            self.label,\
                            ms_module,\
                            imagename,\
                            params[1]))

                if params[1] != False:
                    img_size = aomr_file.image_size()
                    # self._shell.run("Image Size is %i times %i"\
                    #     % (img_size[0], img_size[1]))
                    # print 'Image Size from init'
                    # self._shell.run("%s.image_size()"\
                    #         % (imagename))

                if params[2] != False:
                    self._shell.run("%s = load_image(r'%s')"\
                        % (imagename,\
                        filename))
                    
                    # aomr_file.get_img()
                    
                if params[3] != False:
                    staff_position = aomr_file.staff_position()
                    print staff_position
                
                if params[4] != False:
                    img_no_st = aomr_file.staff_removal()
                    # a= img_no_st.get_img()
                    # print a
                    # im = load_image(img_no_st)
                    # swap = aomr_file.get_img()
                    # name = var_name.get("img_no_st",\
                    #                         self._shell.locals)
                    # im = load_image(img_no_st)
                    self._shell.run("%s_no_st = load_image(r'%s')" \
                        % (imagename, img_no_st))                    

    AomrModuleIcon.register()  

      

# r'/Users/gabriel/Documents/imgs/Liber_Usualis_WORK/processed_tifs/433__Liber_Usualis.tif'
