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
lg = logging.getLogger('zones_fixing')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)


def zone_fixing(mei_file, output_folder):
    """
        Fixes the hand-entered glyphs
    """
    avg_punctum = 17
    scale = {'c':0, 'd':1, 'e':2, 'f':3, 'g':4, 'a':5, 'b':6}
    mei_file = xmltomei.xmltomei(mei_file)
    neumes_in_mei_file = mei_file.search('neume')
    divisions_in_mei_file = mei_file.search('division')

    for n in neumes_in_mei_file:
        neume_type = n.attribute_by_name('name').value
        neume_facs = n.attribute_by_name('facs').value
        neume_zone = mei_file.get_by_id_ref("xml:id", neume_facs)

        if neume_type == 'scandicus' or neume_type == 'salicus':
            no_notes = len(n.descendants_by_name('note'))
            ulx = neume_zone[0].attribute_by_name('ulx').value
            uly = neume_zone[0].attribute_by_name('uly').value
            lrx = neume_zone[0].attribute_by_name('lrx').value
            lry = neume_zone[0].attribute_by_name('lry').value
            fixed_lrx = (int(ulx) + (no_notes - 1) * avg_punctum) # 17 pixels for each avg_punctum_width
            fixed_lry = (int(uly) + (no_notes + 1) * avg_punctum)

            neume_zone[0].attributes = {'lrx': fixed_lrx, 'lry': fixed_lry}
            # lg.debug("{0} {1} ({2}, {3}), lrx : {4} -> {5}, lry : {6} -> {7}".format(neume_type, no_notes, ulx, uly, lrx, result_zone[0].attribute_by_name('lrx').value, lry, result_zone[0].attribute_by_name('lry').value))





        elif neume_type == 'torculus' or neume_type == 'porrectus':
            notes = n.descendants_by_name('note')
            highest_note_value = 0
            ulx_highest_note = 0
            for note in notes:
                pitch = note.attribute_by_name('pname').value
                octave = int(note.attribute_by_name('oct').value) # to retrieve the proper number thorugh all octaves
                note_value = scale[pitch] + (octave*7)
                if note_value > highest_note_value:
                    highest_note_value = note_value
                    ulx = neume_zone[0].attribute_by_name('ulx').value 
                lg.debug("neume_type {0}, pitch ({1}->{4}), octave {2}, note {3}".format(neume_type, pitch, octave, note_value, scale[pitch]))
            print highest_note_value, ulx








    for d in divisions_in_mei_file:
        division_type = d.attribute_by_name('form').value
        division_facs = d.attribute_by_name('facs').value
        division_zone = mei_file.get_by_id_ref("xml:id", division_facs)
        if division_type == 'final':
            ulx = division_zone[0].attribute_by_name('ulx').value
            uly = division_zone[0].attribute_by_name('uly').value
            lrx = division_zone[0].attribute_by_name('lrx').value
            lry = division_zone[0].attribute_by_name('lry').value
            # lg.debug("division {0} ({1}, {2}) ({3}, {4})".format(division_type, ulx, uly, lrx, lry))
            
            fixed_lrx = (int(ulx) + avg_punctum)
            fixed_lry = (int(uly) + avg_punctum * 6)
            
            division_zone[0].attributes = {'lrx': fixed_lrx, 'lry': fixed_lry}
            
    meitoxml.meitoxml(mei_file, os.path.join(output_folder, 'fixed.mei'))
    
    
if __name__ == "__main__":
    usage = "usage: %prog [options] mei_file output_folder"
    opts = OptionParser(usage = usage)
    options, args = opts.parse_args()
    init_gamera()

    if not args:
        opts.error("You must supply arguments to this script")


    mei_file = args[0]
    output_folder = args[1]
    zone_fixing(mei_file, output_folder)

    print "\nDone!\n"