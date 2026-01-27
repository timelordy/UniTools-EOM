# -*- coding: utf-8 -*-
from pyrevit import DB, revit
import socket_utils as su
from utils_units import mm_to_ft
import placement_engine

def _collect_fridge_by_visibility_param(link_doc):
    pts = []
    fridge_keywords = [u'\u0445\u043e\u043b\u043e\u0434\u0438\u043b\u044c\u043d\u0438\u043a', u'\u0445\u043e\u043b\u043e\u0434', u'fridge', u'refriger']
    bics = [
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    for bic in bics:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for e in col:
            try:
                params = e.Parameters
                for p in params:
                    if p is None:
                        continue
                    pname = ''
                    try:
                        pname = (p.Definition.Name or '').lower()
                    except Exception:
                        continue
                    is_fridge_param = False
                    for kw in fridge_keywords:
                        if kw in pname:
                            is_fridge_param = True
                            break
                    if not is_fridge_param:
                        continue
                    if p.StorageType == DB.StorageType.Integer:
                        if p.AsInteger() == 1:
                            loc = e.Location
                            if isinstance(loc, DB.LocationPoint):
                                pts.append(loc.Point)
                            break
            except Exception:
                pass
    return pts

def _project_t_on_segment(p, a, b):
    if p is None or a is None or b is None: return None
    try:
        ax, ay, bx, by, px, py = float(a.X), float(a.Y), float(b.X), float(b.Y), float(p.X), float(p.Y)
        vx, vy = (bx - ax), (by - ay)
        denom = (vx * vx + vy * vy)
        if denom <= 1e-12: return 0.0
        return ((px - ax) * vx + (py - ay) * vy) / denom
    except: return None

def _min_dist_bbox_to_segment(bbox, p0, p1):
    """Calculate minimum distance from bbox to segment in XY plane."""
    if bbox is None or p0 is None or p1 is None:
        return 1e9
    try:
        bmin, bmax = bbox
        corners = [
            DB.XYZ(bmin.X, bmin.Y, 0),
            DB.XYZ(bmax.X, bmin.Y, 0),
            DB.XYZ(bmax.X, bmax.Y, 0),
            DB.XYZ(bmin.X, bmax.Y, 0)
        ]
        min_d = 1e9
        for c in corners:
            proj = _closest_point_on_segment_xy(c, p0, p1)
            if proj:
                d = _dist_xy(c, proj)
                if d < min_d:
                    min_d = d
        for pt in [p0, p1]:
            if _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
                min_d = 0.0
                break
        return min_d
    except:
        return 1e9


def _project_bbox_to_segment(bbox, p0, p1, seg_len, margin_ft, max_dist_ft=None):
    """
    Project bbox onto segment and return blocked interval.
    Only blocks if bbox is CLOSE to the segment (within max_dist_ft).
    """
    if bbox is None or p0 is None or p1 is None: return None
    if max_dist_ft is None:
        max_dist_ft = mm_to_ft(500)  # Default: bbox must be within 500mm of wall
    
    try:
        bmin, bmax = bbox
        
        # CRITICAL FIX: Check if bbox is actually close to this segment
        min_dist = _min_dist_bbox_to_segment(bbox, p0, p1)
        if min_dist > max_dist_ft:
            return None  # bbox is too far from this wall segment
        
        corners = [DB.XYZ(bmin.X, bmin.Y, 0), DB.XYZ(bmax.X, bmin.Y, 0), DB.XYZ(bmax.X, bmax.Y, 0), DB.XYZ(bmin.X, bmax.Y, 0)]
        t_values = [t for t in [_project_t_on_segment(c, p0, p1) for c in corners] if t is not None]
        if not t_values: return None
        t_min, t_max = max(0.0, min(t_values)), min(1.0, max(t_values))
        if t_max <= t_min: return None
        
        return (max(0.0, t_min * seg_len - margin_ft), min(seg_len, t_max * seg_len + margin_ft))
    except: return None

def _is_in_room_bbox(inst, room_bb):
    if inst is None or room_bb is None: return False
    try:
        bb = inst.get_BoundingBox(None)
        if bb is None: return False
        tol = mm_to_ft(500)
        return not (bb.Max.X < room_bb.Min.X - tol or bb.Min.X > room_bb.Max.X + tol or bb.Max.Y < room_bb.Min.Y - tol or bb.Min.Y > room_bb.Max.Y + tol)
    except: return False

def _get_element_name_text(inst):
    """Get combined family name + type name + instance name for filtering."""
    if inst is None:
        return u''
    parts = []
    try:
        sym = inst.Symbol
        if sym:
            fam = sym.Family
            if fam and fam.Name:
                parts.append(fam.Name)
            if sym.Name:
                parts.append(sym.Name)
    except:
        pass
    try:
        if inst.Name:
            parts.append(inst.Name)
    except:
        pass
    return u' '.join(parts).lower()

# Keywords that identify kitchen cabinets/counters (not tables/chairs)
_KITCHEN_UNIT_KEYWORDS = [
    u'\u043a\u0443\u0445\u043d',       # кухн (kitchen)
    u'\u0448\u043a\u0430\u0444',       # шкаф (cabinet)
    u'\u0442\u0443\u043c\u0431',       # тумб (base cabinet)
    u'\u0441\u0442\u043e\u043b\u0435\u0448\u043d',  # столешн (countertop)
    u'\u0433\u0430\u0440\u043d\u0438\u0442\u0443\u0440',  # гарнитур (unit)
    u'cabinet',
    u'counter',
    u'kitchen',
    u'casework',
    u'base unit',
    u'wall unit',
    u'upper',
    u'lower',
    u'\u043d\u0430\u0432\u0435\u0441\u043d',  # навесн (wall-mounted)
    u'\u043d\u0430\u043f\u043e\u043b\u044c\u043d',  # напольн (floor-standing)
]

# Keywords that should EXCLUDE an element (tables, chairs, etc.)
_EXCLUDE_KEYWORDS = [
    u'\u0441\u0442\u043e\u043b ',      # стол (table - with space)
    u'\u0441\u0442\u0443\u043b',       # стул (chair)
    u'\u043a\u0440\u0435\u0441\u043b',  # кресл (armchair)
    u'\u0434\u0438\u0432\u0430\u043d',  # диван (sofa)
    u'table',
    u'chair',
    u'sofa',
    u'desk',
    u'dining',
    u'\u043e\u0431\u0435\u0434\u0435\u043d',  # обеден (dining)
]

def _is_kitchen_unit_element(inst):
    """Check if element is a kitchen cabinet/counter (not table/chair)."""
    if inst is None:
        return False
    name_text = _get_element_name_text(inst)
    if not name_text:
        return False
    # First check exclusions
    for excl in _EXCLUDE_KEYWORDS:
        if excl in name_text:
            return False
    # Then check if it matches kitchen unit keywords
    for kw in _KITCHEN_UNIT_KEYWORDS:
        if kw in name_text:
            return True
    return False


def _collect_kitchen_unit_bboxes(link_doc, room, segs=None):
    """
    Collect bounding boxes of kitchen cabinets/counters that are:
    1. In the room
    2. Named like kitchen unit (not table/chair)
    3. Close to a wall (within 500mm)
    """
    bboxes = []
    if link_doc is None or room is None: 
        return bboxes
    try:
        room_bb = room.get_BoundingBox(None)
    except: 
        return bboxes
    if room_bb is None: 
        return bboxes
    
    max_wall_dist_ft = mm_to_ft(500)  # Element must be within 500mm of wall
    
    for bic in [DB.BuiltInCategory.OST_Casework, DB.BuiltInCategory.OST_Furniture]:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()
            for inst in col:
                if not _is_in_room_bbox(inst, room_bb):
                    continue
                
                # FILTER 1: Check if element name matches kitchen unit pattern
                if not _is_kitchen_unit_element(inst):
                    continue
                
                try:
                    bb = inst.get_BoundingBox(None)
                    if bb is None:
                        continue
                    
                    # FILTER 2: Check if element is close to any wall segment
                    if segs:
                        is_near_wall = False
                        for p0, p1, wall in segs:
                            min_dist = _min_dist_bbox_to_segment((bb.Min, bb.Max), p0, p1)
                            if min_dist <= max_wall_dist_ft:
                                is_near_wall = True
                                break
                        if not is_near_wall:
                            continue
                    
                    bboxes.append((bb.Min, bb.Max))
                except: 
                    pass
        except: 
            pass
    return bboxes

def _calculate_perimeter_allowed_path(link_doc, room, segs, avoid_door_ft, avoid_window_ft, openings_cache, unit_bboxes, unit_margin_ft):
    if not segs: return [], 0.0
    allowed_path, effective_len_ft = [], 0.0
    
    for p0, p1, wall in segs:
        try: seg_len = _dist_xy(p0, p1)
        except: seg_len = 0.0
        if seg_len < 1e-9: continue
        try: curve = DB.Line.CreateBound(p0, p1)
        except: continue
        
        try:
            ops = su._get_wall_openings_cached(link_doc, wall, openings_cache)
        except Exception:
            ops = {}
        blocked = []
        for pt, w in ops.get('windows', []):
            d0 = su._project_dist_on_curve_xy_ft(curve, seg_len, pt, tol_ft=2.0)
            if d0 is not None: blocked.append((d0 - (float(w)*0.5 if w else mm_to_ft(600)) - avoid_window_ft, d0 + (float(w)*0.5 if w else mm_to_ft(600)) + avoid_window_ft))
        for pt, w in ops.get('doors', []):
            d0 = su._project_dist_on_curve_xy_ft(curve, seg_len, pt, tol_ft=2.0)
            if d0 is not None: blocked.append((d0 - (float(w)*0.5 if w else mm_to_ft(450)) - avoid_door_ft, d0 + (float(w)*0.5 if w else mm_to_ft(450)) + avoid_door_ft))
        for bbox in unit_bboxes:
            interval = _project_bbox_to_segment(bbox, p0, p1, seg_len, unit_margin_ft)
            if interval: blocked.append(interval)
            
        for a, b in su._invert_intervals(su._merge_intervals(blocked, 0.0, seg_len), 0.0, seg_len):
            if (b - a) > 1e-6:
                allowed_path.append((wall, curve, seg_len, a, b, p0, p1))
                effective_len_ft += (b - a)
    return allowed_path, effective_len_ft

def _generate_perimeter_candidates(allowed_path, effective_len_ft, spacing_ft, wall_end_clear_ft, num_sockets):
    candidates = []
    if effective_len_ft <= 1e-6 or num_sockets <= 0: return candidates
    segment_len = effective_len_ft / num_sockets
    min_spacing_ft = mm_to_ft(1000)
    while num_sockets > 1 and segment_len < min_spacing_ft:
        num_sockets -= 1
        segment_len = effective_len_ft / num_sockets
    acc, path_idx = 0.0, 0
    path = allowed_path or []

    for i in range(num_sockets):
        target_d = (i + 0.5) * segment_len
        while path_idx < len(path):
            wall, curve, seg_len, a, b, p0, p1 = path[path_idx]
            seg_len_eff = b - a
            if target_d <= (acc + seg_len_eff):
                local_offset = target_d - acc
                local_d = a + local_offset
                local_d = max(a + wall_end_clear_ft, min(b - wall_end_clear_ft, local_d))
                if local_d < a or local_d > b:
                    acc += seg_len_eff
                    path_idx += 1
                    continue
                try:
                    pt = curve.Evaluate(local_d / seg_len, True)
                    d = curve.ComputeDerivatives(local_d / seg_len, True)
                    candidates.append((wall, pt, d.BasisX.Normalize()))
                except:
                    acc += seg_len_eff
                    path_idx += 1
                    continue
                break
            else:
                acc += seg_len_eff
                path_idx += 1
    return candidates

def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''

def _dist_xy(a, b):
    try:
        return ((float(a.X) - float(b.X)) ** 2 + (float(a.Y) - float(b.Y)) ** 2) ** 0.5
    except Exception:
        return 1e9

def _closest_point_on_segment_xy(p, a, b):
    if p is None or a is None or b is None:
        return None
    try:
        ax, ay = float(a.X), float(a.Y)
        bx, by = float(b.X), float(b.Y)
        px, py = float(p.X), float(p.Y)
        vx, vy = (bx - ax), (by - ay)
        denom = (vx * vx + vy * vy)
        if denom <= 1e-12:
            return DB.XYZ(ax, ay, float(p.Z) if hasattr(p, 'Z') else 0.0)
        t = ((px - ax) * vx + (py - ay) * vy) / denom
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        return DB.XYZ(ax + vx * t, ay + vy * t, float(p.Z) if hasattr(p, 'Z') else 0.0)
    except Exception:
        return None

def _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    try:
        x, y = float(pt.X), float(pt.Y)
        minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
        maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
        return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)
    except Exception:
        return False

def _is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        return bool(room.IsPointInRoom(point))
    except Exception:
        return False

def _points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []

    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None

    zmid = None
    zmin = None
    zmax = None
    ztol = mm_to_ft(200)
    if room_bb:
        try:
            zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
            zmin = float(min(room_bb.Min.Z, room_bb.Max.Z)) - float(ztol)
            zmax = float(max(room_bb.Min.Z, room_bb.Max.Z)) + float(ztol)
        except Exception:
            zmid = None
            zmin = None
            zmax = None

    selected = []
    for pt in points:
        if pt is None:
            continue

        if (zmin is not None) and (zmax is not None):
            try:
                z = float(pt.Z)
                if z < float(zmin) or z > float(zmax):
                    continue
            except Exception:
                pass

        if room_bb:
            try:
                min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, room_bb.Min.Z)
                max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, room_bb.Max.Z)
                if not _bbox_contains_point_xy(pt, min_exp, max_exp):
                    continue
            except Exception:
                pass

        if _is_point_in_room(room, pt):
            selected.append(pt)
            continue

        pt_room = None
        if zmid is not None:
            try:
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), float(zmid))
            except Exception:
                pt_room = None

        if pt_room and _is_point_in_room(room, pt_room):
            selected.append(pt)
            continue

        try:
            if room_bb:
                rc = DB.XYZ(
                    (room_bb.Min.X + room_bb.Max.X) * 0.5,
                    (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                    float(pt_room.Z) if pt_room else float(pt.Z)
                )
                v = rc - (pt_room if pt_room else pt)
                if v and v.GetLength() > mm_to_ft(1):
                    vn = v.Normalize()
                    for dmm in (200, 500, 900):
                        probe = (pt_room if pt_room else pt) + vn * mm_to_ft(dmm)
                        if _is_point_in_room(room, probe):
                            selected.append(pt)
                            break
        except Exception:
            pass

    return selected

def _try_get_room_at_point(doc_, pt):
    if doc_ is None or pt is None:
        return None
    try:
        r = doc_.GetRoomAtPoint(pt)
        if r is not None:
            return r
    except Exception:
        pass
    for z in (0.0, mm_to_ft(1500), mm_to_ft(3000)):
        try:
            r = doc_.GetRoomAtPoint(DB.XYZ(float(pt.X), float(pt.Y), float(z)))
            if r is not None:
                return r
        except Exception:
            continue
    return None

def _nearest_segment(pt, segs):
    best = None
    best_proj = None
    best_d = None
    for p0, p1, wall in segs or []:
        proj = _closest_point_on_segment_xy(pt, p0, p1)
        if proj is None:
            continue
        d = _dist_xy(pt, proj)
        if best_d is None or d < best_d:
            best = (p0, p1, wall)
            best_proj = proj
            best_d = d
    return best, best_proj, best_d

def _get_wall_segments(room, link_doc):
    segs = []
    if room is None or link_doc is None:
        return segs
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglist = su._get_room_outer_boundary_segments(room, opts)
    except Exception:
        seglist = None
    if not seglist:
        return segs

    for bs in seglist:
        try:
            curve = bs.GetCurve()
        except Exception:
            curve = None
        if curve is None:
            continue

        try:
            eid = bs.ElementId
        except Exception:
            eid = DB.ElementId.InvalidElementId
        if not eid or eid == DB.ElementId.InvalidElementId:
            continue

        try:
            el = link_doc.GetElement(eid)
        except Exception:
            el = None
        if el is None or (not isinstance(el, DB.Wall)):
            continue
        if su._is_curtain_wall(el):
            continue

        try:
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
        except Exception:
            continue
        segs.append((p0, p1, el))

    return segs

def _get_comments_text(elem):
    if elem is None:
        return u''
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    for nm in (u'\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438', u'Comments'):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsString()
                if v:
                    return v
        except Exception:
            continue
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    for nm in (u'\u041c\u0430\u0440\u043a\u0430', u'Mark'):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsString()
                if v:
                    return v
        except Exception:
            continue
    return u''

def _collect_tagged_instances(host_doc, tag_value):
    ids = set()
    elems = []
    pts = []
    if host_doc is None or not tag_value:
        return ids, elems, pts

    for bic in (
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_Furniture,
    ):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                c = _get_comments_text(e)
            except Exception:
                c = u''
            if not c:
                continue
            try:
                if tag_value not in c:
                    continue
            except Exception:
                continue

            try:
                ids.add(int(e.Id.IntegerValue))
            except Exception:
                pass
            elems.append(e)
            try:
                pt = su._inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    return ids, elems, pts

def _get_abs_z_from_level_offset(inst, host_doc):
    if inst is None or host_doc is None:
        return None
    try:
        lid = getattr(inst, 'LevelId', None)
        if not lid or lid == DB.ElementId.InvalidElementId:
            return None
        lvl = host_doc.GetElement(lid)
        if lvl is None or not hasattr(lvl, 'Elevation'):
            return None
        lvl_z = float(lvl.Elevation)
    except Exception:
        return None

    off = None
    try:
        p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and p.StorageType == DB.StorageType.Double:
            off = p.AsDouble()
    except Exception:
        off = None

    if off is None:
        for nm in (
            u'\u041e\u0442\u043c\u0435\u0442\u043a\u0430 \u043e\u0442 \u0443\u0440\u043e\u0432\u043d\u044f',
            u'\u0421\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u043e\u0442 \u0443\u0440\u043e\u0432\u043d\u044f',
            u'Elevation from Level',
            u'Offset from Level',
        ):
            try:
                p = inst.LookupParameter(nm)
                if p and p.StorageType == DB.StorageType.Double:
                    off = p.AsDouble()
                    break
            except Exception:
                continue

    if off is None:
        return None
    try:
        return float(lvl_z) + float(off)
    except Exception:
        return None

def _try_set_offset_from_level(inst, off_ft):
    if inst is None or off_ft is None:
        return False
    try:
        off = float(off_ft)
    except Exception:
        return False

    try:
        p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
            p.Set(off)
            return True
    except Exception:
        pass

    for nm in (
        u'\u041e\u0442\u043c\u0435\u0442\u043a\u0430 \u043e\u0442 \u0443\u0440\u043e\u0432\u043d\u044f',
        u'\u0421\u043c\u0435\u0449\u0435\u043d\u0438\u0435 \u043e\u0442 \u0443\u0440\u043e\u0432\u043d\u044f',
        u'Elevation from Level',
        u'Offset from Level',
    ):
        try:
            p = inst.LookupParameter(nm)
            if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(off)
                return True
        except Exception:
            continue

    return False

def _is_socket_instance(inst):
    if inst is None:
        return False
    try:
        sym = inst.Symbol
    except Exception:
        sym = None
    try:
        lbl = placement_engine.format_family_type(sym) if sym else ''
    except Exception:
        lbl = ''
    t = _norm(lbl)
    if not t:
        return False
    return (
        (u'\u0440\u0437\u0442' in t)
        or (u'\u04403\u0442' in t)
        or (u'p3t' in t)
        or (u'\u0440\u043e\u0437\u0435\u0442' in t)
        or (u'socket' in t)
        or (u'outlet' in t)
    )

def _collect_host_socket_instances(host_doc):
    items = []
    if host_doc is None:
        return items
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            if not _is_socket_instance(e):
                continue
            pt = su._inst_center_point(e)
            if pt:
                items.append((e, pt))
    return items

def _collect_family_instance_points_by_symbol_id(link_doc, symbol_id_int):
    pts = []
    if link_doc is None or symbol_id_int is None:
        return pts
    try:
        want = int(symbol_id_int)
    except Exception:
        return pts
    try:
        col = (
            DB.FilteredElementCollector(link_doc)
            .OfClass(DB.FamilyInstance)
            .WhereElementIsNotElementType()
        )
    except Exception:
        col = None
    if not col:
        return pts
    for inst in col:
        try:
            sid = int(inst.Symbol.Id.IntegerValue)
        except Exception:
            continue
        if sid != want:
            continue
        try:
            pt = su._inst_center_point(inst)
        except Exception:
            pt = None
        if pt:
            pts.append(pt)
    return pts

def _pick_linked_element_any(link_inst, prompt):
    if link_inst is None:
        return None

    uidoc = revit.uidoc
    if uidoc is None:
        return None

    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class _AnyLinkedFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return elem and elem.Id == link_inst.Id
            except Exception:
                return False

        def AllowReference(self, reference, position):
            try:
                if reference is None:
                    return False
                if reference.ElementId != link_inst.Id:
                    return False
                if reference.LinkedElementId is None or reference.LinkedElementId == DB.ElementId.InvalidElementId:
                    return False
                return True
            except Exception:
                return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.LinkedElement, _AnyLinkedFilter(), prompt)
    except Exception:
        return None

    try:
        if r is None or r.ElementId != link_inst.Id:
            return None
    except Exception:
        return None

    ldoc = link_inst.GetLinkDocument()
    if ldoc is None:
        return None
    try:
        return ldoc.GetElement(r.LinkedElementId)
    except Exception:
        return None
