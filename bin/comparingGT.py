from optparse import OptionParser
from pymei.Import import xmltomei

if __name__ == "__main__":
    usage = "usage: %prog [options] input_ground_truth__file input_file_to_compare output_folder"
    opts = OptionParser(usage)
    (options, args) = opts.parse_args()
    
    gt_file = args[0]
    comp_file = args[1]
    output_folder = args[2]
    
    # GT = []
    # COMP = []
    # e = 0

    # xmlGT = xmltomei.xmltomei(gt_file)
    # xmlCMP = xmltomei.xmltomei(comp_file)
    # 
    # gt_tree = etree.parse(gt_file)
    # comp_tree = etree.parse(comp_file)
    
    # print (etree.tostring(gt_tree))
    # for element in tree.iter("{http://www.music-encoding.org/ns/mei}neume"):
    #     # print element.attrib['name']
    #     print element.attrib

    # for i, element in enumerate(gt_tree.iter('{http://www.music-encoding.org/ns/mei}note')):
    #     # print i, element.attrib['pname']
    #     GT.append(element.attrib['pname'])
    # 
    # for i, element in enumerate(comp_tree.iter('{http://www.music-encoding.org/ns/mei}note')):
    #     # print i, element.attrib['pname']
    #     COMP.append(element.attrib['pname'])
    #     if COMP[i] != GT [i]:
    #         e = e + 1.0
            
    # GABRIEL:
    # Try this:
    ground_truth = xmltomei.xmltomei(gt_file)
    comparison = xmltomei.xmltomei(comp_file)
    
    # use the "search" method to find all <note> elements in the document, and 
    # then create an array of pitches using n.pitchname
    gt_notes = [n.pitchname for n in ground_truth.search('note')]
    cp_notes = [c.pitchname for c in comparison.search('note')]
  
    
    print "\nThe number of notes in the ground truth is: {0}".format(len(gt_notes))
    print "The number of notes in the comparison is {0}".format(len(cp_notes))
    
    # You will get a difference between the number of notes in each, meaning you cannot use
    # indexing, e.g., CMP[i] == GT[i]. For example, if one note is missed in the comparison set, 
    # every other note comparison will be wrong after that, since you will be off by one.
    
    # print GT
    # print COMP
    
    e = 0
    for i in range(len(gt_notes)):
        if gt_notes[i] != cp_notes[i]:
            e = e + 1.0
    
    print
    print("There are {0} errors in {1} glyphs, so {2} per cent of precision". format(e, i+1, 100-(e*100)/(i+1)))
