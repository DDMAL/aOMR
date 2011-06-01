from optparse import OptionParser
from pymei.Import import xmltomei

if __name__ == "__main__":
    usage = "usage: %prog [options] input_ground_truth__file input_file_to_compare output_folder"
    opts = OptionParser(usage)
    (options, args) = opts.parse_args()
    
    gt_file = args[0]
    comp_file = args[1]
    output_folder = args[2]

    ground_truth = xmltomei.xmltomei(gt_file)
    comparison = xmltomei.xmltomei(comp_file)
    
    # use the "search" method to find all <note> elements in the document, and 
    # then create an array of pitches using n.pitchname
    gt_notes = [n.pitchname for n in ground_truth.search('note')]
    cp_notes = [c.pitchname for c in comparison.search('note')]
  
    
    print "\nThe number of notes in the ground truth is: {0}".format(len(gt_notes))
    print "The number of notes in the comparison is {0}".format(len(cp_notes))
    
    for neume in ground_truth.search('neume'):
        print neume, neume.attribute_by_name('name').value, 
        for note in neume.children:
            print note.attribute_by_name('pname').value,
        print

    
    
    e = 0
    for i in range(len(gt_notes)):
        if gt_notes[i] != cp_notes[i]:
            e = e + 1.0
    
    print
    print("There are {0} errors in {1} glyphs, so {2} per cent of precision". format(e, i+1, 100-(e*100)/(i+1)))
