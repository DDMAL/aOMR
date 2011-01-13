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



if has_gui.has_gui:
    from gamera.gui import var_name
    import wx # GVM from wxPython.wx import * 
    import aruspix_module_icon

    class Aomr_tkMenu(toolkit.CustomMenu):
        _items = ["Aomr_tk Toolkit",
                  "Aomr_tk Toolkit 2"]
        def _OnAomr_tk_Toolkit(self, event):
            wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit!").ShowModal()
            main.main()
        def _OnAomr_tk_Toolkit_2(self, event):
            wx.MessageDialog(None, "You clicked on Aomr_tk Toolkit 2!").ShowModal()
            main.main()
        
aomr_tk_menu = Aomr_tkMenu()
print 'aaa'
#shu
