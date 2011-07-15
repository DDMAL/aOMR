from pymei.Import import xmltomei
from gamera.core import *
import PIL, os
init_gamera()


import logging
lg = logging.getLogger('pitch_find')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)




from optparse import OptionParser

def highlight_from_mei(input_mei, input_image, output_folder, num_page):

    mdoc = xmltomei.xmltomei(input_mei)
    
    neumes = mdoc.search('neume')
    clefs = mdoc.search('clef')
    divisions = mdoc.search('division')
    custos = mdoc.search('custos')
    systems = mdoc.search('system')
    
    img = load_image(input_image)
    
    if img.pixel_type_name != "OneBit":
        img = img.to_onebit()
    
    rgb = Image(img, RGB)
    
    neumecolour = RGBPixel(255, 0, 0)
    clefcolour = RGBPixel(0, 255, 0)
    divisioncolour = RGBPixel(0, 0, 255)
    custoscolour = RGBPixel(128, 128, 0)
    systemscolour = RGBPixel(200, 200, 200)
    
    for system in systems:
        facs = mdoc.get_by_facs(system.facs)[0]
        rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), systemscolour)
    
    for neume in neumes:
        facs = mdoc.get_by_facs(neume.facs)[0]
        rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), neumecolour)
        
        note_string = '-'.join([note.pitchname for note in neume.descendants_by_name('note')])
        
        rgb.draw_text((int(facs.ulx) - 0, int(facs.uly) - 20), note_string, RGBPixel(0,0,0), size=10, bold=True, halign="left")
        # rgb.draw_text((int(facs.ulx) - 20, int(facs.uly) - 50), neume.attribute_by_name('name').value, RGBPixel(0,0,0), size=10, bold=True, halign="left")
        
    for clef in clefs:
        facs = mdoc.get_by_facs(clef.facs)[0]
        rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), clefcolour)
    
    for division in divisions:
        facs = mdoc.get_by_facs(division.facs)[0]
        rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), divisioncolour)
        
    for custo in custos:
        facs = mdoc.get_by_facs(custo.facs)[0]
        rgb.draw_filled_rect((int(facs.ulx) - 5, int(facs.uly) - 5), (int(facs.lrx) + 5, int(facs.lry) + 5), custoscolour)
    
    rgb.highlight(img, RGBPixel(0,0,0))
    filename = num_page + '_pitch_find.png'
    output_file = os.path.join(output_folder, filename)
    # print output_file
    rgb.save_PNG(output_file)
    
    
def process_directory(input_folder, output_folder):
    for dirpath, dirnames, filenames in os.walk(input_folder):
        for f in filenames:
            try:                
                if f.startswith("."):
                    continue

                f_split = f.split("_")
                # print f_split
                num_page = f_split[0]

                for f_s in f_split:
                    # print f_s
                    if f_s == "corr.mei":
                        input_mei = os.path.join(dirpath, f)
                        input_image = os.path.join(dirpath, num_page)+"_original_image.tiff"
                        # print input_mei, input_image
                        highlight_from_mei(input_mei, input_image, output_folder, num_page)
            except:
                lg.debug("Cannot process page {0}".format(f))
                continue


if __name__ == "__main__":
    usage = "usage: %prog [options] input_folder output_folder"
    opts = OptionParser(usage = usage)
    options, args = opts.parse_args()
    init_gamera()


    process_directory(args[0], args[1])
    # highlight_from_mei(args[0], args[1])
    