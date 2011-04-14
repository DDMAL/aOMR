from gamera.core import *from gamera.toolkits import musicstavesfrom gamera.toolkits.aomr_tk.AomrExceptions import *from gamera import classifyfrom gamera import knnimport zipfileimport osimport warningsimport tempfileimport copyimport itertoolsimport randomimport logginglg = logging.getLogger('aomr')import pdbinit_gamera()class AomrObject(object):    """    Manipulates an Aomr file and stores its information    """    def __init__(self, filename, **kwargs):        """            Constructs and returns an AOMR object        """        self.filename = filename        # print "loading ", self.filename        self.lines_per_staff = kwargs['lines_per_staff']        self.sfnd_algorithm = kwargs['staff_finder']        self.srmv_algorithm = kwargs['staff_removal']        self.binarization = kwargs["binarization"]        if "glyphs" in kwargs.values():            self.classifier_glyphs = kwargs["glyphs"]        if "weights" in kwargs.values():            self.classifier_weights = kwargs["weights"]        self.discard_size = kwargs["discard_size"]        # the result of the staff finder. Mostly for convenience        self.staves = None        # a global to keep track of the number of stafflines.        self.num_stafflines = None        # cache this once so we don't have to constantly load it        self.image = load_image(self.filename)        self.image_resolution = self.image.resolution                if self.image.data.pixel_type != ONEBIT:            self.image = self.image.to_greyscale()            bintypes = ['threshold',                    'otsu_threshold',                    'sauvola_threshold',                    'niblack_threshold',                    'gatos_threshold',                    'abutaleb_threshold',                    'tsai_moment_preserving_threshold',                    'white_rohrer_threshold']            self.image = getattr(self.image, bintypes[self.binarization])(0)            # BUGFIX: sometimes an image loses its resolution after being binarized.            if self.image.resolution < 1:                self.image.resolution = self.image_resolution                        self.image_size = [self.image.ncols, self.image.nrows]        # store the image without stafflines        self.img_no_st = None        self.rgb = None        self.page_result = {            'staves': {},            'dimensions': self.image_size        }    def run(self):        self.find_staves()        self.remove_stafflines()        self.glyph_classification()        self.pitch_finding()    def find_staves(self):        if self.sfnd_algorithm is 0:            s = musicstaves.StaffFinder_miyao(self.image)        elif self.sfnd_algorithm is 1:            s = musicstaves.StaffFinder_dalitz(self.image)        elif self.sfnd_algorithm is 2:            s = musicstaves.StaffFinder_projections(self.image)        else:            raise AomrStaffFinderNotFoundError("The staff finding algorithm was not found.")        s.find_staves()        av_lines = s.get_average()        # print av_lines        # lg.debug("Linelist is {0}".format(s.linelist))        if len(self._flatten(s.linelist)) == 0:            # no lines were found            return None                # get a polygon object. This stores a set of vertices for x,y values along the staffline.        self.staves = s.get_polygon()        if len(self.staves) < self.lines_per_staff:            # the number of lines found was less than expected.            return None        # lg.debug("Staves is {0}".format(self.staves))        all_line_positions = []                for i, staff in enumerate(self.staves):                                                yv = []            xv = []                        # linepoints is an array of arrays of vertices describing the             # stafflines in the staves.            #            # For the staff, we end up with something like this:            # [            #   [ (x,y), (x,y), (x,y), ... ],            #   [ (x,y), (x,y), (x,y), ... ],            #   ...            # ]            line_positions = []                        for staffline in staff:                pts = staffline.vertices                yv += [p.y for p in pts]                xv += [p.x for p in pts]                line_positions.append([(p.x,p.y) for p in pts])                        ulx,uly = min(xv),min(yv)            lrx,lry = max(xv),max(yv)                        # To accurately interpret objects above and below, we need to project             # ledger lines on the top and bottom. To do this, we estimate points            # based on the line positions we already have.            #            # Since we can't *actually* get the points, we'll predict based on the            # first and last positions of the top and bottom lines.            # first, get the top two and bottom two positions            ledger_lines_top = line_positions[0:2]            ledger_lines_bottom = line_positions[-2:]                        # lg.debug("Len 0: {0}".format(len(ledger_lines_top[0])))            # lg.debug("Len 1: {0}".format(len(ledger_lines_top[1])))                        # fix their lengths to be equal            if len(ledger_lines_top[0]) != len(ledger_lines_top[1]):                if len(ledger_lines_top[0]) > len(ledger_lines_top[1]):                    longest_line = ledger_lines_top[0]                    shortest_line = ledger_lines_top[1]                else:                    longest_line = ledger_lines_top[1]                    shortest_line = ledger_lines_top[0]                                lendiff = len(longest_line) - len(shortest_line)                                # slice off a chunk of the shortest line                short_end = shortest_line[-lendiff:]                long_end = longest_line[-lendiff:]                                for p,pt in enumerate(long_end):                    pt_x = pt[0]                    pt_y = short_end[p][1]                    short_end[p] = (pt_x, pt_y)                                shortest_line.extend(short_end)                            # fix their lengths to be equal            if len(ledger_lines_bottom[0]) != len(ledger_lines_bottom[1]):                if len(ledger_lines_bottom[0]) > len(ledger_lines_bottom[1]):                    longest_line = ledger_lines_bottom[0]                    shortest_line = ledger_lines_bottom[1]                else:                    longest_line = ledger_lines_bottom[1]                    shortest_line = ledger_lines_bottom[0]                lendiff = len(longest_line) - len(shortest_line)                # slice off a chunk of the shortest line                short_end = shortest_line[-lendiff:]                long_end = longest_line[-lendiff:]                for p,pt in enumerate(long_end):                    pt_x = pt[0]                    pt_y = short_end[p][1]                    short_end[p] = (pt_x, pt_y)                shortest_line.extend(short_end)                        imaginary_lines = []                        # take the second line. we'll then subtract each point from the corresponding            # value in the first.            i_line_1 = []            i_line_2 = []            for j,point in enumerate(ledger_lines_top[1]):                                # lg.debug("Point 1: {0}".format(point[1]))                # lg.debug("LL TOP is: {0}".format(ledger_lines_top[0][j][1]))                                diff_y = point[1] - ledger_lines_top[0][j][1]                pt_x = point[0]                pt_y_1 = ledger_lines_top[0][j][1] - diff_y                pt_y_2 = pt_y_1 - diff_y                i_line_1.append((pt_x, pt_y_1))                i_line_2.append((pt_x, pt_y_2))                        # insert these. Make sure the highest line is added last.            line_positions.insert(0, i_line_1)            line_positions.insert(0, i_line_2)                        # now do the bottom ledger lines            i_line_1 = []            i_line_2 = []            for k,point in enumerate(ledger_lines_bottom[1]):                diff_y = point[1] - ledger_lines_bottom[0][k][1]                pt_x = point[0]                pt_y_1 = ledger_lines_bottom[1][k][1] + diff_y                pt_y_2 = pt_y_1 + diff_y                i_line_1.append((pt_x, pt_y_1))                i_line_2.append((pt_x, pt_y_2))            line_positions.extend([i_line_1, i_line_2])            # average lines y_position            avg_lines = []            for l, line in enumerate(av_lines[i]):                avg_lines.append(line.average_y)            diff_up = avg_lines[1]-avg_lines[0]            diff_lo = avg_lines[3]-avg_lines[2]               avg_lines.insert(0, avg_lines[0] - 2 * diff_up)            avg_lines.insert(1, avg_lines[1] - diff_up)            avg_lines.append(avg_lines[5] + diff_lo)            avg_lines.append(avg_lines[5] + 2 * diff_lo) # not using the 8th line            self.page_result['staves'][i] = {                'staff_no': i+1,                'coords': [ulx, uly, lrx, lry],                'num_lines': len(staff),                'line_positions': line_positions,                'contents': [],                'clef_shape': None,                'clef_line': None,                'avg_lines': avg_lines            }        # return True            # print self.page_result['staves'][i]            all_line_positions.append(self.page_result['staves'][i])            # staff_coords.append(self.page_result['staves'][i]['coords'])        return all_line_positions    def staff_coords(self):        """             Returns the coordinates for each one of the staves        """        st_coords = []        for i, staff in enumerate(self.staves):            st_coords.append(self.page_result['staves'][i]['coords'])        return st_coords    def remove_stafflines(self):        """ Remove Stafflines.            Removes staves. Stores the resulting image.        """        if self.srmv_algorithm == 0:            musicstaves_no_staves = musicstaves.MusicStaves_rl_roach_tatem(self.image, 0, 0)        elif self.srmv_algorithm == 1:            musicstaves_no_staves = musicstaves.MusicStaves_rl_fujinaga(self.image, 0, 0)        elif self.srmv_algorithm == 2:            musicstaves_no_staves = musicstaves.MusicStaves_linetracking(self.image, 0, 0)        elif self.srmv_algorithm == 3:            musicstaves_no_staves = musicstaves.MusicStaves_rl_carter(self.image, 0, 0)        elif self.srmv_algorithm == 4:            musicstaves_no_staves = musicstaves.MusicStaves_rl_simple(self.image, 0, 0)                # grab the number of stafflines from the first staff. We'll use that        # as the global value        num_stafflines = self.page_result['staves'][0]['num_lines']        musicstaves_no_staves.remove_staves(u'all', num_stafflines)        self.img_no_st = musicstaves_no_staves.image                # DEBUGGING: Shows a file with the staves removed.        # tfile = tempfile.mkstemp()        # save_image(self.img_no_st, tfile[1])        # self.nost_filename = tfile[1]        def staff_no_non_parallel(self, glyphs, discard_size):        """            XXX        """        st_bound_coords = self.staff_coords()        st_full_coords = self.find_staves()        av_punctum = self.average_punctum(glyphs)        # lg.debug("average_punctum: {0}".format(av_punctum))        # lg.debug("staff_bounding_coordinates: {0}".format(print st_bound_coords))        for g in glyphs:            com = self.x_projection_vector(g, av_punctum, discard_size)            if g.get_main_id().split('.')[0] == 'neume': # just for testing, actual glyphs come prefiltered                print g                st, st_no = self._return_staff_no(g, st_bound_coords, st_full_coords, com)                miyao_line = self._return_vertical_line(g, st[0])                sp_or_ln_no = self._return_line_or_space_no(g, com, st, miyao_line)                print("Glyph: {0}, located at staff No. {1}, between miyao lines {2} and {3}\n".format(g.get_main_id(), st_no + 1, miyao_line - 1, miyao_line))                # break                # for i, s in enumerate(st_bound_coords): # i : staff number                #     print s                #     if s[1] <= g.offset_y < s[3]: # GVM: add the center of mass!                #        print ("This glyph is located at staff No. {0}".format(i))                 #        g_.append([g,i])                #        st_x = st_full_coords[0]['line_positions'][0]                                       # for j, x in enumerate(st_y): # j is the vertical line number                       #     # print("st_x : {1}, glyph x_offset: {0}".format(g.offset_x, x[0]))                       #     if x[0] > g.offset_x:                       #         print("Glyph {0} is located at staff No. {1}, between verticals lines {2} and {3}".format(g, i, j-1, j))                       #         print st_full_coords[i]['line_positions']                       #         # break                                              #         for k, l in enumerate(st_full_coords[i]['line_positions']):                       #             avg_y = 0.5*(l[j-1][1]+l[j][1])                       #             print avg_y                       #             if avg_y > g.offset_y:                       #                 print ("LOCATED IN LINE {0}".format(k))                       #                 # print("l[j][1]: {0}, g_offset_y: {1}".format(l[j-1][1], g.offset_y))                       #                 break                                                                                                                                                                                        def _return_staff_no(self, g, st_bound_coords, st_full_coords, com):        """            Returns the staff and staff number where a specific glyph is located         """        for i, s in enumerate(st_bound_coords):            # print("s[1]: {0}\tg.offset_y: {1}\ts[3]: {2}".format(0.5*(3*s[1]-s[3]), g.offset_y, 0.5*(3*s[3]-s[1])))            if 0.5*(3*s[1]-s[3]) <= g.offset_y + com < 0.5*(3*s[3]-s[1]): # GVM: considering the ledger lines in an unorthodox way.                st_no = st_full_coords[i]['line_positions']                return st_no, i    def _return_vertical_line(self, g, st):        """            Returns the miyao line number just after the glyph, starting from 0        """        for j, x in enumerate(st):            # print j, x[0], x            if x[0] > g.offset_x:                return j    def _return_line_or_space_no(self, g, com, st, miyao_line):        """            Returns the line or space number where the glyph is located for a specific stave an miyao line.        """        for i in range(len(st)):             # if st[i][miyao_line][1] > g.offset_y + com:            if st[i][miyao_line][1] > g.offset_y + com:                print '\t\t\t*'                print st[i][miyao_line-1], st[i][miyao_line]                  return            else:                print st[i][miyao_line-1], st[i][miyao_line]            def glyph_classification(self):        """ Glyph classification.            Returns a list of the classified glyphs with its position and size.        """        cknn = knn.kNNInteractive([],                                ["area",                                 "aspect_ratio",                                "black_area",                                 "compactness",                                 "moments",                                 "ncols_feature",                                "nholes",                                 "nholes_extended",                                 "nrows_feature",                                 "skeleton_features",                                 "top_bottom",                                 "volume",                                 "volume16regions",                                 "volume64regions",                                 "zernike_moments"],                                 True,                                8)                cknn.from_xml_filename(self.classifier_glyphs)        cknn.load_settings(self.classifier_weights) # Option for loading the features and weights of the training stage.                ccs = self.img_no_st.cc_analysis()        grouping_function = classify.ShapedGroupingFunction(16) # variable ?        self.classified_image = cknn.group_and_update_list_automatic(ccs, grouping_function, max_parts_per_group = 4) # variable ?            def pitch_finding(self):        """ Pitch finding.            Returns a list of pitches for a list of classified glyphs.        """        # this filters glyphs under a certain size. Remember we're working         # in tenths of a mm and not aboslute pixels        def __check_size(c):            return self._m10(c.width) > self.discard_size or self._m10(c.height) > self.discard_size        cls_img = [c for c in self.classified_image if __check_size(c)]        self.classified_image = cls_img                        glyph_list = {}        for i,c in enumerate(self.classified_image):            snum = self._get_staff_by_coordinates(c.center_x, c.center_y)                        if snum is not None:                if snum not in glyph_list.keys():                    glyph_list[snum] = []                glyph_list[snum].append([c.ul_x, c.ul_y, c])                        for staff, glyphs in glyph_list.iteritems():             glyphs.sort()             for g, glyph in enumerate(glyphs):                 self.rgb.draw_text((glyph[2].ll_x, glyph[2].ll_y), "X-{0}".format(g), RGBPixel(255, 0, 0), 12, 0, False, False, 0)                 o = glyph.splitx(0.2) # should be in 10mm instead of percentage                 # print o                 # print o[0].ncols                     # private    def _m10(self, pixels):        """             Converts the number of pixels to the number of 10ths of a MM.            This allows us to be fairly precise while still using whole numbers.            mm10 (micrometre) was chosen as it is a common metric typographic unit.            Returns an integer of the number of mm10.        """        # 25.4 mm in an inch * 10.        return int(round((pixels * 254) / self.image.resolution))        def _get_staff_by_coordinates(self, x, y):        for k,v in self.page_result['staves'].iteritems():            top_coord = v['line_positions'][0][0]            bot_coord = v['line_positions'][-1][-1]                        # y is the most important for finding which staff it's on            if top_coord[1] <= y <= bot_coord[1]:                # add 20 mm10 to the x values, since musicstaves doesn't                 # seem to accurately guess the starts and ends of staves.                if top_coord[0] - self._m10(20) <= x <= bot_coord[0] + self._m10(20):                    return k        return None        def _flatten(self, l, ltypes=(list, tuple)):        ltype = type(l)        l = list(l)        i = 0        while i < len(l):            while isinstance(l[i], ltypes):                if not l[i]:                    l.pop(i)                    i -= 1                    break                else:                    l[i:i + 1] = l[i]            i += 1        return ltype(l)        def average_punctum(self, glyphs):        """ Average Punctum.            returns the average number of columns of the punctums in a given page        """        wide = 0        i = 0        avg_punctum_col = 0        for glyph in glyphs:            # print glyph.get_main_id(), glyph.ncols            if glyph.get_main_id() == 'neume.punctum':                wide = wide + glyph.ncols                i = i + 1        avg_punctum_col = wide / i        return avg_punctum_col            def x_projection_vector(self, glyph, avg_punctum, discard_size):        """ Projection Vector            creates a subimage of the original glyph and returns its center of mass        """        com = 0        # print glyph        if glyph.ncols > discard_size and glyph.nrows > discard_size:            if glyph.ncols < avg_punctum:                avg_punctum = glyph.ncols            temp_glyph = glyph.subimage((glyph.offset_x, glyph.offset_y), \                ((glyph.offset_x + avg_punctum - 1), (glyph.offset_y + glyph.nrows - 1)))            projection_vector = temp_glyph.projection_rows()            com = self.center_of_mass(projection_vector)        else:            com = 0        return com    def center_of_mass(self, projection_vector):        """ Center of Mass.            returns the center of mass of a given glyph        """        s = 0.        v = 0.        for i, value in enumerate(projection_vector):            s = s + ( i + 1 ) * projection_vector[i]            v = v + value        com = s / v        return com    def st_avg_post(self):        """ Stave Average Position.            returns the average position of the stave lines        """        st_position, av_lines = aomr_obj.find_staves() # staves position        return av_lines    def glyph_staff_y_pos_ave(self, g, com, st_position):        """ Glyph Staff Average y-Position.            calculates between what stave lines a certain glyph is located        """        g_ = []        y = (g.offset_y + com) # y is the y_position of the center of mass of a glyph        # print("{0}, ({1}, {2}), com: {3}".format(g.get_main_id(), g.offset_x, g.offset_y, y))        for s, staff in enumerate(st_position):            for l, line in enumerate(staff['avg_lines']):                # lg.debug("staff:{0}, line:{1}, line_y:{2}".format(s, l, line))                if l == 7: # awful solution for not having an error with the last line                    l = 6                diff = 0.5 * (staff['avg_lines'][l+1] - staff['avg_lines'][l])                # print ("diff: {0}".format(diff))                if round(line-diff/2) <= y <= round(line+diff/2): # Is the glyph on a line ?                    # print ("staff:{0}, line:{1}, y_pos_line:{2}".format(s+1, l-1, line))                    g_.append([0, s, l])                    return g_                elif round(line+diff/2) <= y <= round(line+3*diff/2): # Is the glyph on a space ?                    # print ("staff:{0}, space:{1}, y_pos_line:{2}".format(s+1, l-1, line))                    g_.append([1, s, l])                    return g_                else:                    # print ("y: {0} line-diff/2: {1} line+diff/2: {2} line+3*diff/2: {3}".format(y, line-diff/2, line+diff/2, line+3*diff/2))                    pass        return g_    # def glyph_staff_pos_miyao(self, g, com):    #     print self.st_avg_post()     def pitch_find(self, glyphs, st_position, discard_size):        """ Pitch Find.            pitch find for all glyphs in a page            g_ is where the glyph and other values such as center of mass and pitch will be                 allocated        """        proc_glyphs = []        scale = ['g', 'f', 'e', 'd', 'c', 'b', 'a', 'g', 'f', 'e', 'd', 'c', 'b', 'a', 'g', 'f']        av_punctum = self.average_punctum(glyphs)        # print av_punctum        for g in glyphs:            # lg.debug("g: {0}".format(g.get_main_id()))            if g.get_main_id().split('.')[0] != '_group':                com = self.x_projection_vector(g, av_punctum, discard_size)                g_ = self.glyph_staff_y_pos_ave(g, com, st_position)                strt_pos = 2*g_[0][2]+g_[0][0]                                note = scale[strt_pos]                stave = g_[0][1]+1                if g.get_main_id().split('.')[0] == 'division' \                    or g.get_main_id().split('.')[0] =='custos' \                    or g.get_main_id().split('.')[0] =='alteration':                    note = None            else:                note = None                stave = None                strt_pos=None                # print "HERE!"            # proc_glyphs.append((g.get_main_id(), stave, g.offset_x, note))             proc_glyphs.append([g, stave, g.offset_x, note, strt_pos])         print "END!"        return proc_glyphs