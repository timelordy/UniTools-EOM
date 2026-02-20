# -*- coding: utf-8 -*-

import math

from pyrevit import DB

from utils_units import mm_to_ft


def _closest_point_on_segment_xy(px, py, ax, ay, bx, by):
    try:
        abx = float(bx) - float(ax)
        aby = float(by) - float(ay)
        apx = float(px) - float(ax)
        apy = float(py) - float(ay)
        denom = abx * abx + aby * aby
        if denom <= 1e-12:
            return float(ax), float(ay), 0.0
        t = (apx * abx + apy * aby) / denom
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        qx = float(ax) + abx * t
        qy = float(ay) + aby * t
        return qx, qy, float(t)
    except Exception:
        return float(ax), float(ay), 0.0


def _get_room_boundary_segments(room):
    if room is None:
        return []
    try:
        opts = DB.SpatialElementBoundaryOptions()
        try:
            opts.SpatialElementBoundaryLocation = DB.SpatialElementBoundaryLocation.Finish
        except Exception:
            pass
        seglists = room.GetBoundarySegments(opts)
    except Exception:
        seglists = None
    if not seglists:
        return []

    segs = []
    for seglist in seglists:
        if not seglist:
            continue
        for seg in seglist:
            try:
                crv = seg.GetCurve()
            except Exception:
                crv = None
            if crv is None:
                continue
            try:
                p0 = crv.GetEndPoint(0)
                p1 = crv.GetEndPoint(1)
            except Exception:
                continue
            if p0 is None or p1 is None:
                continue
            try:
                eid = seg.ElementId
            except Exception:
                eid = None
            segs.append((p0, p1, eid))
    return segs


def project_point_to_room_boundary(room, point_link):
    """Project point (link coords) to closest room boundary segment (XY).

    Returns dict: {point, tangent, element_id, t} or None.
    """
    if room is None or point_link is None:
        return None

    segs = _get_room_boundary_segments(room)
    if not segs:
        return None

    best = None
    best_d2 = None

    px = float(point_link.X)
    py = float(point_link.Y)
    pz = float(point_link.Z)

    for p0, p1, eid in segs:
        ax = float(p0.X)
        ay = float(p0.Y)
        bx = float(p1.X)
        by = float(p1.Y)
        qx, qy, t = _closest_point_on_segment_xy(px, py, ax, ay, bx, by)
        dx = qx - px
        dy = qy - py
        d2 = dx * dx + dy * dy
        if best_d2 is None or d2 < best_d2:
            tx = float(bx) - float(ax)
            ty = float(by) - float(ay)
            ln = (tx * tx + ty * ty) ** 0.5
            if ln > 1e-9:
                tx /= ln
                ty /= ln
            best_d2 = d2
            best = {
                'point': DB.XYZ(float(qx), float(qy), float(pz)),
                'tangent': DB.XYZ(float(tx), float(ty), 0.0),
                'element_id': eid,
                't': float(t),
            }

    return best


def pick_interior_normal_for_room(room, boundary_point_link, tangent_link, inset_ft):
    """Return unit normal pointing inside room, based on IsPointInRoom."""
    if room is None or boundary_point_link is None or tangent_link is None:
        return None

    eps = float(inset_ft or 0.0)
    if eps <= 0.0:
        eps = float(mm_to_ft(5) or 0.0)

    try:
        tx = float(tangent_link.X)
        ty = float(tangent_link.Y)
        n1 = DB.XYZ(-ty, tx, 0.0)
        n2 = DB.XYZ(ty, -tx, 0.0)
    except Exception:
        return None

    for n in (n1, n2):
        try:
            test = DB.XYZ(
                float(boundary_point_link.X) + float(n.X) * eps,
                float(boundary_point_link.Y) + float(n.Y) * eps,
                float(boundary_point_link.Z)
            )
            if hasattr(room, 'IsPointInRoom') and room.IsPointInRoom(test):
                return n.Normalize() if n.GetLength() > 1e-9 else n
        except Exception:
            continue

    try:
        return n1.Normalize() if n1.GetLength() > 1e-9 else n1
    except Exception:
        return None


def _xy_unit(vec):
    if vec is None:
        return None
    try:
        v = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
        if v.GetLength() <= 1e-9:
            return None
        return v.Normalize()
    except Exception:
        return None


def get_instance_primary_dir_xy(inst, prefer_hand=True):
    if inst is None:
        return None
    candidates = []
    if prefer_hand:
        try:
            candidates.append(getattr(inst, 'HandOrientation', None))
        except Exception:
            pass
    try:
        candidates.append(getattr(inst, 'FacingOrientation', None))
    except Exception:
        pass
    for v in candidates:
        u = _xy_unit(v)
        if u is not None:
            return u
    return None


def rotate_instance_to_direction_xy(doc, inst, target_dir_host):
    """Rotate instance around Z so that its main axis is parallel to target.

    IMPORTANT: We test both axis variants (base and base rotated 90deg) and
    choose the smallest rotation, because different families expose either
    FacingOrientation or HandOrientation as the "parallel" axis.
    """
    if doc is None or inst is None or target_dir_host is None:
        return False

    target = _xy_unit(target_dir_host)
    if target is None:
        return False

    try:
        loc = inst.Location
        origin = loc.Point
    except Exception:
        return False

    # Strict policy: align by HandOrientation first (panel long axis in our family),
    # fallback to FacingOrientation only if Hand is unavailable.
    base = None
    try:
        base = _xy_unit(getattr(inst, 'HandOrientation', None))
    except Exception:
        base = None
    if base is None:
        base = _xy_unit(getattr(inst, 'FacingOrientation', None))
    if base is None:
        return False

    dot = max(-1.0, min(1.0, float(base.DotProduct(target))))
    best_ang = math.acos(dot)
    cross_z = float(base.X) * float(target.Y) - float(base.Y) * float(target.X)
    if cross_z < 0.0:
        best_ang = -best_ang

    if best_ang is None or abs(best_ang) < 1e-4:
        return True

    try:
        axis = DB.Line.CreateBound(origin, DB.XYZ(float(origin.X), float(origin.Y), float(origin.Z) + 10.0))
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, float(best_ang))
        return True
    except Exception:
        return False


def wall_half_width(wall):
    try:
        return max(0.0, float(getattr(wall, 'Width', 0.0) or 0.0) * 0.5)
    except Exception:
        return 0.0


def wall_normal_towards_point(wall, point_host, target_point_host, link_transform=None):
    if wall is None or point_host is None:
        return None

    try:
        curve = wall.Location.Curve
    except Exception:
        return None
    if curve is None:
        return None

    try:
        if link_transform is not None:
            inv = link_transform.Inverse
            point_local = inv.OfPoint(point_host)
            proj_local = curve.Project(point_local)
            if proj_local is None:
                return None
            deriv_local = curve.ComputeDerivatives(proj_local.Parameter, True)
            tangent_local = deriv_local.BasisX
            tangent_host = link_transform.OfVector(tangent_local)
        else:
            proj_host = curve.Project(point_host)
            if proj_host is None:
                return None
            deriv_host = curve.ComputeDerivatives(proj_host.Parameter, True)
            tangent_host = deriv_host.BasisX
    except Exception:
        return None

    tangent_xy = _xy_unit(tangent_host)
    if tangent_xy is None:
        return None

    n1 = DB.XYZ(-float(tangent_xy.Y), float(tangent_xy.X), 0.0)
    n2 = DB.XYZ(float(tangent_xy.Y), -float(tangent_xy.X), 0.0)

    try:
        if target_point_host is not None:
            to_target = DB.XYZ(
                float(target_point_host.X) - float(point_host.X),
                float(target_point_host.Y) - float(point_host.Y),
                0.0
            )
            if to_target.GetLength() > 1e-9:
                if float(n1.DotProduct(to_target)) >= float(n2.DotProduct(to_target)):
                    return n1
                return n2
    except Exception:
        pass

    return n1


def outside_point_from_wall(base_point, wall, target_point_host, wall_offset_ft, link_transform=None):
    if base_point is None or wall is None:
        return base_point, 0.0, False

    normal = wall_normal_towards_point(wall, base_point, target_point_host, link_transform=link_transform)
    if normal is None:
        return base_point, 0.0, False

    shift = float(wall_half_width(wall)) + max(0.0, float(wall_offset_ft or 0.0))
    shifted = DB.XYZ(
        float(base_point.X) + float(normal.X) * shift,
        float(base_point.Y) + float(normal.Y) * shift,
        float(base_point.Z)
    )
    return shifted, shift, True


def align_instance_outer_face_to_boundary(inst, boundary_point_host, inward_normal_host, target_offset_ft=0.0):
    if inst is None or boundary_point_host is None or inward_normal_host is None:
        return 0.0, False

    n = _xy_unit(inward_normal_host)
    if n is None:
        return 0.0, False

    try:
        bbox = inst.get_BoundingBox(None)
    except Exception:
        bbox = None
    if bbox is None:
        return 0.0, False

    # Use transformed bbox corners, otherwise rotated instances may compute wrong plane distance.
    pts = _bbox_corners(bbox)
    if not pts:
        return 0.0, False

    min_d = None
    bx = float(boundary_point_host.X)
    by = float(boundary_point_host.Y)
    nzx = float(n.X)
    nzy = float(n.Y)

    for p in pts:
        try:
            d = (float(p.X) - bx) * nzx + (float(p.Y) - by) * nzy
            if min_d is None or d < min_d:
                min_d = d
        except Exception:
            continue

    if min_d is None:
        return 0.0, False

    shift = float(target_offset_ft or 0.0) - float(min_d)
    if abs(shift) < 1e-5:
        return 0.0, True

    try:
        loc = inst.Location
        pt = loc.Point
        if pt is None:
            return 0.0, False
        loc.Point = DB.XYZ(
            float(pt.X) + nzx * shift,
            float(pt.Y) + nzy * shift,
            float(pt.Z)
        )
        return float(shift), True
    except Exception:
        return 0.0, False


def _bbox_corners(bbox):
    if bbox is None:
        return []
    try:
        tr = getattr(bbox, 'Transform', None)
    except Exception:
        tr = None
    try:
        xs = [float(bbox.Min.X), float(bbox.Max.X)]
        ys = [float(bbox.Min.Y), float(bbox.Max.Y)]
        zs = [float(bbox.Min.Z), float(bbox.Max.Z)]
    except Exception:
        return []
    pts = []
    for x in xs:
        for y in ys:
            for z in zs:
                p = DB.XYZ(float(x), float(y), float(z))
                try:
                    if tr is not None:
                        p = tr.OfPoint(p)
                except Exception:
                    pass
                pts.append(p)
    return pts


def _max_proj_along_dir(points, origin, dir_unit):
    if not points or origin is None or dir_unit is None:
        return None
    best = None
    ox = float(origin.X)
    oy = float(origin.Y)
    oz = float(origin.Z)
    dx = float(dir_unit.X)
    dy = float(dir_unit.Y)
    dz = float(dir_unit.Z)
    for p in points:
        try:
            v = DB.XYZ(float(p.X) - ox, float(p.Y) - oy, float(p.Z) - oz)
            s = float(v.X) * dx + float(v.Y) * dy + float(v.Z) * dz
            if best is None or s > best:
                best = s
        except Exception:
            continue
    return best


def _min_proj_along_dir(points, origin, dir_unit):
    if not points or origin is None or dir_unit is None:
        return None
    best = None
    ox = float(origin.X)
    oy = float(origin.Y)
    oz = float(origin.Z)
    dx = float(dir_unit.X)
    dy = float(dir_unit.Y)
    dz = float(dir_unit.Z)
    for p in points:
        try:
            v = DB.XYZ(float(p.X) - ox, float(p.Y) - oy, float(p.Z) - oz)
            s = float(v.X) * dx + float(v.Y) * dy + float(v.Z) * dz
            if best is None or s < best:
                best = s
        except Exception:
            continue
    return best


def align_instance_right_face_to_opening(inst,
                                        opening_elem_link,
                                        link_transform,
                                        tangent_host,
                                        debug_output=None,
                                        align_mode='max',
                                        nudge_mm=0,
                                        clamp_mm=600):
    if inst is None or opening_elem_link is None or link_transform is None or tangent_host is None:
        return 0.0, False

    t_host = _xy_unit(tangent_host)
    if t_host is None:
        return 0.0, False

    # NOTE: Do not canonicalize tangent direction here.
    # "Right" depends on corridor interior orientation; caller must pass
    # the tangent direction corresponding to desired right edge alignment.

    try:
        bb_open = opening_elem_link.get_BoundingBox(None)
    except Exception:
        bb_open = None
    if bb_open is None:
        return 0.0, False

    try:
        open_pts_host = []
        for p_link in _bbox_corners(bb_open):
            try:
                open_pts_host.append(link_transform.OfPoint(p_link))
            except Exception:
                continue
        origin = DB.XYZ(0.0, 0.0, 0.0)
        open_max = _max_proj_along_dir(open_pts_host, origin, t_host)
        open_min = _min_proj_along_dir(open_pts_host, origin, t_host)
    except Exception:
        open_max = None
        open_min = None
    if open_max is None or open_min is None:
        return 0.0, False

    try:
        bb_panel = inst.get_BoundingBox(None)
    except Exception:
        bb_panel = None
    if bb_panel is None:
        return 0.0, False

    try:
        panel_pts = _bbox_corners(bb_panel)
        origin = DB.XYZ(0.0, 0.0, 0.0)
        panel_max = _max_proj_along_dir(panel_pts, origin, t_host)
        panel_min = _min_proj_along_dir(panel_pts, origin, t_host)
    except Exception:
        panel_max = None
        panel_min = None
    if panel_max is None or panel_min is None:
        return 0.0, False

    delta_max = float(open_max) - float(panel_max)
    delta_min = float(open_min) - float(panel_min)

    # Choose alignment strategy.
    mode = str(align_mode or 'max').strip().lower()
    if mode in ('min', 'left'):
        delta = delta_min
        mode = 'min'
    elif mode in ('auto', 'nearest'):
        delta = delta_max
        mode = 'max'
        if abs(delta_min) < abs(delta_max):
            delta = delta_min
            mode = 'min'
    else:
        delta = delta_max
        mode = 'max'

    # Optional small correction (positive = move towards "right" / +tangent).
    try:
        delta += float(mm_to_ft(int(nudge_mm or 0)) or 0.0)
    except Exception:
        pass

    if abs(delta) < 1e-5:
        return 0.0, True

    try:
        clamp_ft = float(mm_to_ft(int(clamp_mm or 0)) or 0.0)
    except Exception:
        clamp_ft = float(mm_to_ft(600) or 0.0)

    if clamp_ft > 1e-9 and abs(delta) > clamp_ft:
        if debug_output is not None:
            try:
                debug_output.print_md(u'DEBUG: edge-align skipped (delta={:.0f} mm > clamp={} mm)'.format(
                    delta * 304.8,
                    int(clamp_mm or 0)
                ))
            except Exception:
                pass
        return 0.0, False

    try:
        loc = inst.Location
        pt = loc.Point
        loc.Point = DB.XYZ(
            float(pt.X) + float(t_host.X) * delta,
            float(pt.Y) + float(t_host.Y) * delta,
            float(pt.Z)
        )
        if debug_output is not None:
            try:
                debug_output.print_md(u'DEBUG: edge-align({}) delta = {:.1f} mm'.format(mode, delta * 304.8))
            except Exception:
                pass
        return float(delta), True
    except Exception:
        return 0.0, False
