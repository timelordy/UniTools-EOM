# -*- coding: utf-8 -*-

from pyrevit import DB

class SocketItem(object):
    def __init__(self, elem, doc):
        self.Id = elem.Id
        self.Name = "ID: {}".format(elem.Id.IntegerValue)
        
        # Level
        lvl_name = "?"
        try:
            lid = elem.LevelId
            l = doc.GetElement(lid)
            if l: lvl_name = l.Name
        except: pass
        
        # Location
        loc_str = ""
        try:
            loc = elem.Location
            if loc and hasattr(loc, "Point"):
                pt = loc.Point
                loc_str = "({:.1f}, {:.1f}, {:.1f})".format(pt.X, pt.Y, pt.Z)
        except: pass
        
        self.Desc = "Lvl: {} | {}".format(lvl_name, loc_str)

def calculate_bbox(elem, margin=3.0, default_size=2.0):
    bb = elem.get_BoundingBox(None)
    if not bb:
        pt = elem.Location.Point
        min_pt = DB.XYZ(pt.X - default_size, pt.Y - default_size, pt.Z - default_size)
        max_pt = DB.XYZ(pt.X + default_size, pt.Y + default_size, pt.Z + default_size)
        bb = DB.BoundingBoxXYZ()
        bb.Min = min_pt
        bb.Max = max_pt
    else:
        bb.Min = DB.XYZ(bb.Min.X - margin, bb.Min.Y - margin, bb.Min.Z - margin)
        bb.Max = DB.XYZ(bb.Max.X + margin, bb.Max.Y + margin, bb.Max.Z + margin)
    return bb