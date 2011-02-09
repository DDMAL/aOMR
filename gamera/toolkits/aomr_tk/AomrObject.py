from gamera.core import *
from gamera.toolkits import musicstaves
from gamera.toolkits.aomr_tk.AomrExceptions import *

import zipfile
import os
import warnings
import tempfile
import copy
import itertools

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
        self.classifier_glyphs = kwargs["glyphs"]
        self.classifier_weights = kwargs["weights"]
        
        # the result of the staff finder. Mostly for convenience
        self.staves = None 
        
        # cache this once so we don't have to constantly load it
        self.image = load_image(self.filename)
        self.image_size = [self.image.ncols, self.image.nrows]
        
        self.page_result = {
            'staves': {},
            'dimensions': self.image_size
        }
        
        self._find_staves()
        self._remove_stafflines()
        
    def _find_staves(self):
        if self.sfnd_algorithm is 0:
            s = musicstaves.StaffFinder_miyao(self.image)
        elif self.sfnd_algorithm is 1:
            s = musicstaves.StaffFinder_dalitz(self.image)
        elif self.sfnd_algorithm is 2:
            s = musicstaves.StaffFinder_projections(self.image)
        else:
            raise AomrStaffFinderNotFoundError("The staff finding algorithm was not found.")
            
        s.find_staves()
        
        # get a polygon object. This stores a set of vertices for x,y values along the staffline.
        self.staves = s.get_polygon()
        
        for i, staff in enumerate(self.staves):
            lg.debug("Staff {0} ({1} lines)".format(i+1, len(staff)))
            
            yv = []
            xv = []
            
            # linepoints is an array of arrays of vertices describing the 
            # stafflines in the staves.
            #
            # For the staff, we end up with something like this:
            # [
            #   [ (x,y), (x,y), (x,y), ... ],
            #   [ (x,y), (x,y), (x,y), ... ],
            #   ...
            # ]
            line_positions = []
            
            for staffline in staff:
                pts = staffline.vertices
                yv += [p.y for p in pts]
                xv += [p.x for p in pts]
                line_positions.append([(p.x,p.y) for p in pts])
            
            ulx,uly = min(xv),min(yv)
            lrx,lry = max(xv),max(yv)
            
            # To accurately interpret objects above and below, we need to project 
            # ledger lines on the top and bottom. To do this, we estimate points
            # based on the line positions we already have.
            #
            # Since we can't *actually* get the points, we'll predict based on the
            # first and last positions of the top and bottom lines.
            # first, get the top two and bottom two positions
            ledger_lines_top = line_positions[0:2]
            ledger_lines_bottom = line_positions[-2:]
            
            imaginary_lines = []
            
            # take the second line. we'll then subtract each point from the corresponding
            # value in the first.
            i_line_1 = []
            i_line_2 = []
            for j,point in enumerate(ledger_lines_top[1]):
                diff_y = point[1] - ledger_lines_top[0][j][1]
                pt_x = point[0]
                pt_y_1 = ledger_lines_top[0][j][1] - diff_y
                pt_y_2 = pt_y_1 - diff_y
                i_line_1.append((pt_x, pt_y_1))
                i_line_2.append((pt_x, pt_y_2))
            
            # insert these. Make sure the highest line is added last.
            line_positions.insert(0, i_line_1)
            line_positions.insert(0, i_line_2)
            i_line_1 = []
            i_line_2 = []
            for k,point in enumerate(ledger_lines_bottom[1]):
                diff_y = point[1] - ledger_lines_bottom[0][k][1]
                pt_x = point[0]
                pt_y_1 = ledger_lines_bottom[1][k][1] + diff_y
                pt_y_2 = pt_y_1 + diff_y
                i_line_1.append((pt_x, pt_y_1))
                i_line_2.append((pt_x, pt_y_2))
            line_positions.extend([i_line_1, i_line_2])
            
            self.page_result['staves'][i] = {
                'coords': [ulx, uly, lrx, lry],
                'num_lines': len(staff),
                'line_positions': line_positions,
                'contents': [],
                'clef_shape': None,
                'clef_line': None
            }
        pdb.set_trace()
            
    def _remove_stafflines(self):
        """ Removes staves. 
            Returns a file object of the image with staves removed.
        """
        musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(self.image, 0, 0)
        musicstaves_no_staves.remove_staves(u'all', len(self.staves))
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
                                8)
        
        cknn.from_xml_filename(self.classifier_glyphs)
        cknn.load_settings(self.classifier_weights) # Option for loading the features and weights of the training stage.
        
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
    
    
    def _find_pitch(self, staff, x, y):
        """ 
            Placeholder for a possible pitch finding method; that is,
            given an staff number and an x,y coordinate of a glyph, figure
            out the pitch in relation to the staff's clef.
            
            If we're smart about it, we won't need to store a pitch's "space line" --
            that is, the line that bisects a staff space.
            
            Lotsa work to do here.
        """
        pass
        
        
        
    
    
    
