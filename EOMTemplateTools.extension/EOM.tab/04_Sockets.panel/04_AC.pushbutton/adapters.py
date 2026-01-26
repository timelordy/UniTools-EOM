# -*- coding: utf-8 -*-

import System
from pyrevit import DB
import constants
import domain
import math

def get_socket_symbol(doc):
    """Find the socket family symbol by name."""
    target_name = constants.SOCKET_FAMILY_NAME
    
    # Check Electrical Fixtures
    collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalFixtures).OfClass(DB.FamilySymbol)
    for sym in collector:
        if target_name in (sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or ""):
            return sym
    
    # Check Electrical Equipment as fallback
    collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment).OfClass(DB.FamilySymbol)
    for sym in collector:
        if target_name in (sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or ""):
            return sym
            
    return None

def collect_baskets(doc):
    """Collect AC baskets from linked models."""
    baskets = []
    
    for link in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        try:
            ldoc = link.GetLinkDocument()
            if not ldoc: continue
            
            tf = link.GetTotalTransform()
            
            # Categories to search
            cats = [DB.BuiltInCategory.OST_MechanicalEquipment, DB.BuiltInCategory.OST_GenericModel]
            
            for cat in cats:
                if len(baskets) >= constants.MAX_BASKETS: break
                
                elements = DB.FilteredElementCollector(ldoc).OfCategory(cat).WhereElementIsNotElementType()
                for e in elements:
                    # Check name keywords
                    name = (e.Name or "").lower()
                    
                    # Check Symbol name too
                    sym = getattr(e, 'Symbol', None)
                    if sym:
                        name += " " + (sym.Family.Name or "").lower()
                        
                    if not any(k in name for k in constants.BASKET_KW):
                        continue
                        
                    # Get location point
                    pt = None
                    loc = e.Location
                    if isinstance(loc, DB.LocationPoint):
                        pt = loc.Point
                    else:
                        bb = e.get_BoundingBox(None)
                        if bb:
                            pt = DB.XYZ((bb.Min.X + bb.Max.X)/2, (bb.Min.Y + bb.Max.Y)/2, bb.Min.Z)
                    
                    if pt:
                        # Transform to host coordinates
                        host_pt = tf.OfPoint(pt)
                        baskets.append({
                            'point': host_pt,
                            'element': e,
                            'link_transform': tf
                        })
        except:
            continue
            
    return baskets

def collect_walls(doc):
    """Collect walls from linked models."""
    walls = []
    
    for link in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        try:
            ldoc = link.GetLinkDocument()
            if not ldoc: continue
            
            tf = link.GetTotalTransform()
            
            raw_walls = DB.FilteredElementCollector(ldoc).OfClass(DB.Wall).WhereElementIsNotElementType()
            
            for w in raw_walls:
                try:
                    # Basic validation
                    loc = w.Location
                    if not isinstance(loc, DB.LocationCurve): continue
                    
                    # Get Geometry info
                    curve = loc.Curve
                    p0 = tf.OfPoint(curve.GetEndPoint(0))
                    p1 = tf.OfPoint(curve.GetEndPoint(1))
                    
                    # Z-Range
                    bb = w.get_BoundingBox(None)
                    if bb:
                        z_min = tf.OfPoint(bb.Min).Z
                        z_max = tf.OfPoint(bb.Max).Z
                    else:
                        z_min = p0.Z
                        z_max = p0.Z + domain.mm2ft(3000)
                        
                    direction = domain.get_wall_direction(w)
                    if not direction: continue
                    
                    # Transform direction (rotation only)
                    host_dir = tf.OfVector(direction)
                    
                    walls.append({
                        'wall': w,
                        'transform': tf,
                        'p0': p0,
                        'p1': p1,
                        'z_min': z_min,
                        'z_max': z_max,
                        'direction': host_dir,
                        'is_exterior': domain.is_exterior(w),
                        'width': domain.get_wall_width(w)
                    })
                except:
                    continue
        except:
            continue
            
    return walls

def collect_rooms(doc):
    """Collect rooms from linked models to check valid placement areas."""
    rooms = []
    
    for link in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        try:
            ldoc = link.GetLinkDocument()
            if not ldoc: continue
            
            tf = link.GetTotalTransform()
            
            raw_rooms = DB.FilteredElementCollector(ldoc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType()
            
            for r in raw_rooms:
                if r.Area < 0.1: continue
                
                # Check Balcony
                name = (r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() or "").lower()
                is_balcony = any(k in name for k in constants.BALCONY_KW)
                
                # Boundary box for fast check
                bb = r.get_BoundingBox(None)
                if not bb: continue
                
                bb_min = tf.OfPoint(bb.Min)
                bb_max = tf.OfPoint(bb.Max)
                
                rooms.append({
                    'room': r,
                    'is_balcony': is_balcony,
                    'bb_min': bb_min,
                    'bb_max': bb_max,
                    'transform': tf
                })
        except:
            continue
            
    return rooms

def get_room_at_point(pt, rooms_data):
    """Check which room contains the point."""
    # 1. Fast BoundingBox check
    candidates = []
    for r in rooms_data:
        if (r['bb_min'].X <= pt.X <= r['bb_max'].X and
            r['bb_min'].Y <= pt.Y <= r['bb_max'].Y and
            r['bb_min'].Z <= pt.Z <= r['bb_max'].Z):
            candidates.append(r)
            
    if not candidates:
        return None
        
    # 2. Detailed check (using Revit API IsPointInRoom if possible, or just trust BB for now?)
    # Since IsPointInRoom requires coordinate transformation, let's use IsPointInRoom on the linked room
    # We need to transform point BACK to link coordinates
    
    for r_data in candidates:
        room = r_data['room']
        tf_inverse = r_data['transform'].Inverse
        pt_local = tf_inverse.OfPoint(pt)
        
        if room.IsPointInRoom(pt_local):
            return r_data
            
    return None

def create_socket(doc, location, symbol, level, normal):
    """Create socket instance."""
    try:
        # Create instance
        instance = doc.Create.NewFamilyInstance(location, symbol, level, DB.Structure.StructuralType.NonStructural)
        
        # Rotate to align with wall
        angle = math.atan2(normal.Y, normal.X) - math.pi / 2
        
        axis = DB.Line.CreateBound(location, DB.XYZ(location.X, location.Y, location.Z + 1.0))
        DB.ElementTransformUtils.RotateElement(doc, instance.Id, axis, angle)
        
        # Set Comment Parameter
        p = instance.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p:
            p.Set(constants.PARAM_COMMENTS)
            
        return instance
    except Exception as e:
        return None

def create_debug_view(doc, uidoc, target_level, ids_list, socket_z):
    """Create a floor plan to debug socket placement."""
    try:
        # Find FloorPlan ViewType
        vft = None
        for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            if vt.ViewFamily == DB.ViewFamily.FloorPlan:
                vft = vt
                break
        
        if not vft: return None
        
        # Create View
        plan = DB.ViewPlan.Create(doc, vft.Id, target_level.Id)
        plan.Name = "DEBUG_AC_{}_{}".format(target_level.Name, System.DateTime.Now.ToString("HHmmss"))
        
        # Calculate offsets
        cut_offset = socket_z - target_level.Elevation + domain.mm2ft(100)
        
        # Set ViewRange
        vr = plan.GetViewRange()
        vr.SetOffset(DB.PlanViewPlane.CutPlane, cut_offset)
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, cut_offset + domain.mm2ft(500))
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, cut_offset - domain.mm2ft(500))
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, cut_offset - domain.mm2ft(500))
        plan.SetViewRange(vr)
        
        return plan
    except:
        return None
