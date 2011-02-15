from gamera.core import *
from gamera.toolkits import musicstaves
from gamera.toolkits.aomr_tk.AomrExceptions import *
from gamera import classify
from gamera import knn

import zipfile
import os
import warnings
import tempfile
import copy
import itertools
import random

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
        
        print "loading ", self.filename
        
        self.lines_per_staff = kwargs['lines_per_staff']
        self.sfnd_algorithm = kwargs['staff_finder']
        self.srmv_algorithm = kwargs['staff_removal']
        self.binarization = kwargs["binarization"]
        
        if "glyphs" in kwargs.values():
            self.classifier_glyphs = kwargs["glyphs"]
        if "weights" in kwargs.values():
            self.classifier_weights = kwargs["weights"]
            
        self.discard_size = kwargs["discard_size"]
        
        # the result of the staff finder. Mostly for convenience
        self.staves = None
        
        # a global to keep track of the number of stafflines.
        self.num_stafflines = None
        
        # cache this once so we don't have to constantly load it
        self.image = load_image(self.filename)
        self.image_resolution = self.image.resolution
        
        if self.image.data.pixel_type != ONEBIT:
            self.image = self.image.to_greyscale()
            bintypes = ['threshold',
                    'otsu_threshold',
                    'sauvola_threshold',
                    'niblack_threshold',
                    'gatos_threshold',
                    'abutaleb_threshold',
                    'tsai_moment_preserving_threshold',
                    'white_rohrer_threshold']
            self.image = getattr(self.image, bintypes[self.binarization])(0)
            # BUGFIX: sometimes an image loses its resolution after being binarized.
            if self.image.resolution < 1:
                self.image.resolution = self.image_resolution
                
        self.image_size = [self.image.ncols, self.image.nrows]
        
        # store the image without stafflines
        self.img_no_st = None
        self.rgb = None
        
        self.page_result = {
            'staves': {},
            'dimensions': self.image_size
        }
        
    def run(self):
        self.find_staves()
        self.remove_stafflines()
        self.glyph_classification()
        self.pitch_finding()
    
    def find_staves(self):
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
            # lg.debug("Staff {0} ({1} lines)".format(i+1, len(staff)))
            
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
            
            lg.debug("LL Top: {0}".format(ledger_lines_top))
            
            
            imaginary_lines = []
            
            # take the second line. we'll then subtract each point from the corresponding
            # value in the first.
            i_line_1 = []
            i_line_2 = []
            for j,point in enumerate(ledger_lines_top[1]):
                
                lg.debug("Point 1: {0}".format(point[1]))
                
                
                diff_y = point[1] - ledger_lines_top[0][j][1]
                pt_x = point[0]
                pt_y_1 = ledger_lines_top[0][j][1] - diff_y
                pt_y_2 = pt_y_1 - diff_y
                i_line_1.append((pt_x, pt_y_1))
                i_line_2.append((pt_x, pt_y_2))
            
            # insert these. Make sure the highest line is added last.
            line_positions.insert(0, i_line_1)
            line_positions.insert(0, i_line_2)
            
            # now do the bottom ledger lines
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
            
    def remove_stafflines(self):
        """ 
            Removes staves. Stores the resulting image.
        """
        if self.srmv_algorithm == 0:
            musicstaves_no_staves = musicstaves.MusicStaves_rl_roach_tatem(self.image, 0, 0)
        elif self.srmv_algorithm == 1:
            musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(self.image, 0, 0)
        elif self.srmv_algorithm == 2:
            musicstaves_no_staves = musicstaves.MusicStaves_linetracking(self.image, 0, 0)
        elif self.srmv_algorithm == 3:
            musicstaves_no_staves = musicstaves.MusicStaves_rl_carter(self.image, 0, 0)
        elif self.srmv_algorithm == 4:
            musicstaves_no_staves = musicstaves.MusicStaves_rl_simple(self.image, 0, 0)
        
        # grab the number of stafflines from the first staff. We'll use that
        # as the global value
        num_stafflines = self.page_result['staves'][0]['num_lines']
        musicstaves_no_staves.remove_staves(u'all', num_stafflines)
        self.img_no_st = musicstaves_no_staves.image
        
        # DEBUGGING: Shows a file with the staves removed.
        # tfile = tempfile.mkstemp()
        # save_image(self.img_no_st, tfile[1])
        # self.nost_filename = tfile[1]
        
        
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
        
        ccs = self.img_no_st.cc_analysis()
        grouping_function = classify.ShapedGroupingFunction(16) # variable ?
        self.classified_image = cknn.group_and_update_list_automatic(ccs, grouping_function, max_parts_per_group = 4) # variable ?
        
    def pitch_finding(self):
        """ Pitch finding.
            Returns a list of pitches for a list of classified glyphs.
        """
        # this filters glyphs under a certain size. Remember we're working 
        # in tenths of a mm and not aboslute pixels
        def __check_size(c):
            return self._m10(c.width) > self.discard_size or self._m10(c.height) > self.discard_size
        cls_img = [c for c in self.classified_image if __check_size(c)]
        self.classified_image = cls_img
        
        self.rgb = Image(self.image, RGB)
        # DEBUGGING: Color the staves
        # for k,s in self.page_result['staves'].iteritems():
        #     staffcolor = RGBPixel(190 + (11*k) % 66, \
        #                           190 + (31*(k + 1)) % 66, \
        #                           190 + (51*(k + 2)) % 66)
        #     self.rgb.draw_filled_rect((s['line_positions'][0][0][0] - self._m10(20), s['line_positions'][0][0][1]), (s['line_positions'][-1][-1][0] + self._m10(20), s['line_positions'][-1][-1][1]), staffcolor)
        
        
        # DEBUGGING: Color the glyphs
        # for i,c in enumerate(self.classified_image):
        #     name = c.get_main_id().split(".")
        #     if len(name) > 1:
        #         name = name[1]
        #     else:
        #         name = name[0]
        #     neumecolor = RGBPixel(190 + (11*i) % 66, \
        #                           190 + (31*(i + 1)) % 66, \
        #                           190 + (51*(i + 2)) % 66)
        #     self.rgb.draw_filled_rect((c.ul_x - 5, c.ul_y - 5), (c.lr_x + 5, c.lr_y + 5), neumecolor)
        #     # self.rgb.draw_text((c.ul_x - 20, c.ul_y - random.randint(10,40)), "{0}".format(name), RGBPixel(0,0,0), 10, 0, False, False, 0)
        #     self.rgb.draw_text((c.ul_x, c.ul_y), "{0},{1}".format(c.ul_x, c.ul_y), RGBPixel(0,0,0), 9, 0, False, False, 0)
        #     self.rgb.draw_text((c.lr_x, c.lr_y), "{0},{1}".format(c.lr_x, c.lr_y), RGBPixel(0,0,0), 9, 0, False, False, 0)
        # 
        
        glyph_list = {}
        for i,c in enumerate(self.classified_image):
            snum = self._get_staff_by_coordinates(c.center_x, c.center_y)
            
            # DEBUGGING: Highlight the glyphs that are not found on a staff
            # if snum is None:
            #     neumecolor = RGBPixel(240, 10, 10)
            #     self.rgb.draw_filled_rect((c.ul_x - 5, c.ul_y - 5), (c.lr_x + 5, c.lr_y + 5), neumecolor)
            
            # assemble a glyph list so we can sort the glyphs. The way we get
            # the proper order is by putting the x value as the first element.
            # The sort method will sort by this value, so elements that are
            # further to the left will sort first.
            # We'll keep the original glyph object around. It may come in 
            # handy in a few steps.
            if snum is not None:
                if snum not in glyph_list.keys():
                    glyph_list[snum] = []
                glyph_list[snum].append([c.ul_x, c.ul_y, c])
                
        for staff, glyphs in glyph_list.iteritems():
             glyphs.sort()
             for g, glyph in enumerate(glyphs):
                 self.rgb.draw_text((glyph[2].ll_x, glyph[2].ll_y), "X-{0}".format(g), RGBPixel(255, 0, 0), 12, 0, False, False, 0)
            
        # lg.debug("C is a {0} at {1},{2}, has a width and height of {3}x{4} and is on staff {5}, idx {6}".format(glyph_name, c.center_x, c.center_y, c.width, c.height, snum, i))
        
        
        
        
        # DEBUGGING: Create temp files so that we can see this in the 
        # Gamera shell.
        tfile = tempfile.mkstemp()
        self.rgb.highlight(self.image, RGBPixel(0, 0, 0))
        
        save_image(self.rgb, tfile[1])
        self.rgb_filename = tfile[1]
        
        # for c in class_im:
        # 
        #     staff_number = '' 
        #     uod = ''
        #     staff_number = '' 
        #     line_number = ''
        #     note = ''
        #     mid = 0
        #     if c.nrows<10 and c.ncols<10: # If error found
        #         er = er + 1
        #     else:
        #         sep_c = c.get_main_id().split('.')
        #         if len(sep_c) <= 3:
        #             for i in range(3-len(sep_c)):
        #                 sep_c.append('')
        # 
        #         if sep_c[0] == 'neume':
        #             uod = up_or_down(sep_c[1], sep_c[2])
        #             neume_count = neume_count + 1
        #             for i, stave in enumerate(stavelines):
        #                 if uod == 'D':
        #                     if stave[2] > (c.offset_y - 4): # 4 is the value is for excluding notes touching the line
        #                         staff_number = stave[0]
        #                         line_number = stave[1]
        #                         note = notes[line_number]
        #                         break
        #                 elif uod == 'U':
        #                     if stave[2] > (c.offset_y + c.nrows - 4): # 4 is the value is for excluding notes touching the line
        #                         staff_number = stave[0]
        #                         line_number = stavelines[i-1][1] # we want the previous line
        #                         note = notes[line_number]
        #                         break
        # 
        #         elif sep_c[0] == 'clef':
        #             for stave in stavelines:
        #                 if abs((c.offset_y + c.nrows/2) - stave[2]) <= 4:
        #                     staff_number = stave[0]
        #                     line_number = stave[1]
        # 
        #         else:
        #             uod = ''
        #             staff_number = '' 
        #             line_number = ''
        #             note = ''
        # 
        #         glyph_kind = sep_c[0]
        #         actual_glyph = sep_c[1] 
        #         glyph_char = sep_c[2:]
        #         glyph_list.append([staff_number, #Which one of these do we actually need?
        #                             c.offset_x, 
        #                             c.offset_y, 
        #                             note, 
        #                             line_number, 
        #                             glyph_kind, 
        #                             actual_glyph, 
        #                             glyph_char, 
        #                             uod, 
        #                             c.ncols, 
        #                             c.nrows])
        # 
        # glyph_list.sort()
        # return glyph_list
    
    
    # private
    def _m10(self, pixels):
        """ 
            Converts the number of pixels to the number of 10ths of a MM.
            This allows us to be fairly precise while still using whole numbers.
            
            mm10 (micrometre) was chosen as it is a common metric typographic unit.
            
            Returns an integer of the number of mm10.
        """
        # 25.4 mm in an inch * 10.
        return int(round((pixels * 254) / self.image.resolution))
    
    def _get_staff_by_coordinates(self, x, y):
        for k,v in self.page_result['staves'].iteritems():
            top_coord = v['line_positions'][0][0]
            bot_coord = v['line_positions'][-1][-1]
            
            # y is the most important for finding which staff it's on
            if top_coord[1] <= y <= bot_coord[1]:
                # add 20 mm10 to the x values, since musicstaves doesn't 
                # seem to accurately guess the starts and ends of staves.
                if top_coord[0] - self._m10(20) <= x <= bot_coord[0] + self._m10(20):
                    return k
        return None
    
    
