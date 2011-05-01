from optparse import OptionParser
from pymei.Import import xmltomei
from pymei.Export import meitoxml
from lxml import etree


if __name__ == "__main__":
    usage = "usage: %prog [options] input_ground_truth__file input_file_to_compare output_folder"
    opts = OptionParser(usage)
    (options, args) = opts.parse_args()
    
    gt_file = args[0]
    comp_file = args[1]
    output_folder = args[2]
    
    GT = []
    COMP = []
    e = 0

    xmlGT = xmltomei.xmltomei(gt_file)
    xmlCMP = xmltomei.xmltomei(comp_file)
    
    gt_tree = etree.parse(gt_file)
    comp_tree = etree.parse(comp_file)
    
    # print (etree.tostring(gt_tree))
    # for element in tree.iter("{http://www.music-encoding.org/ns/mei}neume"):
    #     # print element.attrib['name']
    #     print element.attrib

    for i, element in enumerate(gt_tree.iter('{http://www.music-encoding.org/ns/mei}note')):
        # print i, element.attrib['pname']
        GT.append(element.attrib['pname'])
    
    for i, element in enumerate(comp_tree.iter('{http://www.music-encoding.org/ns/mei}note')):
        # print i, element.attrib['pname']
        COMP.append(element.attrib['pname'])
        if COMP[i] != GT [i]:
            e = e + 1.0
        
    # print GT
    # print COMP
    print
    print("There are {0} errors in {1} glyphs, so {2} per cent of precission". format(e, i+1, 100-(e*100)/i+1))
