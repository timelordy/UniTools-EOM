# -*- coding: utf-8 -*-

import pk_indicator_rules
from pyrevit import DB


def points_near_xy(a, b, r_ft):
    try:
        dx = float(a.X) - float(b.X)
        dy = float(a.Y) - float(b.Y)
        return ((dx * dx + dy * dy) ** 0.5) <= float(r_ft)
    except Exception:
        return False


def dedupe_points_xy(points, radius_ft):
    out = []
    r = float(radius_ft or 0.0)
    if r <= 1e-9:
        return list(points or [])
    for p in points or []:
        if p is None:
            continue
        dup = False
        for q in out:
            if points_near_xy(p, q, r):
                dup = True
                break
        if not dup:
            out.append(p)
    return out


def filter_points_by_view_level(points, view, tol_ft):
    if view is None:
        return list(points or [])
    try:
        lvl = getattr(view, 'GenLevel', None)
        if lvl is None:
            return list(points or [])
        z = float(lvl.Elevation)
    except Exception:
        return list(points or [])
    out = []
    for p in points or []:
        try:
            if abs(float(p.Z) - z) <= float(tol_ft):
                out.append(p)
        except Exception:
            out.append(p)
    return out


def is_view_based(symbol):
    import placement_engine
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.ViewBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and 'viewbased' in pt_name.lower():
            return True
    except Exception:
        pass
    return False


def is_point_based(symbol):
    import placement_engine
    return placement_engine.is_supported_point_placement(symbol)


def get_safe_bic(name):
    try:
        return getattr(DB.BuiltInCategory, name)
    except Exception:
        return None


def as_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [v for v in val if v]
    return [val]
