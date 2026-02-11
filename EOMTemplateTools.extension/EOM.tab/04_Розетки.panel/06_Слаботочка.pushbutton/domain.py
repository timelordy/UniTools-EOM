# -*- coding: utf-8 -*-

from pyrevit import DB
import socket_utils as su


# Ключевые слова для входной (квартирной) стальной двери
ENTRANCE_DOOR_KEYWORDS = [
    u'вход', u'входн', u'дм_', u'дм-', u'металл', u'сталь',
    u'entrance', u'entry', u'steel'
]


def closest_point_xy(points, target_pt):
    if not points or target_pt is None:
        return None, None
    best = None
    best_d = None
    for p in points:
        if p is None:
            continue
        try:
            d = ((float(p.X) - float(target_pt.X)) ** 2 + (float(p.Y) - float(target_pt.Y)) ** 2) ** 0.5
        except Exception:
            continue
        if best is None or d < best_d:
            best, best_d = p, d
    return best, best_d


def find_wall_near_point(link_doc, pt_link, max_dist_ft):
    if link_doc is None or pt_link is None:
        return None, None

    best_wall = None
    best_curve = None
    best_d = None

    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None

    for w in col:
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue
            ir = curve.Project(pt_link)
            if not ir:
                continue
            d = float(ir.Distance)
            if d > float(max_dist_ft or 0.0):
                continue
            if best_wall is None or d < best_d:
                best_wall, best_curve, best_d = w, curve, d
        except Exception:
            continue

    return best_wall, best_curve


def wall_tangent_xy(curve, pt_link):
    if curve is None or pt_link is None:
        return DB.XYZ.BasisX
    try:
        ir = curve.Project(pt_link)
        if not ir:
            return DB.XYZ.BasisX
        p = ir.Parameter
        d = curve.ComputeDerivatives(p, True)
        v = d.BasisX
        v2 = DB.XYZ(float(v.X), float(v.Y), 0.0)
        return v2.Normalize() if v2.GetLength() > 1e-9 else DB.XYZ.BasisX
    except Exception:
        return DB.XYZ.BasisX


def xy_unit(vec):
    if vec is None:
        return None
    try:
        v = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
        return v.Normalize() if v.GetLength() > 1e-9 else None
    except Exception:
        return None


def try_get_door_facing_xy(door):
    if door is None:
        return None
    try:
        v = xy_unit(getattr(door, "FacingOrientation", None))
        if v is not None:
            return v
    except Exception:
        pass
    try:
        host = getattr(door, "Host", None)
        v = xy_unit(getattr(host, "Orientation", None)) if host is not None else None
        if v is not None:
            return v
    except Exception:
        pass
    return None


def try_get_door_hand_xy(door):
    if door is None:
        return None
    try:
        v = xy_unit(getattr(door, "HandOrientation", None))
        if v is not None:
            return v
    except Exception:
        pass
    return None


def door_handle_dir_xy(door):
    hand = try_get_door_hand_xy(door)
    if hand is None:
        return None
    try:
        return xy_unit(DB.XYZ(-float(hand.X), -float(hand.Y), 0.0))
    except Exception:
        return None


def room_side_normal_from_facing(room, door_center, facing_xy, probe_ft):
    if room is None or door_center is None or facing_xy is None:
        return None
    n = xy_unit(facing_xy)
    if n is None:
        return None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
    try:
        z0 = float((room_bb.Min.Z + room_bb.Max.Z) * 0.5) if room_bb else float(door_center.Z)
    except Exception:
        z0 = float(getattr(door_center, "Z", 0.0) or 0.0)
    base = DB.XYZ(float(door_center.X), float(door_center.Y), float(z0))
    eps = float(probe_ft or 0.0)
    if eps <= 1e-9:
        return None
    try:
        p_plus = base + (n * eps)
        p_minus = base - (n * eps)
        in_plus = bool(room.IsPointInRoom(p_plus))
        in_minus = bool(room.IsPointInRoom(p_minus))
        if in_plus and (not in_minus):
            return n
        if in_minus and (not in_plus):
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)
    except Exception:
        return None
    return None


def _text(v):
    try:
        return (v or u'').lower()
    except Exception:
        return u''


def _door_type_text(door):
    family_name = u''
    type_name = u''
    try:
        sym = getattr(door, 'Symbol', None)
        if sym:
            try:
                family_name = _text(sym.Family.Name)
            except Exception:
                family_name = _text(getattr(sym, 'FamilyName', u''))
            try:
                p = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
                if p:
                    type_name = _text(p.AsString())
            except Exception:
                type_name = _text(getattr(sym, 'Name', u''))
    except Exception:
        pass
    return u'{} {}'.format(family_name, type_name)


def _contains_any(text, patterns):
    t = _text(text)
    for p in (patterns or []):
        if _text(p) and _text(p) in t:
            return True
    return False


def is_entrance_door(door, patterns=None):
    txt = _door_type_text(door)
    pats = patterns or ENTRANCE_DOOR_KEYWORDS
    return _contains_any(txt, pats)


def pick_room_door_handle_side(room, doors, room_center, probe_ft, only_entrance=False, entrance_patterns=None):
    if room is None or not doors:
        return None

    # Если requested only entrance - фильтруем заранее
    source_doors = doors
    if only_entrance:
        filtered = []
        for d in doors:
            try:
                if is_entrance_door(d, entrance_patterns):
                    filtered.append(d)
            except Exception:
                continue
        source_doors = filtered

    best = None
    best_d = None
    for d in source_doors:
        c = su._inst_center_point(d)
        if c is None:
            continue
        facing = try_get_door_facing_xy(d)
        if facing is None:
            continue
        room_normal = room_side_normal_from_facing(room, c, facing, probe_ft)
        if room_normal is None:
            # Fallback: если не удалось однозначно определить сторону комнаты,
            # используем Facing как нормаль, чтобы не терять кандидат двери.
            room_normal = facing

        handle = door_handle_dir_xy(d)
        if handle is None:
            # Fallback: строим направление ручки из Facing (поворот на 90°)
            try:
                handle = xy_unit(DB.XYZ(-float(facing.Y), float(facing.X), 0.0))
            except Exception:
                handle = None
        if handle is None:
            continue
        try:
            d0 = su._dist_xy(c, room_center) if room_center is not None else 0.0
        except Exception:
            d0 = 0.0
        if best is None or d0 < best_d:
            best = (d, c, room_normal, handle)
            best_d = d0
    return best
