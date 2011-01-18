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

from gamera.toolkits.aomr_tk.staff_position import AOMR_Staff_Position
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
            self.classes = ["AOMR_Staff_Position",
                    "AOMR_Staff_Removal",
                    "AOMR_Classification",
                    "AOMR_Pitchfinder"]
            # menu id's for creating classes over popup menu
            self._menuids = []
            for c in self.classes:
                self._menuids.append(wx.NewId())
            
        def get_icon(): ### Working here to display the Module Icon in Gamera's window 
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
                    Check("Printed Neume Style", "True")],
                    # Int("Staffline height"),\
                    # Int("Staffspace height")],\
                    "Create a %s object" % ms_module)
            params=dialog.show()

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
                    test = r"test\t"
                    test2 = "test\t"
                    image=load_image(filename)
                    #self._shell.run(imagename + ' = load_image(r"' + filename + '") ') 
                    self._shell.run('%s = load_image(r"%s")'\
                            % (imagename, filename))
                    if image.data.pixel_type != ONEBIT:
                        self._shell.run("%s = %s.to_onebit()"\
                                % (imagename,\
                                imagename))

                    # still exists in the gamera shell
                    del image

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
                    # MusicStaves_XXX class
                    self._shell.run("%s = %s.%s(%s, %d)"\
                            % (imagename,\
                            self.label,\
                            ms_module,\
                            imagename,\
                            params[1]))


    AomrModuleIcon.register()  

      
# aomr_tk_menu = Aomr_tkMenu()
# AomrModuleIcon.register()  

print 'OK!'
#shu
