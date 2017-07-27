from gamera.plugin import *
from gamera.toolkits.aomr_tk.AomrExceptions import *


from pymei import MeiDocument, MeiElement, MeiAttribute, documentToFile

import logging
lg = logging.getLogger('aomr')
f = logging.Formatter("%(levelname)s %(asctime)s On Line: %(lineno)d %(message)s")
h = logging.StreamHandler()
h.setFormatter(f)

# lg.setLevel(logging.DEBUG)
lg.addHandler(h)

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
        'porrectus': ['d', 'u'],
        'salicus': ['u', 'u'],
        'scandicus': ['u', 'u'],
        'torculus': ['u', 'd'],
        'ancus': ['d', 'd'],
        'climacus': ['d', 'd']  # See note 1 below
    }

    # given an alternate form, how many notes does it add to the neume?
    ADD_NOTES = {
        'flexus': ['d'],  # scandicus.flexus, porrectus.flexus
        'resupinus': ['u'],  # torculus.resupinus
    }

    SCALE = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

    def __init__(self, incoming_data):
    # def __init__(self, incoming_data, original_image, page_number=None):
        self._recognition_results = incoming_data

        # self.mei = mod.mei_()
        self.md = MeiDocument()
        self.mei = MeiElement("mei")

        self.staff = None
        self.staff_num = 1
        self.glyph = None

        self._note_elements = None
        self._neume_pitches = []

        # set up a basic MEI document structure

        # header
        self.md.setRootElement(self.mei)

        self.meihead = MeiElement('meiHead')
        self.mei.addChild(self.meihead)

        self.filedesc = MeiElement('fileDesc')
        self.meihead.addChild(self.filedesc)

        self.titlestmt = MeiElement('titleStmt')
        self.filedesc.addChild(self.titlestmt)

        self.title = MeiElement('title')
        self.titlestmt.addChild(self.title)

        self.pubstmt = MeiElement('pubStmt')
        self.filedesc.addChild(self.pubstmt)

#         # music
        self.music = MeiElement("music")
        self.mei.addChild(self.music)
#         self.music = mod.music_()
#         self.facsimile = self._create_facsimile_element()
        self.facsimile = MeiElement("facsimile")
        self.music.addChild(self.facsimile)
#         self.surface = self._create_surface_element()
        self.surface = MeiElement("surface")
        self.facsimile.addChild(self.surface)
#         self.graphic = self._create_graphic_element(original_image)
        self.graphic = MeiElement("graphic")
        self.surface.addChild(self.graphic)  # GVM: check how to add RODAN resource filepath/
#         self.surface.add_child(self.graphic)
#         self.facsimile.add_child(self.surface)
#         self.music.add_child(self.facsimile)

#         self.layout = self._create_layout_element()
#         self.pg = self._create_page_element()
#         if page_number:
#             self.pg.attributes = {"n": page_number}
#         self.layout.add_child(self.pg)
#         self.music.add_child(self.layout)

        self.body = MeiElement("body")
        self.music.addChild(self.body)

        self.mdiv = MeiElement("mdiv")
        self.mdiv.addAttribute("type", "solesmes")
        self.body.addChild(self.mdiv)

        self.score = MeiElement("score")
        self.mdiv.addChild(self.score)

        self.scoredef = MeiElement("scoreDef")
        self.score.addChild(self.scoredef)

        self.staffgrp = MeiElement("staffGrp")
        self.scoredef.addChild(self.staffgrp)

#         self.staffdef = self._create_staffdef_element()
#         self.staffdef.attributes = {'n': self.staff_num}
        self.staffdef = MeiElement("staffDef")
        self.staffdef.addAttribute("n", "0")  # GVM: what the n number means, and how to generate it?
        self.staffgrp.addChild(self.staffdef)

        self.section = MeiElement("section")
        self.score.addChild(self.section)

        self.staffel = MeiElement("staff")  # GVM: staffel corresponds to staff
        self.staffel.addAttribute("n", "0")  # GVM: how to generate n
        self.section.addChild(self.staffel)

        self.layer = MeiElement("layer")
        self.layer.addAttribute("n", "1")
        self.staffel.addChild(self.layer)

        for sysnum, syst in self._recognition_results.iteritems():
            self.system = syst
            self.systembreak = self._parse_system(sysnum, syst)
            z = MeiElement("zone")
            z.addAttribute("ulx", str(self.system["coord"][0]))
            z.addAttribute("uly", str(self.system["coord"][1]))
            z.addAttribute("lrx", str(self.system["coord"][2]))
            z.addAttribute("lry", str(self.system["coord"][3]))

            self.surface.addChild(z)
            self.systembreak.addAttribute("facs", z.getId())

#         if not self.staffel.descendants_by_name('neume'):
#             self.staffgrp.remove_child(self.staffdef)
#             self.section.remove_child(self.staffel)

        documentToFile(self.md, '/Users/gabriel/Downloads/foo.mei')
        print 'Saved file'

    def _parse_system(self, sysnum, syst):
        sysbrk = MeiElement("sb")
        sysbrk.addAttribute("n", str(sysnum + 1))
        self.layer.addChild(sysbrk)

        for c in self.system['content']:
            # parse the glyphs per staff.
            self.glyph = c
            lg.debug("GLYPH: {0}".format(c))

            if c['type'] == 'neume':
                if not self.glyph['form']:
                    lg.debug("Skipping glyph: {0}".format(self.glyph))
                    continue
                if self.glyph['form'][0] not in self.NEUME_NOTES.keys():
                    continue
                else:
                    try:
                        self.layer.addChild(self._create_neume_element())
                    except Exception:
                        lg.debug("Cannot add neume element {0}. Skipping.".format(self.glyph))

            # if c['type'] == 'neume':
            #     self.layer.addChild(self._create_neume_element())

            elif c['type'] == 'clef':
                try:
                    self.layer.addChild(self._create_clef_element())
                except Exception:
                    lg.debug("Cannot add clef element {0}. Skipping.".format(self.glyph))

            elif c['type'] == 'division':
                try:
                    self.layer.addChild(self._create_division_element())
                except Exception:
                    lg.debug("Cannot add division element {0}. Skipping.".format(self.glyph))
            #     if "final" in c['form']:
            #         self.staff_num += 1
            #         new_staff = self._create_staff_element()
            #         new_staffdef = self._create_staffdef_element()
            #         new_staffdef.attributes = {'n': self.staff_num}
            #         new_staff.attributes = {'n': self.staff_num}
            #         new_layer = self._create_layer_element()
            #         new_layer.attributes = {'n': 1}

            #         self.layer = new_layer
            #         self.staffel = new_staff
            #         self.staffdef = new_staffdef
            #         self.staffgrp.addChild(self.staffdef)
            #         self.staffel.addChild(self.layer)
            #         self.section.addChild(self.staffel)

            elif c['type'] == 'custos':
                try:
                    self.layer.addChild(self._create_custos_element())
                except Exception:
                    lg.debug("Cannot add custos element {0}. Skipping".format(self.glyph))

            elif c['type'] == "alteration":
                # staffel.add_child(self._create_alteration_element()) #GVM
                pass

        return sysbrk


#     def _create_graphic_element(self, imgfile):
#         graphic = mod.graphic_()
#         graphic.id = self._idgen()
#         graphic.attributes = {'xlink:href': imgfile}
#         return graphic

#     def _create_alteration_element(self):
#         accid = mod.accid_()
#         accid.id = self._idgen()
#         if self.glyph['form'] is "sharp":
#             accid.attributes = {"accid": "s"}
#         elif self.glyph['form'] is "flat":
#             accid.attributes = {"accid": "f"}

#         zone = self._create_zone_element()
#         note.facs = zone.id

#         return accid

#     def _create_surface_element(self):
#         surface = mod.surface_()
#         surface.id = self._idgen()
#         return surface

#     def _create_facsimile_element(self):
#         facsimile = mod.facsimile_()
#         facsimile.id = self._idgen()
#         return facsimile

    def _create_zone_element(self):
        zone = MeiElement("zone")

        zone.addAttribute("ulx", str(self.glyph["coord"][0]))
        zone.addAttribute("uly", str(self.glyph["coord"][1]))
        zone.addAttribute("lrx", str(self.glyph["coord"][2]))
        zone.addAttribute("lry", str(self.glyph["coord"][3]))

        self.surface.addChild(zone)

        return zone

#     def _create_layer_element(self):
#         layer = mod.layer_()
#         layer.id = self._idgen()
#         return layer

#     def _create_staffgrp_element(self):
#         stfgrp = mod.staffgrp_()
#         stfgrp.id = self._idgen()
#         return stfgrp

#     def _create_staffdef_element(self):
#         stfdef = mod.staffdef_()
#         stfdef.id = self._idgen()
#         return stfdef

#     def _create_staff_element(self):
#         staff = mod.staff_()
#         staff.id = self._idgen()
#         return staff

#     def _create_sb_element(self):
#         sb = mod.sb_()
#         sb.id = self._idgen()
#         return sb

#     def _create_pb_element(self):
#         pb = mod.pb_()
#         pb.id = self._idgen()
#         return pb

#     def _create_layout_element(self):
#         layout = mod.layout_()
#         layout.id = self._idgen()
#         return layout

#     def _create_page_element(self):
#         page = mod.page_()
#         page.id = self._idgen()
#         return page

#     def _create_system_element(self):
#         system = mod.system_()
#         system.id = self._idgen()
#         return system

    def _create_episema_element(self):
        epi = MeiElement("episema")
        return epi

    def _create_neume_element(self):
        full_width_episema = False
        has_dot = False
        has_vertical_episema = False
        has_horizontal_episema = False
        has_quilisma = False
        this_neume_form = None
        local_horizontal_episema = None

        start_octave = self.glyph['octv']
        clef_pos = self.glyph['clef_pos']
        clef_type = self.glyph['clef'].split(".")[-1]  # f or c.

        neume = MeiElement("neume")
        zone = self._create_zone_element()
        neume.addAttribute("facs", zone.getId())
        neumecomponent = MeiElement("nc")

        neume.addChild(neumecomponent)

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
            has_quilisma = True

        if 've' in self.glyph['form']:
            has_vertical_episema = True

        if 'inclinatum' in self.glyph['form']:
            neumecomponent.addAttribute('inclinatum', 'true')

        neume.addAttribute("name", self.glyph['form'][0])

        if 'compound' in self.glyph['form']:
            # do something and create a new set of pitch contours
            this_neume_form = [y for y in (self.__parse_contour(n) for n in self.glyph['form']) if y]
            self._note_elements = [y for y in (self.__parse_steps(n) for n in self.glyph['form']) if y]
        else:
            this_neume_form = copy.deepcopy(self.NEUME_NOTES[self.glyph['form'][0]])
            self._note_elements = self.glyph['form'][1:]
        # get the form so we can find the number of notes we need to construct.

        num_notes = len(this_neume_form) + 1
        # we don't have an off-by-one problem here, since an added interval means an added note
        check_additional = [i for i in self.ADD_NOTES.keys() if i in self.glyph['form'][1:]]
        if check_additional:
            for f in check_additional:
                this_neume_form.extend(self.ADD_NOTES[f])

                ## THIS SHOULD BE CHANGED. Otherwise we may end up with two attributes with the same name.
                neume.addAttribute("variant", f)
            num_notes = num_notes + len(check_additional)


        self._neume_pitches = []
        # note elements are everything after the first form. This determines the shape a note takes.
        self._neume_pitches.append(self.glyph['strt_pitch'])
        nc = []
        note_octaves = [start_octave]
        if num_notes > 1:
            # we need to figure out the rest of the pitches in the neume.
            ivals = [int(d) for d in self._note_elements if d.isdigit()]
            try:
                idx = self.SCALE.index(self.glyph['strt_pitch'])
            except ValueError:
                raise AomrMeiPitchNotFoundError("The pitch {0} was not found in the scale".format(self.glyph['strt_pitch']))

            if len(ivals) != (num_notes - 1):
                if 'scandicus' in self.glyph['form']:
                    diffr = abs(len(ivals) - (num_notes - 1))
                    num_notes = num_notes + diffr
                    this_neume_form.extend(diffr * 'u')
                else:
                    raise AomrMeiNoteIntervalMismatchError("There is a mismatch between the number of notes and number of intervals.")

            # note elements = torculus.2.2.he.ve
            # ivals = [2,2]
            # torculus = ['u','d']
            this_pos = copy.deepcopy(self.glyph['strt_pos'])
            for n in xrange(len(ivals)):
                # get the direction
                dir = this_neume_form[n]
                iv = ivals[n]
                n_idx = idx
                if dir == "u":
                    n_idx = ((idx + iv) % len(self.SCALE)) - 1
                    this_pos -= (iv - 1)
                elif dir == "d":
                    n_idx = idx - (iv - 1)
                    this_pos += (iv - 1)
                    if n_idx < 0:
                        n_idx += len(self.SCALE)
                idx = n_idx
                self._neume_pitches.append(self.SCALE[n_idx])

                actual_line = 10 - (2 * (clef_pos - 1))

                if clef_type == "c":
                    if this_pos <= actual_line:
                        note_octaves.append(4)
                    elif this_pos > actual_line + 7:
                        note_octaves.append(2)
                    else:
                        note_octaves.append(3)
                elif clef_type == "f":
                    if (actual_line + 3) >= this_pos > (actual_line - 3):
                        note_octaves.append(3)
                    elif this_pos < (actual_line - 3):
                        note_octaves.append(4)
                    elif this_pos > (actual_line + 3):
                        note_octaves.append(2)

        if full_width_episema is True:
            epi = self._create_episema_element()
            epi.attributes = {"form": "horizontal"}
            self.layer.add_child(epi)

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

        for n in xrange(num_notes):
            p = self._neume_pitches[n]
            o = note_octaves[n]
            nt = self._create_note_element(p)
            nt.addAttribute("oct", str(o))
            nt.addAttribute("pname", nt.pitchname)

            if n == 0 and full_width_episema is True:
                epi.addAttribute("startid", nt.getId())
            elif n == num_notes and full_width_episema is True:
                epi.addAttribute("endid", nt.getId())

            if has_quilisma:
                if n in qidxs:
                    neumecomponent.addAttribute("quilisma", "true")

            # if has_dot:
            #     if n in dotidxs:
            #         d = self._create_dot_element()
            #         nt.add_child(d)

            if has_vertical_episema:
                if n in veidxs:
                    ep = self._create_episema_element()
                    ep.addAttribute("form", "vertical")
                    ep.addAttribute("startid", nt.getId())
                    self.layer.addChild(ep)

            if has_horizontal_episema:
                if n in heidxs:
                    local_horizontal_episema = self._create_episema_element()
                    local_horizontal_episema.addAttribute("form", "horizontal")
                    local_horizontal_episema.addAttribute("startid", nt.getId())
                    self.layer.addChild(local_horizontal_episema)

            if n == num_notes - 1 and local_horizontal_episema:
                # we've reached the end, and we have an HE we need to close up.
                local_horizontal_episema.attributes = {"endid": nt.id}
                local_horizontal_episema.addAttribute("endid", nt.getId())

            nc.append(nt)

        for n in nc:
            neumecomponent.addChild(n)

        return neume

    def _create_note_element(self, pname=None):
        note = MeiElement("note")
        note.pitchname = pname
        return note

    def _create_dot_element(self):
        dot = MeiElement("dot")
        dot.addAttribute("form", "aug")
        return dot

    def _create_custos_element(self):
        custos = MeiElement("custos")
        zone = self._create_zone_element()

        custos.addAttribute("facs", zone.getId())

        custos.pitchname = self.glyph['strt_pitch']
        custos.addAttribute("pname", custos.pitchname)

        custos.octave = self.glyph['octv']
        custos.addAttribute("oct", str(custos.octave))

        return custos

    def _create_clef_element(self):
        clef = MeiElement("clef")
        zone = self._create_zone_element()

        clef.addAttribute("facs", zone.getId())
        clef.addAttribute("line", str(self.glyph["strt_pos"]))
        clef.addAttribute("shape", str(self.glyph["form"][0].upper()))

        return clef

    def _create_division_element(self):
        division = MeiElement("division")
        zone = self._create_zone_element()

        division.addAttribute("facs", zone.getId())

        if self.glyph['form']:
            division.addAttribute("form", self.glyph['form'][0])

        return division

    # def _create_alteration_element(self):
    #     alteration = mod.alteration_()
    #     alteration.id = self._idgen()
    #     zone = self._create_zone_element()
    #     alteration.facs = zone.id
    #     return alteration

    def __parse_contour(self, form):
        # removes the contour indicator from the neume
        # and creates a neume form.
        if len(form) is 2 and (form.startswith("u") or form.startswith("d")):
            return form[0]
        else:
            return None

    def __parse_steps(self, form):
        if len(form) is 2 and (form.startswith("u") or form.startswith("d")):
            return form[1]
        else:
            return None

    def __note_addition_figurer_outer(self, ntype, idxarray):
        lg.debug('Note addition')
        for i, n in enumerate(self.glyph['form']):
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
        lg.debug('Valid note')
        if form.isdigit():
            return True
        elif len(form) == 2 and form.startswith("u") or form.startswith("d"):
            return True
        else:
            return False




# if __name__ == "__main__":
#     v = AomrMeiOutput(test_data, 'foo..jpg')
#     from pymei.Export import meitoxml
#     meitoxml.meitoxml(v.md, 'testfile.mei')




# # [1] http://wwvv.newadvent.org/cathen/10765b.htm; Some of the liquescent 
# #   neums have special names. Thus the liquescent podatus is called epiphonus, 
# #   the liquescent clivis, cephalicus, the liquescent climacus, ancus.

