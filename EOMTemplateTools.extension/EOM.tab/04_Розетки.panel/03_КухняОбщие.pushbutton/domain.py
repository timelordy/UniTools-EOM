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


def project_t_on_segment(p, a, b):
    """Return parameter t (0..1) of point p projected onto segment a-b."""
    if p is None or a is None or b is None:
        return None
    try:
        ax, ay = float(a.X), float(a.Y)
        bx, by = float(b.X), float(b.Y)
        px, py = float(p.X), float(p.Y)
        vx, vy = (bx - ax), (by - ay)
        denom = (vx * vx + vy * vy)
        if denom <= 1e-12:
            return 0.0
        t = ((px - ax) * vx + (py - ay) * vy) / denom
        return t
    except Exception:
        return None


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
        segs.append((el, curve, curve.Length, p0, p1))

    return segs


def calculate_allowed_path(link_doc, room, avoid_door_ft, avoid_window_ft, openings_cache, unit_bboxes, unit_margin_ft):
    """Calculate allowed wall segments for socket placement, excluding doors, windows, and kitchen unit zones."""
    segs = get_wall_segments(room, link_doc)
    if not segs:
        return [], 0.0

    allowed_path = []
    effective_len_ft = 0.0

    for wall, curve, seg_len, p0, p1 in segs:
        if seg_len < 1e-9:
            continue

        ops = su._get_wall_openings_cached(link_doc, wall, openings_cache)

        blocked = []

        # Block windows
        for pt, w in ops.get('windows', []):
            half = (float(w) * 0.5) if w else mm_to_ft(600)
            d0 = su._project_dist_on_curve_xy_ft(curve, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                blocked.append((d0 - half - avoid_window_ft, d0 + half + avoid_window_ft))

        # Block doors
        for pt, w in ops.get('doors', []):
            half = (float(w) * 0.5) if w else mm_to_ft(450)
            d0 = su._project_dist_on_curve_xy_ft(curve, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                blocked.append((d0 - half - avoid_door_ft, d0 + half + avoid_door_ft))

        # Block kitchen unit zones (project bbox corners onto wall segment)
        for bbox in unit_bboxes:
            interval = _project_bbox_to_segment(bbox, p0, p1, seg_len, unit_margin_ft)
            if interval:
                blocked.append(interval)

        merged = su._merge_intervals(blocked, 0.0, seg_len)
        allowed = su._invert_intervals(merged, 0.0, seg_len)

        for a, b in allowed:
            if (b - a) > 1e-6:
                allowed_path.append((wall, curve, seg_len, a, b, p0, p1))
                effective_len_ft += (b - a)

    return allowed_path, effective_len_ft


def _project_bbox_to_segment(bbox, p0, p1, seg_len, margin_ft):
    """Project bounding box corners onto wall segment and return blocked interval."""
    if bbox is None or p0 is None or p1 is None:
        return None
    
    try:
        bmin, bmax = bbox
        corners = [
            DB.XYZ(bmin.X, bmin.Y, 0),
            DB.XYZ(bmax.X, bmin.Y, 0),
            DB.XYZ(bmax.X, bmax.Y, 0),
            DB.XYZ(bmin.X, bmax.Y, 0),
        ]
    except Exception:
        return None
    
    t_values = []
    for corner in corners:
        t = project_t_on_segment(corner, p0, p1)
        if t is not None:
            t_values.append(t)
    
    if not t_values:
        return None
    
    t_min = max(0.0, min(t_values))
    t_max = min(1.0, max(t_values))
    
    if t_max <= t_min:
        return None
    
    # Check if bbox is close enough to the wall (within ~1m)
    wall_dist_check = mm_to_ft(1000)
    seg_mid_t = (t_min + t_max) / 2.0
    seg_mid = DB.XYZ(
        p0.X + (p1.X - p0.X) * seg_mid_t,
        p0.Y + (p1.Y - p0.Y) * seg_mid_t,
        0
    )
    bbox_center = DB.XYZ((bmin.X + bmax.X) / 2, (bmin.Y + bmax.Y) / 2, 0)
    if dist_xy(seg_mid, bbox_center) > wall_dist_check + max(bmax.X - bmin.X, bmax.Y - bmin.Y) / 2:
        return None
    
    d_min = t_min * seg_len - margin_ft
    d_max = t_max * seg_len + margin_ft
    
    return (max(0.0, d_min), min(seg_len, d_max))


def generate_candidates(allowed_path, effective_len_ft, spacing_ft, wall_end_clear_ft):
    """Generate socket placement candidates every spacing_ft along allowed path."""
    candidates = []
    if effective_len_ft <= 1e-6 or spacing_ft <= 1e-6:
        return candidates

    try:
        num = int(math.floor(effective_len_ft / spacing_ft))
    except Exception:
        num = 0
    if num < 1:
        return candidates

    acc = 0.0
    path_idx = 0

    for k in range(1, num + 1):
        target_d = k * spacing_ft

        while path_idx < len(allowed_path):
            wall, curve, seg_len, a, b, p0, p1 = allowed_path[path_idx]
            seg_len_eff = b - a
            if target_d <= (acc + seg_len_eff):
                local_d = a + (target_d - acc)
                local_d = max(local_d, a + wall_end_clear_ft)
                local_d = min(local_d, b - wall_end_clear_ft)
                if local_d < a or local_d > b:
                    acc += seg_len_eff
                    path_idx += 1
                    continue
                pt = curve.Evaluate(local_d / seg_len, True)
                d = curve.ComputeDerivatives(local_d / seg_len, True)
                v = d.BasisX.Normalize()
                candidates.append((wall, pt, v))
                break
            else:
                acc += seg_len_eff
                path_idx += 1

    return candidates


def collect_kitchen_unit_bboxes(link_doc, room, patterns):
    """Collect bounding boxes of kitchen unit elements (Casework/Furniture) in the room.
    
    All Casework and Furniture in kitchen rooms are considered part of the unit.
    """
    bboxes = []
    if link_doc is None or room is None:
        return bboxes
    
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        pass
    
    if room_bb is None:
        return bboxes
    
    categories = [
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_Furniture,
    ]
    
    for bic in categories:
        try:
            col = (
                DB.FilteredElementCollector(link_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            continue
        
        for inst in col:
            if not _is_in_room_bbox(inst, room_bb):
                continue
            
            try:
                bb = inst.get_BoundingBox(None)
                if bb:
                    bboxes.append((bb.Min, bb.Max))
            except Exception:
                continue
    
    return bboxes


def _is_in_room_bbox(inst, room_bb):
    """Check if instance is within room bounding box (XY plane)."""
    if inst is None or room_bb is None:
        return False
    try:
        bb = inst.get_BoundingBox(None)
        if bb is None:
            return False
        tol = mm_to_ft(500)
        if bb.Max.X < room_bb.Min.X - tol or bb.Min.X > room_bb.Max.X + tol:
            return False
        if bb.Max.Y < room_bb.Min.Y - tol or bb.Min.Y > room_bb.Max.Y + tol:
            return False
        return True
    except Exception:
        return False
