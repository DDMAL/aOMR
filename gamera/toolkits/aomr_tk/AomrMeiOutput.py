from gamera.plugin import *
from gamera.toolkits.aomr_tk.AomrExceptions import *


from pymei.Components import MeiDocument
from pymei.Components import Modules as mod

import logging
lg = logging.getLogger('aomr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

lg.setLevel(logging.DEBUG)
lg.addHandler(h)

import uuid
import pdb
import copy

# [staff_number, c.offset_x, c.offset_y, note, line_number, 
#   glyph_kind, actual_glyph, glyph_char, uod, c.ncols, c.nrows]
#
# {'direction': 'D', 'form': ['clivis', '2'], 'strt_pos': 5, 'coord': [213, 179, 26, 35], 'strt_pitch': 'A', 'type': 'neume'}, 
# neume.scandicus.flexus.2.q.2.3.dot
# neume.he.torculus.liquescent.2.2
# neume.compound.dot.u3.u2.u2.d2
# neume.torculus.2.2.he.ve


class AomrMeiOutput(object):
    
    # define the form of a neume.
    # form: [ num, interval_dir... ]
    # e.g., clivis: [2, 'd']
    # torculus: [3, 'u', 'd']
    NEUME_NOTES = {
        'punctum': [],
        'virga': [],
        'cephalicus': ['d'],
        'clivis': ['d'],
        'epiphonus': ['u'],
        'podatus': ['u'],
        'porrectus': ['d','u'],
        'salicus': ['u', 'u'],
        'scandicus': ['u','u'],
        'torculus': ['u','d'],
        'ancus': ['d','d'], # See note 1 below
    }
    
    # given an alternate form, how many notes does it add to the neume?
    ADD_NOTES = {
        'flexus': ['d'], # scandicus.flexus, porrectus.flexus
        'resupinus': ['u'], # torculus.resupinus
    }
    
    SCALE = ['a','b','c','d','e','f','g']
    
    def __init__(self, incoming_data, original_image):
        self._recognition_results = incoming_data
        self.mei = mod.mei_()
        self.staff = None
        self.glyph = None
        
        self._note_elements = None
        self._neume_pitches = []
        
        # set up a basic MEI document structure
        
        # header
        self.meihead = mod.meihead_()
        self.filedesc = mod.filedesc_()
        self.titlestmt = mod.titlestmt_()
        self.title = mod.title_()
        self.pubstmt = mod.pubstmt_()
        
        self.titlestmt.add_child(self.title)
        self.filedesc.add_children([self.titlestmt, self.pubstmt])
        self.meihead.add_child(self.filedesc)
        self.mei.add_child(self.meihead)
        
        # music
        self.music = mod.music_()
        self.facsimile = self._create_facsimile_element()
        self.surface = self._create_surface_element()
        self.graphic = self._create_graphic_element(original_image)
        
        self.surface.add_child(self.graphic)
        self.facsimile.add_child(self.surface)
        self.music.add_child(self.facsimile)
        
        self.layout = self._create_layout_element()
        self.pg = self._create_page_element()
        self.layout.add_child(self.pg)
        self.music.add_child(self.layout)
        
        self.body = mod.body_()
        self.music.add_child(self.body)
        
        self.mdiv = mod.mdiv_()
        self.mdiv.attributes = {"type": "solesmes"}
        self.body.add_child(self.mdiv)
        
        self.score = mod.score_()
        
        self.mdiv.add_child(self.score)
        
        self.scoredef = mod.scoredef_()
        self.score.add_child(self.scoredef)
        
        self.section = mod.section_()
        self.pagebreak = self._create_pb_element()
        self.pagebreak.attributes = {"pageref": self.pg.id}
        self.section.add_child(self.pagebreak)
        self.score.add_child(self.section)
        
        self.staffgrp = self._create_staffgrp_element()
        self.staffdef = self._create_staffdef_element()
        self.staffdef.attributes = {'n': 1}
        self.staffgrp.add_child(self.staffdef)
        self.scoredef.add_child(self.staffgrp)
        
        self.layer = self._create_layer_element()
        self.staffel = self._create_staff_element()
        self.layer.add_child(self.staffel)
        self.section.add_child(self.layer)
        
        for sysnum,syst in self._recognition_results.iteritems():            
            self.system = syst
            self.systembreak = self._parse_system(sysnum, syst)
            z = mod.zone_()
            z.id = self._idgen()
            z.attributes = {'ulx': self.system['coord'][0], 'uly': self.system['coord'][1], \
                                'lrx': self.system['coord'][2], 'lry': self.system['coord'][3]}
            
            self.surface.add_child(z)
            # self.system.facs = z.id
            s = self._create_system_element()
            s.facs = z.id
            self.pg.add_child(s)
            self.systembreak.attributes = {"systemref": s.id}
        
        self.mei.add_child(self.music)
        
        self.md = MeiDocument.MeiDocument()
        self.md.addelement(self.mei)
        
        
    def _parse_system(self, sysnum, syst):
        sysbrk = self._create_sb_element()
        sysbrk.attributes = {"n": sysnum + 1}
        self.staffel.add_child(sysbrk)
        # staffel = self._create_staff_element()
        # staffel.attributes = {'n': stfnum}
        
        for c in self.system['content']:
            # parse the glyphs per staff.
            self.glyph = c
            # lg.debug(self.glyph)
            
            if c['type'] == 'neume':
                self.staffel.add_child(self._create_neume_element())
            elif c['type'] == 'clef':
                self.staffel.add_child(self._create_clef_element())
            elif c['type'] == 'division':
                self.staffel.add_child(self._create_division_element())
            elif c['type'] == 'custos':
                self.staffel.add_child(self._create_custos_element())
            elif c['type'] == "alteration":
                # staffel.add_child(self._create_alteration_element()) #GVM
                pass
        return sysbrk
        
        
    def _create_graphic_element(self, imgfile):
        graphic = mod.graphic_()
        graphic.id = self._idgen()
        graphic.attributes = {'xlink:href': imgfile}
        return graphic
    
    def _create_alteration_element(self):
        accid = mod.accid_()
        accid.id = self._idgen()
        if self.glyph['form'] is "sharp":
            accid.attributes = {"accid": "s"}
        elif self.glyph['form'] is "flat":
            accid.attributes = {"accid": "f"}
        
        zone = self._create_zone_element()
        note.facs = zone.id
        
        return accid
        
    def _create_surface_element(self):
        surface = mod.surface_()
        surface.id = self._idgen()
        return surface
    
    def _create_facsimile_element(self):
        facsimile = mod.facsimile_()
        facsimile.id = self._idgen()
        return facsimile
    
    def _create_zone_element(self):
        zone = mod.zone_()
        zone.id = self._idgen()
        zone.attributes = {'ulx': self.glyph['coord'][0], 'uly': self.glyph['coord'][1], \
                            'lrx': self.glyph['coord'][2], 'lry': self.glyph['coord'][3]}
        self.surface.add_child(zone)
        return zone
    
    def _create_layer_element(self):
        layer = mod.layer_()
        layer.id = self._idgen()
        return layer
    
    def _create_staffgrp_element(self):
        stfgrp = mod.staffgrp_()
        stfgrp.id = self._idgen()
        return stfgrp
    
    def _create_staffdef_element(self):
        stfdef = mod.staffdef_()
        stfdef.id = self._idgen()
        return stfdef
    
    def _create_staff_element(self):
        staff = mod.staff_()
        staff.id = self._idgen()
        return staff
    
    def _create_sb_element(self):
        sb = mod.sb_()
        sb.id = self._idgen()
        return sb
        
    def _create_pb_element(self):
        pb = mod.pb_()
        pb.id = self._idgen()
        return pb
    
    def _create_layout_element(self):
        layout = mod.layout_()
        layout.id = self._idgen()
        return layout
    
    def _create_page_element(self):
        page = mod.page_()
        page.id = self._idgen()
        return page
    
    def _create_system_element(self):
        system = mod.system_()
        system.id = self._idgen()
        return system
    
    def _create_episema_element(self):
        epi = mod.episema_()
        epi.id = self._idgen()
        return epi
    
    def _create_neume_element(self):
        # lg.debug("glyph: {0}".format(self.glyph['form']))
        full_width_episema = False
        has_dot = False
        has_vertical_episema = False
        has_horizontal_episema = False
        has_quilisma = False
        this_neume_form = None
        local_horizontal_episema = None
        
        neume = mod.neume_()
            
        neume.id = self._idgen()
        zone = self._create_zone_element()
        neume.facs = zone.id
        
        # lg.debug(self.glyph['form'])
        
        if self.glyph['form'][0] == "he":
            full_width_episema = True
            del self.glyph['form'][0]
        
        # we've removed any global he's, so 
        # any leftovers should be local.
        if 'he' in self.glyph['form']:
            has_horizontal_episema = True
        
        if 'dot' in self.glyph['form']:
            has_dot = True
        
        if 'q' in self.glyph['form']:
            # lg.debug("HAS QUILISMA!")
            has_quilisma = True
        
        if 've' in self.glyph['form']:
            has_vertical_episema = True
        
        if 'inclinatum' in self.glyph['form']:
            neume.attributes = {'variant': 'inclinatum'}
            
        neume.attributes = {'name': self.glyph['form'][0]}
        
        if 'compound' in self.glyph['form']:
            # do something and create a new set of pitch contours
            this_neume_form = [y for y in (self.__parse_contour(n) for n in self.glyph['form']) if y]
            self._note_elements = [y for y in (self.__parse_steps(n) for n in self.glyph['form']) if y]
        else:
            this_neume_form = copy.deepcopy(self.NEUME_NOTES[self.glyph['form'][0]])
            self._note_elements = self.glyph['form'][1:]
        # get the form so we can find the number of notes we need to construct.
        
        num_notes = len(this_neume_form) + 1
        # lg.debug("Glyph form: {0}".format(this_neume_form))
        # lg.debug("Num notes before add check: {0}".format(num_notes))
        # lg.debug("Neume form before add check: {0}".format(this_neume_form))
        
        # we don't have an off-by-one problem here, since an added interval means an added note
        check_additional = [i for i in self.ADD_NOTES.keys() if i in self.glyph['form'][1:]]
        # lg.debug("Check additional: {0}".format(check_additional))
        if check_additional:
            lg.debug("Adding extra notes.")
            for f in check_additional:
                this_neume_form.extend(self.ADD_NOTES[f])
                
                ## THIS SHOULD BE CHANGED. Otherwise we may end up with two attributes with the
                # same name.
                neume.attributes = {"variant": self.ADD_NOTES[f]}
            
            num_notes = num_notes + len(check_additional)
            
        # lg.debug("Num notes after add check: {0}".format(num_notes))
        # lg.debug("Neume form after add check: {0}".format(this_neume_form))
        
        self._neume_pitches = []
        # note elements are everything after the first form. This determines the shape a note takes.
        self._neume_pitches.append(self.glyph['strt_pitch'])
        # lg.debug("neume pitches: {0}, no notes: {1}".format(self._neume_pitches, num_notes))
        nc = []
        if num_notes > 1:
            # we need to figure out the rest of the pitches in the neume.
            ivals = [int(d) for d in self._note_elements if d.isdigit()]
            # lg.debug("ivals: {0}, idx: {1}".format(ivals, self.SCALE.index(self.glyph['strt_pitch'])))
            try:
                idx = self.SCALE.index(self.glyph['strt_pitch'])
            except ValueError:
                raise AomrMeiPitchNotFoundError("The pitch {0} was not found in the scale".format(self.glyph['strt_pitch']))
                
            if len(ivals) != (num_notes - 1):
                raise AomrMeiNoteIntervalMismatchError("There is a mismatch between the number of notes and number of intervals.")
            
            # note elements = torculus.2.2.he.ve
            # ivals = [2,2]
            # torculus = ['u','d']
            
            # lg.debug(ivals)
            for n in xrange(len(ivals)):
                # get the direction
                dir = this_neume_form[n]
                # lg.debug("direction is {0}".format(dir))
                iv = ivals[n]
                n_idx = idx
                
                # lg.debug("index: {0}".format(idx))
                
                if dir == "u":
                    n_idx = ((idx + iv) % len(self.SCALE)) - 1
                elif dir == "d":
                    n_idx = idx - (iv -1)
                    if n_idx < 0:
                        n_idx += len(self.SCALE)
                        
                idx = n_idx
                self._neume_pitches.append(self.SCALE[n_idx])
        
        if full_width_episema is True:
            epi = self._create_episema_element()
            epi.attributes = {"form": "horizontal"}
            self.staffel.add_child(epi)
        
        qidxs = []
        if has_quilisma:
            self.__note_addition_figurer_outer("q", qidxs)
            
        dotidxs = []
        if has_dot:
            self.__note_addition_figurer_outer("dot", dotidxs)
            
        veidxs = []
        if has_vertical_episema:
            self.__note_addition_figurer_outer("ve", veidxs)
                            
        heidxs = []
        if has_horizontal_episema:
            self.__note_addition_figurer_outer("he", heidxs)
            
        # lg.debug("HE IDX: {0}".format(heidxs))
            
        # lg.debug("Num Notes: {0}".format(num_notes))
        for n in xrange(num_notes):
            p = self._neume_pitches[n]
            nt = self._create_note_element(p)
            if n == 0 and full_width_episema is True:
                epi.attributes = {"startid": nt.id}
            elif n == num_notes and full_width_episema is True:
                epi.attributes = {"endid": nt.id}
            
            if has_quilisma:
                if n in qidxs:
                    nt.attributes = {"quil": "true"}
            
            if has_dot:
                if n in dotidxs:
                    d = self._create_dot_element()
                    nt.add_child(d)
            
            if has_vertical_episema:
                if n in veidxs:
                    ep = self._create_episema_element()
                    ep.attributes = {"form": "vertical", "startid": nt.id}
                    self.staffel.add_child(ep)
            
            if has_horizontal_episema:
                # lg.debug("N is: {0}".format(n))
                if n in heidxs:
                    local_horizontal_episema = self._create_episema_element()
                    local_horizontal_episema.attributes = {"form": "horizontal", "startid": nt.id}
                    self.staffel.add_child(local_horizontal_episema)
                    
            
            if n == num_notes - 1 and local_horizontal_episema:
                # we've reached the end, and we have an HE we need to close up.
                local_horizontal_episema.attributes = {"endid": nt.id}
                
            nc.append(nt)
        neume.add_children(nc)
        
        return neume
        
    def _create_note_element(self, pname=None):
        note = mod.note_()
        note.id = self._idgen()
        note.pitchname = pname
        return note
    
    def _create_dot_element(self):
        dot = mod.dot_()
        dot.id = self._idgen()
        dot.attributes = {"form": "aug"}
        return dot
    
    def _create_custos_element(self):
        custos = mod.custos_()
        custos.id = self._idgen()
        zone = self._create_zone_element()
        custos.facs = zone.id
        return custos
    
    def _create_clef_element(self):
        clef = mod.clef_()
        clef.id = self._idgen()
        zone = self._create_zone_element()
        clef.facs = zone.id
        return clef
    
    def _create_division_element(self):
        division = mod.division_()
        division.id = self._idgen()
        zone = self._create_zone_element()
        division.facs = zone.id
        
        if self.glyph['form']:
            division.attributes = {'form': self.glyph['form'][0]}
        
        return division
    
    # def _create_alteration_element(self):
    #     alteration = mod.alteration_()
    #     alteration.id = self._idgen()
    #     zone = self._create_zone_element()
    #     alteration.facs = zone.id
    #     return alteration    
    
    def _idgen(self):
        """ Returns a UUID. """
        return "{0}-{1}".format('m', str(uuid.uuid4()))

    def __parse_contour(self, form):
        # removes the contour indicator from the neume
        # and creates a neume form.
        if len(form) is 2 and (form.startswith("u") or form.startswith("d")):
            # do something
            return form[0]
        else:
            return None
    
    def __parse_steps(self, form):
        if len(form) is 2 and (form.startswith("u") or form.startswith("d")):
            return form[1]
        else:
            return None
    
    def __note_addition_figurer_outer(self, ntype, idxarray):
        for i,n in enumerate(self.glyph['form']):
            if n == ntype:
                j = copy.copy(i) - 1
                if j == 0:
                    idxarray.append(0)
                while j:
                    if self.__is_valid_note_indicator(self.glyph['form'][j]):
                        idxarray.append(j)
                        break
                    else:
                        j -= 1
        
    
    def __is_valid_note_indicator(self, form):
        # used to test if a form is a valid indicator of a note (and not a q, dot, or anything else)
        if form.isdigit():
            return True
        elif len(form) == 2 and form.startswith("u") or form.startswith("d"):
            return True
        else:
            return False




if __name__ == "__main__":
    test_data = {0: {'content': [{'strt_pos': 6, 'strt_pitch': 'a', 'type': 'clef',
    'coord': [15, 143, 51, 198], 'form': ['f']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [81, 160, 132, 215],
    'form': ['torculus', '3', '2']}, {'strt_pos': 6, 'strt_pitch': 'a',
    'type': 'neume', 'coord': [173, 160, 191, 181], 'form': ['punctum']},
    {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume', 'coord': [198,
    160, 216, 181], 'form': ['punctum']}, {'strt_pos': 6, 'strt_pitch':
    'a', 'type': 'neume', 'coord': [222, 162, 256, 217], 'form':
    ['clivis', '3']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume',
    'coord': [265, 162, 315, 201], 'form': ['torculus', '2', '2']},
    {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord': [346,
    187, 381, 256], 'form': ['clivis', 'he', '2']}, {'strt_pos': 3,
    'strt_pitch': None, 'type': 'division', 'coord': [421, 128, 428, 159],
    'form': ['small']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type':
    'neume', 'coord': [463, 199, 482, 221], 'form': ['punctum']},
    {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume', 'coord': [489,
    166, 507, 187], 'form': ['punctum']}, {'strt_pos': 6, 'strt_pitch':
    'a', 'type': 'neume', 'coord': [515, 166, 532, 187], 'form':
    ['punctum']}, {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume',
    'coord': [540, 166, 558, 187], 'form': ['punctum']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [589, 167, 607, 223],
    'form': ['podatus', '3']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [615, 177, 632, 208], 'form': ['punctum',
    'inclinatum']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume',
    'coord': [633, 201, 646, 248], 'form': ['punctum', 'inclinatum',
    've']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord':
    [714, 204, 731, 224], 'form': ['punctum']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [764, 170, 782, 226],
    'form': ['podatus', '3']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [791, 179, 806, 217], 'form': ['punctum',
    'inclinatum']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume',
    'coord': [807, 204, 838, 238], 'form': ['punctum', 'inclinatum',
    'dot']}, {'strt_pos': 5, 'strt_pitch': None, 'type': 'division',
    'coord': [885, 165, 894, 235], 'form': ['minor']}, {'strt_pos': 8,
    'strt_pitch': 'f', 'type': 'neume', 'coord': [947, 188, 965, 229],
    'form': ['podatus', '2']}, {'strt_pos': 9, 'strt_pitch': 'e', 'type':
    'neume', 'coord': [1005, 225, 1021, 245], 'form': ['punctum']},
    {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume', 'coord': [1029,
    175, 1047, 197], 'form': ['punctum']}, {'strt_pos': 6, 'strt_pitch':
    'a', 'type': 'neume', 'coord': [1055, 175, 1076, 196], 'form':
    ['punctum']}, {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume',
    'coord': [1080, 175, 1098, 197], 'form': ['punctum']}, {'strt_pos': 6,
    'strt_pitch': 'a', 'type': 'neume', 'coord': [1106, 158, 1123, 197],
    'form': ['podatus', '2']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [1132, 175, 1146, 199], 'form': ['punctum',
    'inclinatum']}, {'strt_pos': 10, 'strt_pitch': 'd', 'type': 'neume',
    'coord': [1164, 220, 1180, 271], 'form': ['punctum', 'inclinatum',
    've']}, {'strt_pos': 9, 'strt_pitch': 'e', 'type': 'neume', 'coord':
    [1196, 210, 1213, 231], 'form': ['punctum']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [1222, 178, 1240, 198],
    'form': ['punctum']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [1247, 178, 1265, 199], 'form': ['punctum']},
    {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [1270,
    168, 1304, 232], 'form': ['clivis', 'he', '3']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [1313, 163, 1381, 204],
    'form': ['torculus', 'resupinus', '2', '2', '2']}, {'strt_pos': 8,
    'strt_pitch': None, 'type': 'custos', 'coord': [1416, 181, 1431, 239],
    'form': []}], 'coord': [16, 136, 1429, 256]}, 1: {'content':
    [{'strt_pos': 6, 'strt_pitch': 'a', 'type': 'clef', 'coord': [12, 359,
    47, 414], 'form': ['f']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [95, 366, 146, 431], 'form': ['he', 'torculus', '2',
    '2']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord':
    [178, 400, 209, 431], 'form': ['punctum', 'dot']}, {'strt_pos': 7,
    'strt_pitch': None, 'type': 'division', 'coord': [260, 353, 281, 460],
    'form': ['final']}], 'coord': [11, 352, 1425, 471]}, 2: {'content':
    [{'strt_pos': 6, 'strt_pitch': 'a', 'type': 'clef', 'coord': [173,
    1069, 207, 1124], 'form': ['f']}, {'strt_pos': 7, 'strt_pitch': 'g',
    'type': 'neume', 'coord': [240, 1102, 258, 1123], 'form':
    ['punctum']}, {'strt_pos': 6, 'strt_pitch': 'a', 'type': 'neume',
    'coord': [266, 1083, 284, 1131], 'form': ['podatus', '2']},
    {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord': [315,
    1084, 349, 1141], 'form': ['scandicus', '2', 'q', '2']}, {'strt_pos':
    7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [396, 1085, 418,
    1155], 'form': ['cephalicus', '4']}, {'strt_pos': 7, 'strt_pitch':
    'g', 'type': 'neume', 'coord': [556, 1105, 574, 1125], 'form':
    ['punctum']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume',
    'coord': [581, 1084, 601, 1126], 'form': ['podatus', '2']},
    {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [631,
    1087, 649, 1145], 'form': ['cephalicus', '3']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [723, 1064, 790, 1125],
    'form': ['torculus', 'resupinus', '3', '2', '2']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [822, 1106, 840, 1126],
    'form': ['punctum']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [847, 1079, 879, 1128], 'form': ['podatus', '2',
    'dot']}, {'strt_pos': 3, 'strt_pitch': None, 'type': 'division',
    'coord': [909, 1051, 918, 1082], 'form': ['small']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [956, 1109, 973, 1128],
    'form': ['punctum']}, {'strt_pos': 9, 'strt_pitch': 'e', 'type':
    'neume', 'coord': [1013, 1140, 1031, 1161], 'form': ['punctum']},
    {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [1072,
    1090, 1092, 1137], 'form': ['podatus', '2']}, {'strt_pos': 8,
    'strt_pitch': 'f', 'type': 'neume', 'coord': [1098, 1111, 1114, 1152],
    'form': ['punctum', 'inclinatum', 've']}, {'strt_pos': 8,
    'strt_pitch': 'f', 'type': 'neume', 'coord': [1116, 1126, 1128, 1144],
    'form': ['punctum', 'inclinatum']}, {'strt_pos': 8, 'strt_pitch': 'f',
    'type': 'neume', 'coord': [1163, 1114, 1194, 1145], 'form':
    ['punctum', 'dot']}, {'strt_pos': 4, 'strt_pitch': None, 'type':
    'division', 'coord': [1226, 1069, 1235, 1171], 'form': ['major']},
    {'strt_pos': 9, 'strt_pitch': 'e', 'type': 'neume', 'coord': [1272,
    1143, 1289, 1164], 'form': ['punctum']}, {'strt_pos': 8, 'strt_pitch':
    'f', 'type': 'neume', 'coord': [1354, 1111, 1372, 1151], 'form':
    ['epiphonus', '2']}, {'strt_pos': 7, 'strt_pitch': None, 'type':
    'custos', 'coord': [1408, 1089, 1423, 1141], 'form': []}], 'coord':
    [172, 1062, 1422, 1170]}, 3: {'content': [{'strt_pos': 6,
    'strt_pitch': 'a', 'type': 'clef', 'coord': [5, 1289, 42, 1344],
    'form': ['f']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume',
    'coord': [73, 1323, 90, 1344], 'form': ['punctum']}, {'strt_pos': 8,
    'strt_pitch': 'f', 'type': 'neume', 'coord': [138, 1339, 157, 1360],
    'form': ['punctum']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type':
    'neume', 'coord': [164, 1287, 216, 1361], 'form': ['torculus', '3',
    '4']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord':
    [219, 1340, 256, 1392], 'form': ['clivis', '2']}, {'strt_pos': 6,
    'strt_pitch': 'a', 'type': 'neume', 'coord': [305, 1288, 324, 1343],
    'form': ['podatus', '3']}, {'strt_pos': 6, 'strt_pitch': 'a', 'type':
    'neume', 'coord': [363, 1303, 382, 1326], 'form': ['punctum']},
    {'strt_pos': 5, 'strt_pitch': 'b', 'type': 'neume', 'coord': [472,
    1269, 492, 1310], 'form': ['podatus', '2']}, {'strt_pos': 5,
    'strt_pitch': 'b', 'type': 'neume', 'coord': [498, 1281, 514, 1334],
    'form': ['punctum', 'inclinatum', 've']}, {'strt_pos': 7,
    'strt_pitch': 'g', 'type': 'neume', 'coord': [523, 1319, 539, 1344],
    'form': ['punctum', 'inclinatum']}, {'strt_pos': 7, 'strt_pitch': 'g',
    'type': 'neume', 'coord': [572, 1322, 604, 1343], 'form': ['punctum',
    'dot']}, {'strt_pos': 5, 'strt_pitch': None, 'type': 'division',
    'coord': [644, 1297, 651, 1366], 'form': ['minor']}, {'strt_pos': 9,
    'strt_pitch': 'e', 'type': 'neume', 'coord': [697, 1356, 714, 1377],
    'form': ['punctum']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type':
    'neume', 'coord': [788, 1322, 807, 1363], 'form': ['epiphonus', '2']},
    {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [880,
    1323, 899, 1343], 'form': ['punctum']}, {'strt_pos': 8, 'strt_pitch':
    'f', 'type': 'neume', 'coord': [954, 1339, 973, 1360], 'form':
    ['punctum']}, {'strt_pos': 9, 'strt_pitch': 'e', 'type': 'neume',
    'coord': [1096, 1356, 1112, 1377], 'form': ['punctum']}, {'strt_pos':
    9, 'strt_pitch': 'e', 'type': 'neume', 'coord': [1187, 1322, 1222,
    1378], 'form': ['scandicus', '2', '2']}, {'strt_pos': 7, 'strt_pitch':
    'g', 'type': 'neume', 'coord': [1253, 1323, 1272, 1345], 'form':
    ['punctum']}, {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume',
    'coord': [1277, 1323, 1327, 1372], 'form': ['clivis', '2', 'dot']},
    {'strt_pos': 5, 'strt_pitch': None, 'type': 'division', 'coord':
    [1358, 1299, 1366, 1369], 'form': ['minor']}, {'strt_pos': 8,
    'strt_pitch': None, 'type': 'custos', 'coord': [1407, 1309, 1423,
    1368], 'form': []}], 'coord': [6, 1280, 1419, 1384]}, 4: {'content':
    [{'strt_pos': 6, 'strt_pitch': 'a', 'type': 'clef', 'coord': [4, 1508,
    40, 1560], 'form': ['f']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type':
    'neume', 'coord': [71, 1555, 89, 1577], 'form': ['punctum']},
    {'strt_pos': 8, 'strt_pitch': 'f', 'type': 'neume', 'coord': [128,
    1555, 147, 1577], 'form': ['punctum']}, {'strt_pos': 10, 'strt_pitch':
    'd', 'type': 'neume', 'coord': [178, 1570, 230, 1614], 'form':
    ['porrectus', '2', '2']}, {'strt_pos': 11, 'strt_pitch': 'c', 'type':
    'neume', 'coord': [263, 1608, 293, 1628], 'form': ['punctum', 'dot']},
    {'strt_pos': 3, 'strt_pitch': None, 'type': 'division', 'coord': [334,
    1483, 341, 1516], 'form': ['small']}, {'strt_pos': 9, 'strt_pitch':
    'e', 'type': 'neume', 'coord': [387, 1554, 406, 1602], 'form':
    ['epiphonus', '2']}, {'strt_pos': 8, 'strt_pitch': 'f', 'type':
    'neume', 'coord': [446, 1552, 463, 1575], 'form': ['punctum']},
    {'strt_pos': 7, 'strt_pitch': 'g', 'type': 'neume', 'coord': [503,
    1511, 556, 1576], 'form': ['he', 'torculus', '2', '2']}, {'strt_pos':
    8, 'strt_pitch': 'f', 'type': 'neume', 'coord': [586, 1543, 618,
    1575], 'form': ['punctum', 'dot']}, {'strt_pos': 7, 'strt_pitch':
    None, 'type': 'division', 'coord': [653, 1497, 672, 1601], 'form':
    ['final']}], 'coord': [6, 1497, 1419, 1601]}}
    
    v = AomrMeiOutput(test_data, 'foo.jpg')
    
    from pymei.Export import meitoxml
    meitoxml.meitoxml(v.md, 'testfile.mei')
    
    
    # pdb.set_trace()
    
    
    




# [1] http://wwvv.newadvent.org/cathen/10765b.htm; Some of the liquescent 
#   neums have special names. Thus the liquescent podatus is called epiphonus, 
#   the liquescent clivis, cephalicus, the liquescent climacus, ancus.

