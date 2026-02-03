# -*- coding: utf-8 -*-

import math
from pyrevit import DB
from utils_units import mm_to_ft
import socket_utils as su


def norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def dist_xy(a, b):
    try:
        return ((float(a.X) - float(b.X)) ** 2 + (float(a.Y) - float(b.Y)) ** 2) ** 0.5
    except Exception:
        return 1e9


def closest_point_on_segment_xy(p, a, b):
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


def bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    try:
        x, y = float(pt.X), float(pt.Y)
        minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
        maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
        return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)
    except Exception:
        return False


def is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        return bool(room.IsPointInRoom(point))
    except Exception:
        return False


def points_in_room(points, room, padding_ft=2.0):
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
                if not bbox_contains_point_xy(pt, min_exp, max_exp):
                    continue
            except Exception:
                pass

        if is_point_in_room(room, pt):
            selected.append(pt)
            continue

        pt_room = None
        if zmid is not None:
            try:
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), float(zmid))
            except Exception:
                pt_room = None

        if pt_room and is_point_in_room(room, pt_room):
            selected.append(pt)
            continue

        # Boundary-adjacent tolerance: probe inward towards room bbox center
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
                        if is_point_in_room(room, probe):
                            selected.append(pt)
                            break
        except Exception:
            pass

    return selected


def try_get_room_at_point(doc_, pt):
    if doc_ is None or pt is None:
        return None
    # Try as-is first
    try:
        r = doc_.GetRoomAtPoint(pt)
        if r is not None:
            return r
    except Exception:
        pass
    # Fallbacks: same XY, typical Z probes
    for z in (0.0, mm_to_ft(1500), mm_to_ft(3000)):
        try:
            r = doc_.GetRoomAtPoint(DB.XYZ(float(pt.X), float(pt.Y), float(z)))
            if r is not None:
                return r
        except Exception:
            continue
    return None


def nearest_segment(pt, segs):
    best = None
    best_proj = None
    best_d = None
    for p0, p1, wall in segs or []:
        proj = closest_point_on_segment_xy(pt, p0, p1)
        if proj is None:
            continue
        d = dist_xy(pt, proj)
        if best_d is None or d < best_d:
            best = (p0, p1, wall)
            best_proj = proj
            best_d = d
    return best, best_proj, best_d


def get_wall_segments(room, link_doc):
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


def collect_tagged_instances(host_doc, tag_value):
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
                c = su._get_comments_text(e)
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
