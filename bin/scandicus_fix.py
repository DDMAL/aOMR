from optparse import OptionParser
import os
from gamera.core import *
from gamera import gamera_xml
from gamera.toolkits.aruspix.ax_file import AxFile
from gamera.toolkits.aomr_tk import AomrObject
from gamera.toolkits.aomr_tk import AomrMeiOutput
import simplejson

from operator import itemgetter
from pymei.Export import meitoxml
from pymei.Import import xmltomei
import time, shutil

import logging
lg = logging.getLogger('pitch_find')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)


def scandicus_fixing(mei_file):
    """
        Compares the pitches of the ground truth and the classifier
    """
    # error = 0
    # m = mei_file.split('/')[-1]
    # n = m.split('.')[-2] + '_GT.mei'
    # ground_truth = os.path.join(ground_truth_directory, n)
    # ground_truth = xmltomei.xmltomei(ground_truth)
    mei_file = xmltomei.xmltomei(mei_file)
    

    neumes_in_mei_file = mei_file.search('neume')
    

    for n in neumes_in_mei_file:
        # print n
        neume_type = n.attribute_by_name('name').value#, n.children[0].attribute_by_name('pname').value
        if neume_type == 'scandicus' or neume_type == 'salicus':
            neume_facs = n.attribute_by_name('facs').value
            no_notes = len(n.descendants_by_name('note'))


            result_zone = mei_file.get_by_id_ref("xml:id", neume_facs)
            ulx = result_zone[0].attribute_by_name('ulx').value
            uly = result_zone[0].attribute_by_name('uly').value
            lrx = result_zone[0].attribute_by_name('lrx').value
            lry = result_zone[0].attribute_by_name('lry').value
            
            print neume_type, no_notes, ulx, uly, lrx, lry
            new_lrx = (int(ulx)+no_notes*17)
            # print new_lrx
            result_zone[0].attribute_by_name('lrx').value(new_lrx)

            print neume_type, no_notes, ulx, uly, lrx, lry
            
            # neume_zone = mei_file.get_by_facs(facs_in_neume)
            # print neume_zone
    
    # all_elements = mei_file.flat()
    # for each in all_elements:
    #     # print each
    #     # print each.name
    #     if each.name == 'neume':
    #         print each
    #         # print each.children_by_name()
    #         # print each.name.descendants_by_name('nc')
    #         # print each.element

    
    
if __name__ == "__main__":
    usage = "usage: %prog [options] working_directory ground_truth_directory output_directory staff_algorithm"
    opts = OptionParser(usage = usage)
    options, args = opts.parse_args()
    init_gamera()

    if not args:
        opts.error("You must supply arguments to this script")


    mei_file = args[0]
    # mei_file = args[1]
    scandicus_fixing(mei_file)

    no_glyphs = 0
    no_errors = 0



    print "\nDone!\n"