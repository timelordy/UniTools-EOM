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
    return mm2ft(200)


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
                    wall_width = get_wall_width(w)
                    
                    all_walls.append({
                        'p0': p0,
                        'p1': p1,
                        'ext': ext,
                        'dir': wall_direction(w),
                        'zmax': zmax,
                        'th': wall_width
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
                proj, dist = project_to_wall(pt, wd['p0'], wd['p1'])
                if proj and dist < facade_dist:
                    facade_dist = dist
                    facade_dir = wd['dir']
            
            if not facade_dir:
                for wd in all_walls:
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
                proj, dist = project_to_wall(pt, wd['p0'], wd['p1'])
                if proj and dist <= search_ft and dist < perp_dist:
                    perp_dist = dist
                    perp_wall = wd
            
            if not perp_wall:
                skip_no_perp += 1
                continue
            
            # Calculate socket position
            d = perp_wall['dir']
            n = DB.XYZ(-d.Y, d.X, 0)  # wall normal
            p0, p1 = perp_wall['p0'], perp_wall['p1']
            
            # Wall half-thickness + offset to place ON surface
            half_th = perp_wall['th'] / 2.0
            if half_th < mm2ft(25):
                half_th = mm2ft(100)
            surface_offset = half_th + mm2ft(2)  # 2mm outside surface
            
            # Corner closest to basket
            if dist_xy(p0, pt) < dist_xy(p1, pt):
                cx, cy = p0.X + d.X * corner_ft, p0.Y + d.Y * corner_ft
            else:
                cx, cy = p1.X - d.X * corner_ft, p1.Y - d.Y * corner_ft
            
            z = perp_wall['zmax'] - ceil_ft
            
            # Find level
            lvl = None
            min_dz = 1e9
            for l in levels:
                dz = abs(l.Elevation - z)
                if dz < min_dz:
                    min_dz, lvl = dz, l
            
            # Place on BOTH sides of wall
            for sign in [1, -1]:
                sx = cx + n.X * surface_offset * sign
                sy = cy + n.Y * surface_offset * sign
                socket_pt = DB.XYZ(sx, sy, z)
                
                key = (round(sx, 1), round(sy, 1))
                if key in existing:
                    skip_dup += 1
                    continue
                
                try:
                    inst = doc.Create.NewFamilyInstance(socket_pt, sym, lvl, DB.Structure.StructuralType.NonStructural)
                    
                    # Rotate to face away from wall
                    angle = math.atan2(n.Y * sign, n.X * sign)
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
