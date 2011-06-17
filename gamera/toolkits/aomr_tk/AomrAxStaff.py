import os

class AomrAxStaff(object):
    def __init__(self, **kwargs):
        rstring = "You must pass {0} into this class"
        if 'staff' in kwargs.values():
            self.staff = kwargs['staff'] 
        else:
            raise AomrAxStaffError(rstring.format('staff'))
        
        if 'staff_height' in kwargs.values():
            self.staff_height = kwargs['staff_height'] 
        else:
            raise AomrAxStaffError(rstring.format('staff_height'))
        if 'ymax' in kwargs.values():
            self.ymax = kwargs['ymax']    
        else:
            raise AomrAxStaffError(rstring.format('ymax'))
            
        if 'staffspace_height' in kwargs.values():
            self.staffspace_height = kwargs['staffspace_height']
        else:
            raise AomrAxStaffError(rstring.format('staffspace_height'))
        
        if 'staffline_height' in kwargs.values():
            self.staffline_height = kwargs['staffline_height'] 
        else:
            raise AomrAxStaffError(rstring.format('staffline_height'))
        
        self.glyphs = []
        self.gt_glyphs = []
        
        self.staffno = self.staff.staffno
        self.yposlist = self.staff.yposlist
        if self.yposlist:
            self.center_y = sum(self.yposlist) / len(self.yposlist)
        else:
            self.center_y = 0
        
        self.bbox_ymin = max(0, self.center_y - self.staff_height / 2)
    