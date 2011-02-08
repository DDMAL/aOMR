from gamera.core import *
from gamera.toolkits import musicstaves
from gamera.toolkits.aomr_tk.AomrExceptions import *

import zipfile
import os
import warnings
import tempfile

import logging
lg = logging.getLogger('aomr')
import pdb


class AomrObject(object):
    """
    Manipulates an Aomr file and stores its information
    """
    def __init__(self, filename, **kwargs):
        """
            Constructs and returns an AOMR object
        """
        self.filename = filename
        
        self.number_of_staves = kwargs['number_of_staves']
        self.sfnd_algorithm = kwargs['staff_finder']
        self.srmv_algorithm = kwargs['staff_removal']
        
        self.page_result = {}
        
        
        # cache this once so we don't have to constantly load it
        self.image = load_image(self.filename)
        self.image_size = [self.image.ncols, self.image.nrows]
        
        self.page_result = {
            'staves': {},
            'dimensions': self.image_size
        }
        
    def process_image(self):
        lg.debug(self.sfnd_algorithm)
        
        if self.sfnd_algorithm is 0:
            s = musicstaves.StaffFinder_miyao(self.image)
        elif self.sfnd_algorithm is 1:
            s = musicstaves.StaffFinder_dalitz(self.image)
        elif self.sfnd_algorithm is 2:
            s = musicstaves.StaffFinder_projections(self.image)
        else:
            raise AomrStaffFinderNotFoundError("The staff finding algorithm was not found.")
            
        s.find_staves()
        staves = s.get_average()
        print staves
        
        for i, staff in enumerate(staves):
            lg.debug("Staff {0} ({1} lines)".format(i+1, len(staff)))
            yvals = [y.average_y for y in staff]
            leftx = [x.left_x for x in staff]
            rightx = [x.right_x for x in staff]
            
            # grab the staff coords with some extra padding to account for
            # staff curvature and some ledger lines.
            ulx,uly = min(leftx), min(yvals) - s.staffspace_height
            lrx,lry = max(rightx), max(yvals) + s.staffspace_height
            
            line_positions = [(leftx[j], rightx[j], yvals[j]) for j in xrange(len(staff))]
            
            # pdb.set_trace()
            lg.debug("I is : {0}".format(i))
            
            self.page_result['staves'][i] = {
                'coords': [ulx, uly, lrx, lry],
                'num_lines': len(staff),
                'line_pos': line_positions,
                'contents': []
            }
        
        lg.debug(self.page_result)
        
    def remove_staves(self):
        """ Removes staves. 
            Returns a file object of the image with staves removed.
        """
        musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(self.image, 0, 0)
        musicstaves_no_staves.remove_staves(u'all', self.number_of_staves)
        img_no_st = musicstaves_no_staves.image
        
        #mkstemp returns a tuple with (filedescriptor, path)
        tmpfile = tempfile.mkstemp()
        # tf = os.fdopen(tmpfile[0], 'wb')
        save_image(musicstaves_no_staves.image, tmpfile[1])
        # tf.close()
        
        # now we return just the path to be re-opened on the other end.
        return tmpfile[1]
        
    def glyph_classification(self):
        """ Glyph classification.
            Returns a list of the classified glyphs with its position and size.
        """
        cknn = knn.kNNInteractive([],
                                ["area", 
                                "aspect_ratio",
                                "black_area", 
                                "compactness", 
                                "moments", 
                                "ncols_feature", 
                                "nholes", 
                                "nholes_extended", 
                                "nrows_feature", 
                                "skeleton_features", 
                                "top_bottom", 
                                "volume", 
                                "volume16regions", 
                                "volume64regions", 
                                "zernike_moments"], 
                                8))
        cknn.from_xml_filename(self.filename)
        # cknn.load_settings() # Option for loading the features and weights of the training stage.
        css = image_no_st.cc_analysis()
        grouping_function = classify.ShapedGroupingFunction(16) # variable ?
        classified_image = cknn.group_and_update_list_automatic(ccs, grouping_function, max_parts_per_group = 4) # variable ?
        return classified_image


    def pitch_finding(self):
        """ Pitch finding.
            Returns a list of pitches for a list of classified glyphs.
        """
        
        for c in class_im:

            staff_number = '' 
            uod = ''
            staff_number = '' 
            line_number = ''
            note = ''
            mid = 0
            if c.nrows<10 and c.ncols<10: # If error found
                er = er + 1
            else:
                sep_c = c.get_main_id().split('.')
                if len(sep_c) <= 3:
                    for i in range(3-len(sep_c)):
                        sep_c.append('')

                if sep_c[0] == 'neume':
                    uod = up_or_down(sep_c[1], sep_c[2])
                    neume_count = neume_count + 1
                    for i, stave in enumerate(stavelines):
                        if uod == 'D':
                            if stave[2] > (c.offset_y - 4): # 4 is the value is for excluding notes touching the line
                                staff_number = stave[0]
                                line_number = stave[1]
                                note = notes[line_number]
                                break
                        elif uod == 'U':
                            if stave[2] > (c.offset_y + c.nrows - 4): # 4 is the value is for excluding notes touching the line
                                staff_number = stave[0]
                                line_number = stavelines[i-1][1] # we want the previous line
                                note = notes[line_number]
                                break

                elif sep_c[0] == 'clef':
                    for stave in stavelines:
                        if abs((c.offset_y + c.nrows/2) - stave[2]) <= 4:
                            staff_number = stave[0]
                            line_number = stave[1]

                else:
                    uod = ''
                    staff_number = '' 
                    line_number = ''
                    note = ''

                glyph_kind = sep_c[0]
                actual_glyph = sep_c[1] 
                glyph_char = sep_c[2:]
                glyph_list.append([staff_number, #Which one of these do we actually need?
                                    c.offset_x, 
                                    c.offset_y, 
                                    note, 
                                    line_number, 
                                    glyph_kind, 
                                    actual_glyph, 
                                    glyph_char, 
                                    uod, 
                                    c.ncols, 
                                    c.nrows])

        glyph_list.sort()
        return glyph_list
