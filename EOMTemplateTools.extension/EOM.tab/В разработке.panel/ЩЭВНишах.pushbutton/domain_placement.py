# -*- coding: utf-8 -*-

from pyrevit import DB


def find_host_wall_near_point(doc, host_point, search_radius_ft):
    best_wall = None
    best_proj = None
    best_dist = None

    walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType()
    for wall in walls:
        try:
            loc = wall.Location
            curve = getattr(loc, 'Curve', None)
            if curve is None:
                continue
            proj = curve.Project(host_point)
            if proj is None:
                continue
            p = proj.XYZPoint
            if p is None:
                continue
            dist = p.DistanceTo(host_point)
            if dist > search_radius_ft:
                continue
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_wall = wall
                best_proj = p
        except Exception:
            continue

    return best_wall, best_proj, best_dist


def find_link_wall_projection(link_doc, link_transform, link_point, search_radius_ft):
    best_wall = None
    best_proj = None
    best_dist = None

    walls = DB.FilteredElementCollector(link_doc).OfClass(DB.Wall).WhereElementIsNotElementType()
    for wall in walls:
        try:
            loc = wall.Location
            curve = getattr(loc, 'Curve', None)
            if curve is None:
                continue
            proj = curve.Project(link_point)
            if proj is None:
                continue
            p_link = proj.XYZPoint
            if p_link is None:
                continue
            dist = p_link.DistanceTo(link_point)
            if dist > search_radius_ft:
                continue
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_wall = wall
                best_proj = link_transform.OfPoint(p_link)
        except Exception:
            continue

    return best_wall, best_proj, best_dist


def set_instance_height(inst, level, height_mm, mm_to_ft):
    try:
        base = float(level.Elevation)
    except Exception:
        base = 0.0
    target_z = base + float(mm_to_ft(height_mm) or 0.0)

    loc = getattr(inst, 'Location', None)
    pt = getattr(loc, 'Point', None) if loc else None
    if pt is None:
        return False

    try:
        loc.Point = DB.XYZ(float(pt.X), float(pt.Y), float(target_z))
        return True
    except Exception:
        return False


def get_host_level_by_elevation(doc, target_elev):
    best_level = None
    best_delta = None
    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for lvl in levels:
        try:
            delta = abs(float(lvl.Elevation) - float(target_elev))
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_level = lvl
        except Exception:
            continue
    return best_level


def dedupe_existing(doc, symbol, target_point, radius_ft):
    best = None
    best_dist = None

    col = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()
    for inst in col:
        try:
            if getattr(inst, 'Symbol', None) is None:
                continue
            if inst.Symbol.Id.IntegerValue != symbol.Id.IntegerValue:
                continue
            loc = getattr(inst, 'Location', None)
            pt = getattr(loc, 'Point', None) if loc else None
            if pt is None:
                continue
            dist = pt.DistanceTo(target_point)
            if dist > radius_ft:
                continue
            if best_dist is None or dist < best_dist:
                best = inst
                best_dist = dist
        except Exception:
            continue

    return best

