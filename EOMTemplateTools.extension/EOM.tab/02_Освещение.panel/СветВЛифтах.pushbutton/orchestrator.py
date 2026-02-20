# -*- coding: utf-8 -*-

import re

from pyrevit import DB, forms, revit
import config_loader
import link_reader
import magic_context
import placement_engine
import socket_utils
from utils_revit import alert, find_nearest_level, set_comments, trace, tx
from utils_units import mm_to_ft
from constants import LIGHT_LIFT_SHAFT_TAG
from domain import (
    geom_center_and_z,
    bbox_contains_point,
    bbox_intersects,
    expand_bbox_xy,
    transform_bbox,
    match_exact_names,
    segment_ranges,
    chunks,
    is_wall_hosted,
    is_one_level_based,
)
from adapters import (
    store_symbol_id,
    store_symbol_unique_id,
    pick_light_symbol,
    check_symbol_compatibility,
)


def find_host_wall_in_bbox_near_point(doc, pt, bbox_min, bbox_max, max_dist_ft):
    if doc is None or pt is None or bbox_min is None or bbox_max is None:
        return None, None, None

    best_wall = None
    best_curve = None
    best_pt = None
    best_d = None
    best_tie = None

    try:
        tie_eps = float(mm_to_ft(5.0) or 0.0)
    except Exception:
        tie_eps = 0.0
    if tie_eps <= 0.0:
        tie_eps = 1e-6

    try:
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None, None

    for w in col:
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue

            wbb = None
            try:
                wbb = w.get_BoundingBox(None)
            except Exception:
                wbb = None
            if wbb is not None:
                wmin = DB.XYZ(min(float(wbb.Min.X), float(wbb.Max.X)),
                              min(float(wbb.Min.Y), float(wbb.Max.Y)),
                              min(float(wbb.Min.Z), float(wbb.Max.Z)))
                wmax = DB.XYZ(max(float(wbb.Min.X), float(wbb.Max.X)),
                              max(float(wbb.Min.Y), float(wbb.Max.Y)),
                              max(float(wbb.Min.Z), float(wbb.Max.Z)))
                if not bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue
            pt_flat = pt
            try:
                p0 = curve.GetEndPoint(0)
                pt_flat = DB.XYZ(float(pt.X), float(pt.Y), float(p0.Z))
            except Exception:
                pt_flat = pt
            ir = curve.Project(pt_flat)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not bbox_contains_point(bbox_min, bbox_max, proj):
                continue
            d = float(ir.Distance)
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            tie_key = (0, 0.0)
            try:
                cdir = curve.Direction
                ax = abs(float(cdir.X))
                ay = abs(float(cdir.Y))
                # In equal-distance cases prefer side walls (Y-oriented in plan)
                # then the left side (smaller X projection).
                orient_rank = 1 if ay >= ax else 0
                left_rank = -float(proj.X) if proj is not None else 0.0
                tie_key = (orient_rank, left_rank)
            except Exception:
                tie_key = (0, 0.0)

            replace = False
            if best_wall is None:
                replace = True
            elif d < (best_d - tie_eps):
                replace = True
            elif abs(d - best_d) <= tie_eps:
                if best_tie is None or tie_key > best_tie:
                    replace = True
            if replace:
                best_wall = w
                best_curve = curve
                best_pt = proj
                best_d = d
                best_tie = tie_key
        except Exception:
            continue

    return best_wall, best_curve, best_pt


def find_link_wall_in_bbox_near_point(link_doc, pt_link, bbox_min, bbox_max, max_dist_ft, limit=None):
    if link_doc is None or pt_link is None or bbox_min is None or bbox_max is None:
        return None, None

    best_wall = None
    best_pt = None
    best_d = None
    best_tie = None

    try:
        tie_eps = float(mm_to_ft(5.0) or 0.0)
    except Exception:
        tie_eps = 0.0
    if tie_eps <= 0.0:
        tie_eps = 1e-6

    for w in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Walls, limit=limit, level_id=None):
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue

            wbb = None
            try:
                wbb = w.get_BoundingBox(None)
            except Exception:
                wbb = None
            if wbb is not None:
                wmin = DB.XYZ(min(float(wbb.Min.X), float(wbb.Max.X)),
                              min(float(wbb.Min.Y), float(wbb.Max.Y)),
                              min(float(wbb.Min.Z), float(wbb.Max.Z)))
                wmax = DB.XYZ(max(float(wbb.Min.X), float(wbb.Max.X)),
                              max(float(wbb.Min.Y), float(wbb.Max.Y)),
                              max(float(wbb.Min.Z), float(wbb.Max.Z)))
                if not bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue

            pt_flat = pt_link
            try:
                p0 = curve.GetEndPoint(0)
                pt_flat = DB.XYZ(float(pt_link.X), float(pt_link.Y), float(p0.Z))
            except Exception:
                pt_flat = pt_link
            ir = curve.Project(pt_flat)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not bbox_contains_point(bbox_min, bbox_max, proj):
                continue

            d = float(ir.Distance)
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            tie_key = (0, 0.0)
            try:
                cdir = curve.Direction
                ax = abs(float(cdir.X))
                ay = abs(float(cdir.Y))
                orient_rank = 1 if ay >= ax else 0
                left_rank = -float(proj.X) if proj is not None else 0.0
                tie_key = (orient_rank, left_rank)
            except Exception:
                tie_key = (0, 0.0)

            replace = False
            if best_wall is None:
                replace = True
            elif d < (best_d - tie_eps):
                replace = True
            elif abs(d - best_d) <= tie_eps:
                if best_tie is None or tie_key > best_tie:
                    replace = True
            if replace:
                best_wall = w
                best_pt = proj
                best_d = d
                best_tie = tie_key
        except Exception:
            continue

    return best_wall, best_pt


def place_wall_hosted(doc, symbol, wall, pt, level):
    if doc is None or symbol is None or wall is None or pt is None:
        return None

    placement_engine.ensure_symbol_active(doc, symbol)

    try:
        inst = doc.Create.NewFamilyInstance(
            pt,
            symbol,
            wall,
            level,
            DB.Structure.StructuralType.NonStructural
        )
        return inst
    except Exception:
        pass

    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Interior))
        except Exception:
            pass
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Exterior))
        except Exception:
            pass

        best_ref = None
        best_d = None
        for r in refs:
            try:
                face = wall.GetGeometryObjectFromReference(r)
                if face is None:
                    continue
                ir = face.Project(pt)
                if not ir:
                    continue
                d = float(ir.Distance)
                if best_ref is None or d < best_d:
                    best_ref = r
                    best_d = d
            except Exception:
                continue

        if best_ref is not None:
            try:
                return doc.Create.NewFamilyInstance(best_ref, pt, DB.XYZ.BasisZ, symbol)
            except Exception:
                return None
    except Exception:
        return None

    return None


def _set_yesno_param(elem, preferred_names, value):
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

    for n in names:
        try:
            p = elem.LookupParameter(n)
        except Exception:
            p = None
        if _try_set(p):
            return True

    try:
        params = list(elem.Parameters)
    except Exception:
        params = []
    if not params:
        return False

    tokens = []
    for n in names:
        try:
            t = (n or u'').strip().lower()
        except Exception:
            t = u''
        if t:
            tokens.append(t)
    if u'настенный' not in tokens:
        tokens.append(u'настенный')
    if u'wall mounted' not in tokens:
        tokens.append(u'wall mounted')
    if u'wallmounted' not in tokens:
        tokens.append(u'wallmounted')

    for p in params:
        try:
            pname = (p.Definition.Name or u'').strip().lower()
        except Exception:
            pname = u''
        if not pname:
            continue
        matched = False
        for tok in tokens:
            if tok and tok in pname:
                matched = True
                break
        if not matched:
            continue
        if _try_set(p):
            return True

    return False


def _set_length_param_ft(elem, preferred_names, value_ft):
    if elem is None:
        return False

    names = [n for n in (preferred_names or []) if n]
    try:
        target = float(value_ft or 0.0)
    except Exception:
        target = 0.0

    def _try_set(param):
        if param is None:
            return False
        try:
            if param.IsReadOnly:
                return False
            if param.StorageType == DB.StorageType.Double:
                param.Set(float(target))
                return True
        except Exception:
            return False
        return False

    for n in names:
        try:
            p = elem.LookupParameter(n)
        except Exception:
            p = None
        if _try_set(p):
            return True

    try:
        params = list(elem.Parameters)
    except Exception:
        params = []
    for p in params:
        try:
            pname = (p.Definition.Name or u'').strip().lower()
        except Exception:
            pname = u''
        if not pname:
            continue
        is_host_offset = False
        try:
            if u'offset from host' in pname:
                is_host_offset = True
            elif (u'смещ' in pname and (u'основ' in pname or u'хост' in pname)):
                is_host_offset = True
            elif (u'offset' in pname and (u'host' in pname or u'base' in pname)):
                is_host_offset = True
        except Exception:
            is_host_offset = False
        if not is_host_offset:
            continue
        if _try_set(p):
            return True

    return False


def _set_element_level_param(elem, level):
    if elem is None or level is None:
        return False

    level_id = None
    try:
        level_id = level.Id
    except Exception:
        level_id = None
    if level_id is None:
        return False

    bips = []
    for bip_name in (
        'FAMILY_LEVEL_PARAM',
        'INSTANCE_REFERENCE_LEVEL_PARAM',
        'SCHEDULE_LEVEL_PARAM',
        'LEVEL_PARAM',
    ):
        try:
            bip = getattr(DB.BuiltInParameter, bip_name, None)
        except Exception:
            bip = None
        if bip is not None:
            bips.append(bip)

    for bip in bips:
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
        if p is None:
            continue
        try:
            if p.IsReadOnly or p.StorageType != DB.StorageType.ElementId:
                continue
            p.Set(level_id)
            return True
        except Exception:
            continue

    for pname in (u'Уровень', u'Базовый уровень', u'Reference Level', u'Level'):
        try:
            p = elem.LookupParameter(pname)
        except Exception:
            p = None
        if p is None:
            continue
        try:
            if p.IsReadOnly or p.StorageType != DB.StorageType.ElementId:
                continue
            p.Set(level_id)
            return True
        except Exception:
            continue

    # Last resort: try any writable ElementId parameter that points to a Level.
    try:
        doc = elem.Document
        params = list(elem.Parameters)
    except Exception:
        doc = None
        params = []
    if doc is not None and params:
        for p in params:
            if p is None:
                continue
            try:
                if p.IsReadOnly or p.StorageType != DB.StorageType.ElementId:
                    continue
            except Exception:
                continue
            pname = u''
            try:
                pname = (p.Definition.Name or u'').strip().lower()
            except Exception:
                pname = u''
            if not pname:
                continue
            if (u'уров' not in pname) and (u'level' not in pname):
                continue
            try:
                cur = p.AsElementId()
            except Exception:
                cur = None
            looks_like_level_ref = False
            if cur and cur != DB.ElementId.InvalidElementId:
                try:
                    cur_elem = doc.GetElement(cur)
                    looks_like_level_ref = isinstance(cur_elem, DB.Level)
                except Exception:
                    looks_like_level_ref = False
            else:
                looks_like_level_ref = True
            if not looks_like_level_ref:
                continue
            try:
                p.Set(level_id)
                return True
            except Exception:
                continue
    return False


def _set_instance_elevation_from_level(elem, target_z, level):
    if elem is None or target_z is None or level is None:
        return False
    try:
        off = float(target_z) - float(level.Elevation)
    except Exception:
        return False

    try:
        p = elem.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
    except Exception:
        p = None
    if p is not None:
        try:
            if (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(float(off))
                return True
        except Exception:
            pass

    for pname in (
        u'Отметка от уровня',
        u'Смещение от уровня',
        u'Elevation from Level',
        u'Offset from Level',
    ):
        try:
            p = elem.LookupParameter(pname)
        except Exception:
            p = None
        if p is None:
            continue
        try:
            if (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(float(off))
                return True
        except Exception:
            continue
    return False


def _force_instance_level_and_z(doc, elem, target_level, target_z):
    if doc is None or elem is None:
        return False

    changed = False
    level_param_set = False
    offset_param_set = False
    try:
        if _set_element_level_param(elem, target_level):
            changed = True
            level_param_set = True
    except Exception:
        pass
    try:
        if _set_instance_elevation_from_level(elem, target_z, target_level):
            changed = True
            offset_param_set = True
    except Exception:
        pass

    # Regenerate before reading location.
    # For some OneLevelBased families, location may be stale right after setting params,
    # and immediate MoveElement can double-shift in Z.
    if level_param_set or offset_param_set:
        try:
            doc.Regenerate()
        except Exception:
            pass

    # Keep geometry at target Z even if level/offset params are not writable.
    try:
        p0 = _instance_point(elem)
    except Exception:
        p0 = None
    if p0 is not None and target_z is not None:
        try:
            dz = float(target_z) - float(p0.Z)
            tol_ft = float(mm_to_ft(3.0) or 0.0)
            if tol_ft <= 1e-9:
                tol_ft = 1e-6
            if abs(dz) > tol_ft:
                DB.ElementTransformUtils.MoveElement(doc, elem.Id, DB.XYZ(0.0, 0.0, dz))
                changed = True
        except Exception:
            pass

    return changed


def _wall_width_ft(wall):
    if wall is None:
        return None
    try:
        w = float(getattr(wall, 'Width', 0.0) or 0.0)
        if w > 1e-9:
            return w
    except Exception:
        pass
    try:
        p = wall.get_Parameter(DB.BuiltInParameter.WALL_ATTR_WIDTH_PARAM)
        if p is not None:
            w = float(p.AsDouble() or 0.0)
            if w > 1e-9:
                return w
    except Exception:
        pass
    return None


def _shift_point_from_wall_centerline(wall, centerline_pt, toward_pt, inset_mm=5.0):
    """Move point from wall centerline to nearest side toward shaft center."""
    if wall is None or centerline_pt is None or toward_pt is None:
        return centerline_pt

    w = _wall_width_ft(wall)
    if w is None:
        return centerline_pt

    try:
        vx = float(toward_pt.X) - float(centerline_pt.X)
        vy = float(toward_pt.Y) - float(centerline_pt.Y)
        ln = ((vx * vx) + (vy * vy)) ** 0.5
    except Exception:
        return centerline_pt
    if ln <= 1e-9:
        return centerline_pt

    try:
        inset_ft = float(mm_to_ft(inset_mm) or 0.0)
    except Exception:
        inset_ft = 0.0
    shift = max(0.0, (float(w) * 0.5) - inset_ft)
    if shift <= 1e-9:
        return centerline_pt

    try:
        ux = vx / ln
        uy = vy / ln
        return DB.XYZ(
            float(centerline_pt.X) + ux * shift,
            float(centerline_pt.Y) + uy * shift,
            float(centerline_pt.Z),
        )
    except Exception:
        return centerline_pt


def _collect_link_door_points_host(link_doc, transform_host_from_link, limit=None):
    pts = []
    if link_doc is None:
        return pts
    for d in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, limit=limit, level_id=None):
        p = None
        try:
            loc = getattr(d, 'Location', None)
            p = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            p = None
        if p is None:
            continue
        try:
            hp = transform_host_from_link.OfPoint(p) if transform_host_from_link is not None else p
            pts.append(hp)
        except Exception:
            continue
    return pts


def _instance_point(elem):
    if elem is None:
        return None
    try:
        loc = getattr(elem, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is not None:
            return pt
    except Exception:
        pass
    try:
        bb = elem.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        return None
    try:
        return DB.XYZ(
            (float(bb.Min.X) + float(bb.Max.X)) * 0.5,
            (float(bb.Min.Y) + float(bb.Max.Y)) * 0.5,
            (float(bb.Min.Z) + float(bb.Max.Z)) * 0.5,
        )
    except Exception:
        return None


def _element_level(doc, elem):
    if doc is None or elem is None:
        return None

    # Prefer explicit level parameters over LevelId.
    # Some fixture families keep LevelId at Level 1 while real reference level is stored in params.
    for bip_name in ('FAMILY_LEVEL_PARAM', 'INSTANCE_REFERENCE_LEVEL_PARAM', 'SCHEDULE_LEVEL_PARAM', 'LEVEL_PARAM'):
        try:
            bip = getattr(DB.BuiltInParameter, bip_name, None)
        except Exception:
            bip = None
        if bip is None:
            continue
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
        if p is None:
            continue
        try:
            lid = p.AsElementId()
        except Exception:
            lid = None
        if not lid or lid == DB.ElementId.InvalidElementId:
            continue
        try:
            lvl = doc.GetElement(lid)
        except Exception:
            lvl = None
        if lvl is not None:
            return lvl

    try:
        lid = getattr(elem, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId:
            lvl = doc.GetElement(lid)
            if lvl is not None:
                return lvl
    except Exception:
        pass
    return None


def _nearest_level_from_list(levels, z_ft):
    if not levels:
        return None
    best = None
    best_d = None
    for lvl in levels:
        if lvl is None:
            continue
        try:
            d = abs(float(lvl.Elevation) - float(z_ft))
        except Exception:
            continue
        if best is None or d < best_d:
            best = lvl
            best_d = d
    return best


def _pick_family_center_xy(elem, bmin, bmax, fallback_center):
    """Pick reliable XY center for lift family instance.

    Prefer bbox center, but fallback to insertion point when bbox center is clearly invalid.
    """
    if fallback_center is None:
        return None

    try:
        bbox_cx = (float(bmin.X) + float(bmax.X)) * 0.5
        bbox_cy = (float(bmin.Y) + float(bmax.Y)) * 0.5
    except Exception:
        bbox_cx = None
        bbox_cy = None

    ins_pt = _instance_point(elem)
    if bbox_cx is None or bbox_cy is None:
        if ins_pt is not None:
            try:
                return DB.XYZ(float(ins_pt.X), float(ins_pt.Y), float(fallback_center.Z))
            except Exception:
                return fallback_center
        return fallback_center

    # If bbox center is too far from insertion point, treat bbox as unreliable.
    # This happens in some 2D families where bbox may not represent real instance location.
    if ins_pt is not None:
        try:
            dx = float(bbox_cx) - float(ins_pt.X)
            dy = float(bbox_cy) - float(ins_pt.Y)
            d = (dx * dx + dy * dy) ** 0.5
            max_ok = float(mm_to_ft(4000) or 0.0)
            if max_ok > 0.0 and d > max_ok:
                return DB.XYZ(float(ins_pt.X), float(ins_pt.Y), float(fallback_center.Z))
        except Exception:
            pass

    try:
        return DB.XYZ(float(bbox_cx), float(bbox_cy), float(fallback_center.Z))
    except Exception:
        return fallback_center


def _bbox_union(min_a, max_a, min_b, max_b):
    if min_a is None or max_a is None:
        return min_b, max_b
    if min_b is None or max_b is None:
        return min_a, max_a
    try:
        return (
            DB.XYZ(
                min(float(min_a.X), float(min_b.X)),
                min(float(min_a.Y), float(min_b.Y)),
                min(float(min_a.Z), float(min_b.Z)),
            ),
            DB.XYZ(
                max(float(max_a.X), float(max_b.X)),
                max(float(max_a.Y), float(max_b.Y)),
                max(float(max_a.Z), float(max_b.Z)),
            ),
        )
    except Exception:
        return min_a, max_a


def _collect_existing_tagged_instances(host_doc, tag_value):
    out = []
    if host_doc is None or not tag_value:
        return out
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        try:
            rule = DB.FilterStringRule(provider, DB.FilterStringContains(), tag_value)
        except Exception:
            rule = DB.FilterStringRule(provider, DB.FilterStringContains(), tag_value, False)
        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .OfClass(DB.FamilyInstance)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))
        for e in col:
            p = _instance_point(e)
            if p is None:
                continue
            out.append((e, p))
    except Exception:
        pass
    return out


def collect_shafts_from_openings_and_generic(link_doc, rx_inc, rx_exc, limit, min_height_ft=None):
    shafts = []
    processed_openings = 0
    skipped_openings_bbox = 0
    skipped_openings_height = 0
    processed_generic = 0
    skipped_generic_name = 0
    skipped_generic_bbox = 0
    skipped_generic_height = 0

    for e in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_ShaftOpening, limit=limit, level_id=None):
        processed_openings += 1
        center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
        if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
            skipped_openings_bbox += 1
            continue
        if min_height_ft is not None:
            try:
                if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                    skipped_openings_height += 1
                    continue
            except Exception:
                pass
        shafts.append({'name': u'ShaftOpening', 'center': center, 'zmin': zmin, 'zmax': zmax,
                       'bbox_min': bmin, 'bbox_max': bmax})

    if rx_inc or rx_exc:
        for e in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_GenericModel, limit=limit, level_id=None):
            processed_generic += 1
            txt = socket_utils._elem_text(e) or u''
            if rx_inc and (not socket_utils._match_any(rx_inc, txt)):
                skipped_generic_name += 1
                continue
            if rx_exc and socket_utils._match_any(rx_exc, txt):
                skipped_generic_name += 1
                continue

            center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
            if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
                skipped_generic_bbox += 1
                continue
            if min_height_ft is not None:
                try:
                    if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                        skipped_generic_height += 1
                        continue
                except Exception:
                    pass
            shafts.append({'name': txt or u'GenericModel', 'center': center, 'zmin': zmin, 'zmax': zmax,
                           'bbox_min': bmin, 'bbox_max': bmax})

    return (shafts, processed_openings, skipped_openings_bbox,
            skipped_openings_height, processed_generic, skipped_generic_name,
            skipped_generic_bbox, skipped_generic_height)


def collect_shafts_from_families(link_doc, rx_inc, rx_exc, limit, min_height_ft=None, exact_names=None):
    """Collect shaft volumes from family instances (GenericModel + Furniture) by name patterns."""
    shafts = []
    processed = 0
    skipped_name = 0
    skipped_bbox = 0
    skipped_height = 0

    for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Furniture):
        for e in link_reader.iter_elements_by_category(link_doc, bic, limit=limit, level_id=None):
            processed += 1
            txt = socket_utils._elem_text(e) or u''
            if exact_names:
                if not match_exact_names(txt, exact_names):
                    skipped_name += 1
                    continue
            else:
                if rx_inc and (not socket_utils._match_any(rx_inc, txt)):
                    skipped_name += 1
                    continue
                if rx_exc and socket_utils._match_any(rx_exc, txt):
                    skipped_name += 1
                    continue

            center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
            if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
                skipped_bbox += 1
                continue
            center = _pick_family_center_xy(e, bmin, bmax, center)
            if min_height_ft is not None:
                try:
                    if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                        skipped_height += 1
                        continue
                except Exception:
                    pass
            link_level = _element_level(link_doc, e)
            shafts.append({'name': txt or u'Family', 'center': center, 'zmin': zmin, 'zmax': zmax,
                           'bbox_min': bmin, 'bbox_max': bmax, 'link_level': link_level})

    return shafts, processed, skipped_name, skipped_bbox, skipped_height


def iter_loaded_link_docs(doc, parent_transform=None, max_depth=2, visited=None, depth=0):
    """Yield (link_instance, link_doc, cumulative_transform, is_nested)."""
    if doc is None:
        return
    if visited is None:
        visited = set()

    try:
        key = doc.PathName or doc.Title
    except Exception:
        key = None
    if key:
        if key in visited:
            return
        visited.add(key)

    try:
        links = link_reader.list_link_instances(doc)
    except Exception:
        links = []

    for ln in links:
        try:
            if not link_reader.is_link_loaded(ln):
                continue
        except Exception:
            continue
        try:
            ld = link_reader.get_link_doc(ln)
        except Exception:
            ld = None
        if ld is None:
            continue
        try:
            t = link_reader.get_total_transform(ln)
        except Exception:
            t = DB.Transform.Identity
        if parent_transform is not None:
            try:
                t = parent_transform.Multiply(t)
            except Exception:
                pass
        yield ln, ld, t, (depth > 0)
        if max_depth and max_depth > 1:
            for sub in iter_loaded_link_docs(ld, parent_transform=t, max_depth=max_depth - 1, visited=visited, depth=depth + 1):
                yield sub


def find_link_with_families(host_doc, rx_inc, rx_exc, limit, min_height_ft, exact_names, max_depth=2):
    """Find the first loaded link (or nested link) that contains any of the exact family/type names."""
    if host_doc is None or not exact_names:
        return None, None, None, None, 0, 0, 0, 0

    for ln, ld, t, is_nested in iter_loaded_link_docs(host_doc, parent_transform=None, max_depth=max_depth):
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            ld, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
        )
        if shafts_fam:
            # If nested link, avoid linked-wall hosting (link_inst not valid in host doc)
            return (None if is_nested else ln), ld, t, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height
    return None, None, None, None, 0, 0, 0, 0


def find_link_doc_with_families(link_doc, base_transform, rx_inc, rx_exc, limit, min_height_ft, exact_names, max_depth=2):
    """Search selected link doc and its nested links for families; return doc + transform."""
    if link_doc is None or not exact_names:
        return None, None, None, 0, 0, 0, 0

    shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
        link_doc, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
    )
    if shafts_fam:
        return link_doc, base_transform, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height

    for ln, ld, t, _ in iter_loaded_link_docs(link_doc, parent_transform=base_transform, max_depth=max_depth):
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            ld, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
        )
        if shafts_fam:
            return ld, t, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height

    return None, None, None, 0, 0, 0, 0


def sorted_levels(doc):
    lvls = link_reader.list_levels(doc)
    try:
        return sorted([l for l in lvls if l], key=lambda x: float(x.Elevation))
    except Exception:
        return lvls


_BS_KEY_PATTERNS = (
    re.compile(u'(?:^|[^0-9a-zа-я])(бс|bs)\\s*[-_.]?\\s*0*(\\d{1,3})(?:$|[^0-9a-zа-я])', re.IGNORECASE | re.UNICODE),
    re.compile(u'(?:^|[^0-9a-zа-я])(блок\\s*секц(?:ия)?|block\\s*section|секц(?:ия)?|section)\\s*[-_.]?\\s*0*(\\d{1,3})(?:$|[^0-9a-zа-я])', re.IGNORECASE | re.UNICODE),
)
_FLOOR_NO_PATTERNS = (
    re.compile(u'(?:^|[^0-9a-zа-я])(э|этаж|fl|floor)\\s*[-_.]?\\s*0*(\\d{1,3})(?:$|[^0-9a-zа-я])', re.IGNORECASE | re.UNICODE),
    re.compile(u'^\\s*0*(\\d{1,3})\\s*(?:этаж|fl|floor)\\b', re.IGNORECASE | re.UNICODE),
    # Common AR naming: "31_+0.000", "32_+3.150", etc.
    re.compile(u'^\\s*0*(\\d{1,3})(?:\\s*[_\\-].*)?$', re.IGNORECASE | re.UNICODE),
)


def _norm_text(v):
    if v is None:
        return u''
    try:
        t = (v or u'').strip().lower()
    except Exception:
        t = u''
    try:
        t = t.replace(u'ё', u'е')
    except Exception:
        pass
    return t


def _norm_level_name(name):
    try:
        return (name or '').strip().lower()
    except Exception:
        return ''


def _extract_bs_keys(text):
    txt = _norm_text(text)
    if not txt:
        return set()

    out = set()
    for rx in _BS_KEY_PATTERNS:
        try:
            for m in rx.finditer(txt):
                if not m:
                    continue
                if m.lastindex and m.lastindex >= 2:
                    raw_num = m.group(2)
                else:
                    raw_num = m.group(1)
                if not raw_num:
                    continue
                try:
                    out.add(str(int(raw_num)))
                except Exception:
                    continue
        except Exception:
            continue
    return out


def _extract_floor_no(text):
    txt = _norm_text(text)
    if not txt:
        return None
    for rx in _FLOOR_NO_PATTERNS:
        try:
            m = rx.search(txt)
        except Exception:
            m = None
        if not m:
            continue
        raw = None
        try:
            li = int(m.lastindex or 0)
        except Exception:
            li = 0
        if li > 0:
            for gi in range(li, 0, -1):
                try:
                    g = m.group(gi)
                except Exception:
                    g = None
                if not g:
                    continue
                raw = g
                break
        if not raw:
            try:
                raw = m.group(1)
            except Exception:
                raw = None
        if not raw:
            continue
        try:
            return int(raw)
        except Exception:
            continue
    return None


def _build_host_level_index(doc):
    levels = sorted_levels(doc)
    by_name = {}
    for lvl in levels:
        if lvl is None:
            continue
        try:
            key = _norm_level_name(getattr(lvl, 'Name', None))
        except Exception:
            key = ''
        if key and key not in by_name:
            by_name[key] = lvl
    return levels, by_name


def _link_level_to_host_elevation(link_level, link_transform):
    if link_level is None:
        return None
    try:
        z = float(link_level.Elevation)
    except Exception:
        return None
    try:
        if link_transform is not None:
            z = float(link_transform.OfPoint(DB.XYZ(0.0, 0.0, z)).Z)
    except Exception:
        pass
    return z


def _find_level_by_elevation(levels, target_z_ft, tol_ft):
    if not levels:
        return None
    best = None
    best_d = None
    for lvl in levels:
        if lvl is None:
            continue
        try:
            d = abs(float(lvl.Elevation) - float(target_z_ft))
        except Exception:
            continue
        if best is None or d < best_d:
            best = lvl
            best_d = d
    if best is None:
        return None
    try:
        if float(best_d) <= float(tol_ft):
            return best
    except Exception:
        pass
    return None


def _ensure_host_levels_from_link_levels(
    doc,
    selected_link_levels,
    link_transform,
    tol_mm=20.0,
    temporary=False,
    name_prefix=u'AUTO_EOM_TMP_LIFT_LEVEL_',
):
    if doc is None:
        return []
    try:
        levels_src = list(selected_link_levels or [])
    except Exception:
        levels_src = []
    if not levels_src:
        return []

    tol_ft = mm_to_ft(tol_mm) or 0.0
    if tol_ft <= 1e-9:
        tol_ft = mm_to_ft(20.0) or 1e-6

    host_levels, _ = _build_host_level_index(doc)
    used_names = set()
    for lvl in host_levels:
        if lvl is None:
            continue
        try:
            used_names.add(_norm_level_name(getattr(lvl, 'Name', None)))
        except Exception:
            continue

    planned = []
    planned_elevs = []
    for ll in levels_src:
        hz = _link_level_to_host_elevation(ll, link_transform)
        if hz is None:
            continue

        if _find_level_by_elevation(host_levels, hz, tol_ft) is not None:
            continue

        duplicate_plan = False
        for ez in planned_elevs:
            try:
                if abs(float(ez) - float(hz)) <= float(tol_ft):
                    duplicate_plan = True
                    break
            except Exception:
                continue
        if duplicate_plan:
            continue

        try:
            base_name = (getattr(ll, 'Name', u'') or u'').strip()
        except Exception:
            base_name = u''
        if not base_name:
            base_name = u'Уровень из связи'

        candidate = base_name
        norm_candidate = _norm_level_name(candidate)
        if norm_candidate in used_names:
            idx = 2
            while True:
                candidate2 = u'{0} (АР {1})'.format(base_name, idx)
                norm2 = _norm_level_name(candidate2)
                if norm2 not in used_names:
                    candidate = candidate2
                    norm_candidate = norm2
                    break
                idx += 1
                if idx > 500:
                    break

        planned.append((float(hz), candidate))
        planned_elevs.append(float(hz))
        used_names.add(norm_candidate)

    if not planned:
        return []

    created = []
    tx_name = 'ЭОМ: Создание уровней из связи АР'
    if temporary:
        tx_name = 'ЭОМ: Временные уровни из связи АР'
    with tx(tx_name, doc=doc, swallow_warnings=True):
        for i, (hz, nm) in enumerate(sorted(planned, key=lambda x: x[0]), 1):
            try:
                lvl_new = DB.Level.Create(doc, float(hz))
            except Exception:
                lvl_new = None
            if lvl_new is None:
                continue
            try:
                final_name = nm
                if temporary:
                    final_name = u'{0}{1:02d}_{2}'.format(name_prefix or u'', i, nm)
                lvl_new.Name = final_name
            except Exception:
                pass
            created.append(lvl_new)
    return created


def _resolve_host_level_from_link_level(link_level, host_levels_by_name, doc, link_transform):
    if link_level is None:
        return None

    by_name = None
    try:
        key = _norm_level_name(getattr(link_level, 'Name', None))
        if key:
            by_name = host_levels_by_name.get(key)
    except Exception:
        by_name = None
    if by_name is not None:
        return by_name

    try:
        lvl_elev = float(link_level.Elevation)
    except Exception:
        return None

    try:
        if link_transform is not None:
            lvl_elev = float(link_transform.OfPoint(DB.XYZ(0.0, 0.0, lvl_elev)).Z)
    except Exception:
        pass

    try:
        return find_nearest_level(doc, lvl_elev)
    except Exception:
        return None


def _resolve_host_levels_for_shaft(shaft_data, selected_levels_meta, host_levels_by_name, doc, link_transform, fallback_levels):
    if not selected_levels_meta:
        return list(fallback_levels or []), False, set()

    shaft_name = u''
    try:
        shaft_name = shaft_data.get('name', u'') or u''
    except Exception:
        shaft_name = u''
    shaft_bs_keys = _extract_bs_keys(shaft_name)

    scoped_meta = None
    if shaft_bs_keys:
        scoped = []
        for item in selected_levels_meta:
            lvl_keys = item.get('bs_keys', set()) or set()
            if lvl_keys and lvl_keys.intersection(shaft_bs_keys):
                scoped.append(item)
        if scoped:
            scoped_meta = scoped

    source_meta = scoped_meta if scoped_meta is not None else selected_levels_meta

    resolved = []
    used_ids = set()
    for item in source_meta:
        host_lvl = _resolve_host_level_from_link_level(
            item.get('level'),
            host_levels_by_name,
            doc,
            link_transform,
        )
        if host_lvl is None:
            continue
        try:
            hid = int(host_lvl.Id.IntegerValue)
        except Exception:
            hid = None
        if hid is None or hid in used_ids:
            continue
        used_ids.add(hid)
        resolved.append(host_lvl)

    if resolved:
        try:
            resolved = sorted(resolved, key=lambda x: float(x.Elevation))
        except Exception:
            pass
        return resolved, bool(scoped_meta is not None), shaft_bs_keys

    return list(fallback_levels or []), False, shaft_bs_keys


def get_or_create_debug_plan_view(doc, level, name, aliases=None):
    if doc is None or level is None:
        return None

    try:
        aliases = list(aliases or [])
    except Exception:
        aliases = []

    try:
        for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    return v
            except Exception:
                continue
    except Exception:
        pass

    if aliases:
        try:
            for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
                try:
                    if v and (not v.IsTemplate) and v.Name in aliases:
                        try:
                            v.Name = name
                        except Exception:
                            pass
                        return v
                except Exception:
                    continue
        except Exception:
            pass

    vft_id = None
    try:
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.FloorPlan:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
    except Exception:
        vft_id = None

    if vft_id is None:
        return None

    try:
        vplan = DB.ViewPlan.Create(doc, vft_id, level.Id)
    except Exception:
        return None

    try:
        vplan.Name = name
    except Exception:
        pass
    return vplan


def set_plan_view_range(vplan, cut_mm=3000, top_mm=12000, bottom_mm=-2000, depth_mm=-4000):
    if vplan is None:
        return
    try:
        vr = vplan.GetViewRange()
    except Exception:
        vr = None
    if vr is None:
        return

    try:
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, mm_to_ft(top_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.CutPlane, mm_to_ft(cut_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, mm_to_ft(bottom_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, mm_to_ft(depth_mm) or 0.0)
    except Exception:
        pass

    try:
        vplan.SetViewRange(vr)
    except Exception:
        pass


def as_net_id_list(ids):
    try:
        from System.Collections.Generic import List
        lst = List[DB.ElementId]()
        for i in ids or []:
            try:
                if i is not None:
                    lst.Add(i)
            except Exception:
                continue
        return lst
    except Exception:
        return None


def open_debug_plans(uidoc, doc, created_elems):
    if not created_elems:
        return

    level_map = {}
    for e in created_elems:
        if e is None:
            continue
        lvl = None
        try:
            lid = e.LevelId
            if lid and lid != DB.ElementId.InvalidElementId:
                lvl = doc.GetElement(lid)
        except Exception:
            lvl = None

        if lvl is None:
            try:
                loc = getattr(e, 'Location', None)
                pt = loc.Point if loc and hasattr(loc, 'Point') else None
                if pt is not None:
                    lvl = find_nearest_level(doc, pt.Z)
            except Exception:
                lvl = None

        if lvl is None:
            continue

        key = int(lvl.Id.IntegerValue)
        level_map.setdefault(key, (lvl, []))
        level_map[key][1].append(e)

    if not level_map:
        return

    first_view = None
    with tx('ЭОМ: Отладочные планы шахт лифта', doc=doc, swallow_warnings=True):
        for _, (lvl, elems) in sorted(level_map.items(), key=lambda x: x[0]):
            name = u'ЭОМ_ОТЛАДКА_ШахтаЛифта_План_{0}'.format(lvl.Name)
            vplan = get_or_create_debug_plan_view(doc, lvl, name)
            if not vplan:
                continue

            try:
                vplan.ViewTemplateId = DB.ElementId.InvalidElementId
            except Exception:
                pass
            try:
                vplan.DetailLevel = DB.ViewDetailLevel.Fine
            except Exception:
                pass

            set_plan_view_range(vplan)

            ids = [e.Id for e in elems if e]
            id_list = as_net_id_list(ids)
            if id_list is not None:
                try:
                    vplan.IsolateElementsTemporary(id_list)
                except Exception:
                    pass

            if first_view is None:
                first_view = vplan

    if first_view is None:
        return

    try:
        uidoc.ActiveView = first_view
        try:
            uidoc.RefreshActiveView()
            views = uidoc.GetOpenUIViews()
            if views:
                views[0].ZoomToFit()
        except Exception:
            pass
    except Exception:
        pass


def run_placement(doc, output, script_module):
    trace('Place_Lights_LiftShaft: start')
    output.print_md('# Размещение светильников в шахтах лифта')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))
    output.print_md('Алгоритм: `liftshaft-v2026.02.18.13`')

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    scan_limit_rooms = int(rules.get('scan_limit_rooms', 500) or 500)
    max_place = int(rules.get('max_place_count', 200) or 200)
    batch_size = int(rules.get('batch_size', 25) or 25)

    model_keywords = rules.get('lift_shaft_generic_model_keywords', None)
    if not model_keywords:
        model_keywords = rules.get('lift_shaft_room_name_patterns', []) or []
    exact_family_names = rules.get('lift_shaft_family_names', []) or []
    exclude_patterns = rules.get('lift_shaft_generic_model_exclude_patterns', None)
    if exclude_patterns is None:
        exclude_patterns = rules.get('lift_shaft_room_exclude_patterns', []) or []
    min_height_mm = float(rules.get('lift_shaft_min_height_mm', 2000) or 2000)
    edge_offset_mm = float(rules.get('lift_shaft_edge_offset_mm', 500) or 500)
    floor_place_offset_mm = float(rules.get('lift_shaft_floor_place_offset_mm', 900) or 900)
    if floor_place_offset_mm < 0.0:
        floor_place_offset_mm = 0.0
    # User rule: edge lights must be within 500mm from top/bottom of the shaft
    if edge_offset_mm > 500.0:
        edge_offset_mm = 500.0
    center_only_mode = bool(rules.get('lift_shaft_center_only_mode', False))
    one_row_xy_dedupe_mm = float(rules.get('lift_shaft_one_row_xy_dedupe_mm', 1200) or 1200)
    min_wall_clear_mm = float(rules.get('lift_shaft_min_wall_clearance_mm', 0) or 0)
    wall_search_mm = float(rules.get('lift_shaft_wall_search_mm', rules.get('host_wall_search_mm', 300)) or 300)
    dedupe_mm = rules.get('lift_shaft_dedupe_radius_mm', rules.get('dedupe_radius_mm', 500))
    enable_existing_dedupe = bool(rules.get('enable_existing_dedupe', False))
    link_search_depth = int(rules.get('lift_shaft_link_search_depth', 4) or 4)

    # For lift family workflow we must place per floor (+ top/bottom points),
    # not collapse to a single center point in XY.
    if exact_family_names:
        center_only_mode = False

    fams = rules.get('family_type_names', {}) or {}
    type_names = fams.get('light_lift_shaft') or fams.get('light_ceiling_point') or None

    rx_inc = socket_utils._compile_patterns(model_keywords)
    rx_exc = socket_utils._compile_patterns(exclude_patterns)

    cfg = script_module.get_config()
    symbol = pick_light_symbol(doc, cfg, type_names)
    if symbol is None:
        alert('Не найден тип светильника для шахты лифта. Загрузите тип из rules.default.json (family_type_names.light_lift_shaft).')
        return

    if not check_symbol_compatibility(symbol):
        return
    is_wall_symbol = is_wall_hosted(symbol)
    is_one_level_symbol = is_one_level_based(symbol)

    try:
        store_symbol_id(cfg, 'last_light_lift_shaft_symbol_id', symbol)
        store_symbol_unique_id(cfg, 'last_light_lift_shaft_symbol_uid', symbol)
        script_module.save_config()
    except Exception:
        pass

    min_height_ft = mm_to_ft(min_height_mm) or 0.0
    edge_offset_ft = mm_to_ft(edge_offset_mm) or 0.0
    floor_place_offset_ft = mm_to_ft(floor_place_offset_mm) or 0.0
    one_row_xy_dedupe_ft = mm_to_ft(one_row_xy_dedupe_mm) or 0.0
    min_wall_clear_ft = mm_to_ft(min_wall_clear_mm) or 0.0
    wall_search_ft = mm_to_ft(wall_search_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0
    edge_group_xy_tol_mm = float(rules.get('lift_shaft_edge_group_xy_tolerance_mm', 600) or 600)
    edge_group_xy_tol_ft = mm_to_ft(edge_group_xy_tol_mm) or 0.0
    if edge_group_xy_tol_ft <= 1e-9:
        edge_group_xy_tol_ft = mm_to_ft(600) or 1.0
    fam_min_height_ft = None if exact_family_names else min_height_ft
    group_edge_mode = bool((not center_only_mode) and exact_family_names and is_one_level_symbol)
    use_link_level_floor_mode = bool((not center_only_mode) and exact_family_names)

    # Auto-detect link by exact family names if provided
    link_inst = None
    link_doc = None
    link_transform = None
    shafts_fam = None
    processed_fam = skipped_fam_name = skipped_fam_bbox = skipped_fam_height = 0
    if exact_family_names:
        # Scan all loaded links without limit to find the target lift families
        link_inst, link_doc, link_transform, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = find_link_with_families(
            doc, rx_inc, rx_exc, None, fam_min_height_ft, exact_family_names, max_depth=link_search_depth
        )
        # If not found in any link, try current (host) model
        if not shafts_fam:
            try:
                shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
                    doc, rx_inc, rx_exc, None, min_height_ft=fam_min_height_ft, exact_names=exact_family_names
                )
                if shafts_fam:
                    link_inst = None
                    link_doc = doc
                    link_transform = None
            except Exception:
                pass

    if link_inst is None and link_doc is None:
        link_inst = socket_utils._select_link_instance_ru(doc, 'Выберите связь АР')
        if link_inst is None:
            output.print_md('**Отменено.**')
            return

        if not link_reader.is_link_loaded(link_inst):
            alert('Связь не загружена. Загрузите её в Manage Links и повторите.')
            return

        link_doc = link_reader.get_link_doc(link_inst)
        if link_doc is None:
            alert('Не удалось получить документ связи. Проверьте загрузку связи.')
            return

        if exact_family_names:
            base_t = link_reader.get_total_transform(link_inst)
            # Do not limit when exact list provided; search selected link + nested
            selected_link_doc = link_doc
            link_doc_found, link_transform_found, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = find_link_doc_with_families(
                link_doc, base_t, rx_inc, rx_exc, None, fam_min_height_ft, exact_family_names, max_depth=link_search_depth
            )
            if link_doc_found is not None:
                link_doc = link_doc_found
                link_transform = link_transform_found
                # If family found in nested link, linked-wall hosting is unsafe; disable it
                try:
                    if selected_link_doc is not link_doc:
                        link_inst = None
                except Exception:
                    link_inst = None

    if link_transform is not None:
        t = link_transform
        try:
            t_inv = t.Inverse
        except Exception:
            t_inv = None
    elif link_inst is None:
        try:
            t = DB.Transform.Identity
            t_inv = DB.Transform.Identity
        except Exception:
            t = None
            t_inv = None
    else:
        t = link_reader.get_total_transform(link_inst)
        try:
            t_inv = t.Inverse
        except Exception:
            t_inv = None

    # Prefer family-based shaft volumes (GenericModel/Furniture). If found, ignore ShaftOpening.
    if shafts_fam is None:
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            link_doc, rx_inc, rx_exc, (None if exact_family_names else scan_limit_rooms), min_height_ft=fam_min_height_ft, exact_names=exact_family_names
        )
    if exact_family_names:
        if not shafts_fam:
            alert(u'Не найдены семейства лифта по списку: {0}'.format(u', '.join(exact_family_names)))
            return
        shafts = shafts_fam
        processed_openings = skipped_openings = skipped_openings_height = 0
        processed_generic = skipped_generic_name = skipped_generic_bbox = skipped_generic_height = 0
        processed_families = processed_fam
        skipped_families_name = skipped_fam_name
        skipped_families_bbox = skipped_fam_bbox
        skipped_families_height = skipped_fam_height
    elif shafts_fam:
        shafts = shafts_fam
        processed_openings = skipped_openings = skipped_openings_height = 0
        processed_generic = skipped_generic_name = skipped_generic_bbox = skipped_generic_height = 0
        processed_families = processed_fam
        skipped_families_name = skipped_fam_name
        skipped_families_bbox = skipped_fam_bbox
        skipped_families_height = skipped_fam_height
    else:
        processed_families = skipped_families_name = skipped_families_bbox = skipped_families_height = 0
        (shafts, processed_openings, skipped_openings, skipped_openings_height,
         processed_generic, skipped_generic_name, skipped_generic_bbox, skipped_generic_height) = collect_shafts_from_openings_and_generic(
            link_doc, rx_inc, rx_exc, scan_limit_rooms, min_height_ft=min_height_ft
        )

    if not shafts:
        alert('Не найдены шахты лифта в связи АР (ShaftOpening и Generic Model).')
        return

    selected_link_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_link_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
        return
    level_transform = t
    level_transform_source = 'shaft_link'
    try:
        lvl0 = None
        for _lv in (selected_link_levels or []):
            if _lv is not None:
                lvl0 = _lv
                break
        lvl_doc = getattr(lvl0, 'Document', None) if lvl0 is not None else None
        same_doc = False
        try:
            same_doc = (lvl_doc is link_doc)
        except Exception:
            same_doc = False
        if (not same_doc) and (lvl_doc is not None):
            sel_link = getattr(magic_context, 'SELECTED_LINK', None)
            if sel_link is not None:
                sel_doc = link_reader.get_link_doc(sel_link)
                doc_match = False
                try:
                    doc_match = (sel_doc is lvl_doc)
                except Exception:
                    doc_match = False
                if (not doc_match) and sel_doc is not None:
                    try:
                        p1 = getattr(sel_doc, 'PathName', None) or ''
                        p2 = getattr(lvl_doc, 'PathName', None) or ''
                        t1 = getattr(sel_doc, 'Title', None) or ''
                        t2 = getattr(lvl_doc, 'Title', None) or ''
                        if (p1 and p2 and p1 == p2) or ((not p1) and (not p2) and t1 and t1 == t2):
                            doc_match = True
                    except Exception:
                        doc_match = False
                if doc_match:
                    level_transform = link_reader.get_total_transform(sel_link)
                    level_transform_source = 'selected_link'
    except Exception:
        level_transform = t
        level_transform_source = 'shaft_link'

    host_levels_all, host_levels_by_name = _build_host_level_index(doc)
    permanent_host_levels = list(host_levels_all or [])
    temp_link_levels = []
    temp_link_level_ids = set()
    temp_levels_created_count = 0
    temp_levels_deleted_count = 0
    temp_levels_rehosted_count = 0

    # For OneLevelBased lift lights we keep stable placement by XYZ/offset only.
    # Temporary host levels from links caused side-effects (rehosting/noise in logs),
    # so keep them disabled unless explicitly forced in rules.
    use_temp_link_levels = False
    try:
        if bool(rules.get('lift_shaft_force_temp_link_levels', False)):
            use_temp_link_levels = True
    except Exception:
        use_temp_link_levels = False
    if use_temp_link_levels:
        try:
            temp_link_levels = _ensure_host_levels_from_link_levels(
                doc,
                selected_link_levels,
                t,
                tol_mm=float(rules.get('lift_shaft_level_match_tolerance_mm', 20) or 20),
                temporary=True,
                name_prefix=u'AUTO_EOM_TMP_LIFT_LEVEL_',
            )
        except Exception:
            temp_link_levels = []
        temp_levels_created_count = len(temp_link_levels or [])
        if temp_levels_created_count:
            try:
                temp_link_level_ids = set([int(l.Id.IntegerValue) for l in temp_link_levels if l is not None])
            except Exception:
                temp_link_level_ids = set()
            host_levels_all, host_levels_by_name = _build_host_level_index(doc)

    selected_levels_meta = []
    for lvl in selected_link_levels:
        if lvl is None:
            continue
        lvl_name = u''
        try:
            lvl_name = getattr(lvl, 'Name', u'') or u''
        except Exception:
            lvl_name = u''
        lvl_host_z = _link_level_to_host_elevation(lvl, t)
        selected_levels_meta.append({
            'level': lvl,
            'name': lvl_name,
            'bs_keys': _extract_bs_keys(lvl_name),
            'floor_no': _extract_floor_no(lvl_name),
            'host_z': _link_level_to_host_elevation(lvl, level_transform),
            'host_z_raw': lvl_host_z,
        })
    selected_levels_count = len(selected_levels_meta or [])
    selected_levels_with_floor_no = 0
    try:
        selected_levels_with_floor_no = len([i for i in (selected_levels_meta or []) if i.get('floor_no') is not None])
    except Exception:
        selected_levels_with_floor_no = 0

    default_levels = []
    used_level_ids = set()
    for item in selected_levels_meta:
        host_lvl = _resolve_host_level_from_link_level(item.get('level'), host_levels_by_name, doc, level_transform)
        if host_lvl is None:
            continue
        try:
            host_lvl_id = int(host_lvl.Id.IntegerValue)
        except Exception:
            host_lvl_id = None
        if host_lvl_id is None or host_lvl_id in used_level_ids:
            continue
        used_level_ids.add(host_lvl_id)
        default_levels.append(host_lvl)

    if default_levels:
        try:
            default_levels = sorted(default_levels, key=lambda x: float(x.Elevation))
        except Exception:
            pass

    if not default_levels:
        alert('Не удалось сопоставить выбранные уровни с уровнями модели ЭОМ.')
        return

    comment_value = '{0}:{1}'.format(comment_tag, LIGHT_LIFT_SHAFT_TAG)
    existing_tagged_pairs = _collect_existing_tagged_instances(doc, comment_value)
    existing_tagged_pts = [p for _, p in existing_tagged_pairs]

    idx = socket_utils._XYZIndex(cell_ft=5.0)
    idx_xy_row = socket_utils._XYZIndex(cell_ft=5.0)
    if enable_existing_dedupe:
        try:
            for p in existing_tagged_pts:
                idx.add(p.X, p.Y, p.Z)
                if center_only_mode and one_row_xy_dedupe_ft > 0.0:
                    idx_xy_row.add(p.X, p.Y, 0.0)
        except Exception:
            pass

    points = []
    replace_existing_ids = set()
    truncated = False
    skipped_dedupe = 0
    skipped_no_wall = 0
    skipped_place = 0
    placed_by_pref_xy_fallback = 0
    shafts_scoped_by_bs = 0
    shafts_bs_unmatched = 0
    shaft_edge_groups = {}
    edge_points_added = 0
    forced_level_fix_count = 0
    column_anchor_xy = {}
    floor_points_added = 0
    floor_points_from_link_levels = 0
    floor_points_from_shaft_families = 0
    floor_points_from_floor_numbers = 0
    floor_points_from_level_intervals = 0
    floor_level_splits_added = 0
    floor_levels_interpolated_by_number = 0

    with forms.ProgressBar(title='ЭОМ: Поиск шахт лифта', cancellable=True, step=1) as pb:
        pb.max_value = len(shafts)
        for i, sh in enumerate(shafts):
            pb.update_progress(i + 1, pb.max_value)
            if pb.cancelled:
                return

            center = sh.get('center')
            zmin = sh.get('zmin')
            zmax = sh.get('zmax')
            bmin = sh.get('bbox_min')
            bmax = sh.get('bbox_max')
            if center is None or zmin is None or zmax is None:
                continue

            try:
                host_c = t.OfPoint(center)
                host_zmin = t.OfPoint(DB.XYZ(float(center.X), float(center.Y), float(zmin))).Z
                host_zmax = t.OfPoint(DB.XYZ(float(center.X), float(center.Y), float(zmax))).Z
                host_bmin, host_bmax = transform_bbox(t, bmin, bmax)
            except Exception:
                continue

            if host_bmin is None or host_bmax is None:
                continue
            raw_host_bmin = host_bmin
            raw_host_bmax = host_bmax

            # Replace old auto-placed fixtures inside current shaft
            # so reruns always converge to current placement rules.
            if existing_tagged_pairs:
                for inst_old, ep in existing_tagged_pairs:
                    try:
                        if not bbox_contains_point(raw_host_bmin, raw_host_bmax, ep):
                            continue
                    except Exception:
                        continue
                    try:
                        replace_existing_ids.add(inst_old.Id)
                    except Exception:
                        continue

            wall_bbox_pad_ft = max(float(min_wall_clear_ft or 0.0), float(wall_search_ft or 0.0))
            host_bmin, host_bmax = expand_bbox_xy(host_bmin, host_bmax, wall_bbox_pad_ft)

            link_bmin = bmin
            link_bmax = bmax
            if link_bmin is None or link_bmax is None:
                continue
            link_bmin, link_bmax = expand_bbox_xy(link_bmin, link_bmax, wall_bbox_pad_ft)

            shaft_min = min(float(host_zmin), float(host_zmax))
            shaft_max = max(float(host_zmin), float(host_zmax))

            shaft_levels, scoped_by_bs, shaft_bs_keys = _resolve_host_levels_for_shaft(
                sh,
                selected_levels_meta,
                host_levels_by_name,
                doc,
                level_transform,
                default_levels,
            )
            host_level_hint = _resolve_host_level_from_link_level(
                sh.get('link_level'),
                host_levels_by_name,
                doc,
                t,
            )
            if scoped_by_bs:
                shafts_scoped_by_bs += 1
            elif shaft_bs_keys:
                shafts_bs_unmatched += 1

            try:
                bs_key = u'|'.join(sorted([k for k in (shaft_bs_keys or []) if k])) if shaft_bs_keys else u''
            except Exception:
                bs_key = u''
            try:
                key_x = int(round(float(host_c.X) / float(edge_group_xy_tol_ft)))
                key_y = int(round(float(host_c.Y) / float(edge_group_xy_tol_ft)))
            except Exception:
                key_x = key_y = 0
            col_key = (key_x, key_y, bs_key)
            anchor_xy = column_anchor_xy.get(col_key)
            if anchor_xy is None:
                try:
                    anchor_xy = DB.XYZ(float(host_c.X), float(host_c.Y), float(host_c.Z))
                except Exception:
                    anchor_xy = host_c
                column_anchor_xy[col_key] = anchor_xy
            placement_xy = DB.XYZ(float(anchor_xy.X), float(anchor_xy.Y), float(host_c.Z))

            if group_edge_mode:
                gk = (key_x, key_y, bs_key)
                rec = (shaft_min, shaft_max, placement_xy, host_bmin, host_bmax, link_bmin, link_bmax, host_level_hint)
                g = shaft_edge_groups.get(gk)
                if g is None:
                    shaft_edge_groups[gk] = {
                        'zmin': float(shaft_min),
                        'zmax': float(shaft_max),
                        'host_bmin': host_bmin,
                        'host_bmax': host_bmax,
                        'link_bmin': link_bmin,
                        'link_bmax': link_bmax,
                        'bs_keys': set(shaft_bs_keys or []),
                        'records': [rec],
                    }
                else:
                    try:
                        g['zmin'] = min(float(g.get('zmin', shaft_min)), float(shaft_min))
                        g['zmax'] = max(float(g.get('zmax', shaft_max)), float(shaft_max))
                    except Exception:
                        pass
                    try:
                        hbmin, hbmax = _bbox_union(g.get('host_bmin'), g.get('host_bmax'), host_bmin, host_bmax)
                        g['host_bmin'] = hbmin
                        g['host_bmax'] = hbmax
                    except Exception:
                        pass
                    try:
                        lbmin, lbmax = _bbox_union(g.get('link_bmin'), g.get('link_bmax'), link_bmin, link_bmax)
                        g['link_bmin'] = lbmin
                        g['link_bmax'] = lbmax
                    except Exception:
                        pass
                    try:
                        g.setdefault('records', []).append(rec)
                    except Exception:
                        pass
                    try:
                        keys = set(g.get('bs_keys') or set())
                        keys.update(set(shaft_bs_keys or []))
                        g['bs_keys'] = keys
                    except Exception:
                        pass

            if use_link_level_floor_mode:
                continue

            if shaft_max <= shaft_min + 1e-6:
                z_mid = shaft_min
                pt = DB.XYZ(float(placement_xy.X), float(placement_xy.Y), float(z_mid))
                lvl_mid = find_nearest_level(doc, z_mid) or _nearest_level_from_list(shaft_levels, z_mid) or host_level_hint
                if center_only_mode and one_row_xy_dedupe_ft > 0.0 and idx_xy_row.has_near(pt.X, pt.Y, 0.0, one_row_xy_dedupe_ft):
                    skipped_dedupe += 1
                elif dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                else:
                    if center_only_mode and one_row_xy_dedupe_ft > 0.0:
                        idx_xy_row.add(pt.X, pt.Y, 0.0)
                    idx.add(pt.X, pt.Y, pt.Z)
                    points.append((pt, lvl_mid, host_bmin, host_bmax, link_bmin, link_bmax))
                continue

            if center_only_mode:
                segments = [(shaft_min, shaft_max)]
            else:
                segments = segment_ranges(shaft_levels, shaft_min, shaft_max)
                if not segments:
                    segments = [(shaft_min, shaft_max)]

            # One light per level (segment middle)
            for seg_min, seg_max in segments:
                seg_h = float(seg_max) - float(seg_min)
                if seg_h <= 1e-6:
                    continue
                z_mid = seg_min + seg_h * 0.5
                pt = DB.XYZ(float(placement_xy.X), float(placement_xy.Y), float(z_mid))
                lvl_mid = find_nearest_level(doc, z_mid) or _nearest_level_from_list(shaft_levels, z_mid) or host_level_hint
                if center_only_mode and one_row_xy_dedupe_ft > 0.0 and idx_xy_row.has_near(pt.X, pt.Y, 0.0, one_row_xy_dedupe_ft):
                    skipped_dedupe += 1
                elif dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                else:
                    if center_only_mode and one_row_xy_dedupe_ft > 0.0:
                        idx_xy_row.add(pt.X, pt.Y, 0.0)
                    idx.add(pt.X, pt.Y, pt.Z)
                    points.append((pt, lvl_mid, host_bmin, host_bmax, link_bmin, link_bmax))

                if max_place > 0 and len(points) >= max_place:
                    truncated = True
                    break
            if truncated:
                break

            # Extra top/bottom points are optional; disabled in center-only mode.
            if (not center_only_mode) and (not is_one_level_symbol):
                if edge_offset_ft > 0.0:
                    z_list = [shaft_min + edge_offset_ft, shaft_max - edge_offset_ft]
                else:
                    z_list = [shaft_min, shaft_max]

                for z in z_list:
                    if z <= shaft_min + 1e-6:
                        z = shaft_min + 1e-6
                    if z >= shaft_max - 1e-6:
                        z = shaft_max - 1e-6
                    pt = DB.XYZ(float(placement_xy.X), float(placement_xy.Y), float(z))
                    if center_only_mode and one_row_xy_dedupe_ft > 0.0 and idx_xy_row.has_near(pt.X, pt.Y, 0.0, one_row_xy_dedupe_ft):
                        skipped_dedupe += 1
                        continue
                    if dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                        skipped_dedupe += 1
                        continue
                    if center_only_mode and one_row_xy_dedupe_ft > 0.0:
                        idx_xy_row.add(pt.X, pt.Y, 0.0)
                    idx.add(pt.X, pt.Y, pt.Z)
                    lvl_z = find_nearest_level(doc, z) or _nearest_level_from_list(shaft_levels, z) or host_level_hint
                    points.append((pt, lvl_z, host_bmin, host_bmax, link_bmin, link_bmax))

                    if max_place > 0 and len(points) >= max_place:
                        truncated = True
                        break
                if truncated:
                    break

    # Floor points: mandatory one point per floor in each shaft column.
    # Primary source: selected link levels (interval middles).
    # Fallback: middles of shaft family instances in the same column.
    if (not truncated) and use_link_level_floor_mode and shaft_edge_groups:
        floor_z_dedupe_tol = mm_to_ft(float(rules.get('lift_shaft_floor_z_dedupe_mm', 120) or 120)) or 0.0
        if floor_z_dedupe_tol <= 1e-9:
            floor_z_dedupe_tol = mm_to_ft(50) or 1e-6
        floor_level_margin_ft = mm_to_ft(float(rules.get('lift_shaft_floor_level_margin_mm', 600) or 600)) or 0.0
        min_story_h_ft = mm_to_ft(float(rules.get('lift_shaft_min_story_height_mm', 1800) or 1800)) or 0.0

        def _dedupe_sorted_z(z_values, tol_ft):
            out = []
            if not z_values:
                return out
            for z in sorted([float(v) for v in z_values]):
                if not out:
                    out.append(z)
                    continue
                try:
                    if abs(float(z) - float(out[-1])) <= float(tol_ft):
                        continue
                except Exception:
                    pass
                out.append(z)
            return out

        for _, g in shaft_edge_groups.items():
            records = list(g.get('records') or [])
            if not records:
                continue

            try:
                gmin = float(g.get('zmin'))
                gmax = float(g.get('zmax'))
            except Exception:
                gmin = None
                gmax = None

            gbhmin = g.get('host_bmin')
            gbhmax = g.get('host_bmax')
            gblmin = g.get('link_bmin')
            gblmax = g.get('link_bmax')
            if gbhmin is None or gbhmax is None:
                try:
                    _, _, _, hbmin0, hbmax0, _, _, _ = records[0]
                    gbhmin, gbhmax = hbmin0, hbmax0
                except Exception:
                    gbhmin = gbhmax = None
            if gblmin is None or gblmax is None:
                try:
                    _, _, _, _, _, lbmin0, lbmax0, _ = records[0]
                    gblmin, gblmax = lbmin0, lbmax0
                except Exception:
                    gblmin = gblmax = None

            rec_mids = []
            for rec in records:
                try:
                    rzmin, rzmax, rxy, _, _, _, _, rlvl = rec
                    rmid = (float(rzmin) + float(rzmax)) * 0.5
                    rec_mids.append((rmid, rxy, rlvl))
                except Exception:
                    continue
            rec_mids = sorted(rec_mids, key=lambda x: x[0])
            rec_mid_z = _dedupe_sorted_z([rmid for rmid, _, _ in rec_mids], floor_z_dedupe_tol)

            scoped_link_levels = []
            scoped_floor_levels = []
            g_bs_keys = set(g.get('bs_keys') or set())
            for item in selected_levels_meta or []:
                hz = item.get('host_z')
                if hz is None:
                    continue
                try:
                    hz = float(hz)
                except Exception:
                    continue
                if (gmin is not None) and (hz < (gmin - floor_level_margin_ft)):
                    continue
                if (gmax is not None) and (hz > (gmax + floor_level_margin_ft)):
                    continue
                if g_bs_keys:
                    lvl_keys = set(item.get('bs_keys') or set())
                    if lvl_keys and (not lvl_keys.intersection(g_bs_keys)):
                        continue
                scoped_link_levels.append(hz)
                try:
                    fn = item.get('floor_no')
                    if fn is not None:
                        scoped_floor_levels.append((int(fn), float(hz)))
                except Exception:
                    pass
            # Fallback: if BS filtering removed all candidate levels, retry without BS filter.
            if (not scoped_link_levels) and g_bs_keys:
                for item in selected_levels_meta or []:
                    hz = item.get('host_z')
                    if hz is None:
                        continue
                    try:
                        hz = float(hz)
                    except Exception:
                        continue
                    if (gmin is not None) and (hz < (gmin - floor_level_margin_ft)):
                        continue
                    if (gmax is not None) and (hz > (gmax + floor_level_margin_ft)):
                        continue
                    scoped_link_levels.append(hz)
                    try:
                        fn = item.get('floor_no')
                        if fn is not None:
                            scoped_floor_levels.append((int(fn), float(hz)))
                    except Exception:
                        pass
            # Last fallback: use all selected levels regardless of shaft Z range.
            # Final story mid is still clamped to shaft [gmin, gmax], so this is safe.
            if not scoped_link_levels:
                for item in selected_levels_meta or []:
                    hz = item.get('host_z')
                    if hz is None:
                        continue
                    try:
                        scoped_link_levels.append(float(hz))
                    except Exception:
                        continue
                    try:
                        fn = item.get('floor_no')
                        if fn is not None:
                            scoped_floor_levels.append((int(fn), float(hz)))
                    except Exception:
                        pass

            link_level_z = _dedupe_sorted_z(scoped_link_levels, floor_z_dedupe_tol)
            floor_level_z = []
            if scoped_floor_levels:
                floor_map = {}
                for fn, hz in sorted(scoped_floor_levels, key=lambda x: (x[0], x[1])):
                    if fn not in floor_map:
                        floor_map[fn] = float(hz)
                nums = sorted(floor_map.keys())
                if len(nums) >= 2:
                    z_by_num = {}
                    for i3 in range(len(nums) - 1):
                        n0 = int(nums[i3])
                        n1 = int(nums[i3 + 1])
                        if n1 <= n0:
                            continue
                        z0 = float(floor_map[n0])
                        z1 = float(floor_map[n1])
                        dn = float(n1 - n0)
                        step = (z1 - z0) / dn
                        if (n1 - n0) > 1:
                            floor_levels_interpolated_by_number += int((n1 - n0) - 1)
                        for nn in range(n0, n1):
                            z_by_num[nn] = z0 + (step * float(nn - n0))
                        z_by_num[n1] = z1
                    floor_level_z = [float(z_by_num[nn]) for nn in sorted(z_by_num.keys())]
                elif nums:
                    try:
                        floor_level_z = [float(floor_map[nums[0]])]
                    except Exception:
                        floor_level_z = []
            if floor_level_z:
                floor_level_z = _dedupe_sorted_z(floor_level_z, floor_z_dedupe_tol)
                floor_level_z_shifted = []
                z_clip_eps = mm_to_ft(20) or 0.0
                if z_clip_eps <= 1e-9:
                    z_clip_eps = 1e-6
                for zz in floor_level_z:
                    try:
                        zf = float(zz) + float(floor_place_offset_ft)
                    except Exception:
                        continue
                    # Keep one fixture per floor even near shaft extremes:
                    # clamp into shaft bounds instead of dropping the point.
                    if gmin is not None and zf < (gmin + z_clip_eps):
                        zf = float(gmin + z_clip_eps)
                    if gmax is not None and zf > (gmax - z_clip_eps):
                        zf = float(gmax - z_clip_eps)
                    if (gmin is not None) and (gmax is not None) and (zf <= (gmin + 1e-6) or zf >= (gmax - 1e-6)):
                        continue
                    floor_level_z_shifted.append(zf)
                floor_level_z = _dedupe_sorted_z(floor_level_z_shifted, floor_z_dedupe_tol)

            story_mids = []
            if len(link_level_z) >= 2:
                # Dynamic per-project/per-shaft step from selected link levels.
                # If gaps indicate missing intermediate floors, split those gaps automatically.
                min_h = max(float(min_story_h_ft), 1e-6)
                diffs = []
                for i2 in range(len(link_level_z) - 1):
                    try:
                        h2 = float(link_level_z[i2 + 1]) - float(link_level_z[i2])
                    except Exception:
                        continue
                    if h2 > min_h:
                        diffs.append(float(h2))

                base_step = None
                if diffs:
                    try:
                        diffs_u = sorted(list(set([round(float(d), 6) for d in diffs if d > min_h])))
                    except Exception:
                        diffs_u = []
                    if diffs_u:
                        base_step = float(diffs_u[0])
                        if len(diffs_u) > 1:
                            try:
                                d2 = float(diffs_u[1])
                                # Ignore a tiny rare outlier step (e.g. roof parapet) and use next typical step.
                                if d2 > (base_step * 1.35):
                                    base_step = d2
                            except Exception:
                                pass

                for i2 in range(len(link_level_z) - 1):
                    try:
                        z0 = float(link_level_z[i2])
                        z1 = float(link_level_z[i2 + 1])
                    except Exception:
                        continue
                    h = z1 - z0
                    if h <= min_h:
                        continue

                    nseg = 1
                    if base_step and (h > (base_step * 1.7)):
                        try:
                            nseg = int(round(float(h) / float(base_step)))
                        except Exception:
                            nseg = 1
                        nseg = max(1, min(nseg, 8))
                        if nseg > 1:
                            try:
                                seg_h = float(h) / float(nseg)
                                if seg_h < (min_h * 0.9):
                                    nseg = 1
                            except Exception:
                                nseg = 1
                    if nseg > 1:
                        floor_level_splits_added += int(nseg - 1)

                    step_h = float(h) / float(nseg)
                    for sidx in range(nseg):
                        z_mid = z0 + ((float(sidx) * step_h) + float(floor_place_offset_ft))
                        if z_mid >= (z1 - 1e-6):
                            z_mid = z0 + ((float(sidx) + 0.5) * step_h)
                        z_clip_eps = mm_to_ft(20) or 0.0
                        if z_clip_eps <= 1e-9:
                            z_clip_eps = 1e-6
                        if gmin is not None and z_mid < (gmin + z_clip_eps):
                            z_mid = float(gmin + z_clip_eps)
                        if gmax is not None and z_mid > (gmax - z_clip_eps):
                            z_mid = float(gmax - z_clip_eps)
                        if (gmin is not None) and (gmax is not None) and (z_mid <= (gmin + 1e-6) or z_mid >= (gmax - 1e-6)):
                            continue
                        story_mids.append(z_mid)
            story_mids = _dedupe_sorted_z(story_mids, floor_z_dedupe_tol)

            # Hard rule: prefer floor points from selected link levels whenever available.
            # Family-instance mids are fallback only.
            if floor_level_z:
                target_mids = floor_level_z
                source_kind = 'floor_numbers'
            elif story_mids:
                target_mids = story_mids
                source_kind = 'level_intervals'
            else:
                target_mids = rec_mid_z
                source_kind = 'shafts'

            for z_mid in target_mids:
                best_rxy = None
                best_rlvl = None
                best_dz = None
                for rmid, rxy, rlvl in rec_mids:
                    try:
                        dz = abs(float(rmid) - float(z_mid))
                    except Exception:
                        continue
                    if best_rxy is None or dz < best_dz:
                        best_rxy = rxy
                        best_rlvl = rlvl
                        best_dz = dz
                if best_rxy is None:
                    try:
                        _, _, best_rxy, _, _, _, _, best_rlvl = records[0]
                    except Exception:
                        continue
                try:
                    pt = DB.XYZ(float(best_rxy.X), float(best_rxy.Y), float(z_mid))
                except Exception:
                    continue
                if dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                    continue
                idx.add(pt.X, pt.Y, pt.Z)
                lvl_mid = find_nearest_level(doc, z_mid) or best_rlvl
                points.append((pt, lvl_mid, gbhmin, gbhmax, gblmin, gblmax))
                floor_points_added += 1
                if source_kind in ('floor_numbers', 'level_intervals'):
                    floor_points_from_link_levels += 1
                    if source_kind == 'floor_numbers':
                        floor_points_from_floor_numbers += 1
                    else:
                        floor_points_from_level_intervals += 1
                else:
                    floor_points_from_shaft_families += 1

                if max_place > 0 and len(points) >= max_place:
                    truncated = True
                    break
            if truncated:
                break

    # For OneLevelBased workflow with per-floor lift families:
    # add two extra points for each shaft column (top/bottom within edge_offset).
    if (not truncated) and group_edge_mode and shaft_edge_groups:
        for _, g in shaft_edge_groups.items():
            try:
                gmin = float(g.get('zmin'))
                gmax = float(g.get('zmax'))
            except Exception:
                continue
            if gmax <= gmin + 1e-6:
                continue

            if edge_offset_ft > 0.0:
                zb = gmin + edge_offset_ft
                zt = gmax - edge_offset_ft
            else:
                zb = gmin + 1e-6
                zt = gmax - 1e-6
            if zt <= zb + 1e-6:
                continue

            z_list = [zb, zt]
            records = list(g.get('records') or [])
            if not records:
                continue

            gbhmin = g.get('host_bmin')
            gbhmax = g.get('host_bmax')
            gblmin = g.get('link_bmin')
            gblmax = g.get('link_bmax')
            if gbhmin is None or gbhmax is None or gblmin is None or gblmax is None:
                try:
                    _, _, _, hbmin0, hbmax0, lbmin0, lbmax0, _ = records[0]
                    if gbhmin is None or gbhmax is None:
                        gbhmin, gbhmax = hbmin0, hbmax0
                    if gblmin is None or gblmax is None:
                        gblmin, gblmax = lbmin0, lbmax0
                except Exception:
                    pass

            for z in z_list:
                best = None
                best_dz = None
                for rec in records:
                    try:
                        rzmin, rzmax, rxy, rhbmin, rhbmax, rlbmin, rlbmax, rlvl = rec
                        rmid = (float(rzmin) + float(rzmax)) * 0.5
                        dz = abs(float(rmid) - float(z))
                    except Exception:
                        continue
                    if best is None or dz < best_dz:
                        best = (rxy, rhbmin, rhbmax, rlbmin, rlbmax, rlvl)
                        best_dz = dz
                if best is None:
                    continue

                rxy, rhbmin, rhbmax, rlbmin, rlbmax, rlvl = best
                try:
                    pt = DB.XYZ(float(rxy.X), float(rxy.Y), float(z))
                except Exception:
                    continue
                # Top/bottom points are mandatory by rule (<=500 mm from shaft extremes),
                # so do not drop them by generic dedupe.
                idx.add(pt.X, pt.Y, pt.Z)
                lvl_z = find_nearest_level(doc, z) or rlvl
                points.append((pt, lvl_z, gbhmin, gbhmax, gblmin, gblmax))
                edge_points_added += 1

                if max_place > 0 and len(points) >= max_place:
                    truncated = True
                    break
            if truncated:
                break

    if not points:
        alert('Нет точек для размещения. Проверьте уровни и параметры offset.')
        return

    output.print_md('Шахты: **{0}**'.format(len(shafts)))
    try:
        output.print_md('Уровней в ЭОМ: **{0}**'.format(len(host_levels_all or [])))
    except Exception:
        pass
    try:
        output.print_md('Уровней связи с номером этажа: **{0}/{1}**'.format(
            int(selected_levels_with_floor_no or 0), int(selected_levels_count or 0)
        ))
    except Exception:
        pass
    try:
        output.print_md('Смещение от отметки этажа: **{0:.0f} мм**'.format(float(floor_place_offset_mm)))
    except Exception:
        pass
    if temp_levels_created_count:
        output.print_md('Временных уровней из связи: **{0}**'.format(temp_levels_created_count))
    output.print_md('Контекст БС применён: **{0}**'.format(shafts_scoped_by_bs))
    if shafts_bs_unmatched:
        output.print_md('БС не сопоставлен (использован общий набор уровней): **{0}**'.format(shafts_bs_unmatched))
    if exact_family_names:
        output.print_md('Фильтр по семействам лифта: **{0}**'.format(u', '.join(exact_family_names)))
    if processed_families:
        output.print_md('Family (Generic/Furniture) обработано: **{0}**'.format(processed_families))
        if skipped_families_name:
            output.print_md('Пропущено (имя): **{0}**'.format(skipped_families_name))
        if skipped_families_bbox:
            output.print_md('Пропущено (bbox): **{0}**'.format(skipped_families_bbox))
        if skipped_families_height:
            output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_families_height))
    try:
        xy_seen = set()
        for sh in shafts or []:
            c = sh.get('center')
            if c is None:
                continue
            try:
                qx = int(round(float(c.X) / float(edge_group_xy_tol_ft)))
                qy = int(round(float(c.Y) / float(edge_group_xy_tol_ft)))
            except Exception:
                continue
            xy_seen.add((qx, qy))
        if xy_seen:
            output.print_md('Колонн шахт (уникальный XY): **{0}**'.format(len(xy_seen)))
    except Exception:
        pass
    output.print_md('ShaftOpening обработано: **{0}**'.format(processed_openings))
    if skipped_openings:
        output.print_md('Пропущено (bbox): **{0}**'.format(skipped_openings))
    if skipped_openings_height:
        output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_openings_height))
    if rx_inc or rx_exc:
        output.print_md('Generic Model обработано: **{0}**'.format(processed_generic))
        if skipped_generic_name:
            output.print_md('Пропущено (фильтр имён): **{0}**'.format(skipped_generic_name))
        if skipped_generic_bbox:
            output.print_md('Пропущено (bbox): **{0}**'.format(skipped_generic_bbox))
        if skipped_generic_height:
            output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_generic_height))

    output.print_md('Кандидаты: **{0}**'.format(len(points)))
    if skipped_dedupe:
        output.print_md('Дедупликация: **{0}**'.format(skipped_dedupe))
    if floor_points_added:
        output.print_md('Точки по этажам (по шахтам/уровням): **{0}**'.format(floor_points_added))
        output.print_md('Источник этажных точек: уровни связи **{0}**, семейства шахт **{1}**'.format(
            int(floor_points_from_link_levels or 0),
            int(floor_points_from_shaft_families or 0),
        ))
        if floor_points_from_link_levels:
            output.print_md('Из уровней связи: по номерам этажей **{0}**, по интервалам **{1}**'.format(
                int(floor_points_from_floor_numbers or 0),
                int(floor_points_from_level_intervals or 0),
            ))
        if floor_levels_interpolated_by_number:
            output.print_md('Добавлено по номерам этажей (интерполяция): **{0}**'.format(
                int(floor_levels_interpolated_by_number or 0)
            ))
        if floor_level_splits_added:
            output.print_md('Добавлено интерполяцией между уровнями связи: **{0}**'.format(
                int(floor_level_splits_added or 0)
            ))
        output.print_md('Трансформ уровней: **{0}**'.format(level_transform_source))
    if edge_points_added:
        output.print_md('Доп. точки верх/низ: **{0}**'.format(edge_points_added))
    if truncated:
        output.print_md('**Внимание:** достигнут лимит max_place_count ({0}).'.format(max_place))

    replaced_existing_count = 0
    if replace_existing_ids:
        with tx('ЭОМ: Очистка старых светильников шахты лифта', doc=doc, swallow_warnings=True):
            for eid in list(replace_existing_ids):
                try:
                    doc.Delete(eid)
                    replaced_existing_count += 1
                except Exception:
                    continue

    created_count = 0
    created_elems = []
    host_offset_param_names = [
        u'Offset from Host',
        u'Смещение от основы',
        u'Смещение от хоста',
        u'Отступ от основы',
        u'Отступ от хоста',
    ]
    batches = list(chunks(points, batch_size))
    # Keep one wall side per shaft column to avoid "every other floor" visual alternation.
    preferred_wall_xy_by_col = {}
    with forms.ProgressBar(title='ЭОМ: Размещение светильников (шахта лифта)', cancellable=True, step=1) as pb2:
        pb2.max_value = len(batches)
        for i, batch in enumerate(batches):
            pb2.update_progress(i + 1, pb2.max_value)
            if pb2.cancelled:
                break

            with tx('ЭОМ: Светильники шахты лифта', doc=doc, swallow_warnings=True):
                try:
                    _set_yesno_param(symbol, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
                except Exception:
                    pass
                if is_wall_symbol and (not is_one_level_symbol):
                    try:
                        _set_length_param_ft(symbol, host_offset_param_names, 0.0)
                    except Exception:
                        pass

                for pt, lvl, bbox_min, bbox_max, link_bmin, link_bmax in batch:
                    if pt is None or bbox_min is None or bbox_max is None:
                        skipped_place += 1
                        continue
                    col_key = None
                    try:
                        col_qx = int(round(float(pt.X) / float(edge_group_xy_tol_ft)))
                        col_qy = int(round(float(pt.Y) / float(edge_group_xy_tol_ft)))
                        col_key = (col_qx, col_qy)
                    except Exception:
                        col_key = None
                    if lvl is None:
                        try:
                            lvl = find_nearest_level(doc, float(pt.Z))
                        except Exception:
                            lvl = None
                    if lvl is None:
                        skipped_place += 1
                        continue

                    inst = None
                    use_pt = pt
                    search_pt = pt
                    pref_xy = None
                    if col_key is not None:
                        try:
                            pref_xy = preferred_wall_xy_by_col.get(col_key)
                        except Exception:
                            pref_xy = None
                    if pref_xy is not None:
                        try:
                            search_pt = DB.XYZ(float(pref_xy[0]), float(pref_xy[1]), float(pt.Z))
                        except Exception:
                            search_pt = pt
                    # Try wall projection in linked model first.
                    # For OneLevelBased this works even when link_inst is None (nested link case).
                    can_use_link_walls = (
                        (link_doc is not None) and
                        (link_bmin is not None) and
                        (link_bmax is not None) and
                        ((is_one_level_symbol) or (is_wall_symbol and link_inst is not None))
                    )
                    if can_use_link_walls:
                        try:
                            pt_link = t_inv.OfPoint(search_pt) if t_inv is not None else search_pt
                        except Exception:
                            pt_link = search_pt
                        wall_link, proj_pt_link = find_link_wall_in_bbox_near_point(
                            link_doc, pt_link, link_bmin, link_bmax, wall_search_ft, limit=None
                        )
                        if wall_link is None and pref_xy is not None:
                            try:
                                pt_link_retry = t_inv.OfPoint(pt) if t_inv is not None else pt
                            except Exception:
                                pt_link_retry = pt
                            wall_link, proj_pt_link = find_link_wall_in_bbox_near_point(
                                link_doc, pt_link_retry, link_bmin, link_bmax, wall_search_ft, limit=None
                            )
                            pt_link = pt_link_retry
                        if wall_link is not None:
                            link_ref = None
                            face_n_link = None
                            if is_wall_symbol and link_inst is not None:
                                try:
                                    link_ref, proj_pt_link, face_n_link = socket_utils._get_linked_wall_face_ref_and_point(
                                        wall_link, link_inst, pt_link
                                    )
                                except Exception:
                                    link_ref, face_n_link = None, None

                            if proj_pt_link is not None:
                                if is_one_level_symbol:
                                    try:
                                        proj_pt_link = _shift_point_from_wall_centerline(
                                            wall_link,
                                            proj_pt_link,
                                            pt_link,
                                            inset_mm=5.0
                                        )
                                    except Exception:
                                        pass
                                try:
                                    use_pt = t.OfPoint(proj_pt_link)
                                    use_pt = DB.XYZ(float(use_pt.X), float(use_pt.Y), float(pt.Z))
                                    if col_key is not None:
                                        preferred_wall_xy_by_col[col_key] = (float(use_pt.X), float(use_pt.Y))
                                except Exception:
                                    use_pt = pt

                            if is_wall_symbol and link_ref is not None:
                                try:
                                    wall_dir_link = None
                                    try:
                                        wall_dir_link = wall_link.Location.Curve.Direction
                                    except Exception:
                                        wall_dir_link = None
                                    dir_host = t.OfVector(wall_dir_link) if wall_dir_link else DB.XYZ.BasisX
                                    if face_n_link and dir_host.GetLength() > 1e-9:
                                        n_host = t.OfVector(face_n_link)
                                        if n_host and n_host.GetLength() > 1e-9:
                                            n = n_host.Normalize()
                                            comp = n.Multiply(dir_host.DotProduct(n))
                                            dir_host = dir_host - comp
                                    dir_host = dir_host.Normalize() if dir_host.GetLength() > 1e-9 else DB.XYZ.BasisX
                                    try:
                                        inst = doc.Create.NewFamilyInstance(link_ref, use_pt, dir_host, symbol)
                                    except Exception:
                                        try:
                                            inst = doc.Create.NewFamilyInstance(link_ref, use_pt, symbol)
                                        except Exception:
                                            inst = None
                                except Exception:
                                    inst = None
                            elif is_one_level_symbol and proj_pt_link is not None:
                                try:
                                    inst = placement_engine.place_point_family_instance(doc, symbol, use_pt, prefer_level=lvl)
                                except Exception:
                                    inst = None

                    # Fallback: host wall in model; OneLevelBased uses wall-projected point.
                    if inst is None and (is_wall_symbol or is_one_level_symbol):
                        wall, _, proj_pt = find_host_wall_in_bbox_near_point(doc, search_pt, bbox_min, bbox_max, wall_search_ft)
                        if wall is None and pref_xy is not None:
                            wall, _, proj_pt = find_host_wall_in_bbox_near_point(doc, pt, bbox_min, bbox_max, wall_search_ft)
                        if wall is not None:
                            if is_one_level_symbol and proj_pt is not None:
                                try:
                                    proj_pt = _shift_point_from_wall_centerline(wall, proj_pt, pt, inset_mm=5.0)
                                except Exception:
                                    pass
                            try:
                                use_pt = proj_pt if proj_pt is not None else pt
                                use_pt = DB.XYZ(float(use_pt.X), float(use_pt.Y), float(pt.Z))
                                if col_key is not None and proj_pt is not None:
                                    preferred_wall_xy_by_col[col_key] = (float(proj_pt.X), float(proj_pt.Y))
                            except Exception:
                                use_pt = pt

                            if is_wall_symbol:
                                inst = place_wall_hosted(doc, symbol, wall, use_pt, lvl)
                            elif is_one_level_symbol and proj_pt is not None:
                                try:
                                    inst = placement_engine.place_point_family_instance(doc, symbol, use_pt, prefer_level=lvl)
                                except Exception:
                                    inst = None

                    # If wall is not found on top/bottom points, keep fixture on previously
                    # resolved wall side for this shaft column instead of dropping it.
                    if inst is None and is_one_level_symbol and pref_xy is not None:
                        try:
                            use_pt_fb = DB.XYZ(float(pref_xy[0]), float(pref_xy[1]), float(pt.Z))
                            inst = placement_engine.place_point_family_instance(doc, symbol, use_pt_fb, prefer_level=lvl)
                            if inst is not None:
                                placed_by_pref_xy_fallback += 1
                        except Exception:
                            inst = None

                    if inst is None and (is_wall_symbol or is_one_level_symbol):
                        skipped_no_wall += 1
                    if inst is None:
                        skipped_place += 1
                        continue

                    if is_one_level_symbol:
                        try:
                            if _force_instance_level_and_z(doc, inst, lvl, float(pt.Z)):
                                forced_level_fix_count += 1
                        except Exception:
                            pass

                    try:
                        set_comments(inst, comment_value)
                    except Exception:
                        pass
                    try:
                        _set_yesno_param(inst, [u'Настенный', u'Wall Mounted', u'WallMounted'], True)
                    except Exception:
                        pass
                    if is_wall_symbol and (not is_one_level_symbol):
                        try:
                            _set_length_param_ft(inst, host_offset_param_names, 0.0)
                        except Exception:
                            pass

                    created_count += 1
                    created_elems.append(inst)

    # Validate persisted instances after transactions (guard against rolled-back creations).
    persisted = []
    for inst in list(created_elems or []):
        if inst is None:
            continue
        try:
            eid = inst.Id
            if eid is None:
                continue
            live = doc.GetElement(eid)
            if live is not None:
                persisted.append(live)
        except Exception:
            continue
    created_elems = persisted
    created_count = len(created_elems)

    # Cleanup temporary link levels:
    # 1) rehost created instances to permanent levels while preserving Z;
    # 2) delete temporary levels.
    if temp_link_level_ids:
        permanent_levels = []
        for lvl in (permanent_host_levels or []):
            if lvl is None:
                continue
            try:
                lid = int(lvl.Id.IntegerValue)
            except Exception:
                continue
            if lid in temp_link_level_ids:
                continue
            permanent_levels.append(lvl)

        if not permanent_levels:
            try:
                all_now = sorted_levels(doc)
            except Exception:
                all_now = []
            for lvl in all_now:
                if lvl is None:
                    continue
                try:
                    lid = int(lvl.Id.IntegerValue)
                except Exception:
                    continue
                if lid in temp_link_level_ids:
                    continue
                permanent_levels.append(lvl)

        with tx('ЭОМ: Удаление временных уровней связи', doc=doc, swallow_warnings=True):
            for inst in list(created_elems or []):
                if inst is None:
                    continue
                try:
                    lvl_cur = _element_level(doc, inst)
                except Exception:
                    lvl_cur = None
                if lvl_cur is None:
                    continue
                try:
                    cur_id = int(lvl_cur.Id.IntegerValue)
                except Exception:
                    cur_id = None
                if cur_id not in temp_link_level_ids:
                    continue
                try:
                    p = _instance_point(inst)
                    zt = float(p.Z) if p is not None else None
                except Exception:
                    zt = None
                if zt is None:
                    continue
                lvl_dst = _nearest_level_from_list(permanent_levels, zt)
                if lvl_dst is None:
                    continue
                try:
                    if _force_instance_level_and_z(doc, inst, lvl_dst, zt):
                        temp_levels_rehosted_count += 1
                except Exception:
                    continue

            for tl in list(temp_link_levels or []):
                if tl is None:
                    continue
                try:
                    doc.Delete(tl.Id)
                    temp_levels_deleted_count += 1
                except Exception:
                    continue

    output.print_md('---')
    output.print_md('Размещено светильников: **{0}**'.format(created_count))
    if replaced_existing_count:
        output.print_md('Заменено старых в шахтах: **{0}**'.format(replaced_existing_count))
    if skipped_no_wall:
        output.print_md('Пропущено (не найдена стена): **{0}**'.format(skipped_no_wall))
    if skipped_place:
        output.print_md('Пропущено (ошибка размещения): **{0}**'.format(skipped_place))
    if placed_by_pref_xy_fallback:
        output.print_md('Размещено по стороне колонны (без стены в точке): **{0}**'.format(placed_by_pref_xy_fallback))
    if temp_levels_rehosted_count:
        output.print_md('Перепривязано с временных уровней: **{0}**'.format(temp_levels_rehosted_count))
    if temp_levels_created_count:
        output.print_md('Удалено временных уровней: **{0}**'.format(temp_levels_deleted_count))
    if forced_level_fix_count:
        output.print_md('Исправлен уровень/высота: **{0}**'.format(forced_level_fix_count))
    if created_elems:
        level_counts = {}
        z_bins = set()
        z_groups = {}
        link_level_counts = {}
        link_level_bins = []
        for ll in selected_link_levels or []:
            if ll is None:
                continue
            hz = _link_level_to_host_elevation(ll, level_transform)
            if hz is None:
                continue
            try:
                nm = getattr(ll, 'Name', None) or u'(уровень связи)'
            except Exception:
                nm = u'(уровень связи)'
            link_level_bins.append((float(hz), nm))

        for inst in created_elems:
            lname = None
            try:
                lvl = _element_level(doc, inst)
                if lvl is not None:
                    lname = getattr(lvl, 'Name', None)
            except Exception:
                lname = None
            if not lname:
                lname = u'(без уровня)'
            level_counts[lname] = int(level_counts.get(lname, 0) or 0) + 1
            try:
                p = _instance_point(inst)
                if p is not None:
                    z_mm = float(p.Z) * 304.8
                    z_bins.add(int(round(z_mm / 50.0)))
                    z_key = int(round(z_mm / 10.0))
                    z_groups[z_key] = int(z_groups.get(z_key, 0) or 0) + 1
                    if link_level_bins:
                        best_nm = None
                        best_d = None
                        for hz, nm in link_level_bins:
                            try:
                                d = abs(float(hz) - float(p.Z))
                            except Exception:
                                continue
                            if best_nm is None or d < best_d:
                                best_nm = nm
                                best_d = d
                        if best_nm is not None:
                            link_level_counts[best_nm] = int(link_level_counts.get(best_nm, 0) or 0) + 1
            except Exception:
                pass
        try:
            levels_text = u', '.join(
                [u'{0}: {1}'.format(k, v) for k, v in sorted(level_counts.items(), key=lambda kv: kv[0])]
            )
            if levels_text:
                output.print_md(u'По уровням: `{0}`'.format(levels_text))
        except Exception:
            pass
        try:
            if z_bins:
                output.print_md(u'Уникальных высот Z: **{0}**'.format(len(z_bins)))
        except Exception:
            pass
        try:
            if z_groups:
                z_items = []
                for zk, cnt in sorted(z_groups.items(), key=lambda kv: kv[0]):
                    try:
                        z_m = (float(zk) * 10.0) / 1000.0
                        z_items.append(u'{0:+.3f}м: {1}'.format(z_m, int(cnt)))
                    except Exception:
                        continue
                if z_items:
                    output.print_md(u'По высотам Z: `{0}`'.format(u', '.join(z_items)))
        except Exception:
            pass
        try:
            if link_level_counts:
                link_text = u', '.join(
                    [u'{0}: {1}'.format(k, v) for k, v in sorted(link_level_counts.items(), key=lambda kv: kv[0])]
                )
                if link_text:
                    output.print_md(u'По уровням связи: `{0}`'.format(link_text))
        except Exception:
            pass
    output.print_md('Тег Comments: `{0}`'.format(comment_value))
    # logger.info('Placed %s lift shaft light(s)', created_count)

    # Do not create extra debug views automatically.

    try:
        shafts_total = len(shafts or [])
    except Exception:
        shafts_total = 0

    return {
        'placed': int(created_count or 0),
        'shafts': int(shafts_total or 0),
        'skipped': int(skipped_place or 0),
        'skipped_no_wall': int(skipped_no_wall or 0),
    }
