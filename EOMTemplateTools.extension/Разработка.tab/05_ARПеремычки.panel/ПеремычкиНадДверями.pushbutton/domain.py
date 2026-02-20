# -*- coding: utf-8 -*-

import re

from pyrevit import DB

from utils_units import ft_to_mm, mm_to_ft
import constants


def is_door(elem):
    try:
        cat = getattr(elem, 'Category', None)
        return bool(cat and int(cat.Id.IntegerValue) == int(DB.BuiltInCategory.OST_Doors))
    except Exception:
        return False


def get_double_param(elem, bip=None, name=None):
    if elem is None:
        return None
    p = None
    if bip is not None:
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return None
    try:
        return p.AsDouble()
    except Exception:
        return None


def get_string_param(elem, bip=None, name=None):
    if elem is None:
        return ''
    p = None
    if bip is not None:
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return ''
    try:
        return p.AsString() or ''
    except Exception:
        try:
            return p.AsValueString() or ''
        except Exception:
            return ''


def normalize(vec):
    if vec is None:
        return None
    try:
        if float(vec.GetLength()) < 1e-9:
            return None
        return vec.Normalize()
    except Exception:
        return None


def normalize_xy(vec):
    if vec is None:
        return None
    try:
        flat = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
    except Exception:
        return None
    return normalize(flat)


def get_location_point(elem):
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
            try:
                return loc.Curve.Evaluate(0.5, True)
            except Exception:
                return None
    except Exception:
        return None
    return None


def get_door_width_ft(door):
    if door is None:
        return None
    for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
        if target is None:
            continue
        val = get_double_param(target, bip=DB.BuiltInParameter.DOOR_WIDTH, name='Width')
        if val is None:
            continue
        try:
            if float(val) > 1e-6:
                return float(val)
        except Exception:
            continue
    return None


def get_door_height_ft(door):
    if door is None:
        return None
    for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
        if target is None:
            continue
        val = get_double_param(target, bip=DB.BuiltInParameter.DOOR_HEIGHT, name='Height')
        if val is None:
            continue
        try:
            if float(val) > 1e-6:
                return float(val)
        except Exception:
            continue
    return None


def get_door_head_z(door):
    if door is None:
        return None

    level = None
    try:
        if door.LevelId:
            level = door.Document.GetElement(door.LevelId)
    except Exception:
        level = None
    level_z = float(level.Elevation) if level is not None else 0.0

    head = None
    for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
        if target is None:
            continue
        head = get_double_param(target, bip=DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM, name='Head Height')
        if head is not None:
            break
    if head is None:
        for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
            if target is None:
                continue
            head = get_double_param(target, bip=DB.BuiltInParameter.DOOR_HEIGHT, name='Height')
            if head is not None:
                break

    if head is not None:
        return level_z + float(head)

    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return float(bb.Max.Z)
    except Exception:
        pass
    return None


def get_door_axes(door, wall):
    hand = None
    facing = None
    try:
        hand = getattr(door, 'HandOrientation', None)
    except Exception:
        hand = None
    try:
        facing = getattr(door, 'FacingOrientation', None)
    except Exception:
        facing = None

    hand = normalize(hand)
    facing = normalize(facing)

    if facing is None and wall is not None:
        try:
            facing = normalize(wall.Orientation)
        except Exception:
            facing = None

    if hand is None and wall is not None:
        try:
            loc = wall.Location
            curve = loc.Curve if loc else None
            if curve is not None:
                try:
                    dir_vec = getattr(curve, 'Direction', None)
                    if dir_vec is None:
                        deriv = curve.ComputeDerivatives(0.5, True)
                        dir_vec = deriv.BasisX if deriv else None
                    hand = normalize(dir_vec)
                except Exception:
                    hand = None
        except Exception:
            hand = None

    if hand is None and facing is not None:
        try:
            hand = normalize(DB.XYZ.BasisZ.CrossProduct(facing))
        except Exception:
            hand = None

    if facing is None and hand is not None:
        try:
            facing = normalize(hand.CrossProduct(DB.XYZ.BasisZ))
        except Exception:
            facing = None

    hand = normalize_xy(hand)
    facing = normalize_xy(facing)

    if hand is not None and facing is not None:
        try:
            perp = normalize_xy(DB.XYZ(-float(hand.Y), float(hand.X), 0.0))
            if perp is not None and float(perp.DotProduct(facing)) < 0.0:
                perp = DB.XYZ(-float(perp.X), -float(perp.Y), 0.0)
            facing = normalize_xy(perp)
        except Exception:
            pass

    return hand, facing


def get_wall_axes(wall):
    if wall is None:
        return None, None

    wall_norm = None
    try:
        wall_norm = normalize_xy(wall.Orientation)
    except Exception:
        wall_norm = None

    wall_dir = None
    if wall_norm is not None:
        try:
            wall_dir = normalize_xy(DB.XYZ.BasisZ.CrossProduct(wall_norm))
        except Exception:
            wall_dir = None

    if wall_dir is None:
        try:
            loc = wall.Location
            crv = loc.Curve if loc is not None else None
            if crv is not None:
                d = getattr(crv, 'Direction', None)
                if d is None:
                    deriv = crv.ComputeDerivatives(0.5, True)
                    d = deriv.BasisX if deriv else None
                wall_dir = normalize_xy(d)
        except Exception:
            wall_dir = None

    if wall_norm is None and wall_dir is not None:
        try:
            wall_norm = normalize_xy(wall_dir.CrossProduct(DB.XYZ.BasisZ))
        except Exception:
            wall_norm = None

    if wall_dir is not None and wall_norm is not None:
        try:
            perp = normalize_xy(DB.XYZ(-float(wall_dir.Y), float(wall_dir.X), 0.0))
            if perp is not None and float(perp.DotProduct(wall_norm)) < 0.0:
                perp = DB.XYZ(-float(perp.X), -float(perp.Y), 0.0)
            wall_norm = normalize_xy(perp)
        except Exception:
            pass

    return wall_dir, wall_norm


def _safe_lower(val):
    if val is None:
        return ''
    try:
        return str(val).strip().lower()
    except Exception:
        return ''


def _contains_any(text, tokens):
    text = _safe_lower(text)
    if not text:
        return False
    for token in tokens or ():
        t = _safe_lower(token)
        if t and t in text:
            return True
    return False


def _contains_markers(text, markers):
    text = _safe_lower(text)
    if not text:
        return False
    for marker in markers or ():
        token = _safe_lower(marker)
        if not token:
            continue
        if token.isdigit():
            pattern = r'(?<!\d){0}(?!\d)'.format(re.escape(token))
            if re.search(pattern, text):
                return True
            continue
        if token in text:
            return True
    return False


def get_wall_type_name(wall):
    if wall is None:
        return ''
    try:
        wtype = wall.WallType
        if wtype is not None:
            nm = getattr(wtype, 'Name', None)
            if nm:
                return str(nm)
    except Exception:
        pass
    try:
        nm = getattr(wall, 'Name', None)
        if nm:
            return str(nm)
    except Exception:
        pass
    return ''


def get_wall_thickness_mm(wall):
    if wall is None:
        return None
    try:
        return ft_to_mm(float(wall.Width))
    except Exception:
        return None


def _normalize_mark_text_for_prefix(mark):
    txt = _safe_lower(mark)
    if not txt:
        return ''
    txt = txt.replace(' ', '').replace('_', '').replace('-', '')
    txt = txt.replace('pb', 'пб')
    return txt


def _mark_matches_prefixes(mark, prefixes):
    mark_key = _normalize_mark_text_for_prefix(mark)
    if not mark_key:
        return False
    for raw in prefixes or ():
        pref_key = _normalize_mark_text_for_prefix(raw)
        if pref_key and mark_key.startswith(pref_key):
            return True
    return False


def _wall_material_kind_from_name(wall_name):
    name_l = _safe_lower(wall_name)
    if _contains_any(name_l, getattr(constants, 'PGP_WALL_KEYWORDS', ())):
        return 'pgp'
    if _contains_any(name_l, getattr(constants, 'CERAMIC_WALL_KEYWORDS', ())):
        return 'ceramic'
    if _contains_any(name_l, getattr(constants, 'SILICATE_WALL_KEYWORDS', ())):
        return 'silicate'
    return ''


def _wall_material_kind_from_layers(wall):
    for row in _iter_wall_layers(wall):
        mat_name = str(row.get('material_name', '') or '')
        if _contains_any(mat_name, getattr(constants, 'CERAMIC_WALL_KEYWORDS', ())):
            return 'ceramic'
        if _contains_any(mat_name, getattr(constants, 'SILICATE_WALL_KEYWORDS', ())):
            return 'silicate'
    return ''


def _wall_class_mm_from_name_or_thickness(wall_name, thickness_mm, material_kind=''):
    name_l = _safe_lower(wall_name)
    kind = _safe_lower(material_kind)

    if kind == 'pgp':
        if _contains_markers(name_l, getattr(constants, 'PGP_80_MARKERS', ())):
            return int(getattr(constants, 'PGP_80_MM', 80.0))
    else:
        if _contains_markers(name_l, getattr(constants, 'SILICATE_120_MARKERS', ())):
            return int(getattr(constants, 'SILICATE_120_MM', 120.0))
        if _contains_markers(name_l, getattr(constants, 'SILICATE_250_MARKERS', ())):
            return int(getattr(constants, 'SILICATE_250_MM', 250.0))

    if thickness_mm is None:
        return None

    try:
        tmm = float(thickness_mm)
    except Exception:
        return None

    tol = float(getattr(constants, 'WALL_THICKNESS_TOLERANCE_MM', 20.0))
    if kind == 'pgp':
        t80 = float(getattr(constants, 'PGP_80_MM', 80.0))
        if abs(tmm - t80) <= tol:
            return int(round(t80))
        return None

    t120 = float(getattr(constants, 'SILICATE_120_MM', 120.0))
    t250 = float(getattr(constants, 'SILICATE_250_MM', 250.0))
    if abs(tmm - t120) <= tol:
        return int(round(t120))
    if abs(tmm - t250) <= tol:
        return int(round(t250))
    return None


def lintel_plan_for_wall(wall):
    wall_name = get_wall_type_name(wall)
    thickness_mm = get_wall_thickness_mm(wall)

    material_kind = _wall_material_kind_from_name(wall_name)
    if not material_kind or material_kind == 'unknown':
        material_kind = _wall_material_kind_from_layers(wall)

    if material_kind not in ('pgp', 'ceramic', 'silicate'):
        return {
            'eligible': False,
            'count': 0,
            'is_double': False,
            'reason': 'unsupported_wall_material',
            'material_kind': material_kind or '',
            'wall_type_name': wall_name,
            'thickness_mm': thickness_mm,
            'wall_class_mm': None,
        }

    wall_class_mm = _wall_class_mm_from_name_or_thickness(wall_name, thickness_mm, material_kind=material_kind)
    allowed_classes = []
    if material_kind == 'pgp':
        allowed_classes = [int(getattr(constants, 'PGP_80_MM', 80.0))]
    else:
        allowed_classes = [
            int(getattr(constants, 'SILICATE_120_MM', 120.0)),
            int(getattr(constants, 'SILICATE_250_MM', 250.0)),
        ]

    if wall_class_mm not in tuple(allowed_classes):
        return {
            'eligible': False,
            'count': 0,
            'is_double': False,
            'reason': 'unsupported_wall_thickness',
            'material_kind': material_kind,
            'wall_type_name': wall_name,
            'thickness_mm': thickness_mm,
            'wall_class_mm': wall_class_mm,
        }

    is_double = (material_kind != 'pgp') and bool(
        float(wall_class_mm) > float(getattr(constants, 'WALL_DOUBLE_THRESHOLD_MM', 120.0))
    )
    count = 2 if is_double else 1
    reason = '{0}_{1}'.format(material_kind, 'double' if is_double else 'single')
    return {
        'eligible': True,
        'count': count,
        'is_double': bool(is_double),
        'reason': reason,
        'material_kind': material_kind,
        'wall_type_name': wall_name,
        'thickness_mm': thickness_mm,
        'wall_class_mm': int(wall_class_mm),
    }


def lintel_count_for_wall(wall):
    plan = lintel_plan_for_wall(wall)
    try:
        count = int(plan.get('count', 0) or 0)
        return count if count > 0 else 1
    except Exception:
        return 1


def lintel_offset_for_wall(wall, lintel_width_ft):
    if wall is None:
        return 0.0
    try:
        wall_w = float(wall.Width)
    except Exception:
        wall_w = 0.0
    if wall_w <= 0.0:
        return 0.0
    try:
        offset = wall_w * 0.5 - float(lintel_width_ft) * 0.5
    except Exception:
        offset = 0.0
    return offset if offset > 1e-6 else 0.0


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return None


def _wall_class_mm_from_plan(plan):
    if not isinstance(plan, dict):
        return None
    wall_class = _safe_float(plan.get('wall_class_mm'))
    if wall_class is not None:
        return int(round(float(wall_class)))

    reason = _safe_lower(plan.get('reason', ''))
    if reason.startswith('pgp_'):
        return int(getattr(constants, 'PGP_80_MM', 80.0))
    if reason.startswith('silicate_120'):
        return int(constants.SILICATE_120_MM)
    if reason.startswith('silicate_250'):
        return int(constants.SILICATE_250_MM)

    tmm = _safe_float(plan.get('thickness_mm'))
    if tmm is None:
        return None
    options = []
    for attr_name in ('PGP_80_MM', 'SILICATE_120_MM', 'SILICATE_250_MM'):
        val = _safe_float(getattr(constants, attr_name, None))
        if val is not None:
            options.append(float(val))
    if not options:
        options = [float(constants.SILICATE_120_MM), float(constants.SILICATE_250_MM)]
    best = min(options, key=lambda x: abs(float(tmm) - float(x)))
    return int(round(float(best)))


def _iter_wall_layers(wall):
    rows = []
    if wall is None:
        return rows
    try:
        wtype = wall.WallType
        cst = wtype.GetCompoundStructure() if wtype is not None else None
        layers = list(cst.GetLayers()) if cst is not None else []
    except Exception:
        return rows
    if not layers:
        return rows

    total = 0.0
    for layer in layers:
        try:
            total += max(0.0, float(layer.Width))
        except Exception:
            continue
    if total <= 1e-9:
        return rows

    cursor = -0.5 * total
    doc = getattr(wall, 'Document', None)
    for i, layer in enumerate(layers):
        try:
            width_ft = max(0.0, float(layer.Width))
        except Exception:
            width_ft = 0.0
        center_ft = cursor + 0.5 * width_ft
        cursor += width_ft

        mat_name = ''
        try:
            mid = getattr(layer, 'MaterialId', None)
            if mid is not None and mid != DB.ElementId.InvalidElementId and doc is not None:
                mat = doc.GetElement(mid)
                if mat is not None:
                    mat_name = str(getattr(mat, 'Name', '') or '')
        except Exception:
            mat_name = ''

        rows.append({
            'index': int(i),
            'center_ft': float(center_ft),
            'width_ft': float(width_ft),
            'material_name': mat_name,
        })
    return rows


def get_silicate_layer_offsets_ft(wall):
    offsets = []
    for row in _iter_wall_layers(wall):
        if _contains_any(row.get('material_name', ''), constants.SILICATE_WALL_KEYWORDS):
            offsets.append(float(row.get('center_ft', 0.0)))
    return offsets


def _wall_to_door_normal_sign(wall, dir_norm):
    if wall is None or dir_norm is None:
        return 1.0
    try:
        wnorm = normalize(wall.Orientation)
    except Exception:
        wnorm = None
    if wnorm is None:
        return 1.0
    try:
        dot = float(wnorm.DotProduct(dir_norm))
    except Exception:
        dot = 1.0
    return 1.0 if dot >= 0.0 else -1.0


def lintel_offsets_for_wall_layers(wall, lintel_count, lintel_width_ft, dir_norm=None):
    try:
        cnt = int(lintel_count or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        return []

    sign = _wall_to_door_normal_sign(wall, dir_norm)
    silicate_offsets = sorted(get_silicate_layer_offsets_ft(wall))

    if cnt == 1:
        if silicate_offsets:
            best = min(silicate_offsets, key=lambda x: abs(float(x)))
            return [float(best) * sign]
        return [0.0]

    if len(silicate_offsets) >= 2:
        left = float(silicate_offsets[0])
        right = float(silicate_offsets[-1])
        center = (left + right) * 0.5
        return [(left - center) * sign, (right - center) * sign]

    fallback = lintel_offset_for_wall(wall, lintel_width_ft)
    if fallback > 1e-6:
        return [float(fallback), float(-fallback)]
    return [0.0]


def _table_rows_for_wall_class(wall_class_mm):
    rows = []
    if wall_class_mm is None:
        return rows
    for row in constants.LINTEL_SELECTION_TABLE or ():
        try:
            if int(row.get('wall_mm', 0) or 0) == int(wall_class_mm):
                rows.append(row)
        except Exception:
            continue
    rows = sorted(rows, key=lambda r: (int(r.get('opening_w_mm', 0) or 0), int(r.get('opening_h_mm', 0) or 0)))
    return rows


def _family_name_for_wall_class_mm(wall_class_mm):
    mapping = dict(getattr(constants, 'LINTEL_FAMILY_BY_WALL_MM', {}) or {})
    if wall_class_mm is not None:
        try:
            fam = mapping.get(int(round(float(wall_class_mm))))
        except Exception:
            fam = None
        if fam:
            return str(fam)

    family_names = tuple(getattr(constants, 'LINTEL_FAMILY_NAMES', ()) or ())
    for fam in family_names:
        if fam:
            return str(fam)
    return str(getattr(constants, 'LINTEL_FAMILY_NAME', '') or '')


def _with_default_family(spec, wall_class_mm):
    row = dict(spec or {})
    if not row.get('family_name'):
        row['family_name'] = _family_name_for_wall_class_mm(wall_class_mm)
    return row


def _normalize_family_key(text):
    key = _safe_lower(text)
    key = key.replace(' ', '').replace('_', '')
    if key.endswith('.rfa'):
        key = key[:-4]
    return key


def _family_matches_any(row_family_name, candidate_family_names):
    row_key = _normalize_family_key(row_family_name)
    if not row_key:
        return False
    for raw in candidate_family_names or ():
        cand_key = _normalize_family_key(raw)
        if not cand_key:
            continue
        if row_key == cand_key or (cand_key in row_key) or (row_key in cand_key):
            return True
    return False


def _catalog_rows_for_wall_kind(catalog_rows, wall_plan):
    rows = list(catalog_rows or [])
    if not rows:
        return []
    kind = str((wall_plan or {}).get('material_kind', '') or '').strip().lower()

    filtered = []
    if kind == 'pgp':
        pa_primary = (getattr(constants, 'LINTEL_FAMILY_PA', ''),)
        pa_alt = (getattr(constants, 'LINTEL_FAMILY_PA_ALT', ''),)
        primary = []
        secondary = []
        guessed = []
        for row in rows:
            fam_name = str(row.get('family_name', '') or '')
            mark = _normalize_mark_text_for_prefix(row.get('mark', ''))
            if _family_matches_any(fam_name, pa_primary):
                primary.append(row)
                continue
            if _family_matches_any(fam_name, pa_alt):
                secondary.append(row)
                continue
            if mark.startswith('ар'):
                guessed.append(row)
                continue
        if primary:
            return primary
        if guessed:
            return guessed
        return secondary

    if kind not in ('ceramic', 'silicate'):
        return rows

    pb_names = (getattr(constants, 'LINTEL_FAMILY_PB', ''),)
    primary_pb = []
    secondary_by_mark = []
    for row in rows:
        fam_name = str(row.get('family_name', '') or '')
        row_kind = str(row.get('table_kind', '') or '').strip().lower()
        mark = str(row.get('mark', '') or '')

        family_is_pb = _family_matches_any(fam_name, pb_names)
        mark_matches_kind = (
            (kind == 'ceramic' and _mark_matches_prefixes(mark, getattr(constants, 'CERAMIC_MARK_PREFIXES', ()))) or
            (kind == 'silicate' and _mark_matches_prefixes(mark, getattr(constants, 'SILICATE_MARK_PREFIXES', ())))
        )

        if family_is_pb and (row_kind == kind or mark_matches_kind):
            primary_pb.append(row)
            continue

        if row_kind == kind:
            secondary_by_mark.append(row)
            continue
        if mark_matches_kind:
            secondary_by_mark.append(row)
            continue

    if primary_pb:
        return primary_pb
    # For brick walls only PB family is allowed.
    return []


def _pick_pgp_spec_from_lengths(rows, wall_plan, door_width_ft):
    kind = str((wall_plan or {}).get('material_kind', '') or '').strip().lower()
    if kind != 'pgp':
        return None

    dw_mm = None
    if door_width_ft is not None:
        try:
            dw_mm = ft_to_mm(float(door_width_ft))
        except Exception:
            dw_mm = None
    if dw_mm is None or float(dw_mm) <= 1e-6:
        dw_mm = float(getattr(constants, 'DEFAULT_OPENING_WIDTH_MM', 900.0))

    min_bearing_mm = float(getattr(constants, 'PGP_MIN_BEARING_MM', 90.0))
    req_len_mm = float(dw_mm) + 2.0 * float(min_bearing_mm)

    lengths = []
    for row in rows or ():
        ln = _safe_float(row.get('len_mm'))
        if ln is not None and float(ln) > 1e-6:
            lengths.append(float(ln))
    for val in getattr(constants, 'PGP_REBAR_LENGTHS_MM', ()) or ():
        try:
            num = float(val)
        except Exception:
            continue
        if num > 1e-6:
            lengths.append(num)
    lengths = sorted(set(lengths))
    if not lengths:
        lengths = [float(req_len_mm)]

    tol = 1e-6
    feasible = [float(ln) for ln in lengths if float(ln) + tol >= float(req_len_mm)]
    if feasible:
        target_len_mm = float(sorted(feasible)[0])
    else:
        target_len_mm = float(lengths[-1])

    chosen_row = None
    rows_len = []
    for row in rows or ():
        ln = _safe_float(row.get('len_mm'))
        if ln is None:
            continue
        rows_len.append((
            0 if float(ln) + tol >= float(req_len_mm) else 1,
            abs(float(ln) - float(target_len_mm)),
            float(ln),
            row
        ))
    if rows_len:
        rows_len = sorted(rows_len, key=lambda x: (x[0], x[1], x[2]))
        chosen_row = rows_len[0][3]
        target_len_mm = float(rows_len[0][2])

    trim_len_mm = float(target_len_mm)
    bearing_mm = max(float(min_bearing_mm), (float(trim_len_mm) - float(dw_mm)) * 0.5)

    fam_name = str(getattr(constants, 'LINTEL_FAMILY_PA', '') or getattr(constants, 'LINTEL_FAMILY_PA_ALT', '') or '')
    result = {
        'mark': 'Ар_А400_D16_L{0}'.format(int(round(float(target_len_mm)))),
        'len_mm': float(target_len_mm),
        'trim_len_mm': float(trim_len_mm),
        'w_mm': 80.0,
        'h_mm': 16.0,
        'bearing_mm': float(bearing_mm),
        'opening_w_mm': float(dw_mm),
        'count': 1,
        'family_name': fam_name,
    }
    if chosen_row is not None:
        result['mark'] = str(chosen_row.get('mark', result['mark']) or result['mark'])
        result['w_mm'] = float(_safe_float(chosen_row.get('w_mm')) or result['w_mm'])
        result['h_mm'] = float(_safe_float(chosen_row.get('h_mm')) or result['h_mm'])
        result['family_name'] = str(chosen_row.get('family_name', result['family_name']) or result['family_name'])
        sym = chosen_row.get('symbol', None)
        if sym is not None:
            result['symbol'] = sym
    return result


def pick_lintel_spec_from_catalog(catalog_rows, wall_plan, door_width_ft, door_height_ft=None):
    rows = _catalog_rows_for_wall_kind(catalog_rows, wall_plan)
    if not rows:
        return None
    kind = str((wall_plan or {}).get('material_kind', '') or '').strip().lower()
    if kind == 'pgp':
        return _pick_pgp_spec_from_lengths(rows, wall_plan, door_width_ft)

    dw_mm = ft_to_mm(float(door_width_ft)) if door_width_ft is not None else None
    tol = float(constants.LINTEL_TABLE_TOLERANCE_MM)

    def _sort_key(row):
        try:
            width_pref = abs(float(row.get('w_mm', constants.LINTEL_WIDTH_MM)) - float(constants.LINTEL_WIDTH_MM))
        except Exception:
            width_pref = 1e12
        return (
            float(row.get('opening_w_mm') if row.get('opening_w_mm') is not None else 1e12),
            float(width_pref),
            float(row.get('h_mm') if row.get('h_mm') is not None else 1e12),
            float(row.get('len_mm') if row.get('len_mm') is not None else 1e12),
            _normalize_mark_text_for_prefix(row.get('mark', '')),
        )

    rows = sorted(rows, key=_sort_key)

    if dw_mm is None:
        chosen = rows[0]
    else:
        eligible = []
        for row in rows:
            opening = row.get('opening_w_mm', None)
            if opening is None:
                continue
            try:
                opening = float(opening)
            except Exception:
                continue
            if opening + tol >= float(dw_mm):
                eligible.append(row)
        if eligible:
            chosen = sorted(eligible, key=_sort_key)[0]
        else:
            rows_by_opening = [r for r in rows if r.get('opening_w_mm') is not None]
            if rows_by_opening:
                chosen = sorted(rows_by_opening, key=lambda r: float(r.get('opening_w_mm', 0.0)), reverse=True)[0]
            else:
                chosen = rows[0]

    count = int((wall_plan or {}).get('count', 1) or 1)
    result = dict(chosen)
    result['count'] = 2 if count > 1 else 1
    if not result.get('family_name'):
        result['family_name'] = str(getattr(constants, 'LINTEL_FAMILY_PB', '') or '')
    return result


def pick_lintel_spec_from_table(wall_plan, door_width_ft, door_height_ft):
    wall_class_mm = _wall_class_mm_from_plan(wall_plan)
    rows = _table_rows_for_wall_class(wall_class_mm)
    if not rows:
        return None

    dw_mm = ft_to_mm(float(door_width_ft)) if door_width_ft is not None else None
    dh_mm = ft_to_mm(float(door_height_ft)) if door_height_ft is not None else None
    tol = float(constants.LINTEL_TABLE_TOLERANCE_MM)

    if dw_mm is None or dh_mm is None:
        return _with_default_family(rows[0], wall_class_mm)

    eligible = []
    for row in rows:
        try:
            rw = float(row.get('opening_w_mm', 0) or 0)
            rh = float(row.get('opening_h_mm', 0) or 0)
        except Exception:
            continue
        d_w = rw - float(dw_mm)
        d_h = rh - float(dh_mm)
        if d_w >= -tol and d_h >= -tol:
            eligible.append((max(0.0, d_w), max(0.0, d_h), rw, rh, row))

    if eligible:
        eligible = sorted(eligible, key=lambda x: (x[0], x[1], x[2], x[3]))
        return _with_default_family(eligible[0][4], wall_class_mm)

    # If exact/greater match is not found, choose the closest entry in the wall class.
    rows_by_distance = []
    for row in rows:
        try:
            rw = float(row.get('opening_w_mm', 0) or 0)
            rh = float(row.get('opening_h_mm', 0) or 0)
        except Exception:
            continue
        dist = abs(rw - float(dw_mm)) + abs(rh - float(dh_mm))
        rows_by_distance.append((dist, rw, rh, row))
    if not rows_by_distance:
        return None
    rows_by_distance = sorted(rows_by_distance, key=lambda x: (x[0], x[1], x[2]))
    return _with_default_family(rows_by_distance[0][3], wall_class_mm)


def fallback_lintel_spec(door_width_ft, wall_plan=None):
    width_ft = float(door_width_ft) if door_width_ft is not None else float(constants.DEFAULT_OPENING_WIDTH_FT)
    wall_kind = str((wall_plan or {}).get('material_kind', '') or '').strip().lower()
    if wall_kind == 'pgp':
        min_bearing_mm = float(getattr(constants, 'PGP_MIN_BEARING_MM', 90.0))
        bearing_mm = float(getattr(constants, 'PGP_TARGET_BEARING_MM', min_bearing_mm))
        if bearing_mm < min_bearing_mm:
            bearing_mm = min_bearing_mm
        bearing_ft = mm_to_ft(bearing_mm)
        length_ft = float(width_ft) + 2.0 * float(bearing_ft)
        width_mm = 80.0
        height_mm = 16.0
    else:
        bearing_mm = float(constants.LINTEL_BEARING_MM)
        length_ft = float(width_ft) + 2.0 * float(constants.LINTEL_BEARING_FT)
        width_mm = float(constants.LINTEL_WIDTH_MM)
        height_mm = float(constants.LINTEL_HEIGHT_MM)
    wall_class_mm = _wall_class_mm_from_plan(wall_plan)
    return {
        'mark': '',
        'len_mm': ft_to_mm(length_ft),
        'trim_len_mm': ft_to_mm(length_ft),
        'w_mm': width_mm,
        'h_mm': height_mm,
        'bearing_mm': bearing_mm,
        'count': 1,
        'family_name': _family_name_for_wall_class_mm(wall_class_mm),
    }


def lintel_spec_to_ft(spec):
    data = dict(spec or {})
    default_length_ft = float(constants.DEFAULT_OPENING_WIDTH_FT) + 2.0 * float(constants.LINTEL_BEARING_FT)
    default_length_mm = ft_to_mm(default_length_ft)
    len_mm = float(data.get('len_mm', default_length_mm))
    trim_len_mm = float(data.get('trim_len_mm', len_mm))
    return {
        'mark': str(data.get('mark', '') or ''),
        'length_ft': mm_to_ft(len_mm),
        'trim_length_ft': mm_to_ft(trim_len_mm),
        'width_ft': mm_to_ft(float(data.get('w_mm', constants.LINTEL_WIDTH_MM))),
        'height_ft': mm_to_ft(float(data.get('h_mm', constants.LINTEL_HEIGHT_MM))),
        'bearing_ft': mm_to_ft(float(data.get('bearing_mm', constants.LINTEL_BEARING_MM))),
        'count': int(data.get('count', 1) or 1),
        'family_name': str(data.get('family_name', '') or ''),
    }


def build_comment(tag, door_id, count, length_mm, width_mm, height_mm):
    return "{0}|door={1}|count={2}|len_mm={3}|w_mm={4}|h_mm={5}".format(
        tag, int(door_id), int(count), int(round(length_mm)), int(round(width_mm)), int(round(height_mm))
    )


def parse_door_id_from_comment(comment, tag):
    if not comment:
        return None
    try:
        if tag not in comment:
            return None
    except Exception:
        return None
    try:
        parts = str(comment).split('|')
    except Exception:
        return None
    for part in parts:
        part = part.strip()
        if part.startswith('door='):
            try:
                return int(part.split('=', 1)[1])
            except Exception:
                return None
    return None
