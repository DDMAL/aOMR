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


from gamera.core import *
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

from gamera import toolkit
from gamera.toolkits.aomr.plugins import *

if has_gui.has_gui:
    print 'has gui OK'
    from gamera.gui import var_name
    import wx 
    import aomr_module_icon

    class Aomr_tkMenu(toolkit.CustomMenu):
        _items = ["Aomr_tk Toolkit",
                  "Aomr_tk Toolkit 2"]
        def _OnAomr_tk_Toolkit(self, event):
            wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit!").ShowModal()
            main.main()
        def _OnAomr_tk_Toolkit_2(self, event):
            wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit 2!").ShowModal()
            main.main()
            
    class AomrModuleIcon(toolkit.CustomIcon):
        
        def __init__(self, *args, **kwargs):
            toolkit.CustomIcon.__init__(self, *args, **kwargs)
            
        def get_icon():
            return toolkit.CustomIcon.toicon(\
                    aomr_module_icon.getBitmap())
        get_icon = staticmethod(get_icon)

        def check(data):
            import inspect
            return inspect.ismodule(data) and\
                    data.__name__.endswith("aomr")
        check = staticmethod(check)

        def right_click(self, parent, event, shell):
            self._shell=shell
            x, y = event.GetPoint()
            menu = wx.Menu()

            # create the menu entry for each class listed in
            # 'classes' (they all point to the same method but
            # can be distinguished by their menu index)
            for index, entry in enumerate(self.classes):
                menu.Append(self._menuids[index],
                        "Create a %s object" % entry)
                wx.EVT_MENU(parent, self._menuids[index],\
                        self.createMusicStavesObj)
            parent.PopupMenu(menu, wx.Point(x, y))

        def double_click(self):
            pass
            
            
    AomrModuleIcon.register()  
    
      
aomr_tk_menu = Aomr_tkMenu()
AomrModuleIcon.register()  
print 'OK!'
#shu
