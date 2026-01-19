# -*- coding: utf-8 -*-
"""AC Socket Placement - Places sockets on both sides of perpendicular interior walls."""
import math
import sys
import os

from pyrevit import DB, forms, revit, script

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
import config_loader

CEIL_OFF_MM = 300
CORNER_OFF_MM = 200
SEARCH_RADIUS_MM = 2000
PERP_TOLERANCE = 0.4
COMMENT = "AUTO_EOM:SOCKET_AC"
MAX_BASKETS = 100
MAX_WALLS = 2000

BASKET_KW = [u"корзин", u"basket", u"кондиц", u"конденс"]
EXT_KW = [u"фасад", u"наружн", u"exterior", u"facade", u"curtain", u"витраж"]


def mm2ft(mm):
    return float(mm) / 304.8

def ft2mm(ft):
    return float(ft) * 304.8

def dist_xy(p1, p2):
    return math.sqrt((p1.X - p2.X)**2 + (p1.Y - p2.Y)**2)

def is_exterior(wall):
    try:
        p = wall.get_Parameter(DB.BuiltInParameter.FUNCTION_PARAM)
        if p and p.AsInteger() == 1:
            return True
    except:
        pass
    try:
        name = ((wall.Name or u"") + (wall.WallType.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or u"")).lower()
        return any(k in name for k in EXT_KW)
    except:
        return False

def wall_direction(wall):
    try:
        c = wall.Location.Curve
        p0, p1 = c.GetEndPoint(0), c.GetEndPoint(1)
        dx, dy = p1.X - p0.X, p1.Y - p0.Y
        ln = math.sqrt(dx*dx + dy*dy)
        if ln > 1e-9:
            return DB.XYZ(dx/ln, dy/ln, 0)
    except:
        pass
    return None

def walls_perpendicular(d1, d2):
    if not d1 or not d2:
        return False
    return abs(d1.X*d2.X + d1.Y*d2.Y) < PERP_TOLERANCE

def project_to_wall(pt, p0, p1):
    dx, dy = p1.X - p0.X, p1.Y - p0.Y
    ln2 = dx*dx + dy*dy
    if ln2 < 1e-9:
        return None, 1e9
    t = max(0, min(1, ((pt.X - p0.X)*dx + (pt.Y - p0.Y)*dy) / ln2))
    px, py = p0.X + t*dx, p0.Y + t*dy
    return DB.XYZ(px, py, pt.Z), math.sqrt((pt.X-px)**2 + (pt.Y-py)**2)

def get_wall_width(wall):
    try:
        if hasattr(wall, 'Width') and wall.Width:
            return wall.Width
    except:
        pass
    try:
        if hasattr(wall, 'WallType') and wall.WallType:
            wt = wall.WallType
            if hasattr(wt, 'Width') and wt.Width:
                return wt.Width
    except:
        pass
    # Try to get width from BoundingBox
    try:
        bb = wall.get_BoundingBox(None)
        if bb:
            loc = wall.Location
            if isinstance(loc, DB.LocationCurve):
                curve = loc.Curve
                p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)
                dx, dy = p1.X - p0.X, p1.Y - p0.Y
                length = math.sqrt(dx*dx + dy*dy)
                if length > 1e-9:
                    # Wall is along X or Y - get perpendicular dimension
                    if abs(dx) > abs(dy):
                        # Wall along X, width is in Y
                        return bb.Max.Y - bb.Min.Y
                    else:
                        # Wall along Y, width is in X
                        return bb.Max.X - bb.Min.X
    except:
        pass
    return mm2ft(200)


def get_wall_surface_points(wall, target_pt, link_transform, corner_offset, z_coord):
    """Get points on both wall surfaces closest to target point.
    
    Places sockets perpendicular to wall from target point.
    Returns list of dicts with 'point' and 'normal'.
    """
    results = []
    
    try:
        loc = wall.Location
        if isinstance(loc, DB.LocationCurve):
            curve = loc.Curve
            p0 = link_transform.OfPoint(curve.GetEndPoint(0))
            p1 = link_transform.OfPoint(curve.GetEndPoint(1))
            
            # Wall direction and normal
            dx, dy = p1.X - p0.X, p1.Y - p0.Y
            length = math.sqrt(dx*dx + dy*dy)
            if length < 1e-9:
                return results
            wall_dir = DB.XYZ(dx/length, dy/length, 0)
            wall_normal = DB.XYZ(-wall_dir.Y, wall_dir.X, 0)
            
            # Get wall bounds from BoundingBox for accurate center
            bb = wall.get_BoundingBox(None)
            if bb:
                # Transform BB corners to host coordinates
                bb_min = link_transform.OfPoint(bb.Min)
                bb_max = link_transform.OfPoint(bb.Max)
                
                # Calculate actual wall center and half-width from BB
                if abs(wall_dir.X) > abs(wall_dir.Y):
                    # Wall mostly along X axis - width is in Y
                    half_width = abs(bb_max.Y - bb_min.Y) / 2.0
                    wall_center_offset = (bb_max.Y + bb_min.Y) / 2.0
                else:
                    # Wall mostly along Y axis - width is in X  
                    half_width = abs(bb_max.X - bb_min.X) / 2.0
                    wall_center_offset = (bb_max.X + bb_min.X) / 2.0
            else:
                # Fallback to Width property
                width = get_wall_width(wall)
                half_width = width / 2.0
                if half_width < mm2ft(25):
                    half_width = mm2ft(100)
                wall_center_offset = None
            
            # Find perpendicular intersection point on wall centerline
            # Vector from p0 to target
            to_target_x = target_pt.X - p0.X
            to_target_y = target_pt.Y - p0.Y
            
            # Project onto wall direction to get distance along wall
            t = (to_target_x * wall_dir.X + to_target_y * wall_dir.Y)
            # Clamp to wall length with corner offset
            t = max(corner_offset, min(length - corner_offset, t))
            
            # Point on wall - use BB center if available
            if bb and wall_center_offset is not None:
                if abs(wall_dir.X) > abs(wall_dir.Y):
                    # Wall along X - center_y from BB, center_x from projection
                    center_x = p0.X + wall_dir.X * t
                    center_y = wall_center_offset
                else:
                    # Wall along Y - center_x from BB, center_y from projection
                    center_x = wall_center_offset
                    center_y = p0.Y + wall_dir.Y * t
            else:
                center_x = p0.X + wall_dir.X * t
                center_y = p0.Y + wall_dir.Y * t
            
            # Two surface points - one on each side of wall
            for sign in [1, -1]:
                surface_pt = DB.XYZ(
                    center_x + wall_normal.X * half_width * sign,
                    center_y + wall_normal.Y * half_width * sign,
                    z_coord
                )
                results.append({
                    'point': surface_pt,
                    'normal': DB.XYZ(wall_normal.X * sign, wall_normal.Y * sign, 0)
                })
    except:
        pass
    
    return results


def main():
    import System
    out = script.get_output()
    doc = revit.doc
    uidoc = revit.uidoc
    
    out.print_md("# AC Socket Placement")
    
    try:
        rules = config_loader.load_rules()
    except:
        rules = {}
    
    ceil_ft = mm2ft(rules.get('ac_ceiling_offset_mm', CEIL_OFF_MM))
    corner_ft = mm2ft(rules.get('ac_corner_offset_mm', CORNER_OFF_MM))
    search_ft = mm2ft(rules.get('ac_search_radius_mm', SEARCH_RADIUS_MM))
    
    # Find socket type
    sym = None
    tname = rules.get('ac_socket_type_name', 'TSL_EF_т_СТ_в_IP20_Рзт_1P+N+PE')
    for cat in [DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment]:
        try:
            for s in DB.FilteredElementCollector(doc).OfCategory(cat).OfClass(DB.FamilySymbol):
                if tname in (s.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or ""):
                    sym = s
                    break
        except:
            pass
        if sym:
            break
    
    if not sym:
        forms.alert("Socket type '{}' not found".format(tname), exitscript=True)
        return
    
    out.print_md("Socket: {}".format(tname))
    
    # Find baskets and walls in links
    out.print_md("---")
    baskets = []
    all_walls = []
    
    for link in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        try:
            ldoc = link.GetLinkDocument()
            if not ldoc:
                continue
            tf = link.GetTotalTransform()
            
            # Find baskets
            for cat in [DB.BuiltInCategory.OST_MechanicalEquipment, DB.BuiltInCategory.OST_GenericModel]:
                if len(baskets) >= MAX_BASKETS:
                    break
                try:
                    for e in DB.FilteredElementCollector(ldoc).OfCategory(cat).WhereElementIsNotElementType():
                        if len(baskets) >= MAX_BASKETS:
                            break
                        try:
                            sym_e = getattr(e, 'Symbol', None)
                            txt = u"{} {}".format(e.Name or u"", sym_e.Family.Name if sym_e and sym_e.Family else u"").lower()
                            if not any(k in txt for k in BASKET_KW):
                                continue
                            
                            loc = e.Location
                            pt = loc.Point if isinstance(loc, DB.LocationPoint) else None
                            if not pt:
                                bb = e.get_BoundingBox(None)
                                if bb:
                                    pt = DB.XYZ((bb.Min.X+bb.Max.X)/2, (bb.Min.Y+bb.Max.Y)/2, bb.Min.Z)
                            if pt:
                                baskets.append({'pt': pt, 'tf': tf})
                        except:
                            continue
                except:
                    continue
            
            # Find walls
            for w in DB.FilteredElementCollector(ldoc).OfClass(DB.Wall).WhereElementIsNotElementType():
                if len(all_walls) >= MAX_WALLS:
                    break
                try:
                    loc = w.Location
                    if not isinstance(loc, DB.LocationCurve):
                        continue
                    c = loc.Curve
                    bb = w.get_BoundingBox(None)
                    ext = is_exterior(w)
                    
                    p0 = tf.OfPoint(c.GetEndPoint(0))
                    p1 = tf.OfPoint(c.GetEndPoint(1))
                    zmax = tf.OfPoint(DB.XYZ(0, 0, bb.Max.Z)).Z if bb else p0.Z + mm2ft(2700)
                    zmin = tf.OfPoint(DB.XYZ(0, 0, bb.Min.Z)).Z if bb else p0.Z
                    
                    all_walls.append({
                        'wall': w,
                        'transform': tf,
                        'p0': p0,
                        'p1': p1,
                        'ext': ext,
                        'dir': wall_direction(w),
                        'zmax': zmax,
                        'zmin': zmin
                    })
                except:
                    continue
        except:
            continue
    
    out.print_md("Found {} baskets, {} walls".format(len(baskets), len(all_walls)))
    
    if not baskets:
        forms.alert("No baskets found", exitscript=True)
        return
    if not all_walls:
        forms.alert("No walls found", exitscript=True)
        return
    
    # Get levels and existing sockets
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    existing = set()
    for cat in [DB.BuiltInCategory.OST_ElectricalFixtures]:
        try:
            for e in DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType():
                try:
                    p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                    if p and COMMENT in (p.AsString() or ""):
                        loc = e.Location
                        if isinstance(loc, DB.LocationPoint):
                            existing.add((round(loc.Point.X, 1), round(loc.Point.Y, 1)))
                except:
                    continue
        except:
            continue
    
    # Place sockets
    created = 0
    created_ids = []
    target_level = None
    skip_no_facade = 0
    skip_no_perp = 0
    skip_dup = 0
    skip_err = 0
    
    with DB.Transaction(doc, "AC Sockets") as t:
        t.Start()
        if not sym.IsActive:
            sym.Activate()
            doc.Regenerate()
        
        for b in baskets:
            pt_local = b['pt']
            tf = b['tf']
            pt = tf.OfPoint(pt_local)
            
            # Find facade wall
            facade_dir = None
            facade_dist = 1e9
            
            for wd in all_walls:
                if not wd['ext']:
                    continue
                # Check wall is on same floor as basket
                if pt.Z < wd['zmin'] or pt.Z > wd['zmax']:
                    continue
                proj, dist = project_to_wall(pt, wd['p0'], wd['p1'])
                if proj and dist < facade_dist:
                    facade_dist = dist
                    facade_dir = wd['dir']
            
            if not facade_dir:
                for wd in all_walls:
                    # Check wall is on same floor as basket
                    if pt.Z < wd['zmin'] or pt.Z > wd['zmax']:
                        continue
                    proj, dist = project_to_wall(pt, wd['p0'], wd['p1'])
                    if proj and dist < facade_dist:
                        facade_dist = dist
                        facade_dir = wd['dir']
            
            if not facade_dir:
                skip_no_facade += 1
                continue
            
            # Find perpendicular interior wall
            perp_wall = None
            perp_dist = 1e9
            
            for wd in all_walls:
                if wd['ext']:
                    continue
                if not walls_perpendicular(wd['dir'], facade_dir):
                    continue
                # Check wall is on same floor as basket (Z range overlap)
                if pt.Z < wd['zmin'] or pt.Z > wd['zmax']:
                    continue
                proj, dist = project_to_wall(pt, wd['p0'], wd['p1'])
                if proj and dist <= search_ft and dist < perp_dist:
                    perp_dist = dist
                    perp_wall = wd
            
            if not perp_wall:
                skip_no_perp += 1
                continue
            
            # Calculate Z coordinate
            z = perp_wall['zmax'] - ceil_ft
            
            # Find level
            lvl = None
            min_dz = 1e9
            for l in levels:
                dz = abs(l.Elevation - z)
                if dz < min_dz:
                    min_dz, lvl = dz, l
            
            # Get wall surface points using geometry
            surface_points = get_wall_surface_points(
                perp_wall['wall'],
                pt,
                perp_wall['transform'],
                corner_ft,
                z
            )
            
            # Place socket on each surface
            for surface in surface_points:
                socket_pt = surface['point']
                face_normal = surface['normal']
                
                key = (round(socket_pt.X, 1), round(socket_pt.Y, 1))
                if key in existing:
                    skip_dup += 1
                    continue
                
                try:
                    inst = doc.Create.NewFamilyInstance(socket_pt, sym, lvl, DB.Structure.StructuralType.NonStructural)
                    
                    # Rotate socket to face away from wall (normal points outward)
                    angle = math.atan2(face_normal.Y, face_normal.X) - math.pi / 2  # 90 degrees clockwise
                    axis = DB.Line.CreateBound(socket_pt, DB.XYZ(socket_pt.X, socket_pt.Y, socket_pt.Z + 1))
                    DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, angle)
                    
                    cp = inst.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                    if cp:
                        cp.Set(COMMENT)
                    
                    created += 1
                    existing.add(key)
                    created_ids.append(inst.Id)
                    if target_level is None:
                        target_level = lvl
                except:
                    skip_err += 1
        
        t.Commit()
    
    # Results
    out.print_md("---")
    out.print_md("## Results")
    out.print_md("- **Created:** {}".format(created))
    out.print_md("- Skip (no facade): {}".format(skip_no_facade))
    out.print_md("- Skip (no perp wall): {}".format(skip_no_perp))
    out.print_md("- Skip (duplicate): {}".format(skip_dup))
    out.print_md("- Skip (error): {}".format(skip_err))
    
    if created == 0:
        forms.alert("No sockets created", title="Done")
        return
    
    # Dialog
    ids_list = System.Collections.Generic.List[DB.ElementId]()
    for eid in created_ids:
        ids_list.Add(eid)
    
    choice = forms.alert(
        "Created {} sockets.\n\nOpen view?".format(created),
        title="Done",
        options=["Open Plan", "Create Debug Plan", "Close"]
    )
    
    if choice == "Open Plan" and target_level:
        for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
            try:
                if v.ViewType == DB.ViewType.FloorPlan and not v.IsTemplate:
                    if v.GenLevel and v.GenLevel.Id == target_level.Id:
                        uidoc.ActiveView = v
                        uidoc.Selection.SetElementIds(ids_list)
                        break
            except:
                continue
    
    elif choice == "Create Debug Plan" and target_level and created_ids:
        try:
            socket_z = doc.GetElement(created_ids[0]).Location.Point.Z
            with DB.Transaction(doc, "Debug Plan") as t2:
                t2.Start()
                vft = None
                for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
                    if vt.ViewFamily == DB.ViewFamily.FloorPlan:
                        vft = vt
                        break
                if vft:
                    plan = DB.ViewPlan.Create(doc, vft.Id, target_level.Id)
                    plan.Name = "DEBUG_AC_{}".format(target_level.Name)
                    vr = plan.GetViewRange()
                    cut = socket_z - target_level.Elevation + mm2ft(50)
                    vr.SetOffset(DB.PlanViewPlane.CutPlane, cut)
                    vr.SetOffset(DB.PlanViewPlane.TopClipPlane, cut + mm2ft(500))
                    vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, cut - mm2ft(500))
                    vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, cut - mm2ft(500))
                    plan.SetViewRange(vr)
                    t2.Commit()
                    uidoc.ActiveView = plan
                    uidoc.Selection.SetElementIds(ids_list)
                else:
                    t2.RollBack()
        except Exception as ex:
            out.print_md("Error: {}".format(ex))


if __name__ == '__main__':
    import System
    try:
        main()
    except Exception as e:
        import traceback
        script.get_output().print_md("**Error:**\n```\n{}\n```".format(traceback.format_exc()))
