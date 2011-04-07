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
        self.meihead.add_child(self.filedesc)
        
        self.encodingdesc = mod.encodingdesc_()
        self.meihead.add_child(self.encodingdesc)
        self.mei.add_child(self.meihead)
        
        # music
        self.music = mod.music_()
        self.facsimile = self._create_facsimile_element()
        self.surface = self._create_surface_element()
        self.graphic = self._create_graphic_element(original_image)
        
        self.surface.add_child(self.graphic)
        self.facsimile.add_child(self.surface)
        self.music.add_child(self.facsimile)
        
        self.body = mod.body_()
        self.music.add_child(self.body)
        
        self.mdiv = mod.mdiv_()        
        self.body.add_child(self.mdiv)
        
        self.score = mod.score_()
        self.mdiv.add_child(self.score)
        
        self.scoredef = mod.scoredef_()
        self.score.add_child(self.scoredef)
        
        self.section = mod.section_()
        self.score.add_child(self.section)
        
        for snum,stf in self._recognition_results.iteritems():
            self.staffdef = self._create_staffdef_element()
            self.staffdef.attributes = { 'n': snum }
            self.scoredef.add_child(self.staffdef)
            
            self.staff = stf
            self.staffel = self._parse_staff(snum, stf)
            z = mod.zone_()
            z.id = self._idgen()
            z.attributes = {'ulx': self.staff['coord'][0], 'uly': self.staff['coord'][1], \
                                'lrx': self.staff['coord'][2], 'lry': self.staff['coord'][3]}
            
            self.surface.add_child(z)
            self.staffel.facs = z.id
            
            self.section.add_child(self.staffel)
        
        self.mei.add_child(self.music)
        
        self.md = MeiDocument.MeiDocument()
        self.md.addelement(self.mei)
        
        
    def _parse_staff(self, stfnum, stf):
        staffel = self._create_staff_element()
        staffel.attributes = {'n': stfnum}
        
        for c in self.staff['content']:
            # parse the glyphs per staff.
            self.glyph = c
            lg.debug(self.glyph)
            
            if c['type'] == 'neume':
                staffel.add_child(self._create_neume_element())
            elif c['type'] == 'clef':
                staffel.add_child(self._create_clef_element())
            elif c['type'] == 'division':
                staffel.add_child(self._create_division_element())
            elif c['type'] == 'custos':
                staffel.add_child(self._create_custos_element())
            elif c['type'] == "alteration":
                # staffel.add_child(self._create_alteration_element()) #GVM
                pass
        return staffel
        
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
    
    def _create_staffdef_element(self):
        stfdef = mod.staffdef_()
        return stfdef
    
    def _create_staff_element(self):
        staff = mod.staff_()
        staff.id = self._idgen()
        return staff
        
    def _create_episema_element(self):
        epi = mod.episema_()
        epi.id = self._idgen()
        return epi
    
    def _create_neume_element(self):
        lg.debug("glyph: {0}".format(self.glyph['form']))
        full_width_episema = False
        
        if 'climacus' in self.glyph['form']:
            neume = mod.ineume_()
        else:
            neume = mod.uneume_()
            
        neume.id = self._idgen()
        zone = self._create_zone_element()
        neume.facs = zone.id
        
        if self.glyph['form'][0] == "he":
            full_width_episema = True
            del self.glyph['form'][0]
            
        neume.attributes = {'name': self.glyph['form'][0]}
        
        # get the form so we can find the number of notes we need to construct.
        try:
             # since we define the form of the intervals, we're always off-by-one in the number of notes.
            num_notes = len(self.NEUME_NOTES[self.glyph['form'][0]]) + 1
        except KeyError:
            raise AomrMeiFormNotFoundError("The form {0} was not found.".format(self.glyph['form'][0]))
        
        
        # do we need to add any further notes? form is pretty loaded, so we 
        # have to check manually, from idx 1 on (since the primary form is always first)
        
        # we don't have an off-by-one problem here, since an added interval means an added note
        check_additional = [i for i in self.ADD_NOTES.keys() if i in self.glyph['form'][1:]]
        num_notes = num_notes + len(check_additional)
        
        self._neume_pitches = []
        # note elements are everything after the first form. This determines the shape a note takes.
        self._note_elements = self.glyph['form'][1:]
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
                dir = self.NEUME_NOTES[self.glyph['form'][0]][n]
                # lg.debug("direction is {0}".format(dir))
                iv = ivals[n]
                n_idx = idx
                
                # lg.debug("index: {0}".format(idx))
                
                
                if dir == 'u':
                    if (idx + (iv - 1)) >= len(self.SCALE):
                        n_idx = 0 + (iv - 1)
                    else:
                        n_idx = idx + (iv - 1)
                elif dir == 'd':
                    if idx - (iv - 1) < 0:
                        n_idx = len(self.SCALE) + (idx - (iv - 1))
                    else:
                        n_idx = idx - (iv - 1)
                idx = n_idx
                
                # lg.debug("Picking pitch {0}".format(self.SCALE[n_idx]))
                self._neume_pitches.append(self.SCALE[n_idx])
        
        if full_width_episema is True:
            epi = self._create_episema_element()
            epi.id = self._idgen()
            epi.attributes = {"form": "horizontal"}
            self.staffel.add_child(epi)
            
        for n in xrange(num_notes):
            p = self._neume_pitches[n]
            nt = self._create_note_element(p)
            if n == 0 and full_width_episema is True:
                epi.attributes = {"startid": nt.id}
            elif n == len(num_notes) - 1 and full_width_episema is True:
                epi.attributes = {"endid": nt.id}
                
            nc.append(nt)
        neume.add_children(nc)
        
        return neume
        
    def _create_note_element(self, pname=None):
        note = mod.note_()
        note.id = self._idgen()
        note.pitchname = pname
        return note
    
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
        return division
    
    # def _create_alteration_element(self):
    #     alteration = mod.alteration_()
    #     alteration.id = self._idgen()
    #     zone = self._create_zone_element()
    #     alteration.facs = zone.id
    #     return alteration    
    
    def _idgen(self):
        """ Returns a UUID. """
        return str(uuid.uuid4())




if __name__ == "__main__":
    test_data = {
        1: {
            'coord': [1,2,3,4],
            'content': [{
                'type': 'neume',
                'form': ['clivis', '4'],
                'coord': [213, 179, 26, 35],
                'strt_pitch': 'E',
                'strt_pos': 5
            }, {
                'type': 'neume',
                'form': ['torculus', '2', '4'],
                'coord': [213, 179, 26, 35],
                'strt_pitch': 'B',
                'strt_pos': 5
            }]
        }, 2: {
            'coord': [4,5,6,7],
            'content': [{
                'type': '',
                'form': [],
                'coord': [],
                'strt_pitch': 'A',
                'strt_pos': ''
            }]
        }
    }
    
    v = AomrMeiOutput(test_data)
    
    from pymei.Export import meitoxml
    meitoxml.meitoxml(v.md, 'testfile.mei')
    
    
    # pdb.set_trace()
    
    
    




# [1] http://wwvv.newadvent.org/cathen/10765b.htm; Some of the liquescent 
#   neums have special names. Thus the liquescent podatus is called epiphonus, 
#   the liquescent clivis, cephalicus, the liquescent climacus, ancus.

