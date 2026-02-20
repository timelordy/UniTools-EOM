# -*- coding: utf-8 -*-

from pyrevit import DB
from System.Collections.Generic import List

import constants
import domain
from utils_units import ft_to_mm
from utils_revit import ensure_symbol_active


def _offset_point(p, vec, dist):
    return DB.XYZ(
        float(p.X) + float(vec.X) * float(dist),
        float(p.Y) + float(vec.Y) * float(dist),
        float(p.Z) + float(vec.Z) * float(dist),
    )


def make_lintel_solid(center, dir_wall, dir_norm, length_ft, width_ft, height_ft):
    if center is None or dir_wall is None or dir_norm is None:
        return None
    try:
        half_len = float(length_ft) * 0.5
        half_w = float(width_ft) * 0.5
        height = float(height_ft)
    except Exception:
        return None

    base = DB.XYZ(float(center.X), float(center.Y), float(center.Z) - height * 0.5)

    p0 = _offset_point(_offset_point(base, dir_wall, -half_len), dir_norm, -half_w)
    p1 = _offset_point(_offset_point(base, dir_wall, half_len), dir_norm, -half_w)
    p2 = _offset_point(_offset_point(base, dir_wall, half_len), dir_norm, half_w)
    p3 = _offset_point(_offset_point(base, dir_wall, -half_len), dir_norm, half_w)

    loop = DB.CurveLoop()
    loop.Append(DB.Line.CreateBound(p0, p1))
    loop.Append(DB.Line.CreateBound(p1, p2))
    loop.Append(DB.Line.CreateBound(p2, p3))
    loop.Append(DB.Line.CreateBound(p3, p0))

    try:
        return DB.GeometryCreationUtilities.CreateExtrusionGeometry([loop], DB.XYZ.BasisZ, height)
    except Exception:
        return None


def create_directshape(doc, solid, name=None):
    if doc is None or solid is None:
        return None
    try:
        ds = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
        ds.SetShape(List[DB.GeometryObject]([solid]))
        if name:
            try:
                ds.Name = name
            except Exception:
                pass
        return ds
    except Exception:
        return None


def _safe_name(obj):
    if obj is None:
        return ''
    try:
        return str(obj) or ''
    except Exception:
        return ''


def _family_name(symbol):
    if symbol is None:
        return ''
    try:
        n = getattr(symbol, 'FamilyName', None)
        if n:
            return _safe_name(n)
    except Exception:
        pass
    try:
        fam = getattr(symbol, 'Family', None)
        if fam is not None:
            return _safe_name(getattr(fam, 'Name', ''))
    except Exception:
        pass
    return ''


def _type_name(symbol):
    if symbol is None:
        return ''
    try:
        return _safe_name(getattr(symbol, 'Name', ''))
    except Exception:
        return ''


def _double_by_names(elem, names):
    if elem is None:
        return None
    for pname in names:
        val = domain.get_double_param(elem, name=pname)
        if val is not None:
            return float(val)
    return None


def _symbol_width_ft(symbol):
    if symbol is None:
        return None
    targets = [symbol]
    try:
        fam = getattr(symbol, 'Family', None)
        if fam is not None:
            targets.append(fam)
    except Exception:
        pass
    for target in targets:
        val = _double_by_names(target, constants.LINTEL_WIDTH_PARAM_NAMES)
        if val is not None and val > 0:
            return val
    return None


def _symbol_length_ft(symbol):
    if symbol is None:
        return None
    targets = [symbol]
    try:
        fam = getattr(symbol, 'Family', None)
        if fam is not None:
            targets.append(fam)
    except Exception:
        pass
    for target in targets:
        val = _double_by_names(target, constants.LINTEL_LENGTH_PARAM_NAMES)
        if val is not None and val > 0:
            return val
    return None


def collect_lintel_symbols(doc):
    infos = []
    if doc is None:
        return infos
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
    except Exception:
        return infos

    for sym in col:
        fam_name = _family_name(sym)
        typ_name = _type_name(sym)
        if not domain.matches_preferred_lintel_name(fam_name, typ_name):
            continue

        info = {
            'symbol': sym,
            'family_name': fam_name,
            'type_name': typ_name,
            'width_ft': _symbol_width_ft(sym),
            'length_ft': _symbol_length_ft(sym),
            'rank': domain.rank_from_name(fam_name, typ_name),
        }
        infos.append(info)

    return infos


def _pick_by_score(infos, target_width_mm, required_length_mm):
    best = None
    best_key = None

    for info in infos:
        width_ft = info.get('width_ft')
        length_ft = info.get('length_ft')

        if width_ft is None:
            width_known = 1
            width_delta = 1e9
            width_mismatch = 1
        else:
            width_known = 0
            width_mm = abs(float(ft_to_mm(width_ft)))
            width_delta = abs(width_mm - target_width_mm)
            width_mismatch = 0 if width_delta <= float(constants.WIDTH_MATCH_TOLERANCE_MM) else 1

        if length_ft is None:
            length_short = 1
            length_delta = 1e9
        else:
            length_mm = abs(float(ft_to_mm(length_ft)))
            length_short = 0 if length_mm >= required_length_mm else 1
            length_delta = abs(length_mm - required_length_mm)

        key = (
            length_short,
            length_delta,
            width_mismatch,
            width_known,
            width_delta,
            int(info.get('rank') or 9999),
            _safe_name(info.get('type_name')),
            _safe_name(info.get('family_name')),
        )
        if best is None or key < best_key:
            best = info
            best_key = key

    return best


def pick_lintel_symbol(infos, target_width_ft, required_length_ft):
    if not infos:
        return None
    try:
        target_width_mm = abs(float(ft_to_mm(target_width_ft)))
    except Exception:
        target_width_mm = abs(float(constants.LINTEL_WIDTH_MM))
    try:
        required_length_mm = abs(float(ft_to_mm(required_length_ft)))
    except Exception:
        required_length_mm = 0.0
    return _pick_by_score(infos, target_width_mm, required_length_mm)


def _create_family_instance(doc, symbol, point, wall=None, level=None):
    if doc is None or symbol is None or point is None:
        return None

    ensure_symbol_active(doc, symbol)

    create = getattr(doc, 'Create', None)
    if create is None:
        return None

    stype = DB.Structure.StructuralType.NonStructural

    if wall is not None and level is not None:
        try:
            return create.NewFamilyInstance(point, symbol, wall, level, stype)
        except Exception:
            pass

    if level is not None:
        try:
            return create.NewFamilyInstance(point, symbol, level, stype)
        except Exception:
            pass

    try:
        return create.NewFamilyInstance(point, symbol, stype)
    except Exception:
        return None


def place_lintel_family_instance(doc, symbol, point, dir_wall, wall=None, level=None):
    inst = _create_family_instance(doc, symbol, point, wall=wall, level=level)
    if inst is None:
        return None
    rotate_instance_to_direction(inst, dir_wall)
    return inst


def rotate_instance_to_direction(inst, dir_wall):
    if inst is None or dir_wall is None:
        return False

    try:
        dir_xy = DB.XYZ(float(dir_wall.X), float(dir_wall.Y), 0.0)
        if dir_xy.GetLength() < 1e-9:
            return False
        dir_xy = dir_xy.Normalize()
    except Exception:
        return False

    try:
        loc = inst.Location
    except Exception:
        return False
    if not isinstance(loc, DB.LocationPoint):
        return False

    try:
        base = DB.XYZ.BasisX
        angle = base.AngleTo(dir_xy)
        cross = base.CrossProduct(dir_xy)
        if cross.Z < 0:
            angle = -angle
        if abs(float(angle)) < 1e-6:
            return True

        p = loc.Point
        axis = DB.Line.CreateBound(p, DB.XYZ(float(p.X), float(p.Y), float(p.Z) + 1.0))
        loc.Rotate(axis, angle)
        return True
    except Exception:
        return False


def find_placeholder_symbol(doc):
    if doc is None:
        return None
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
    except Exception:
        return None
    for sym in col:
        try:
            fam_name = getattr(sym, 'FamilyName', None) or ''
            if not fam_name:
                fam = getattr(sym, 'Family', None)
                fam_name = fam.Name if fam else ''
            if fam_name != constants.PLACEHOLDER_FAMILY_NAME:
                continue
            type_name = getattr(sym, 'Name', None) or ''
            if constants.PLACEHOLDER_TYPE_NAME and type_name and type_name != constants.PLACEHOLDER_TYPE_NAME:
                continue
            return sym
        except Exception:
            continue
    return None
