# -*- coding: utf-8 -*-

import System
import math
from pyrevit import DB
from utils_revit import alert, set_comments, tx, find_nearest_level, trace
from utils_units import mm_to_ft
import link_reader
import adapters
import domain
try:
    import socket_utils as su
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su

from domain import (
    is_excluded_room,
    is_bathroom,
    is_toilet,
    is_apartment_room,
    room_name_matches,
    find_best_door_for_room,
    get_room_centers_multi,
    filter_duplicate_rooms,
    is_too_close
)


def _project_point_to_curve_xy(curve, point_xyz):
    if curve is None or point_xyz is None:
        return None, None
    try:
        base_z = float(curve.GetEndPoint(0).Z)
        p2 = DB.XYZ(float(point_xyz.X), float(point_xyz.Y), base_z)
        ir = curve.Project(p2)
        if not ir:
            return None, None
        proj = ir.XYZPoint
        d = float(ir.Distance)
        return proj, d
    except Exception:
        return None, None


def _find_nearest_wall_in_doc(doc, point_xyz, max_dist_ft):
    if doc is None or point_xyz is None:
        return None, None

    best_wall = None
    best_proj = None
    best_d = None
    try:
        walls = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None

    for wall in walls:
        try:
            try:
                bb = wall.get_BoundingBox(None)
            except Exception:
                bb = None
            if bb is not None:
                z_min = float(min(bb.Min.Z, bb.Max.Z)) - 4.0
                z_max = float(max(bb.Min.Z, bb.Max.Z)) + 4.0
                if float(point_xyz.Z) < z_min or float(point_xyz.Z) > z_max:
                    continue

            loc = getattr(wall, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue
            proj, d = _project_point_to_curve_xy(curve, point_xyz)
            if proj is None or d is None:
                continue
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            if best_wall is None or d < best_d:
                best_wall = wall
                best_proj = proj
                best_d = d
        except Exception:
            continue

    return best_wall, best_proj


def _find_nearest_wall_in_link(link_doc, point_link, max_dist_ft):
    if link_doc is None or point_link is None:
        return None, None

    best_wall = None
    best_proj = None
    best_d = None
    try:
        walls = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None

    for wall in walls:
        try:
            try:
                bb = wall.get_BoundingBox(None)
            except Exception:
                bb = None
            if bb is not None:
                z_min = float(min(bb.Min.Z, bb.Max.Z)) - 4.0
                z_max = float(max(bb.Min.Z, bb.Max.Z)) + 4.0
                if float(point_link.Z) < z_min or float(point_link.Z) > z_max:
                    continue

            loc = getattr(wall, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue
            proj, d = _project_point_to_curve_xy(curve, point_link)
            if proj is None or d is None:
                continue
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            if best_wall is None or d < best_d:
                best_wall = wall
                best_proj = proj
                best_d = d
        except Exception:
            continue

    return best_wall, best_proj


def _build_link_ref_direction(link_transform, link_wall, face_n_link):
    try:
        wall_dir_link = link_wall.Location.Curve.Direction
    except Exception:
        wall_dir_link = None

    try:
        dir_host = link_transform.OfVector(wall_dir_link) if wall_dir_link else DB.XYZ.BasisX
    except Exception:
        dir_host = DB.XYZ.BasisX

    if face_n_link is not None:
        try:
            n_host = link_transform.OfVector(face_n_link)
            if n_host and n_host.GetLength() > 1e-9 and dir_host and dir_host.GetLength() > 1e-9:
                n = n_host.Normalize()
                comp = n.Multiply(dir_host.DotProduct(n))
                dir_host = dir_host - comp
        except Exception:
            pass

    try:
        if dir_host is None or dir_host.GetLength() <= 1e-9:
            return DB.XYZ.BasisX
        return dir_host.Normalize()
    except Exception:
        return DB.XYZ.BasisX


def _get_host_wall_face_ref(host_wall, point_host):
    if host_wall is None or point_host is None:
        return None
    refs = []
    try:
        refs += list(DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Interior))
    except Exception:
        pass
    try:
        refs += list(DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Exterior))
    except Exception:
        pass

    best_ref = None
    best_d = None
    for ref in refs:
        try:
            face = host_wall.GetGeometryObjectFromReference(ref)
            if face is None:
                continue
            ir = face.Project(point_host)
            if not ir:
                continue
            d = float(ir.Distance)
            if best_ref is None or d < best_d:
                best_ref = ref
                best_d = d
        except Exception:
            continue
    return best_ref


def _prepare_wall_placement(doc, link_doc, link_inst, link_transform, p_link, insert_point, wall_search_ft):
    """Return (mode, point, payload) for wall-hosted placement."""
    candidate_point = insert_point

    wall_link, proj_link = _find_nearest_wall_in_link(link_doc, p_link, wall_search_ft)
    if wall_link is not None and link_inst is not None:
        link_ref = None
        face_n_link = None
        try:
            link_ref, proj_face_link, face_n_link = su._get_linked_wall_face_ref_and_point(
                wall_link, link_inst, (proj_link or p_link)
            )
        except Exception:
            link_ref, proj_face_link, face_n_link = None, None, None

        if proj_face_link is not None:
            try:
                p_host = link_transform.OfPoint(proj_face_link)
                candidate_point = DB.XYZ(float(p_host.X), float(p_host.Y), float(insert_point.Z))
            except Exception:
                pass

        if link_ref is not None:
            direction = _build_link_ref_direction(link_transform, wall_link, face_n_link)
            return 'linked_ref', candidate_point, {'reference': link_ref, 'direction': direction}

    host_wall, host_proj = _find_nearest_wall_in_doc(doc, candidate_point, wall_search_ft)
    if host_wall is not None:
        if host_proj is not None:
            candidate_point = DB.XYZ(float(host_proj.X), float(host_proj.Y), float(insert_point.Z))
        return 'host_wall', candidate_point, {'wall': host_wall}

    return None, candidate_point, None


def _create_wall_hosted_instance(doc, symbol, host_level, mode, point, payload):
    if doc is None or symbol is None or mode is None or point is None:
        return None

    if mode == 'linked_ref':
        link_ref = payload.get('reference') if isinstance(payload, dict) else None
        direction = payload.get('direction') if isinstance(payload, dict) else None
        if link_ref is None:
            return None
        try:
            return doc.Create.NewFamilyInstance(link_ref, point, direction or DB.XYZ.BasisX, symbol)
        except Exception:
            try:
                return doc.Create.NewFamilyInstance(link_ref, point, symbol)
            except Exception:
                return None

    if mode == 'host_wall':
        wall = payload.get('wall') if isinstance(payload, dict) else None
        if wall is None:
            return None

        try:
            return doc.Create.NewFamilyInstance(point, symbol, wall, host_level, DB.Structure.StructuralType.NonStructural)
        except Exception:
            pass

        face_ref = _get_host_wall_face_ref(wall, point)
        if face_ref is not None:
            try:
                return doc.Create.NewFamilyInstance(face_ref, point, DB.XYZ.BasisZ, symbol)
            except Exception:
                try:
                    return doc.Create.NewFamilyInstance(face_ref, point, symbol)
                except Exception:
                    return None
    return None


def _curve_direction_xy(curve, near_pt=None):
    if curve is None:
        return None
    try:
        if hasattr(curve, 'Direction'):
            d = curve.Direction
            vx = float(d.X)
            vy = float(d.Y)
            ln = (vx * vx + vy * vy) ** 0.5
            if ln > 1e-9:
                return DB.XYZ(vx / ln, vy / ln, 0.0)
    except Exception:
        pass
    try:
        if near_pt is not None:
            ir = curve.Project(near_pt)
            if ir:
                deriv = curve.ComputeDerivatives(ir.Parameter, True)
                d = deriv.BasisX
                vx = float(d.X)
                vy = float(d.Y)
                ln = (vx * vx + vy * vy) ** 0.5
                if ln > 1e-9:
                    return DB.XYZ(vx / ln, vy / ln, 0.0)
    except Exception:
        pass
    return None


def _curve_tangent_xy_at_point(curve, near_pt=None):
    if curve is None:
        return None
    try:
        if near_pt is not None:
            ir = curve.Project(near_pt)
            if ir:
                deriv = curve.ComputeDerivatives(ir.Parameter, True)
                d = deriv.BasisX
                vx = float(d.X)
                vy = float(d.Y)
                ln = (vx * vx + vy * vy) ** 0.5
                if ln > 1e-9:
                    return DB.XYZ(vx / ln, vy / ln, 0.0)
    except Exception:
        pass
    return _curve_direction_xy(curve, near_pt)


def _find_room_boundary_point_near_anchor(room, anchor_link_pt):
    """Return boundary point/tangent nearest to anchor in link coordinates."""
    if room is None or anchor_link_pt is None:
        return None, None
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglists = room.GetBoundarySegments(opts)
    except Exception:
        seglists = None
    if not seglists:
        return None, None

    best_pt = None
    best_tg = None
    best_d = None
    for segs in seglists:
        if not segs:
            continue
        for seg in segs:
            try:
                curve = seg.GetCurve()
            except Exception:
                curve = None
            if curve is None:
                continue
            try:
                base_z = float(curve.GetEndPoint(0).Z)
                p2 = DB.XYZ(float(anchor_link_pt.X), float(anchor_link_pt.Y), base_z)
                ir = curve.Project(p2)
            except Exception:
                ir = None
            if not ir:
                continue
            try:
                proj = ir.XYZPoint
                d = float(ir.Distance)
            except Exception:
                continue
            if best_pt is None or d < best_d:
                best_pt = proj
                best_d = d
                try:
                    best_tg = _curve_tangent_xy_at_point(curve, proj)
                except Exception:
                    best_tg = None

    return best_pt, best_tg


def _xy_dist2(p1, p2):
    try:
        dx = float(p1.X) - float(p2.X)
        dy = float(p1.Y) - float(p2.Y)
        return dx * dx + dy * dy
    except Exception:
        return 0.0


def _xy_unit(v):
    if v is None:
        return None
    try:
        x = float(v.X)
        y = float(v.Y)
        ln = (x * x + y * y) ** 0.5
        if ln <= 1e-9:
            return None
        return DB.XYZ(x / ln, y / ln, 0.0)
    except Exception:
        return None


def _xy_rotate(v, angle_rad):
    u = _xy_unit(v)
    if u is None:
        return None
    try:
        c = math.cos(float(angle_rad))
        s = math.sin(float(angle_rad))
        x = float(u.X) * c - float(u.Y) * s
        y = float(u.X) * s + float(u.Y) * c
        return _xy_unit(DB.XYZ(x, y, 0.0))
    except Exception:
        return None


def _xyz_unit(v):
    if v is None:
        return None
    try:
        ln = float(v.GetLength())
        if ln <= 1e-9:
            return None
        return v.Normalize()
    except Exception:
        return None


def _xy_dir_points(p_from, p_to):
    if p_from is None or p_to is None:
        return None
    try:
        return _xy_unit(DB.XYZ(float(p_to.X) - float(p_from.X), float(p_to.Y) - float(p_from.Y), 0.0))
    except Exception:
        return None


def _xy_neg(v):
    u = _xy_unit(v)
    if u is None:
        return None
    try:
        return DB.XYZ(-float(u.X), -float(u.Y), 0.0)
    except Exception:
        return None


def _xy_perp_left(v):
    u = _xy_unit(v)
    if u is None:
        return None
    try:
        return DB.XYZ(-float(u.Y), float(u.X), 0.0)
    except Exception:
        return None


def _room_contains_point(room, point_xyz):
    if room is None or point_xyz is None:
        return False
    try:
        return bool(room.IsPointInRoom(point_xyz))
    except Exception:
        return False


def _signed_angle_xy(v_from, v_to):
    a = _xy_unit(v_from)
    b = _xy_unit(v_to)
    if a is None or b is None:
        return None
    try:
        cross_z = float(a.X) * float(b.Y) - float(a.Y) * float(b.X)
        dot = float(a.X) * float(b.X) + float(a.Y) * float(b.Y)
        dot = max(-1.0, min(1.0, dot))
        return math.atan2(cross_z, dot)
    except Exception:
        return None


def _instance_forward_xy(inst):
    if inst is None:
        return None
    try:
        v = _xy_unit(getattr(inst, 'FacingOrientation', None))
        if v is not None:
            return v
    except Exception:
        pass
    try:
        v = _xy_unit(getattr(inst, 'HandOrientation', None))
        if v is not None:
            return v
    except Exception:
        pass
    try:
        tr = inst.GetTransform()
        if tr is not None:
            v = _xy_unit(getattr(tr, 'BasisX', None))
            if v is not None:
                return v
    except Exception:
        pass
    return None


def _rotate_instance_xy_towards(doc, inst, target_xy):
    """Rotate instance in plan so its forward vector looks to target_xy."""
    if doc is None or inst is None:
        return False
    desired = _xy_unit(target_xy)
    if desired is None:
        return False
    current = _instance_forward_xy(inst)
    if current is None:
        return False

    ang = _signed_angle_xy(current, desired)
    if ang is None or abs(float(ang)) < 1e-5:
        return True

    pivot = None
    try:
        loc = getattr(inst, 'Location', None)
        if isinstance(loc, DB.LocationPoint):
            pivot = loc.Point
    except Exception:
        pivot = None
    if pivot is None:
        try:
            pivot = inst.GetTransform().Origin
        except Exception:
            pivot = None
    if pivot is None:
        return False

    try:
        axis = DB.Line.CreateBound(
            pivot,
            DB.XYZ(float(pivot.X), float(pivot.Y), float(pivot.Z) + 1.0),
        )
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, float(ang))
        return True
    except Exception:
        return False


def _safe_rotate_instance_xy_towards(doc, inst, target_xy):
    if doc is None or inst is None or target_xy is None:
        return False
    st = None
    try:
        st = DB.SubTransaction(doc)
        st.Start()
        ok = _rotate_instance_xy_towards(doc, inst, target_xy)
        if ok:
            st.Commit()
            return True
        try:
            st.RollBack()
        except Exception:
            pass
        return False
    except Exception:
        if st is not None:
            try:
                st.RollBack()
            except Exception:
                pass
        return False


def _instance_basis_z(inst):
    if inst is None:
        return None
    try:
        tr = inst.GetTransform()
        if tr is None:
            return None
        return _xyz_unit(getattr(tr, 'BasisZ', None))
    except Exception:
        return None


def _instance_pivot(inst):
    if inst is None:
        return None
    try:
        loc = getattr(inst, 'Location', None)
        if isinstance(loc, DB.LocationPoint):
            return loc.Point
    except Exception:
        pass
    try:
        tr = inst.GetTransform()
        if tr is not None:
            return tr.Origin
    except Exception:
        pass
    return None


def _rotate_instance_about_axis(doc, inst, axis_origin, axis_dir, angle_rad):
    if doc is None or inst is None or axis_origin is None or axis_dir is None:
        return False
    axis_u = _xyz_unit(axis_dir)
    if axis_u is None:
        return False
    try:
        axis = DB.Line.CreateBound(
            axis_origin,
            DB.XYZ(
                float(axis_origin.X) + float(axis_u.X),
                float(axis_origin.Y) + float(axis_u.Y),
                float(axis_origin.Z) + float(axis_u.Z),
            ),
        )
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, float(angle_rad))
        return True
    except Exception:
        return False


def _rotate_vector_about_axis(vec, axis_dir, angle_rad):
    """Rodrigues rotation for XYZ vector."""
    v = _xyz_unit(vec)
    u = _xyz_unit(axis_dir)
    if v is None or u is None:
        return None
    try:
        c = math.cos(float(angle_rad))
        s = math.sin(float(angle_rad))
        term1 = v.Multiply(c)
        term2 = u.CrossProduct(v).Multiply(s)
        term3 = u.Multiply(u.DotProduct(v) * (1.0 - c))
        return term1 + term2 + term3
    except Exception:
        return None


def _tilt_instance_to_vertical_plane(doc, inst, wall_tangent_xy, room_inward_xy):
    """For non-hostable symbols: tilt from floor-plane to wall-plane."""
    if doc is None or inst is None:
        return False
    axis_xy = _xy_unit(wall_tangent_xy)
    inward_xy = _xy_unit(room_inward_xy)
    if axis_xy is None or inward_xy is None:
        return False

    cur_n = _instance_basis_z(inst)
    if cur_n is None:
        return False

    # If placement plane is already near vertical (normal is near-horizontal), skip tilt.
    try:
        if abs(float(cur_n.Z)) < 0.25:
            return True
    except Exception:
        pass

    axis_3d = DB.XYZ(float(axis_xy.X), float(axis_xy.Y), 0.0)
    inward_3d = DB.XYZ(float(inward_xy.X), float(inward_xy.Y), 0.0)

    cand_a = _rotate_vector_about_axis(cur_n, axis_3d, math.pi * 0.5)
    cand_b = _rotate_vector_about_axis(cur_n, axis_3d, -math.pi * 0.5)
    if cand_a is None and cand_b is None:
        return False

    def _score(candidate):
        cxy = _xy_unit(candidate)
        if cxy is None:
            return -1e9
        try:
            return float(cxy.DotProduct(inward_xy))
        except Exception:
            return -1e9

    ang = math.pi * 0.5
    if _score(cand_b) > _score(cand_a):
        ang = -math.pi * 0.5

    pivot = _instance_pivot(inst)
    if pivot is None:
        return False
    return _rotate_instance_about_axis(doc, inst, pivot, axis_3d, ang)


def _safe_tilt_instance_to_vertical_plane(doc, inst, wall_tangent_xy, room_inward_xy):
    if doc is None or inst is None:
        return False
    st = None
    try:
        st = DB.SubTransaction(doc)
        st.Start()
        ok = _tilt_instance_to_vertical_plane(doc, inst, wall_tangent_xy, room_inward_xy)
        if ok:
            st.Commit()
            return True
        try:
            st.RollBack()
        except Exception:
            pass
        return False
    except Exception:
        if st is not None:
            try:
                st.RollBack()
            except Exception:
                pass
        return False


def _room_center_link_point(room, fallback_pt):
    # For orientation near boundaries prefer geometric bbox center (stable for small wet rooms).
    try:
        bb = room.get_BoundingBox(None)
        if bb is not None:
            c = (bb.Min + bb.Max) * 0.5
            if c is not None:
                return c
    except Exception:
        pass
    try:
        pts = get_room_centers_multi(room)
        if pts:
            return pts[0]
    except Exception:
        pass
    return fallback_pt


def _point_on_room_side_wall_surface(link_wall, proj_on_axis, room_center_link, z_target, embed_ft):
    if link_wall is None or proj_on_axis is None:
        return None
    try:
        loc = getattr(link_wall, 'Location', None)
        curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
    except Exception:
        curve = None
    dxy = _curve_direction_xy(curve, proj_on_axis)
    if dxy is None:
        return DB.XYZ(float(proj_on_axis.X), float(proj_on_axis.Y), float(z_target))

    nx = -float(dxy.Y)
    ny = float(dxy.X)
    nlen = (nx * nx + ny * ny) ** 0.5
    if nlen <= 1e-9:
        return DB.XYZ(float(proj_on_axis.X), float(proj_on_axis.Y), float(z_target))
    nx /= nlen
    ny /= nlen

    try:
        width_ft = float(getattr(link_wall, 'Width', 0.0) or 0.0)
    except Exception:
        width_ft = 0.0

    px = float(proj_on_axis.X)
    py = float(proj_on_axis.Y)
    half_w = max(0.0, width_ft * 0.5)
    c1 = DB.XYZ(px + nx * half_w, py + ny * half_w, float(z_target))
    c2 = DB.XYZ(px - nx * half_w, py - ny * half_w, float(z_target))

    if room_center_link is None:
        face_pt = c1
    else:
        face_pt = c1 if _xy_dist2(c1, room_center_link) <= _xy_dist2(c2, room_center_link) else c2

    # Slightly embed inside wall from the room-side surface.
    if room_center_link is not None and embed_ft > 0.0:
        try:
            ix = float(room_center_link.X) - float(face_pt.X)
            iy = float(room_center_link.Y) - float(face_pt.Y)
            ilen = (ix * ix + iy * iy) ** 0.5
            if ilen > 1e-9:
                ix /= ilen
                iy /= ilen
                max_embed = width_ft * 0.45 if width_ft > 0.0 else float(embed_ft)
                embed = min(float(embed_ft), max_embed)
                face_pt = DB.XYZ(float(face_pt.X) - ix * embed, float(face_pt.Y) - iy * embed, float(z_target))
        except Exception:
            pass

    return face_pt


def _snap_anchor_to_room_wall_surface(link_doc, room, anchor_link_pt, search_ft, embed_ft):
    if link_doc is None or room is None or anchor_link_pt is None:
        return None, None, None, 0.0

    wall, proj = _find_nearest_wall_in_link(link_doc, anchor_link_pt, search_ft)
    center = _room_center_link_point(room, anchor_link_pt)

    # Prefer room boundary (interior side) over wall centerline math.
    bpt, btg = _find_room_boundary_point_near_anchor(room, anchor_link_pt)
    if bpt is not None:
        boundary_pt = DB.XYZ(float(bpt.X), float(bpt.Y), float(anchor_link_pt.Z))
        # For wet-room orientation/placement we need true wall normal (not vector to room center).
        inward = None
        if btg is not None:
            n1 = _xy_perp_left(btg)
            n2 = _xy_neg(n1) if n1 is not None else None
            to_center = _xy_dir_points(boundary_pt, center) if center is not None else None
            if n1 is not None and n2 is not None and to_center is not None:
                try:
                    d1 = float(n1.DotProduct(to_center))
                    d2 = float(n2.DotProduct(to_center))
                    inward = n1 if d1 >= d2 else n2
                except Exception:
                    inward = n1
            else:
                inward = n1
        if inward is None:
            inward = _xy_dir_points(boundary_pt, center) if center is not None else None
        if inward is not None:
            try:
                test_in = DB.XYZ(
                    float(boundary_pt.X) + float(inward.X) * mm_to_ft(20),
                    float(boundary_pt.Y) + float(inward.Y) * mm_to_ft(20),
                    float(boundary_pt.Z),
                )
            except Exception:
                test_in = None
            if test_in is not None and (not _room_contains_point(room, test_in)):
                inward2 = _xy_neg(inward)
                if inward2 is not None:
                    try:
                        test_in2 = DB.XYZ(
                            float(boundary_pt.X) + float(inward2.X) * mm_to_ft(20),
                            float(boundary_pt.Y) + float(inward2.Y) * mm_to_ft(20),
                            float(boundary_pt.Z),
                        )
                    except Exception:
                        test_in2 = None
                    if test_in2 is not None and _room_contains_point(room, test_in2):
                        inward = inward2
        point = boundary_pt
        if inward is not None:
            try:
                # Keep insertion on room-side boundary (slightly inside for stability).
                point = DB.XYZ(
                    float(boundary_pt.X) + float(inward.X) * mm_to_ft(2),
                    float(boundary_pt.Y) + float(inward.Y) * mm_to_ft(2),
                    float(boundary_pt.Z),
                )
            except Exception:
                point = boundary_pt
        # Estimate max safe "into wall" shift from nearest wall width (if available).
        max_into_wall_ft = 0.0
        wall_b, _ = _find_nearest_wall_in_link(link_doc, boundary_pt, search_ft)
        if wall_b is not None:
            try:
                w = float(getattr(wall_b, 'Width', 0.0) or 0.0)
                max_into_wall_ft = max(0.0, w * 0.45)
            except Exception:
                max_into_wall_ft = 0.0
        return point, inward, btg, max_into_wall_ft

    if wall is None or proj is None:
        return None, None, None, 0.0

    tangent = None
    try:
        loc = getattr(wall, 'Location', None)
        curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
        tangent = _curve_direction_xy(curve, proj)
    except Exception:
        tangent = None
    point = _point_on_room_side_wall_surface(
        wall,
        proj,
        center,
        float(anchor_link_pt.Z),
        float(embed_ft or 0.0),
    )
    inward = _xy_dir_points(point, center) if point is not None and center is not None else None
    try:
        max_into_wall_ft = max(0.0, float(getattr(wall, 'Width', 0.0) or 0.0) * 0.45)
    except Exception:
        max_into_wall_ft = 0.0
    return point, inward, tangent, max_into_wall_ft


def _get_point_over_door_center(door, default_head_height_ft, above_offset_ft):
    """Return point exactly above door center."""
    if door is None:
        return None
    try:
        loc = getattr(door, 'Location', None)
        door_pt = loc.Point if loc and hasattr(loc, 'Point') else None
    except Exception:
        door_pt = None
    if door_pt is None:
        return None

    h_ft = float(default_head_height_ft or 0.0)
    try:
        p = door.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM)
        if p:
            h_ft = float(p.AsDouble())
    except Exception:
        pass

    try:
        z = float(door_pt.Z) + float(h_ft) + float(above_offset_ft or 0.0)
        return DB.XYZ(float(door_pt.X), float(door_pt.Y), z)
    except Exception:
        return None


def _room_wall_search_radius_ft(room, default_ft):
    """Pick wall search radius based on room bbox, so fallback-center points can still reach a wall."""
    radius = float(default_ft or 0.0)
    try:
        bb = room.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        return radius
    try:
        dx = abs(float(bb.Max.X) - float(bb.Min.X))
        dy = abs(float(bb.Max.Y) - float(bb.Min.Y))
        # Half diagonal in XY + small margin.
        half_diag = ((dx * dx + dy * dy) ** 0.5) * 0.5
        candidate = half_diag + 1.0
        if candidate > radius:
            radius = candidate
    except Exception:
        pass
    return radius


def _symbol_placement_type_name(symbol):
    if symbol is None:
        return 'Unknown'
    try:
        fam = getattr(symbol, 'Family', None)
        pt = fam.FamilyPlacementType if fam else None
        return str(pt) if pt is not None else 'Unknown'
    except Exception:
        return 'Unknown'


def _is_probably_wall_hostable(symbol):
    name = _symbol_placement_type_name(symbol).lower()
    if not name:
        return False
    return ('host' in name) or ('face' in name) or ('wall' in name)


def _supports_vertical_tilt(symbol):
    """Whether symbol can be tilted out of horizontal placement plane."""
    name = _symbol_placement_type_name(symbol).lower()
    if not name:
        return False
    # OneLevelBased families in project context are typically always-vertical;
    # horizontal-axis rotation produces Revit failures on commit.
    if ('onelevelbased' in name) or ('twolevelbased' in name):
        return False
    return ('workplane' in name) or ('face' in name) or ('host' in name)


def _supports_plan_rotation(symbol):
    """Safe check for Z-axis RotateElement in project context."""
    name = _symbol_placement_type_name(symbol).lower()
    return bool(name)


def _symbol_label(symbol):
    if symbol is None:
        return '<NOT FOUND>'
    try:
        fam = getattr(symbol, 'FamilyName', None)
    except Exception:
        fam = None
    if not fam:
        try:
            fam_obj = getattr(symbol, 'Family', None)
            fam = getattr(fam_obj, 'Name', None)
        except Exception:
            fam = None
    try:
        typ = getattr(symbol, 'Name', None)
    except Exception:
        typ = None
    try:
        if fam and typ:
            return u'{0} : {1}'.format(fam, typ)
        if typ:
            return str(typ)
        return str(symbol.Id.IntegerValue)
    except Exception:
        return '<UNKNOWN>'


def _set_yesno_param(elem, preferred_names, value):
    """Set Yes/No parameter on element or type (Integer storage in Revit)."""
    if elem is None:
        return False

    target = 1 if value else 0
    names = [n for n in (preferred_names or []) if n]

    def _try_set(param):
        if param is None:
            return False
        try:
            if param.IsReadOnly:
                return False
            if param.StorageType == DB.StorageType.Integer:
                param.Set(int(target))
                return True
        except Exception:
            return False
        return False

    # 1) Direct lookup by candidate names.
    for n in names:
        try:
            p = elem.LookupParameter(n)
        except Exception:
            p = None
        if _try_set(p):
            return True

    # 2) Fuzzy fallback by parameter name tokens.
    try:
        params = list(elem.Parameters)
    except Exception:
        params = []
    if not params:
        return False

    want_tokens = []
    for n in names:
        try:
            low = (n or u'').strip().lower()
        except Exception:
            low = u''
        if low:
            want_tokens.append(low)
    if u'настенный' not in want_tokens:
        want_tokens.append(u'настенный')
    if u'wall mounted' not in want_tokens:
        want_tokens.append(u'wall mounted')
    if u'wallmounted' not in want_tokens:
        want_tokens.append(u'wallmounted')

    for p in params:
        try:
            pname = (p.Definition.Name or u'').strip().lower()
        except Exception:
            pname = u''
        if not pname:
            continue
        matched = False
        for tok in want_tokens:
            if tok and (tok in pname):
                matched = True
                break
        if not matched:
            continue
        if _try_set(p):
            return True

    return False


def _norm_request_token(value):
    t = (value or u'').strip().lower()
    if not t:
        return u''
    try:
        t = t.replace('\\', '/').split('/')[-1]
    except Exception:
        pass
    try:
        if t.endswith('.rfa'):
            t = t[:-4]
        if t.endswith('.zip'):
            t = t[:-4]
    except Exception:
        pass
    try:
        t = u' '.join(t.split())
    except Exception:
        pass
    return t


def _request_alias_tokens(value):
    base = (value or u'').strip().lower()
    if not base:
        return []

    raw = []
    raw.append(base)
    try:
        short = base.replace('\\', '/').split('/')[-1]
        if short and short not in raw:
            raw.append(short)
    except Exception:
        pass

    out = set()
    for r in raw:
        cur = r
        for _ in range(4):
            n = _norm_request_token(cur)
            if n:
                out.add(n)
            low = (cur or u'').lower()
            if low.endswith('.rfa'):
                cur = cur[:-4]
                continue
            if low.endswith('.zip'):
                cur = cur[:-4]
                continue
            break
        try:
            alt = (r or u'').replace('_', ' ').replace('-', ' ')
            nalt = _norm_request_token(alt)
            if nalt:
                out.add(nalt)
        except Exception:
            pass

    return [x for x in out if x]


def _symbol_match_text(symbol):
    if symbol is None:
        return u''
    parts = []
    try:
        fam = getattr(symbol, 'FamilyName', None)
        if fam:
            parts.append(str(fam))
    except Exception:
        pass
    try:
        fam_obj = getattr(symbol, 'Family', None)
        fam_name = getattr(fam_obj, 'Name', None) if fam_obj is not None else None
        if fam_name:
            parts.append(str(fam_name))
    except Exception:
        pass
    try:
        typ = getattr(symbol, 'Name', None)
        if typ:
            parts.append(str(typ))
    except Exception:
        pass
    try:
        return _norm_request_token(u' '.join(parts))
    except Exception:
        return u''


def _symbol_matches_request(symbol, request_name):
    if symbol is None:
        return False
    tokens = _request_alias_tokens(request_name)
    if not tokens:
        return True
    text = _symbol_match_text(symbol)
    if not text:
        return False
    for tok in tokens:
        if tok in text or text in tok:
            return True

    try:
        text_words = set([w for w in text.replace('_', ' ').split() if len(w) >= 3])
    except Exception:
        text_words = set()
    if not text_words:
        return False

    for tok in tokens:
        try:
            req_words = [w for w in tok.replace('_', ' ').split() if len(w) >= 3]
        except Exception:
            req_words = []
        if not req_words:
            continue
        hit = 0
        for w in req_words:
            if w in text_words:
                hit += 1
        need = 1 if len(req_words) == 1 else 2
        if hit >= need:
            return True

    return False


def _find_symbol_multi_categories(doc, requested_name, primary_bic):
    if doc is None:
        return None, None
    cats = [primary_bic]
    for extra in (
        DB.BuiltInCategory.OST_LightingDevices,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_GenericModel,
    ):
        cats.append(extra)

    tried = set()
    for bic in cats:
        if bic is None:
            continue
        try:
            key = int(bic)
        except Exception:
            key = str(bic)
        if key in tried:
            continue
        tried.add(key)

        sym = adapters.find_family_symbol(doc, requested_name, category_bic=bic)
        if sym is None:
            continue
        if _symbol_matches_request(sym, requested_name):
            return sym, bic

    return None, None


def run_placement(doc, uidoc, output, script_module):
    try:
        System.GC.Collect()
    except Exception:
        pass

    output.print_md('# Размещение светильников по помещениям (правила)')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    trace('Place_Lights_RoomCenters: start')

    def _build_result(placed, skipped_ext, skipped_dup, skipped_wall, skipped_anchor, skipped_symbol):
        skipped_total = skipped_ext + skipped_dup + skipped_wall + skipped_anchor + skipped_symbol
        return {
            'placed': placed,
            'skipped': skipped_total,
            'skipped_ext': skipped_ext,
            'skipped_dup': skipped_dup,
            'skipped_wall': skipped_wall,
            'skipped_anchor': skipped_anchor,
            'skipped_symbol': skipped_symbol,
        }

    def _single_center(room):
        pts = get_room_centers_multi(room)
        return [pts[0]] if pts else []

    rules = adapters.get_rules()

    # Defaults
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    ceiling_height_mm = rules.get('light_center_room_height_mm', 2700)
    ceiling_height_ft = mm_to_ft(ceiling_height_mm) or 0.0
    bath_sink_height_ft = mm_to_ft(rules.get('bath_sink_height_mm', 2000)) or mm_to_ft(2000)
    door_head_height_ft = mm_to_ft(rules.get('door_head_height_mm', 2100)) or mm_to_ft(2100)
    wc_above_door_offset_ft = mm_to_ft(rules.get('wc_light_above_door_offset_mm', 200)) or mm_to_ft(200)
    wall_search_ft = mm_to_ft(rules.get('host_wall_search_mm', 1000)) or mm_to_ft(1000)
    # For host/face placement in wet rooms: bias anchor slightly into room
    # so interior wall face is selected (not exterior).
    wet_host_interior_bias_ft = mm_to_ft(rules.get('wet_host_interior_bias_mm', 40)) or mm_to_ft(40)
    # For non-hostable wet fixtures: shift insertion toward room to compensate
    # family origin often being behind visible geometry.
    wet_nonhost_towards_room_ft = mm_to_ft(rules.get('wet_nonhost_towards_room_mm', 0)) or 0.0
    # Keep wet fixtures on interior room boundary by default (no push "into wall").
    wet_nonhost_into_wall_ft = mm_to_ft(rules.get('wet_nonhost_into_wall_mm', 0)) or 0.0
    bath_rotate_cw_rad = -math.radians(90.0)
    wc_rotate_cw_rad = -math.radians(90.0)
    comment_value = '{0}:LIGHT_CENTER'.format(comment_tag)

    link_inst = adapters.select_link_instance_ru(doc, title='Выберите связь АР')
    if link_inst is None:
        output.print_md('**Отменено.**')
        return _build_result(0, 0, 0, 0, 0, 0)
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её в «Управление связями» и повторите.')
        return _build_result(0, 0, 0, 0, 0, 0)

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи. Убедитесь, что связь загружена.')
        return _build_result(0, 0, 0, 0, 0, 0)

    link_transform = link_reader.get_total_transform(link_inst)

    # Levels
    trace('Select levels UI')
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
        return _build_result(0, 0, 0, 0, 0, 0)

    def _norm_level_name(name):
        try:
            return (name or '').strip().lower()
        except Exception:
            return ''

    # Host doc levels indexed by name (prefer mapping by AR link level name).
    host_levels_by_name = {}
    try:
        for hl in DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements():
            try:
                key = _norm_level_name(getattr(hl, 'Name', None))
                if key and key not in host_levels_by_name:
                    host_levels_by_name[key] = hl
            except Exception:
                pass
    except Exception:
        host_levels_by_name = {}

    def _resolve_host_level_from_link_level(link_level):
        if link_level is None:
            return None
        try:
            by_name = host_levels_by_name.get(_norm_level_name(getattr(link_level, 'Name', None)))
        except Exception:
            by_name = None
        if by_name is not None:
            return by_name
        try:
            elev_host = float(link_level.Elevation) + float(link_transform.Origin.Z)
            return find_nearest_level(doc, elev_host)
        except Exception:
            return None

    # Resolve families
    fam_names = rules.get('family_type_names', {}) or {}
    fam_ceiling = fam_names.get('light_ceiling_point') or ''
    fam_ceiling_terminal = fam_names.get('light_ceiling_terminal') or fam_ceiling
    fam_wall_wc = fam_names.get('light_wall_wc') or ''
    fam_bath = fam_names.get('light_wall_bath') or ''

    terminal_room_patterns = list((rules.get('light_terminal_room_name_patterns') or []))
    apartment_param_names = list((rules.get('apartment_param_names') or []))
    apartment_require_param = bool(rules.get('apartment_require_param', True))
    apartment_allow_department = bool(rules.get('apartment_allow_department_fallback', False))
    apartment_allow_room_number = bool(rules.get('apartment_allow_room_number_fallback', False))
    apartment_name_patterns = list((rules.get('entrance_apartment_room_name_patterns') or []))
    public_name_patterns = list((rules.get('entrance_public_room_name_patterns') or []))

    # Symbols
    sym_ceiling = adapters.find_family_symbol(doc, fam_ceiling, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    if not sym_ceiling:
        # Fallback: pick first valid lighting fixture
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        
        exclude_candidates = [
            'розетк', 'socket', 'выключатель', 'switch', 'рамка', 'frame', 
            'коробка', 'box', 'control', 'датчик', 'sensor'
        ]

        for e in col:
            if isinstance(e, DB.FamilySymbol):
                fn = e.FamilyName
                try:
                    fn_lower = (fn or "").lower()
                except:
                    fn_lower = ""
                
                if any(exc in fn_lower for exc in exclude_candidates):
                    continue

                sym_ceiling = e
                break

    sym_terminal, sym_terminal_bic = _find_symbol_multi_categories(doc, fam_ceiling_terminal, DB.BuiltInCategory.OST_LightingFixtures)
    sym_wall_wc, sym_wall_wc_bic = _find_symbol_multi_categories(doc, fam_wall_wc, DB.BuiltInCategory.OST_LightingFixtures)
    sym_bath, sym_bath_bic = _find_symbol_multi_categories(doc, fam_bath, DB.BuiltInCategory.OST_LightingFixtures)

    if not sym_ceiling:
        alert('Не найдено семейство светильника. Загрузите семейство и повторите.')
        return _build_result(0, 0, 0, 0, 0, 0)

    wc_wall_hostable = _is_probably_wall_hostable(sym_wall_wc)
    bath_wall_hostable = _is_probably_wall_hostable(sym_bath)
    wc_tilt_supported = _supports_vertical_tilt(sym_wall_wc)
    bath_tilt_supported = _supports_vertical_tilt(sym_bath)
    wc_plan_rot_supported = _supports_plan_rotation(sym_wall_wc)
    bath_plan_rot_supported = _supports_plan_rotation(sym_bath)

    try:
        output.print_md(
            u'Настенные типы: WC=`{0}` ({1}), Bath=`{2}` ({3})'.format(
                fam_wall_wc,
                _symbol_placement_type_name(sym_wall_wc),
                fam_bath,
                _symbol_placement_type_name(sym_bath),
            )
        )
        output.print_md(
            u'Фактически выбраны: Ceiling=`{0}`, Terminal=`{1}`, WC=`{2}`, Bath=`{3}`'.format(
                _symbol_label(sym_ceiling),
                _symbol_label(sym_terminal),
                _symbol_label(sym_wall_wc),
                _symbol_label(sym_bath),
            )
        )
        output.print_md(
            u'Категории: Terminal=`{0}`, WC=`{1}`, Bath=`{2}`'.format(
                str(sym_terminal_bic) if sym_terminal_bic is not None else '<NOT FOUND>',
                str(sym_wall_wc_bic) if sym_wall_wc_bic is not None else '<NOT FOUND>',
                str(sym_bath_bic) if sym_bath_bic is not None else '<NOT FOUND>',
            )
        )
    except Exception:
        pass

    if sym_wall_wc is None or sym_bath is None:
        output.print_md(
            u'Причина пропуска мокрых зон: не найдены требуемые семейства WC/Bath в категориях LightingFixtures/LightingDevices/ElectricalFixtures/GenericModel.'
        )

    if (not wc_wall_hostable) or (not bath_wall_hostable):
        output.print_md(
            u'Внимание: один из настенных типов не поддерживает host-на-стену; для них включено размещение на границе помещения.'
        )
        if (not wc_tilt_supported) or (not bath_tilt_supported):
            output.print_md(
                u"Примечание: OneLevelBased не поддерживает наклон в вертикальную плоскость (иначе ошибка Revit `Can't rotate element into this position`)."
            )

    # Activate symbols
    with tx('Activate Symbols', doc=doc):
        for sym in (sym_ceiling, sym_terminal, sym_wall_wc, sym_bath):
            if sym is None:
                continue
            try:
                if not sym.IsActive:
                    sym.Activate()
            except Exception:
                continue
        # Wet room families must be in "wall mode" before placement.
        try:
            if sym_wall_wc is not None:
                _set_yesno_param(sym_wall_wc, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
        except Exception:
            pass
        try:
            if sym_bath is not None:
                _set_yesno_param(sym_bath, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
        except Exception:
            pass
        doc.Regenerate()

    # Pre-collect ALL existing lights (not just current type) to prevent overlap with anything
    existing_centers = adapters.collect_existing_lights_centers(doc, tolerance_ft=1.5)

    # Collect rooms
    rooms_raw = []
    for lvl in selected_levels:
        lid = lvl.Id
        rooms_raw.extend(adapters.iter_rooms(link_doc, level_id=lid))

    if not rooms_raw:
        alert('В выбранных уровнях не найдено помещений (Rooms).')
        return _build_result(0, 0, 0, 0, 0, 0)

    # Deduplicate rooms (handle Design Options or bad links)
    rooms = filter_duplicate_rooms(rooms_raw)

    # Pre-collect doors for "Above Door" logic
    all_doors = list(adapters.iter_doors(link_doc))
    # Pre-collect plumbing for "Above Sink" logic
    all_plumbing = list(adapters.iter_plumbing_fixtures(link_doc))

    # Main Transaction with SWALLOW WARNINGS
    count = 0
    skipped_ext = 0
    skipped_dup = 0
    skipped_wall = 0
    skipped_anchor = 0
    skipped_symbol = 0
    with tx('Place Room Center Lights', doc=doc, swallow_warnings=True):
        count = 0
        skipped_ext = 0
        skipped_dup = 0
        skipped_wall = 0
        skipped_anchor = 0
        skipped_symbol = 0

        for r in rooms:
            if not is_apartment_room(
                r,
                apartment_param_names=apartment_param_names,
                require_param=apartment_require_param,
                allow_department=apartment_allow_department,
                allow_number=apartment_allow_room_number,
                apartment_name_patterns=apartment_name_patterns,
                public_name_patterns=public_name_patterns,
            ):
                skipped_ext += 1
                continue

            # Check exclusions (balcony, loggia, technical/public)
            if is_excluded_room(r):
                skipped_ext += 1
                continue

            # Determine Placement Strategy
            target_pts = []
            target_symbol = sym_ceiling
            require_wall_host = False
            allow_vertical_tilt = False
            allow_plan_rotation = True
            wet_rotate_rad = 0.0
            placement_z_mode = 'ceiling' # ceiling or door_relative or absolute_z

            if is_bathroom(r):
                # Bathroom Rule:
                # 1. Light over sink (height 2m)
                if sym_bath is None:
                    skipped_symbol += 1
                    continue
                target_symbol = sym_bath
                # Wet rooms are placed by interior room boundary (non-host mode).
                require_wall_host = False
                allow_vertical_tilt = False
                # Orient bathroom fixture normal to wall, facing inside room.
                allow_plan_rotation = bool(bath_plan_rot_supported)
                wet_rotate_rad = float(bath_rotate_cw_rad)

                # Try Sink
                pt_sink = domain.get_above_sink_point(r, all_plumbing, bath_sink_height_ft)
                
                if pt_sink:
                    target_pts = [pt_sink]
                    placement_z_mode = 'absolute_z_link'
                else:
                    skipped_anchor += 1
                    continue

            elif is_toilet(r):
                # Toilet Rule:
                # 1. Wall light over door
                if sym_wall_wc is None:
                    skipped_symbol += 1
                    continue
                target_symbol = sym_wall_wc
                # Wet rooms are placed by interior room boundary (non-host mode).
                require_wall_host = False
                allow_vertical_tilt = False
                # For WC orient symbol normal into room (perpendicular from wall plane).
                allow_plan_rotation = bool(wc_plan_rot_supported)
                wet_rotate_rad = float(wc_rotate_cw_rad)
                
                # Try Door
                door = find_best_door_for_room(r, all_doors)
                pt = _get_point_over_door_center(door, door_head_height_ft, wc_above_door_offset_ft) if door else None
                if pt:
                    target_pts = [pt]
                    placement_z_mode = 'door_relative'
                else:
                    skipped_anchor += 1
                    continue

            else:
                # Strategy: Standard room center (one fixture per room)
                target_pts = _single_center(r)
                if room_name_matches(r, terminal_room_patterns):
                    if sym_terminal is None:
                        skipped_symbol += 1
                        continue
                    target_symbol = sym_terminal
                else:
                    target_symbol = sym_ceiling
                placement_z_mode = 'ceiling'

            if not target_pts:
                continue

            # Place loop
            for p_link in target_pts:
                p_host = link_transform.OfPoint(p_link)

                # Find nearest host level
                try:
                    r_level_id = r.LevelId
                    r_level = link_doc.GetElement(r_level_id)
                    r_elev = float(getattr(r_level, 'Elevation', 0.0) or 0.0)
                    host_level = _resolve_host_level_from_link_level(r_level)
                    if not host_level:
                        host_level = find_nearest_level(doc, r_elev + link_transform.Origin.Z)
                except Exception:
                    host_level = None

                if not host_level:
                    continue

                # Calc Z
                if placement_z_mode == 'door_relative' or placement_z_mode == 'absolute_z_link':
                    # p_link.Z already includes height logic.
                    # p_host is transformed (includes link Z offset).
                    z = p_host.Z 
                else:
                    # Use AR link level elevation (transformed) as source of truth.
                    z = (r_elev + link_transform.Origin.Z) + ceiling_height_ft

                insert_point = DB.XYZ(p_host.X, p_host.Y, z)

                placement_mode = None
                placement_payload = None
                placement_point = insert_point
                target_direction_host = None
                wall_tangent_host = None
                wet_snapped_link = None
                wet_inward_link = None
                wet_tangent_link = None
                wet_max_into_wall_ft = 0.0
                wet_room = is_bathroom(r) or is_toilet(r)

                if wet_room:
                    room_wall_search_ft = _room_wall_search_radius_ft(r, wall_search_ft)
                    wet_snapped_link, wet_inward_link, wet_tangent_link, wet_max_into_wall_ft = _snap_anchor_to_room_wall_surface(
                        link_doc, r, p_link, room_wall_search_ft, 0.0
                    )
                    if wet_snapped_link is None:
                        wet_snapped_link, wet_inward_link, wet_tangent_link, wet_max_into_wall_ft = _snap_anchor_to_room_wall_surface(
                            link_doc, r, p_link, mm_to_ft(15000), 0.0
                        )
                    if wet_inward_link is not None:
                        try:
                            target_direction_host = _xy_unit(link_transform.OfVector(wet_inward_link))
                        except Exception:
                            target_direction_host = None
                    if wet_tangent_link is not None:
                        try:
                            wall_tangent_host = _xy_unit(link_transform.OfVector(wet_tangent_link))
                        except Exception:
                            wall_tangent_host = None

                if require_wall_host:
                    room_wall_search_ft = _room_wall_search_radius_ft(r, wall_search_ft)
                    wall_anchor_link = wet_snapped_link if wet_room and wet_snapped_link is not None else p_link
                    if wet_room and wall_anchor_link is not None and wet_inward_link is not None and wet_host_interior_bias_ft > 0.0:
                        try:
                            wall_anchor_link = DB.XYZ(
                                float(wall_anchor_link.X) + float(wet_inward_link.X) * float(wet_host_interior_bias_ft),
                                float(wall_anchor_link.Y) + float(wet_inward_link.Y) * float(wet_host_interior_bias_ft),
                                float(wall_anchor_link.Z),
                            )
                        except Exception:
                            pass
                    wall_insert_point = insert_point
                    if wet_room and wet_snapped_link is not None:
                        try:
                            wph = link_transform.OfPoint(wet_snapped_link)
                            wall_insert_point = DB.XYZ(float(wph.X), float(wph.Y), float(z))
                        except Exception:
                            wall_insert_point = insert_point
                    placement_mode, placement_point, placement_payload = _prepare_wall_placement(
                        doc, link_doc, link_inst, link_transform, wall_anchor_link, wall_insert_point, room_wall_search_ft
                    )
                    if placement_mode is None:
                        # Soft fallback: very broad search to still host to the nearest wall.
                        placement_mode, placement_point, placement_payload = _prepare_wall_placement(
                            doc, link_doc, link_inst, link_transform, wall_anchor_link, wall_insert_point, mm_to_ft(15000)
                        )
                        if placement_mode is None:
                            skipped_wall += 1
                            continue
                    if wet_room and placement_mode == 'linked_ref' and isinstance(placement_payload, dict):
                        try:
                            placement_payload.pop('direction', None)
                        except Exception:
                            pass
                elif wet_room:
                    # Wet symbols: place strictly on interior room boundary (non-host mode).
                    if wet_snapped_link is not None:
                        snapped_host = link_transform.OfPoint(wet_snapped_link)
                        placement_point = DB.XYZ(float(snapped_host.X), float(snapped_host.Y), float(z))
                        if target_direction_host is not None and wet_nonhost_towards_room_ft > 0.0:
                            try:
                                placement_point = DB.XYZ(
                                    float(placement_point.X) + float(target_direction_host.X) * float(wet_nonhost_towards_room_ft),
                                    float(placement_point.Y) + float(target_direction_host.Y) * float(wet_nonhost_towards_room_ft),
                                    float(placement_point.Z),
                                )
                            except Exception:
                                pass
                        if target_direction_host is not None and wet_nonhost_into_wall_ft > 0.0:
                            try:
                                shift_ft = float(wet_nonhost_into_wall_ft)
                                if wet_max_into_wall_ft > 0.0:
                                    shift_ft = min(shift_ft, float(wet_max_into_wall_ft))
                                placement_point = DB.XYZ(
                                    float(placement_point.X) - float(target_direction_host.X) * shift_ft,
                                    float(placement_point.Y) - float(target_direction_host.Y) * shift_ft,
                                    float(placement_point.Z),
                                )
                            except Exception:
                                pass
                    else:
                        skipped_wall += 1
                        continue

                # Check duplicates (manual geometry check against ALL lights)
                if is_too_close(placement_point, existing_centers, tolerance_ft=1.5):
                    skipped_dup += 1
                    continue

                # Place
                inst = None
                if require_wall_host:
                    inst = _create_wall_hosted_instance(
                        doc, target_symbol, host_level, placement_mode, placement_point, placement_payload
                    )
                    if inst is None:
                        skipped_wall += 1
                        continue
                else:
                    try:
                        inst = doc.Create.NewFamilyInstance(
                            placement_point, target_symbol, host_level, DB.Structure.StructuralType.NonStructural
                        )
                    except Exception as e1:
                        print(u'DEBUG: ERROR creating instance at {0}: {1}'.format(placement_point, str(e1)))
                        skipped_symbol += 1
                        continue

                wet_room_now = is_bathroom(r) or is_toilet(r)

                # User-requested family flag for wet rooms: "Настенный" = Yes.
                if wet_room_now:
                    try:
                        set_ok = _set_yesno_param(inst, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
                        if not set_ok:
                            _set_yesno_param(target_symbol, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
                    except Exception:
                        pass
                    # User-requested: disable emergency lighting on wet-room fixtures.
                    try:
                        em_names = [
                            u'EE_Аварийное освещение',
                            u'Аварийное освещение',
                            u'Emergency Lighting',
                            u'Emergency',
                        ]
                        em_ok = _set_yesno_param(inst, em_names, False)
                        if not em_ok:
                            _set_yesno_param(target_symbol, em_names, False)
                    except Exception:
                        pass

                if target_direction_host is not None and allow_plan_rotation:
                    try:
                        target_rot = target_direction_host
                        if wet_room_now and abs(float(wet_rotate_rad)) > 1e-8:
                            rr = _xy_rotate(target_direction_host, wet_rotate_rad)
                            if rr is not None:
                                target_rot = rr
                        _safe_rotate_instance_xy_towards(doc, inst, target_rot)
                        # If family front is flipped out of the room, turn it by 180 deg.
                        fwd = _instance_forward_xy(inst)
                        if fwd is not None:
                            try:
                                if float(fwd.DotProduct(target_rot)) < 0.0:
                                    target_back = _xy_neg(target_rot)
                                    if target_back is not None:
                                        _safe_rotate_instance_xy_towards(doc, inst, target_back)
                            except Exception:
                                pass
                    except Exception:
                        pass
                if (not require_wall_host) and wet_room_now and allow_vertical_tilt:
                    try:
                        _safe_tilt_instance_to_vertical_plane(doc, inst, wall_tangent_host, target_direction_host)
                    except Exception:
                        pass

                try:
                    set_comments(inst, comment_value)
                except Exception:
                    pass
                # Add to existing list to prevent duplicates within same run
                existing_centers.append(placement_point)
                count += 1

        output.print_md('**Готово.** Размещено светильников: {0}'.format(count))
        if skipped_ext > 0:
            output.print_md('Пропущено помещений (внеквартирные/исключенные): {0}'.format(skipped_ext))
        if skipped_dup > 0:
            output.print_md('Пропущено дублей (уже есть светильник): {0}'.format(skipped_dup))
        if skipped_wall > 0:
            output.print_md('Пропущено (не найдена/не подошла стена для настенного светильника): {0}'.format(skipped_wall))
        if skipped_anchor > 0:
            output.print_md('Пропущено (не найдена дверь/раковина для точного размещения): {0}'.format(skipped_anchor))
        if skipped_symbol > 0:
            output.print_md('Пропущено (не найден/не удалось установить требуемый тип семейства): {0}'.format(skipped_symbol))

    return _build_result(count, skipped_ext, skipped_dup, skipped_wall, skipped_anchor, skipped_symbol)
