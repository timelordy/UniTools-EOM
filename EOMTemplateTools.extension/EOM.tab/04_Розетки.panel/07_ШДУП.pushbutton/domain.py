# -*- coding: utf-8 -*-

from pyrevit import DB
import socket_utils as su
import constants
from utils_units import mm_to_ft


def xy0(p):
    try:
        return DB.XYZ(float(p.X), float(p.Y), 0.0)
    except Exception:
        return None


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


def validate_between_sink_tub(seg_p0, seg_p1, sink_pt, tub_pt, inst_pt_link, dist_wall_ft, between_pad_mm=100):
    """
    Validate ШДУП placement. Supports three modes:
    1. Both sink and tub - validates between them
    2. Only sink - validates near sink
    3. Only tub - validates near tub
    """
    p0 = xy0(seg_p0)
    p1 = xy0(seg_p1)
    s = xy0(sink_pt) if sink_pt else None
    b = xy0(tub_pt) if tub_pt else None
    i = xy0(inst_pt_link)

    # Must have segment and instance point
    if not all([p0, p1, i]):
        return False, False, None, None, None, None

    # Must have at least one fixture
    if not s and not b:
        return False, False, None, None, None, None

    pi = closest_point_on_segment_xy(i, p0, p1)
    if pi is None:
        return False, False, None, None, None, None

    try:
        seg_len = p0.DistanceTo(p1)
    except Exception:
        seg_len = 0.0
    if seg_len <= 1e-6:
        return False, False, None, None, None, None

    try:
        dist_to_wall = dist_xy(i, pi)
    except Exception:
        dist_to_wall = None
    on_wall_ok = (dist_to_wall is not None) and (dist_to_wall <= float(dist_wall_ft or mm_to_ft(150)))

    try:
        ti = p0.DistanceTo(pi) / seg_len
    except Exception:
        return on_wall_ok, False, dist_to_wall, None, None, None

    # Case 1: Both fixtures exist - validate between them
    if s and b:
        ps = closest_point_on_segment_xy(s, p0, p1)
        pb = closest_point_on_segment_xy(b, p0, p1)
        if ps is None or pb is None:
            return on_wall_ok, False, dist_to_wall, None, None, None

        try:
            ts = p0.DistanceTo(ps) / seg_len
            tb = p0.DistanceTo(pb) / seg_len
        except Exception:
            return on_wall_ok, False, dist_to_wall, None, None, None

        lo = min(ts, tb)
        hi = max(ts, tb)
        try:
            pad_ft = mm_to_ft(int(between_pad_mm or 100))
        except Exception:
            pad_ft = mm_to_ft(100)
        tol = float(pad_ft) / float(seg_len) if seg_len > 1e-6 else 0.0
        between_ok = (ti >= (lo - tol)) and (ti <= (hi + tol))
        return on_wall_ok, between_ok, dist_to_wall, ts, tb, ti

    # Case 2: Only one fixture - just validate on wall (between_ok = True if on wall)
    else:
        # For single fixture, we don't have "between" constraint, so it's OK if on wall
        ts = None
        tb = None
        if s:
            ps = closest_point_on_segment_xy(s, p0, p1)
            if ps:
                try:
                    ts = p0.DistanceTo(ps) / seg_len
                except: pass
        if b:
            pb = closest_point_on_segment_xy(b, p0, p1)
            if pb:
                try:
                    tb = p0.DistanceTo(pb) / seg_len
                except: pass

        # For single fixture, "between_ok" just means "on the same wall"
        between_ok = on_wall_ok
        return on_wall_ok, between_ok, dist_to_wall, ts, tb, ti


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
        try:
            if su._is_curtain_wall(el):
                continue
        except Exception:
            pass
        try:
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            if p0.DistanceTo(p1) <= 1e-6:
                continue
            segs.append((p0, p1, el))
        except Exception:
            continue
    return segs


def nearest_segment(pt, segments):
    best = None
    best_proj = None
    best_d = None
    for p0, p1, w in segments or []:
        proj = closest_point_on_segment_xy(pt, p0, p1)
        if proj is None:
            continue
        d = dist_xy(pt, proj)
        if best is None or d < best_d:
            best = (p0, p1, w)
            best_proj = proj
            best_d = d
    return best, best_proj, best_d


def points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []
    
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
        
    selected = []
    for pt in points:
        if pt is None:
            continue
            
        # Z adjust
        pt_room = pt
        try:
            if room_bb:
                zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), zmid)
        except Exception:
            pt_room = pt
            
        try:
            if room_bb:
                if not (room_bb.Min.X - padding_ft <= pt.X <= room_bb.Max.X + padding_ft and
                        room_bb.Min.Y - padding_ft <= pt.Y <= room_bb.Max.Y + padding_ft):
                    continue
        except Exception: pass
        
        try:
            if room.IsPointInRoom(pt_room):
                selected.append(pt)
        except: pass
        
    return selected
