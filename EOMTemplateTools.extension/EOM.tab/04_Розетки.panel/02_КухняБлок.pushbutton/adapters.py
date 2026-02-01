# -*- coding: utf-8 -*-

import config_loader
import link_reader
import placement_engine
import socket_utils as su
from pyrevit import DB, forms, revit
from pyrevit.framework import List


def get_rules():
    return config_loader.load_rules()


def get_config():
    from pyrevit import script
    return script.get_config()


def save_config():
    from pyrevit import script
    script.save_config()


def select_link_instance(doc, title):
    return su._select_link_instance_ru(doc, title)


def get_link_doc(link_inst):
    return link_reader.get_link_doc(link_inst)


def get_total_transform(link_inst):
    return link_reader.get_total_transform(link_inst)


def get_all_linked_rooms(link_doc, limit, level_ids=None):
    return su._get_all_linked_rooms(link_doc, limit=limit, level_ids=level_ids)


def collect_sinks_points(link_doc, rules):
    return su._collect_sinks_points(link_doc, rules)


def collect_stoves_points(link_doc, rules):
    return su._collect_stoves_points(link_doc, rules)


def collect_fridges_points(link_doc, rules):
    return su._collect_fridges_points(link_doc, rules)


def _try_get_room_at_point(doc_, pt):
    from utils_units import mm_to_ft
    if doc_ is None or pt is None:
        return None
    try:
        r = doc_.GetRoomAtPoint(pt)
        if r: return r
    except: pass
    for z in (0.0, mm_to_ft(1500), mm_to_ft(3000)):
        try:
            r = doc_.GetRoomAtPoint(DB.XYZ(float(pt.X), float(pt.Y), float(z)))
            if r: return r
        except: continue
    return None


def _get_wall_segments(room, link_doc):
    segs = []
    if room is None or link_doc is None:
        return segs
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglist = su._get_room_outer_boundary_segments(room, opts)
    except:
        seglist = None
    if not seglist:
        return segs

    for bs in seglist:
        try:
            curve = bs.GetCurve()
            if curve is None: continue
            eid = bs.ElementId
            if not eid or eid == DB.ElementId.InvalidElementId: continue
            el = link_doc.GetElement(eid)
            if el is None or (not isinstance(el, DB.Wall)): continue
            if su._is_curtain_wall(el): continue
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            segs.append((p0, p1, el))
        except: continue
    return segs


def _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None: return False
    try:
        x, y = float(pt.X), float(pt.Y)
        minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
        maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
        return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)
    except: return False


def _is_point_in_room(room, point):
    if room is None or point is None: return False
    try: return bool(room.IsPointInRoom(point))
    except: return False


def _points_in_room(points, room, padding_ft=2.0):
    from utils_units import mm_to_ft
    if not points or room is None: return []
    try: room_bb = room.get_BoundingBox(None)
    except: room_bb = None

    zmid = None
    try:
        if room_bb:
            zmid = (float(room_bb.Min.Z) + float(room_bb.Max.Z)) * 0.5
    except:
        zmid = None

    try:
        eps = float(mm_to_ft(50))
    except:
        eps = 0.0

    selected = []
    for pt in points:
        if pt is None: continue

        # XY prefilter (never an accept-condition)
        if room_bb:
            try:
                if not _bbox_contains_point_xy(pt, room_bb.Min, room_bb.Max, tol=padding_ft):
                    continue
            except:
                pass

        if _is_point_in_room(room, pt):
            selected.append(pt); continue

        # Z-normalized check (common when source points come from annotations/views)
        if zmid is not None:
            try:
                pt_zmid = DB.XYZ(float(pt.X), float(pt.Y), float(zmid))
            except:
                pt_zmid = None

            if pt_zmid and _is_point_in_room(room, pt_zmid):
                selected.append(pt); continue

            # Small XY probes at zmid for boundary/precision cases
            if eps and eps > 1e-9:
                for dx, dy in ((eps, 0.0), (-eps, 0.0), (0.0, eps), (0.0, -eps)):
                    try:
                        pp = DB.XYZ(float(pt.X) + float(dx), float(pt.Y) + float(dy), float(zmid))
                    except:
                        pp = None
                    if pp and _is_point_in_room(room, pp):
                        selected.append(pt)
                        break

    return selected


def _closest_point_on_segment_xy(p, a, b):
    if p is None or a is None or b is None: return None
    try:
        ax, ay = float(a.X), float(a.Y)
        bx, by = float(b.X), float(b.Y)
        px, py = float(p.X), float(p.Y)
        vx, vy = (bx - ax), (by - ay)
        denom = (vx * vx + vy * vy)
        if denom <= 1e-12: return DB.XYZ(ax, ay, float(p.Z) if hasattr(p, 'Z') else 0.0)
        t = ((px - ax) * vx + (py - ay) * vy) / denom
        t = max(0.0, min(1.0, t))
        return DB.XYZ(ax + vx * t, ay + vy * t, float(p.Z) if hasattr(p, 'Z') else 0.0)
    except: return None


def _dist_xy(a, b):
    try: return ((float(a.X) - float(b.X))**2 + (float(a.Y) - float(b.Y))**2)**0.5
    except: return 1e9


def _nearest_segment(pt, segs):
    best = None; best_proj = None; best_d = None
    for p0, p1, wall in segs or []:
        proj = _closest_point_on_segment_xy(pt, p0, p1)
        if proj is None: continue
        d = _dist_xy(pt, proj)
        if best_d is None or d < best_d:
            best = (p0, p1, wall); best_proj = proj; best_d = d
    return best, best_proj, best_d


def pick_socket_symbol(doc, cfg, prefer):
    return su._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_kitchen_unit')


def find_symbol_by_fullname(doc, name):
    return su._find_symbol_by_fullname(doc, name)


def format_family_type(sym):
    return placement_engine.format_family_type(sym)


def collect_host_socket_instances(host_doc):
    items = []
    if host_doc is None: return items
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        try:
            col = DB.FilteredElementCollector(host_doc).OfCategory(bic).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()
            for e in col:
                if not su._is_socket_instance(e): continue
                pt = su._inst_center_point(e)
                if pt: items.append((e, pt))
        except: continue
    return items


def pick_linked_element_any(link_inst, prompt):
    if link_inst is None: return None
    uidoc = revit.uidoc
    if uidoc is None: return None
    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
    class _AnyLinkedFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try: return elem and elem.Id == link_inst.Id
            except: return False
        def AllowReference(self, reference, position):
            try: return reference and reference.ElementId == link_inst.Id and reference.LinkedElementId != DB.ElementId.InvalidElementId
            except: return False
    try:
        r = uidoc.Selection.PickObject(ObjectType.LinkedElement, _AnyLinkedFilter(), prompt)
        if r: return link_inst.GetLinkDocument().GetElement(r.LinkedElementId)
    except: pass
    return None


def _collect_family_instance_points_by_symbol_id(link_doc, symbol_id_int):
    pts = []
    if link_doc is None or symbol_id_int is None: return pts
    try:
        col = DB.FilteredElementCollector(link_doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()
        for inst in col:
            try:
                if int(inst.Symbol.Id.IntegerValue) == int(symbol_id_int):
                    pt = su._inst_center_point(inst)
                    if pt: pts.append(pt)
            except: continue
    except: pass
    return pts


def select_levels(doc):
    # This is a dummy or needs proper implementation if orchestrator calls it
    # But user asked to remove level selection, so let's provide a safe empty implementation if still called.
    return []
