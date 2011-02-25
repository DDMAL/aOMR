import os

class AomrAxStaff(object):
    def __init__(self, **kwargs):
        rstring = "You must pass {0} into this class"
        self.staff = kwargs['staff'] if 'staff' in kwargs.values() else raise AomrAxStaffError(rstring.format('staff'))
        self.staff_height = kwargs['staff_height'] if 'staff_height' in kwargs.values() else raise AomrAxStaffError(rstring.format('staff_height'))
        self.ymax = kwargs['ymax'] if 'ymax' in kwargs.values() else raise AomrAxStaffError(rstring.format('ymax'))
        self.staffspace_height = kwargs['staffspace_height'] if 'staffspace_height' in kwargs.values() else raise AomrAxStaffError(rstring.format('staffspace_height'))
        self.staffline_height = kwargs['staffline_height'] if 'staffline_height' in kwargs.values() else raise AomrAxStaffError(rstring.format('staffline_height'))
        
        self.glyphs = []
        self.gt_glyphs = []
        
        self.staffno = self.staff.staffno
        self.yposlist = self.staff.yposlist
        if self.yposlist:
            self.center_y = sum(self.yposlist) / len(self.yposlist)
        else:
            self.center_y = 0
        
        self.bbox_ymin = max(0, self.center_y - self.staff_height / 2)
    