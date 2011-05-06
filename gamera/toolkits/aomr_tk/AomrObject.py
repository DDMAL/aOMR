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
import math
from operator import itemgetter, attrgetter

import logging
lg = logging.getLogger('aomr')
import pdb

init_gamera()

class AomrObject(object):
    """
    Manipulates an Aomr file and stores its information
    """
    def __init__(self, filename, **kwargs):
        """
            Constructs and returns an AOMR object
        """
        self.filename = filename
        self.extended_processing = True
        # print "loading ", self.filename
        
        self.lines_per_staff = kwargs['lines_per_staff']
        self.sfnd_algorithm = kwargs['staff_finder']
        self.srmv_algorithm = kwargs['staff_removal']
        self.binarization = kwargs["binarization"]
        
        if "glyphs" in kwargs.values():
            self.classifier_glyphs = kwargs["glyphs"]
        if "weights" in kwargs.values():
            self.classifier_weights = kwargs["weights"]
        
        self.discard_size = kwargs["discard_size"]
        self.avg_punctum = None
        
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
     
        av_lines = s.get_average()
        # print av_lines
        # lg.debug("Linelist is {0}".format(s.linelist))
        
        if len(self._flatten(s.linelist)) == 0:
            # no lines were found
            return None
        
        # get a polygon object. This stores a set of vertices for x,y values along the staffline.
        self.staves = s.get_polygon()
        
        if len(self.staves) < self.lines_per_staff:
            # the number of lines found was less than expected.
            return None
            
        # lg.debug("Staves is {0}".format(self.staves))
        all_line_positions = []
        
        for i, staff in enumerate(self.staves):
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
            
            # lg.debug("Len 0: {0}".format(len(ledger_lines_top[0])))
            # lg.debug("Len 1: {0}".format(len(ledger_lines_top[1])))
            
            # fix their lengths to be equal
            if len(ledger_lines_top[0]) != len(ledger_lines_top[1]):
                if len(ledger_lines_top[0]) > len(ledger_lines_top[1]):
                    longest_line = ledger_lines_top[0]
                    shortest_line = ledger_lines_top[1]
                else:
                    longest_line = ledger_lines_top[1]
                    shortest_line = ledger_lines_top[0]
                
                lendiff = len(longest_line) - len(shortest_line)
                
                # slice off a chunk of the shortest line
                short_end = shortest_line[-lendiff:]
                long_end = longest_line[-lendiff:]
                
                for p,pt in enumerate(long_end):
                    pt_x = pt[0]
                    pt_y = short_end[p][1]
                    short_end[p] = (pt_x, pt_y)
                
                shortest_line.extend(short_end)
                
            # fix their lengths to be equal
            if len(ledger_lines_bottom[0]) != len(ledger_lines_bottom[1]):
                if len(ledger_lines_bottom[0]) > len(ledger_lines_bottom[1]):
                    longest_line = ledger_lines_bottom[0]
                    shortest_line = ledger_lines_bottom[1]
                else:
                    longest_line = ledger_lines_bottom[1]
                    shortest_line = ledger_lines_bottom[0]
                lendiff = len(longest_line) - len(shortest_line)
                # slice off a chunk of the shortest line
                short_end = shortest_line[-lendiff:]
                long_end = longest_line[-lendiff:]
                for p,pt in enumerate(long_end):
                    pt_x = pt[0]
                    pt_y = short_end[p][1]
                    short_end[p] = (pt_x, pt_y)
                shortest_line.extend(short_end)
            
            imaginary_lines = []
            
            # take the second line. we'll then subtract each point from the corresponding
            # value in the first.
            i_line_1 = []
            i_line_2 = []
            for j,point in enumerate(ledger_lines_top[1]):
                
                # lg.debug("Point 1: {0}".format(point[1]))
                # lg.debug("LL TOP is: {0}".format(ledger_lines_top[0][j][1]))
                
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
            
            # average lines y_position
            avg_lines = []
            for l, line in enumerate(av_lines[i]):
                avg_lines.append(line.average_y)
            diff_up = avg_lines[1]-avg_lines[0]
            diff_lo = avg_lines[3]-avg_lines[2]   
            avg_lines.insert(0, avg_lines[0] - 2 * diff_up)
            avg_lines.insert(1, avg_lines[1] - diff_up)
            avg_lines.append(avg_lines[5] + diff_lo)
            avg_lines.append(avg_lines[5] + 2 * diff_lo) # not using the 8th line
            
            self.page_result['staves'][i] = {
                'staff_no': i+1,
                'coords': [ulx, uly, lrx, lry],
                'num_lines': len(staff),
                'line_positions': line_positions,
                'contents': [],
                'clef_shape': None,
                'clef_line': None,
                'avg_lines': avg_lines
            }
            all_line_positions.append(self.page_result['staves'][i])
        return all_line_positions



        
        
    def staff_coords(self):
        """ 
            Returns the coordinates for each one of the staves
        """
        st_coords = []
        for i, staff in enumerate(self.staves):
            st_coords.append(self.page_result['staves'][i]['coords'])
        return st_coords
        
        
    def remove_stafflines(self):
        """ Remove Stafflines.
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
        
        
    def miyao_pitch_find(self, glyphs):
        """
            Returns a set of glyphs with pitches
        """
        proc_glyphs = []
        st_bound_coords = self.staff_coords()
        st_full_coords = self.find_staves()
        
        # what to do if there are no punctum on a page???
        av_punctum = self.average_punctum(glyphs)
        for g in glyphs:
            g_cc = None
            sub_glyph_center_of_mass = None
            glyph_id = g.get_main_id()
            glyph_var = glyph_id.split('.')
            glyph_type = glyph_var[0]
            # lg.debug("glyph_id: {0}".format(glyph_id))
            

            if glyph_type == 'neume':
                
                center_of_mass = self.process_neume(g)
                lg.debug("COM: {0}".format(center_of_mass))
                                
            else:
                center_of_mass = self.x_projection_vector(g)
                # lg.debug("\tCenter of mass of G_CC {1}".format(g_cc, center_of_mass))

            if glyph_type == '_group':
                strt_pos = None
                st_no = None
                center_of_mass = 0
            
            else:
                st, st_no = self._return_staff_no(g, st_bound_coords, st_full_coords, center_of_mass)
                miyao_line = self._return_vertical_line(g, st[0])
                # lg.debug("\nst[0]: {0}\nmiyao line: {1}".format(st[0], miyao_line))
                
                if glyph_type == 'division' or glyph_type =='alteration':
                    strt_pos = None
                elif glyph_type == "neume" or glyph_type == "custos" or glyph_type == "clef":
                    line_or_space, line_num = self._return_line_or_space_no(g, center_of_mass, st, miyao_line) # line (0) or space (1), no
                    strt_pos = self.strt_pos_find(g, line_or_space, line_num) 
                    # lg.debug("line (0) or space(1): {0}, number: {1}, Start Position: {2}".format(line_or_space, line_num, strt_pos))
                else:
                    strt_pos = None
                    st_no = None
            # lg.debug("\nGlyph {0} \tStave {1} \tOffset {2} \tStart Pos {3}".format(g, st_no, g.offset_x, strt_pos))
            proc_glyphs.append([g, st_no, g.offset_x, strt_pos])
        sorted_glyphs = self.sort_glyphs(proc_glyphs)  
    
                  
        return sorted_glyphs

    def biggest_cc(self, g_cc):
        """
            Returns the biggest cc area glyph
        """
        sel = 0
        black_area = 0
        for i, each in enumerate(g_cc):
            if each.black_area() > black_area:
                black_area = each.black_area()
                sel = i
        # lg.debug("HE, VE OR DOT. g_cc {0}, sel: {1} g_cc[sel] {2}".format(g_cc, sel, g_cc[sel]))
        return g_cc[sel]
        
    def strt_pos_find(self, glyph, line_or_space, line_num):
        """ Start position finding.
            Returns the start position, starting from ledger line 0, which strt_pos value is 0.
            
        """
        strt_pos = (line_num + 1)*2 + line_or_space
        return strt_pos
        
        
    def pitch_find_from_strt_pos(self, strt_pos):
        """ Pitch Find.
            pitch find algorithm for all glyphs in a page
            
        """
        scale = ['g', 'f', 'e', 'd', 'c', 'b', 'a', 'g', 'f', 'e', 'd', 'c', 'b', 'a', 'g', 'f', 'e', 'd', 'c', 'b', 'a']
        pitch = scale[strt_pos]
        # lg.debug("PITCH: {0}".format(pitch))
        return pitch
        
    def sort_glyphs(self, proc_glyphs):
        """
            Sorts the glyphs by its place in the page (up-bottom, left-right) and appends the proper note
            according to the clef at the beginning of each stave
        """
        sorted_glyphs = sorted(proc_glyphs, key = itemgetter(1,2))

        
        for glyph_array in sorted_glyphs:
            this_glyph = glyph_array[0]
            this_glyph_id = this_glyph.get_main_id()
            this_glyph_type = this_glyph_id.split(".")[0]
            # lg.debug("glyph array: {0}, {1}".format(this_glyph_id, glyph_array))
            if this_glyph_type == 'clef':
                shift = self.clef_shift(glyph_array)
                lg.debug("CLEF!!!!!!! OLD POSITION: {0} {1}".format(glyph_array[3], glyph_array))
                glyph_array[3] = 6 - glyph_array[3]/2
                lg.debug("CLEF!!!!!!! ACTUAL POSITION: {0}".format(glyph_array[3]))
                glyph_array.append(None)
                
            elif this_glyph_type == 'neume' or this_glyph_type == 'custos':
                # lg.debug("shift {0}".format(shift))
                pitch = self.pitch_find_from_strt_pos(glyph_array[3]-shift)
                
                glyph_array.append(pitch)
                
            else:
                glyph_array.append(None)
            # lg.debug("glyph_array:{0}".format(glyph_array))    
        return sorted_glyphs
        
    def clef_shift(self, glyph_array):
        """ Clef Shift.
            This methods shifts the note names depending on the staff clef
        """
        this_clef = glyph_array[0]
        this_clef_id = this_clef.get_main_id()
        this_clef_type = this_clef_id.split(".")[1]
        shift = 0
        if this_clef_type == 'c':
            shift = glyph_array[3] - 4
            # lg.debug("C clef in position {0}, shift {1}".format(glyph_array[3], shift))
            return shift
        elif this_clef_type == 'f':
            shift = glyph_array[3] - 1
            # lg.debug("F clef in position {0}, shift {1}".format(glyph_array[3], shift))
            return shift




    def _return_staff_no(self, g, st_bound_coords, st_full_coords, center_of_mass):
        """
            Returns the staff and staff number where a specific glyph is located 
        """
        
        for i, s in enumerate(st_bound_coords):
            # lg.debug("s[1]: {0}\tg.offset_y: {1}\ts[3]: {2}".format(0.5*(3*s[1]-s[3]), g.offset_y, 0.5*(3*s[3]-s[1])))
            if 0.5*(3* s[1] - s[3]) <= g.offset_y + center_of_mass < 0.5*(3 * s[3] - s[1]): # GVM: considering the ledger lines in an unorthodox way.
                st_no = st_full_coords[i]['line_positions']
                return st_no, i+1
                
                
    def _return_vertical_line(self, g, st):
        """
            Returns the miyao line number just after the glyph, starting from 0
        """
        for j, stf in enumerate(st[1:]):
            # lg.debug("Miyao Line {0}: {1} g.offset_x: {2}".format(j, stf, g.offset_x))
            if stf[0] > g.offset_x:
                return j
                
    def _return_line_or_space_no(self, glyph, center_of_mass, st, miyao_line):
        """
            Returns the line or space number where the glyph is located for a specific stave an miyao line.
            
            Remember kids :)
                Line = 0
                Space = 1
            
        """
        # lg.debug("\nGLYPH: {0}\nCOM: {1}\nSTAVE: {2}\nMIYAO LINE: {3}".format(glyph, center_of_mass, st, miyao_line))
        horz_diff = float(st[0][miyao_line][0] - st[0][miyao_line-1][0])
        # lg.debug("HOR_MIYAO: {0} AND {0}".format(glyph, st[0][miyao_line-1][0], st[0][miyao_line][0]))
        for i, stf in enumerate(st[1:]):
            # lg.debug("i : {0} st[i][miyao_line+1][1] : {1}".format(i, st[i]))
            vert_diff_up = float(stf[miyao_line][1] - stf[miyao_line-1][1]) # y_pos difference with the upper miyao line
            vert_diff_lo = float(stf[miyao_line+1][1] - stf[miyao_line][1]) # y_pos difference with the lower miyao line
            factor_up = vert_diff_up/horz_diff
            factor_lo = vert_diff_lo/horz_diff
            diff_x_glyph_bar = float(glyph.offset_x - stf[miyao_line-1][0]) # difference between the glyph x_pos and the previous bar
            vert_pos_shift_up = factor_up * diff_x_glyph_bar # vert_pos_shift is the shifted vertical position of each line for each x position
            vert_pos_shift_lo = factor_lo * diff_x_glyph_bar # vert_pos_shift is the shifted vertical position of each line for each x position

            diff = (stf[miyao_line][1] + vert_pos_shift_lo) - (st[i][miyao_line-1][1] + vert_pos_shift_up)
            # lg.debug("DIFF: {1}, VERT_DIFF_UP: {2}, VERT_DIFF_LO: {3}".format(glyph, diff, vert_diff_up, vert_diff_lo))
            # print diff
            if stf[miyao_line][1] + 6*diff/16 > glyph.offset_y + center_of_mass:
                # lg.debug("CASE LINE 1. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE LINE 2. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 3*diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE LINE 3. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 4*diff/4, glyph.offset_y + center_of_mass))
                line_or_space = 0
                # print 'line', i
                return line_or_space, i
                
            elif stf[miyao_line][1] + 13*diff/16 > glyph.offset_y + center_of_mass:
                # lg.debug("CASE LINE 1. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE SPACE 2. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 3*diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE LINE 3. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 4*diff/4, glyph.offset_y + center_of_mass))
                line_or_space = 1
                # print 'space', i
                return line_or_space, i
                
            elif stf[miyao_line][1] + 4*diff/4 > glyph.offset_y + center_of_mass:
                # lg.debug("CASE LINE 1. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE SPACE 2. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 3*diff/4, glyph.offset_y + center_of_mass))
                # lg.debug("CASE LINE 3. Staff line {0}, Glyph {1} ".format(stf[miyao_line][1] + 4*diff/4, glyph.offset_y + center_of_mass))
                line_or_space = 0
                # print 'line+1', i+1
                return line_or_space, i+1
            else:
                pass



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
                                True,
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
                
        glyph_list = {}
        for i,c in enumerate(self.classified_image):
            snum = self._get_staff_by_coordinates(c.center_x, c.center_y)
            
            if snum is not None:
                if snum not in glyph_list.keys():
                    glyph_list[snum] = []
                glyph_list[snum].append([c.ul_x, c.ul_y, c])
                
        for staff, glyphs in glyph_list.iteritems():
             glyphs.sort()
             for g, glyph in enumerate(glyphs):
                 self.rgb.draw_text((glyph[2].ll_x, glyph[2].ll_y), "X-{0}".format(g), RGBPixel(255, 0, 0), 12, 0, False, False, 0)
                 o = glyph.splitx(0.2) # should be in 10mm instead of percentage
                 # 
                 #  o
                 # print o[0].ncols
                 
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
    
    def _flatten(self, l, ltypes=(list, tuple)):
        ltype = type(l)
        l = list(l)
        i = 0
        while i < len(l):
            while isinstance(l[i], ltypes):
                if not l[i]:
                    l.pop(i)
                    i -= 1
                    break
                else:
                    l[i:i + 1] = l[i]
            i += 1
        return ltype(l)
    
    def average_punctum(self, glyphs):
        """ Average Punctum.
            returns the average number of columns of the punctums in a given page
        """
        wide = 0
        i = 0
        avg_punctum_col = 0
        for glyph in glyphs:
            # print glyph.get_main_id(), glyph.ncols
            if glyph.get_main_id() == 'neume.punctum':
                wide = wide + glyph.ncols
                i = i + 1
        avg_punctum_col = wide / i
        
        self.avg_punctum = avg_punctum_col
        
    def x_projection_vector(self, glyph):
        """ Projection Vector
            creates a subimage of the original glyph and returns its center of mass
        """
        center_of_mass = 0
        # print glyph
        if glyph.ncols > self.discard_size and glyph.nrows > self.discard_size:
            if glyph.ncols < self.avg_punctum:
                this_punctum_size = glyph.ncols
            else:
                this_punctum_size = self.avg_punctum
                
            temp_glyph = glyph.subimage((glyph.offset_x + 0.0 * this_punctum_size, glyph.offset_y), \
                ((glyph.offset_x + 1.0 * this_punctum_size - 1), (glyph.offset_y + glyph.nrows - 1)))
            projection_vector = temp_glyph.projection_rows()
            center_of_mass = self.center_of_mass(projection_vector)
        else:
            center_of_mass = 0
        return center_of_mass

    def center_of_mass(self, projection_vector):
        """ Center of Mass.
            returns the center of mass of a given glyph
        """
        com = 0.
        s = 0.
        v = 0.
        for i, value in enumerate(projection_vector):
            s = s + ( i + 1 ) * value
            v = v + value
        if v == 0:
            return com
        com = s / v
        return com

    def glyph_staff_y_pos_ave(self, g, center_of_mass, st_position):
        """ Glyph Staff Average y-Position.
            calculates between what stave lines a certain glyph is located
        """
        glyph_array = []
        y = round(g.offset_y + center_of_mass) # y is the y_position of the center of mass of a glyph
        lg.debug("{0}, ({1}, {2}), com: {3}".format(g.get_main_id(), g.offset_x, g.offset_y, y))

        for s, staff in enumerate(st_position):
            for l, line in enumerate(staff['avg_lines'][1:]):
                # lg.debug("\tOFFSET + COM: {3}\t staff:{0}, line:{1}, line_y:{2}".format(s, l, line, y))
                diff = (0.5 * (line - staff['avg_lines'][l]))
                # lg.debug("\ndiff: {0}".format(diff))
                if math.floor(line-diff/2) <= y <= math.ceil(line+diff/2): # Is the glyph on a line ?
                    # lg.debug("staff:{0}, line:{1}, y_pos_line:{2}".format(s+1, l-1, line))
                    glyph_array.append([0, s, l])
                    return glyph_array
                elif math.floor(line+diff/2) <= y <= math.ceil(line+3*diff/2): # Is the glyph on a space ?
                    # lg.debug("\tstaff:{0}, space:{1}, y_pos_line:{2}".format(s+1, l-1, line))
                    glyph_array.append([1, s, l])
                    return glyph_array
                else:
                    # lg.debug("\ty: {0} line-diff/2: {1} line+diff/2: {2} line+3*diff/2: {3}".format(y, (line-diff/2), (line+diff/2), round(line+3*diff/2)))
                    pass
        lg.debug("glyph {0} glyph array {1}".format(g.get_main_id(), glyph_array))
        return glyph_array
        
    def pitch_find(self, glyphs, st_position):
        """ Pitch Find.
            pitch find algorithm for all glyphs in a page
            Returns a list of processed glyphs with the following structure:
                glyph, stave_number, offset_x, note_name, start_position
        """
        proc_glyphs = [] # processed glyphs
        av_punctum = self.average_punctum(glyphs)
        for g in glyphs:
            glyph_id = g.get_main_id()
            glyph_type = glyph_id.split(".")[0]
            if glyph_type != '_group':
                if glyph_type == 'neume':
                    center_of_mass = self.process_neume(g)
                else:
                    center_of_mass = self.x_projection_vector(g)
                glyph_array = self.glyph_staff_y_pos_ave(g, center_of_mass, st_position)
                strt_pos = 2 * (glyph_array[0][2]) + glyph_array[0][0] + 2
                lg.debug("\tGlyph Array: {0} \t\t\t\tStart Pos: {1}".format(glyph_array, strt_pos))
               #  lg.debug("\nglyph name: {0}\t {1} \tglyph_array: {2}\t COM: {3}\t ST POSITION: {4}".format(glyph_id, g, glyph_array, center_of_mass, strt_pos))

                stave = glyph_array[0][1]+1
                if glyph_type == 'division' or glyph_type =='alteration':
                    note = None
            else:
                note = None
                stave = None
                strt_pos=None

            # proc_glyphs.append([g, stave, g.offset_x, note, strt_pos]) 
            proc_glyphs.append([g, stave, g.offset_x, strt_pos])
            # lg.debug("\nGlyph {0} \tStave {1} \tOffset {2} \tStart Pos {3}".format(g, stave, g.offset_x, strt_pos))
                    
        sorted_glyphs = self.sort_glyphs(proc_glyphs)  
        return sorted_glyphs

    def process_neume(self, g):
        """
            Handles the cases of glyphs as podatus, epiphonus, cephalicus, and he, ve or dot.
        """
        g_cc = None
        sub_glyph_center_of_mass = None
        glyph_id = g.get_main_id()
        glyph_var = glyph_id.split('.')
        glyph_type = glyph_var[0]
        check_additions = False
            
        if not self.extended_processing:
            return self.x_projection_vector(g)
        else:
            # if check_gcc has elements, we know it's got one of these in it.
            if "he" in glyph_var or "ve" in glyph_var or "dot" in glyph_var:
                lg.debug("Check additions is true.")
                check_additions = True
            
            # if we want to use the biggest cc (when there are dots or other things),
            # set this_glyph to the biggest_cc. Otherwise, set it to the whole glyph.
            if check_additions:
                this_glyph = self.biggest_cc(g.cc_analysis())
            else:
                this_glyph = g
                
            g_center_of_mass, offset_y = self.check_special_neumes(this_glyph)
            
            if "podatus" in glyph_var or "epiphonus" in glyph_var or "cephalicus" in glyph_var:
                if check_additions is True:
                    center_of_mass = this_glyph.offset_y - g.offset_y + self.x_projection_vector(this_glyph)
                    return center_of_mass
                else:
                    center_of_mass = offset_y - this_glyph.offset_y + g_center_of_mass
                    return center_of_mass
            
            if check_additions:
                center_of_mass = this_glyph.offset_y - g.offset_y + self.x_projection_vector(this_glyph)
                return center_of_mass
            
            # if we've made it this far then we just return the plain old projection vector.
            return self.x_projection_vector(g)
                
    def check_special_neumes(self, glyph):
        glyph_var = glyph.get_main_id().split('.')
        
        if "podatus" in glyph_var or "epiphonus" in glyph_var:
            this_glyph = glyph.splity()[1]
        elif "cephalicus" in glyph_var:
            this_glyph = self.biggest_cc(glyph.splity())
        else:
            this_glyph = glyph
        glyph_center_of_mass = self.x_projection_vector(this_glyph)
        return glyph_center_of_mass, glyph.offset_y
            