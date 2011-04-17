from pymei.Import import xmltomei
from gamera.core import *
import PIL
init_gamera()

from optparse import OptionParser

if __name__ == "__main__":
    usage = "usage: %prog [options] input_mei_file input_image_file"
    opts = OptionParser(usage)
    (options, args) = opts.parse_args()
    
    input_file = args[0]
    mdoc = xmltomei.xmltomei(input_file)
    
    neumes = mdoc.search('neume')
    clefs = mdoc.search('clef')
    divisions = mdoc.search('division')
    custos = mdoc.search('custos')
    systems = mdoc.search('system')
    
    img = load_image(args[1])
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
        
        note_string = '-'.join([note.pitchname for note in neume.children_by_name('note')])
        print note_string
        rgb.draw_text((int(facs.ulx) - 20, int(facs.uly) - 20), note_string, RGBPixel(0,0,0), halign="left")
    
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
    
    rgb.save_tiff('test.tiff')
    
    
    
    
    
