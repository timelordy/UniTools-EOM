# -*- coding: utf-8 -*-

import re

from pyrevit import DB
from System.Collections.Generic import List

import constants
from utils_units import ft_to_mm, mm_to_ft


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


def _safe_lower(val):
    if val is None:
        return ''
    try:
        return str(val).strip().lower()
    except Exception:
        return ''


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return None


def _normalize_family_name(name):
    val = _safe_lower(name)
    val = val.replace(' ', '').replace('_', '')
    if val.endswith('.rfa'):
        val = val[:-4]
    return val


def get_required_lintel_family_names():
    names = []
    single = str(getattr(constants, 'LINTEL_FAMILY_NAME', '') or '').strip()
    if single and single not in names:
        names.append(single)
    for raw in tuple(getattr(constants, 'LINTEL_FAMILY_NAMES', ()) or ()):
        val = str(raw or '').strip()
        if val and val not in names:
            names.append(val)
    return names


def _configured_family_entries():
    entries = []
    for raw in get_required_lintel_family_names():
        norm = _normalize_family_name(raw)
        if not norm:
            continue
        exists = False
        for _, known_norm in entries:
            if known_norm == norm:
                exists = True
                break
        if not exists:
            entries.append((raw, norm))
    return entries


def _configured_family_names():
    return [x[1] for x in _configured_family_entries()]


def _is_family_loaded(loaded_norms, target_norm):
    if not target_norm:
        return False
    for loaded_norm in loaded_norms or ():
        if not loaded_norm:
            continue
        if loaded_norm == target_norm:
            return True
        if target_norm in loaded_norm:
            return True
        if loaded_norm in target_norm:
            return True
    return False


def find_missing_lintel_families(doc):
    entries = _configured_family_entries()
    if not entries:
        return []

    loaded_norms = set()
    for sym in _collect_symbols(doc):
        try:
            fam_name, _ = get_symbol_names(sym)
            fam_norm = _normalize_family_name(fam_name)
            if fam_norm:
                loaded_norms.add(fam_norm)
        except Exception:
            continue

    missing = []
    for raw_name, norm_name in entries:
        if not _is_family_loaded(loaded_norms, norm_name):
            missing.append(raw_name)
    return missing


def get_symbol_names(symbol):
    fam_name = ''
    type_name = ''
    if symbol is None:
        return fam_name, type_name
    try:
        fam_name = getattr(symbol, 'FamilyName', None) or ''
    except Exception:
        fam_name = ''
    if not fam_name:
        try:
            fam = getattr(symbol, 'Family', None)
            fam_name = getattr(fam, 'Name', '') if fam is not None else ''
        except Exception:
            fam_name = ''
    try:
        type_name = getattr(symbol, 'Name', None) or ''
    except Exception:
        type_name = ''
    return str(fam_name or ''), str(type_name or '')


def get_symbol_display_name(symbol):
    fam_name, type_name = get_symbol_names(symbol)
    if fam_name and type_name:
        return "{0} : {1}".format(fam_name, type_name)
    return fam_name or type_name or "<unknown symbol>"


def _get_symbol_search_blob(symbol):
    fam_name, type_name = get_symbol_names(symbol)
    return _safe_lower("{0} {1}".format(fam_name, type_name))


def _collect_symbols(doc):
    if doc is None:
        return []
    try:
        return list(DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol))
    except Exception:
        return []


def _iter_parameters(elem):
    if elem is None:
        return []
    try:
        return list(elem.Parameters)
    except Exception:
        return []


def _get_param_double_value(elem, name):
    if elem is None or not name:
        return None
    try:
        p = elem.LookupParameter(name)
    except Exception:
        p = None
    if p is None:
        return None
    try:
        if p.StorageType != DB.StorageType.Double:
            return None
        return float(p.AsDouble())
    except Exception:
        return None


def _extract_length_ft_from_name(name):
    text = str(name or '')
    if not text:
        return None
    vals = []
    for raw in re.findall(r'(\d+(?:[.,]\d+)?)', text):
        try:
            val = float(raw.replace(',', '.'))
        except Exception:
            continue
        if 300.0 <= val <= 5000.0:
            vals.append(val)
    if not vals:
        return None
    return mm_to_ft(max(vals))


def get_symbol_length_ft(symbol):
    if symbol is None:
        return None

    for pname in constants.LINTEL_LENGTH_PARAM_NAMES:
        val = _get_param_double_value(symbol, pname)
        if val is not None and val > 1e-6:
            return val

    for p in _iter_parameters(symbol):
        try:
            if p.StorageType != DB.StorageType.Double:
                continue
            defn = getattr(p, 'Definition', None)
            pname = _safe_lower(getattr(defn, 'Name', '') if defn is not None else '')
            if ('длина' in pname) or ('length' in pname):
                val = float(p.AsDouble())
                if val > 1e-6:
                    return val
        except Exception:
            continue

    fam_name, type_name = get_symbol_names(symbol)
    return _extract_length_ft_from_name(type_name or fam_name)


def _get_first_param_double_ft(elem, names):
    for pname in names or ():
        val = _get_param_double_value(elem, pname)
        if val is None:
            continue
        try:
            return float(val)
        except Exception:
            continue
    return None


def _to_mm_safe(val_ft):
    if val_ft is None:
        return None
    try:
        return float(ft_to_mm(float(val_ft)))
    except Exception:
        return None


def _normalize_mark_key(text):
    try:
        val = _normalize_mark_text(text)
    except Exception:
        val = ''
    return str(val or '').upper()


def _mark_has_prefix(mark, prefixes):
    mark_key = _normalize_mark_key(mark)
    if not mark_key:
        return False
    for raw in prefixes or ():
        key = _normalize_mark_key(raw)
        if key and mark_key.startswith(key):
            return True
    return False


def _table_kind_for_mark(mark):
    norm = _normalize_mark_key(mark)
    if norm.startswith('АР') or ('D16' in norm):
        return 'pgp'
    if _mark_has_prefix(mark, getattr(constants, 'CERAMIC_MARK_PREFIXES', ())):
        return 'ceramic'
    if _mark_has_prefix(mark, getattr(constants, 'SILICATE_MARK_PREFIXES', ())):
        return 'silicate'
    return ''


def collect_lintel_specs(symbols):
    rows = []
    for sym in list(symbols or []):
        fam_name, type_name = get_symbol_names(sym)
        mark = str(type_name or fam_name or '').strip()
        if not mark:
            continue

        len_ft = _get_first_param_double_ft(sym, ('ADSK_Размер_Длина', 'Длина', 'Length', 'L'))
        if len_ft is None:
            len_ft = get_symbol_length_ft(sym)
        w_ft = _get_first_param_double_ft(sym, ('ADSK_Размер_Ширина', 'Ширина', 'Width'))
        h_ft = _get_first_param_double_ft(sym, ('ADSK_Размер_Высота', 'Высота', 'Height'))
        opening_ft = _get_first_param_double_ft(sym, ('Ширина проема', 'Ширина проёма', 'Opening Width'))
        left_bearing_ft = _get_first_param_double_ft(sym, ('Ширина опирания слева', 'Опирание слева'))
        right_bearing_ft = _get_first_param_double_ft(sym, ('Ширина опирания справа', 'Опирание справа'))

        len_mm = _to_mm_safe(len_ft)
        w_mm = _to_mm_safe(w_ft)
        h_mm = _to_mm_safe(h_ft)
        opening_w_mm = _to_mm_safe(opening_ft)
        bearing_left_mm = _to_mm_safe(left_bearing_ft)
        bearing_right_mm = _to_mm_safe(right_bearing_ft)

        bearing_candidates = [x for x in (bearing_left_mm, bearing_right_mm) if x is not None]
        bearing_mm = max(bearing_candidates) if bearing_candidates else float(constants.LINTEL_BEARING_MM)

        if opening_w_mm is None and len_mm is not None:
            try:
                opening_w_mm = max(0.0, float(len_mm) - 2.0 * float(bearing_mm))
            except Exception:
                opening_w_mm = None

        if len_mm is None:
            continue

        table_kind = _table_kind_for_mark(mark)
        if table_kind == 'pgp':
            default_w_mm = 80.0
            default_h_mm = 16.0
        else:
            default_w_mm = float(constants.LINTEL_WIDTH_MM)
            default_h_mm = float(constants.LINTEL_HEIGHT_MM)

        rows.append({
            'symbol': sym,
            'family_name': str(fam_name or ''),
            'mark': mark,
            'table_kind': table_kind,
            'opening_w_mm': opening_w_mm,
            'len_mm': len_mm,
            'w_mm': w_mm if w_mm is not None else default_w_mm,
            'h_mm': h_mm if h_mm is not None else default_h_mm,
            'bearing_mm': bearing_mm,
        })

    rows = sorted(
        rows,
        key=lambda r: (
            float(r.get('opening_w_mm') if r.get('opening_w_mm') is not None else 1e12),
            float(r.get('h_mm') if r.get('h_mm') is not None else 1e12),
            float(r.get('len_mm') if r.get('len_mm') is not None else 1e12),
            _normalize_mark_key(r.get('mark', ''))
        )
    )
    return rows


def _symbol_category_id(symbol):
    if symbol is None:
        return None
    try:
        cat = getattr(symbol, 'Category', None)
        if cat is None or cat.Id is None:
            return None
        return int(cat.Id.IntegerValue)
    except Exception:
        return None


def _is_lintel_category(symbol):
    cat_id = _symbol_category_id(symbol)
    if cat_id is None:
        return True
    allowed = (
        int(DB.BuiltInCategory.OST_GenericModel),
        int(DB.BuiltInCategory.OST_StructuralFraming),
    )
    return cat_id in allowed


def find_placeholder_symbol(doc):
    for sym in _collect_symbols(doc):
        try:
            if not _is_lintel_category(sym):
                continue
            fam_name, type_name = get_symbol_names(sym)
            if fam_name != constants.PLACEHOLDER_FAMILY_NAME:
                continue
            if constants.PLACEHOLDER_TYPE_NAME and type_name and type_name != constants.PLACEHOLDER_TYPE_NAME:
                continue
            return sym
        except Exception:
            continue
    return None


def find_lintel_symbols(doc):
    symbols = _collect_symbols(doc)
    if not symbols:
        return []

    fam_exact_list = _configured_family_names()
    typ_exact = _safe_lower(constants.LINTEL_TYPE_NAME)
    if fam_exact_list:
        exact = []
        for sym in symbols:
            try:
                if not _is_lintel_category(sym):
                    continue
                fam_name, type_name = get_symbol_names(sym)
                fam_norm = _normalize_family_name(fam_name)
                if not fam_norm:
                    continue
                family_match = False
                for fam_exact_norm in fam_exact_list:
                    is_exact = (fam_norm == fam_exact_norm)
                    is_contains = (fam_exact_norm in fam_norm) or (fam_norm in fam_exact_norm)
                    if is_exact or is_contains:
                        family_match = True
                        break
                if not family_match:
                    continue
                if typ_exact and _safe_lower(type_name) != typ_exact:
                    continue
                exact.append(sym)
            except Exception:
                continue
        if exact:
            return sorted(exact, key=lambda s: _get_symbol_search_blob(s))
        # If explicit family names are configured, do not fallback to loose keyword search.
        return []

    keywords = tuple(_safe_lower(k) for k in constants.LINTEL_SYMBOL_KEYWORDS if _safe_lower(k))
    candidates = []
    if keywords:
        for sym in symbols:
            try:
                if not _is_lintel_category(sym):
                    continue
                blob = _get_symbol_search_blob(sym)
                if any(k in blob for k in keywords):
                    candidates.append(sym)
            except Exception:
                continue

    if candidates:
        if constants.PREFER_SYMBOL_WITH_120:
            preferred = []
            for sym in candidates:
                try:
                    if '120' in _get_symbol_search_blob(sym):
                        preferred.append(sym)
                except Exception:
                    continue
            if preferred:
                candidates = preferred
        return sorted(candidates, key=lambda s: _get_symbol_search_blob(s))

    ph = find_placeholder_symbol(doc)
    return [ph] if ph is not None else []


def find_lintel_symbol(doc):
    syms = find_lintel_symbols(doc)
    return syms[0] if syms else None


def _symbol_matches_family(symbol, family_name):
    fam_target = _normalize_family_name(family_name)
    if not fam_target:
        return True
    fam_name, _ = get_symbol_names(symbol)
    fam_norm = _normalize_family_name(fam_name)
    if not fam_norm:
        return False
    return (fam_norm == fam_target) or (fam_target in fam_norm) or (fam_norm in fam_target)


def pick_lintel_symbol_for_length(symbols, required_length_ft, preferred_family_name=None):
    symbols = list(symbols or [])
    if not symbols:
        return None
    fam_target = _normalize_family_name(preferred_family_name)
    if fam_target:
        symbols = [s for s in symbols if _symbol_matches_family(s, fam_target)]
        if not symbols:
            return None
    if len(symbols) == 1:
        return symbols[0]

    req = _safe_float(required_length_ft)
    if req is None or req <= 1e-6:
        return symbols[0]

    rows = []
    for sym in symbols:
        lft = get_symbol_length_ft(sym)
        if lft is None:
            continue
        rows.append((sym, float(lft)))

    if not rows:
        return symbols[0]

    tol_ft = mm_to_ft(float(constants.LINTEL_LENGTH_PICK_TOLERANCE_MM))
    longer = [r for r in rows if r[1] + tol_ft >= req]
    if longer:
        longer = sorted(longer, key=lambda x: x[1])
        return longer[0][0]

    rows = sorted(rows, key=lambda x: x[1], reverse=True)
    return rows[0][0]


def _normalize_mark_text(text):
    val = _safe_lower(text)
    if not val:
        return ''
    val = val.replace('—', '-').replace('–', '-')
    val = val.replace(' ', '').replace('_', '')
    val = val.replace('pb', 'пб')
    return val


def _extract_mark_root(mark):
    txt = _normalize_mark_text(mark)
    if not txt:
        return ''
    m = re.search(r'(\d+пб\d+(?:-\d+)?)', txt)
    if m:
        return m.group(1)
    return txt


def pick_lintel_symbol_for_mark(symbols, mark, preferred_family_name=None):
    syms = list(symbols or [])
    if not syms:
        return None
    fam_target = _normalize_family_name(preferred_family_name)
    if fam_target:
        syms = [s for s in syms if _symbol_matches_family(s, fam_target)]
        if not syms:
            return None
    mark_norm = _normalize_mark_text(mark)
    if not mark_norm:
        return None
    mark_root = _extract_mark_root(mark_norm)

    rows = []
    for sym in syms:
        try:
            fam_name, type_name = get_symbol_names(sym)
            type_norm = _normalize_mark_text(type_name)
            blob_norm = _normalize_mark_text("{0} {1}".format(fam_name, type_name))
            exact = (type_norm == mark_norm) or (blob_norm == mark_norm)
            starts = type_norm.startswith(mark_norm) or blob_norm.startswith(mark_norm)
            has_root = bool(mark_root and ((mark_root in type_norm) or (mark_root in blob_norm)))
            if not (exact or starts or has_root):
                continue
            bad_token_score = 0
            for t in ('atv', 'atlvc', 'ativc', 'at'):
                if t in blob_norm:
                    bad_token_score += 1
            extra_score = abs(len(type_norm) - len(mark_norm))
            rows.append((0 if exact else 1, 0 if starts else 1, 0 if has_root else 1, bad_token_score, extra_score, sym))
        except Exception:
            continue

    if not rows:
        return None

    rows = sorted(rows, key=lambda x: (x[0], x[1], x[2], x[3], x[4], _get_symbol_search_blob(x[5])))
    return rows[0][5]


def pick_lintel_symbol(symbols, required_length_ft=None, mark=None, preferred_family_name=None):
    by_mark = pick_lintel_symbol_for_mark(symbols, mark, preferred_family_name=preferred_family_name)
    if by_mark is not None:
        return by_mark
    return pick_lintel_symbol_for_length(symbols, required_length_ft, preferred_family_name=preferred_family_name)


def create_family_instance(doc, symbol, point, level=None, host=None):
    if doc is None or symbol is None or point is None:
        return None

    creator = getattr(doc, 'Create', None)
    if creator is None:
        return None

    try:
        non_struct = DB.Structure.StructuralType.NonStructural
    except Exception:
        non_struct = None

    attempts = []
    if host is not None and non_struct is not None:
        attempts.append(lambda: creator.NewFamilyInstance(point, symbol, host, non_struct))
    if level is not None and non_struct is not None:
        attempts.append(lambda: creator.NewFamilyInstance(point, symbol, level, non_struct))
    if non_struct is not None:
        attempts.append(lambda: creator.NewFamilyInstance(point, symbol, non_struct))
    attempts.append(lambda: creator.NewFamilyInstance(point, symbol, level) if level is not None else None)
    attempts.append(lambda: creator.NewFamilyInstance(point, symbol))

    for fn in attempts:
        try:
            inst = fn()
            if inst is not None:
                return inst
        except Exception:
            continue
    return None


def rotate_element_to_direction(doc, elem, center, direction):
    if doc is None or elem is None or center is None or direction is None:
        return False
    try:
        target = DB.XYZ(float(direction.X), float(direction.Y), 0.0)
        if target.GetLength() < 1e-9:
            return False
        target = target.Normalize()
        basis = DB.XYZ.BasisX
        angle = float(basis.AngleTo(target))
        cross = basis.CrossProduct(target)
        if cross.Z < 0:
            angle = -angle
        if abs(angle) < 1e-7:
            return False
        axis_start = DB.XYZ(float(center.X), float(center.Y), float(center.Z))
        axis_end = DB.XYZ(float(center.X), float(center.Y), float(center.Z) + 1.0)
        axis = DB.Line.CreateBound(axis_start, axis_end)
        DB.ElementTransformUtils.RotateElement(doc, elem.Id, axis, angle)
        return True
    except Exception:
        return False


def _get_location_point(elem):
    if elem is None:
        return None
    try:
        loc = elem.Location
    except Exception:
        return None
    if loc is None:
        return None
    try:
        if isinstance(loc, DB.LocationPoint):
            return loc.Point
        if isinstance(loc, DB.LocationCurve):
            crv = getattr(loc, 'Curve', None)
            if crv is not None:
                return crv.Evaluate(0.5, True)
    except Exception:
        return None
    return None


def _get_bbox(elem):
    if elem is None:
        return None
    try:
        return elem.get_BoundingBox(None)
    except Exception:
        return None


def align_element_to_target(doc, elem, target_center=None, target_bottom_z=None):
    if doc is None or elem is None:
        return False
    if target_center is None and target_bottom_z is None:
        return False

    bb = _get_bbox(elem)
    if bb is None:
        try:
            doc.Regenerate()
        except Exception:
            pass
        bb = _get_bbox(elem)

    cur_x = None
    cur_y = None
    cur_z = None
    cur_bottom_z = None

    if bb is not None:
        cur_x = (float(bb.Min.X) + float(bb.Max.X)) * 0.5
        cur_y = (float(bb.Min.Y) + float(bb.Max.Y)) * 0.5
        cur_z = (float(bb.Min.Z) + float(bb.Max.Z)) * 0.5
        cur_bottom_z = float(bb.Min.Z)
    else:
        loc_pt = _get_location_point(elem)
        if loc_pt is None:
            return False
        cur_x = float(loc_pt.X)
        cur_y = float(loc_pt.Y)
        cur_z = float(loc_pt.Z)
        cur_bottom_z = float(loc_pt.Z)

    dx = 0.0
    dy = 0.0
    dz = 0.0
    if target_center is not None:
        dx = float(target_center.X) - cur_x
        dy = float(target_center.Y) - cur_y
        dz = float(target_center.Z) - cur_z
    if target_bottom_z is not None:
        dz = float(target_bottom_z) - cur_bottom_z

    tol = 1e-7
    if abs(dx) < tol and abs(dy) < tol and abs(dz) < tol:
        return False

    candidates = [DB.XYZ(dx, dy, dz)]
    if abs(dz) > tol:
        candidates.append(DB.XYZ(dx, dy, 0.0))

    for vec in candidates:
        try:
            if vec.GetLength() < tol:
                continue
            DB.ElementTransformUtils.MoveElement(doc, elem.Id, vec)
            return True
        except Exception:
            continue
    return False


def try_join_and_cut_with_wall(doc, wall, lintel_elem, force=False, allow_cut=True):
    if doc is None or wall is None or lintel_elem is None:
        return False
    if (not bool(force)) and (not bool(constants.LINTEL_JOIN_WITH_WALL)):
        return False

    changed = False

    if bool(allow_cut):
        # If family has unattached voids and supports wall cutting, use explicit void cut.
        try:
            if DB.InstanceVoidCutUtils.CanBeCutWithVoid(wall) and DB.InstanceVoidCutUtils.IsVoidInstanceCuttingElement(lintel_elem):
                exists = False
                try:
                    exists = DB.InstanceVoidCutUtils.InstanceVoidCutExists(wall, lintel_elem)
                except Exception:
                    exists = False
                if not exists:
                    DB.InstanceVoidCutUtils.AddInstanceVoidCut(doc, wall, lintel_elem)
                    changed = True
        except Exception:
            pass

        # Try solid-solid cut when possible (some families cut walls this way).
        try:
            can_cut = False
            try:
                can_cut = bool(DB.SolidSolidCutUtils.CanElementCutElement(lintel_elem, wall))
            except Exception:
                can_cut = False
            if can_cut:
                cut_exists = False
                try:
                    cut_exists = bool(DB.SolidSolidCutUtils.CutExistsBetweenElements(doc, lintel_elem, wall))
                except Exception:
                    cut_exists = False
                if not cut_exists:
                    DB.SolidSolidCutUtils.AddCutBetweenSolids(doc, lintel_elem, wall)
                    changed = True
        except Exception:
            pass

    # Fallback/extra cleanup with geometry join.
    try:
        joined = DB.JoinGeometryUtils.AreElementsJoined(doc, wall, lintel_elem)
    except Exception:
        joined = False

    try:
        if joined:
            DB.JoinGeometryUtils.UnjoinGeometry(doc, wall, lintel_elem)
            joined = False
    except Exception:
        pass

    try:
        if not joined:
            DB.JoinGeometryUtils.JoinGeometry(doc, wall, lintel_elem)
            joined = True
            changed = True
    except Exception:
        joined = False

    if joined:
        try:
            if DB.JoinGeometryUtils.IsCuttingElementInJoin(doc, wall, lintel_elem):
                DB.JoinGeometryUtils.SwitchJoinOrder(doc, wall, lintel_elem)
                changed = True
        except Exception:
            try:
                DB.JoinGeometryUtils.SwitchJoinOrder(doc, wall, lintel_elem)
                changed = True
            except Exception:
                pass

    return changed


def set_instance_length(instance, length_ft):
    if instance is None or length_ft is None:
        return False

    candidates = []
    try:
        p = instance.get_Parameter(DB.BuiltInParameter.INSTANCE_LENGTH_PARAM)
        if p is not None:
            candidates.append(p)
    except Exception:
        pass

    for pname in ('Длина', 'Length', 'L'):
        try:
            p = instance.LookupParameter(pname)
            if p is not None:
                candidates.append(p)
        except Exception:
            continue

    for p in candidates:
        try:
            if p.IsReadOnly:
                continue
            if p.StorageType != DB.StorageType.Double:
                continue
            p.Set(float(length_ft))
            return True
        except Exception:
            continue
    return False


def _set_instance_double(instance, param_name, value_ft):
    if instance is None or not param_name:
        return False
    try:
        p = instance.LookupParameter(param_name)
    except Exception:
        p = None
    if p is None:
        return False
    try:
        if p.IsReadOnly:
            return False
        if p.StorageType != DB.StorageType.Double:
            return False
        p.Set(float(value_ft))
        return True
    except Exception:
        return False


def set_instance_elevation_from_level(instance, elevation_ft):
    if instance is None or elevation_ft is None:
        return False
    try:
        p = instance.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
    except Exception:
        p = None
    if p is not None:
        try:
            if (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(float(elevation_ft))
                return True
        except Exception:
            pass
    for pname in ('Elevation from Level', 'Отметка от уровня', 'Смещение по высоте'):
        if _set_instance_double(instance, pname, elevation_ft):
            return True
    return False


def set_instance_pa_pgp_offsets(instance, elevation_ft=None, host_wall_width_ft=None):
    changed = False
    # Keep PA rods directly over opening top.
    changed = _set_instance_double(instance, 'ADSK_Размер_Смещение от уровня', 0.0) or changed
    if elevation_ft is not None:
        changed = set_instance_elevation_from_level(instance, elevation_ft) or changed

    # If family exposes editable wall-width parameter, sync it with host.
    if host_wall_width_ft is not None:
        for pname in ('стена_толщина', 'Толщина стены', 'Ширина'):
            changed = _set_instance_double(instance, pname, float(host_wall_width_ft)) or changed
    return changed


def _set_instance_yes_no(instance, param_name, enabled):
    if instance is None or not param_name:
        return False
    try:
        p = instance.LookupParameter(param_name)
    except Exception:
        p = None
    if p is None:
        return False
    try:
        if p.IsReadOnly:
            return False
        if p.StorageType != DB.StorageType.Integer:
            return False
        p.Set(1 if bool(enabled) else 0)
        return True
    except Exception:
        return False


def set_instance_piece_flags(instance, use_two_pieces):
    two = bool(use_two_pieces)
    one = not two
    ok = False
    for pname in ('1 шт', '1шт'):
        ok = _set_instance_yes_no(instance, pname, one) or ok
    for pname in ('2 шт', '2шт'):
        ok = _set_instance_yes_no(instance, pname, two) or ok
    return ok
