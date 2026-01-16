# -*- coding: utf-8 -*-
import math

from pyrevit import DB, forms, revit, script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception
from utils_units import mm_to_ft, ft_to_mm
import socket_utils as su


doc = revit.doc
output = script.get_output()
logger = script.get_logger()


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _dist_xy(a, b):
    try:
        return ((float(a.X) - float(b.X)) ** 2 + (float(a.Y) - float(b.Y)) ** 2) ** 0.5
    except Exception:
        return 1e9


def _closest_point_on_segment_xy(p, a, b):
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


def _pt_in_room(room, pt_xy, base_z_ft):
    if room is None or pt_xy is None:
        return False
    try:
        z0 = float(base_z_ft or 0.0)
    except Exception:
        z0 = 0.0
    for dz in (1.0, 3.0, 0.5):
        try:
            p = DB.XYZ(float(pt_xy.X), float(pt_xy.Y), z0 + dz)
            if room.IsPointInRoom(p):
                return True
        except Exception:
            continue
    return False


def _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    try:
        x, y = float(pt.X), float(pt.Y)
        minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
        maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
        return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)
    except Exception:
        return False


def _is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        return bool(room.IsPointInRoom(point))
    except Exception:
        return False


def _points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []

    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None

    selected = []
    for pt in points:
        if pt is None:
            continue

        pt_room = pt
        try:
            if room_bb:
                zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), zmid)
        except Exception:
            pt_room = pt

        if room_bb:
            try:
                min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, room_bb.Min.Z)
                max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, room_bb.Max.Z)
                if not _bbox_contains_point_xy(pt, min_exp, max_exp):
                    continue
            except Exception:
                pass

        if _is_point_in_room(room, pt_room):
            selected.append(pt)
            continue

        # Boundary-adjacent tolerance: probe inward towards room bbox center
        try:
            if room_bb:
                rc = DB.XYZ(
                    (room_bb.Min.X + room_bb.Max.X) * 0.5,
                    (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                    float(pt_room.Z)
                )
                v = rc - pt_room
                if v and v.GetLength() > mm_to_ft(1):
                    vn = v.Normalize()
                    for dmm in (200, 500, 900):
                        probe = pt_room + vn * mm_to_ft(dmm)
                        if _is_point_in_room(room, probe):
                            selected.append(pt)
                            break
        except Exception:
            pass

    return selected


def _get_comments_text(elem):
    if elem is None:
        return u''
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    for nm in (u'Комментарии', u'Comments'):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsString()
                if v:
                    return v
        except Exception:
            continue
    return u''


def _collect_tagged_instances(host_doc, tag_value, symbol_id=None):
    ids = set()
    elems = []
    pts = []
    if host_doc is None or not tag_value:
        return ids, elems, pts

    try:
        sym_id_int = int(symbol_id) if symbol_id is not None else None
    except Exception:
        sym_id_int = None

    tag_value_norm = None
    try:
        tag_value_norm = (tag_value or u'').strip().lower()
    except Exception:
        tag_value_norm = None

    for bic in (
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_Furniture,
    ):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                c = _get_comments_text(e)
            except Exception:
                c = u''
            if not c:
                continue
            try:
                if tag_value not in c:
                    continue
            except Exception:
                continue

            # Only treat as existing if tag matches exactly at the start of a token.
            # Prevents false positives when other tools embed similar substrings.
            try:
                c_norm = (c or u'').lower()
            except Exception:
                c_norm = u''
            if tag_value_norm:
                try:
                    ok = False
                    for part in c_norm.split():
                        if part.startswith(tag_value_norm):
                            ok = True
                            break
                    if not ok:
                        continue
                except Exception:
                    pass

            # Optional: restrict dedupe candidates to the exact target type (FamilySymbol).
            if sym_id_int is not None:
                try:
                    es = getattr(e, 'Symbol', None)
                    if es is None:
                        continue
                    if int(es.Id.IntegerValue) != sym_id_int:
                        continue
                except Exception:
                    continue

            try:
                ids.add(int(e.Id.IntegerValue))
            except Exception:
                pass
            elems.append(e)
            try:
                pt = su._inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    return ids, elems, pts


def _get_instance_point(inst):
    try:
        return su._inst_center_point(inst)
    except Exception:
        return None


def _get_offset_from_level_ft(inst, host_doc=None):
    if inst is None:
        return None
    try:
        p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and p.StorageType == DB.StorageType.Double:
            v = p.AsDouble()
            if v is not None:
                return float(v)
    except Exception:
        pass

    for nm in (
        u'Отметка от уровня',
        u'Смещение от уровня',
        u'Elevation from Level',
        u'Offset from Level',
    ):
        try:
            p = inst.LookupParameter(nm)
            if p and p.StorageType == DB.StorageType.Double:
                v = p.AsDouble()
                if v is not None:
                    return float(v)
        except Exception:
            continue

    try:
        pt = _get_instance_point(inst)
        lid = getattr(inst, 'LevelId', None)
        if pt is not None and lid and lid != DB.ElementId.InvalidElementId:
            d = host_doc or doc
            lvl = d.GetElement(lid) if d else None
            if lvl and hasattr(lvl, 'Elevation'):
                return float(pt.Z) - float(lvl.Elevation)
    except Exception:
        pass

    return None


def _xy0(p):
    try:
        return DB.XYZ(float(p.X), float(p.Y), 0.0)
    except Exception:
        return None


def _validate_between_sink_tub(seg_p0, seg_p1, sink_pt, tub_pt, inst_pt_link, dist_wall_ft, between_pad_mm=100):
    """
    Validate ШДУП placement. Supports three modes:
    1. Both sink and tub - validates between them
    2. Only sink - validates near sink
    3. Only tub - validates near tub
    """
    p0 = _xy0(seg_p0)
    p1 = _xy0(seg_p1)
    s = _xy0(sink_pt) if sink_pt else None
    b = _xy0(tub_pt) if tub_pt else None
    i = _xy0(inst_pt_link)

    # Must have segment and instance point
    if not all([p0, p1, i]):
        return False, False, None, None, None, None

    # Must have at least one fixture
    if not s and not b:
        return False, False, None, None, None, None

    pi = _closest_point_on_segment_xy(i, p0, p1)
    if pi is None:
        return False, False, None, None, None, None

    try:
        seg_len = p0.DistanceTo(p1)
    except Exception:
        seg_len = 0.0
    if seg_len <= 1e-6:
        return False, False, None, None, None, None

    try:
        dist_to_wall = _dist_xy(i, pi)
    except Exception:
        dist_to_wall = None
    on_wall_ok = (dist_to_wall is not None) and (dist_to_wall <= float(dist_wall_ft or mm_to_ft(150)))

    try:
        ti = p0.DistanceTo(pi) / seg_len
    except Exception:
        return on_wall_ok, False, dist_to_wall, None, None, None

    # Case 1: Both fixtures exist - validate between them
    if s and b:
        ps = _closest_point_on_segment_xy(s, p0, p1)
        pb = _closest_point_on_segment_xy(b, p0, p1)
        if ps is None or pb is None:
            return on_wall_ok, False, dist_to_wall, None, None, None

        try:
            ts = p0.DistanceTo(ps) / seg_len
            tb = p0.DistanceTo(pb) / seg_len
        except Exception:
            return on_wall_ok, False, dist_to_wall, None, None, None

        lo = min(ts, tb)
        hi = max(ts, tb)
        try:
            pad_ft = mm_to_ft(int(between_pad_mm or 100))
        except Exception:
            pad_ft = mm_to_ft(100)
        tol = float(pad_ft) / float(seg_len) if seg_len > 1e-6 else 0.0
        between_ok = (ti >= (lo - tol)) and (ti <= (hi + tol))
        return on_wall_ok, between_ok, dist_to_wall, ts, tb, ti

    # Case 2: Only one fixture - just validate on wall (between_ok = True if on wall)
    else:
        # For single fixture, we don't have "between" constraint, so it's OK if on wall
        ts = None
        tb = None
        if s:
            ps = _closest_point_on_segment_xy(s, p0, p1)
            if ps:
                try:
                    ts = p0.DistanceTo(ps) / seg_len
                except: pass
        if b:
            pb = _closest_point_on_segment_xy(b, p0, p1)
            if pb:
                try:
                    tb = p0.DistanceTo(pb) / seg_len
                except: pass

        # For single fixture, "between_ok" just means "on the same wall"
        between_ok = on_wall_ok
        return on_wall_ok, between_ok, dist_to_wall, ts, tb, ti


def _get_wall_segments(room, link_doc):
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
        try:
            if su._is_curtain_wall(el):
                continue
        except Exception:
            pass
        try:
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            if p0.DistanceTo(p1) <= 1e-6:
                continue
            segs.append((p0, p1, el))
        except Exception:
            continue
    return segs


def _nearest_segment(pt, segments):
    best = None
    best_proj = None
    best_d = None
    for p0, p1, w in segments or []:
        proj = _closest_point_on_segment_xy(pt, p0, p1)
        if proj is None:
            continue
        d = _dist_xy(pt, proj)
        if best is None or d < best_d:
            best = (p0, p1, w)
            best_proj = proj
            best_d = d
    return best, best_proj, best_d


def _pick_shdup_symbol(host_doc, cfg, rules):
    if host_doc is None:
        return None, None

    try:
        sym = su._load_symbol_from_saved_unique_id(host_doc, cfg, 'last_shdup_symbol_uid')
        if not sym:
            sym = su._load_symbol_from_saved_id(host_doc, cfg, 'last_shdup_symbol_id')
        if sym:
            return sym, placement_engine.format_family_type(sym)
    except Exception:
        pass

    fams = rules.get('family_type_names', {}) if rules else {}
    prefer = fams.get('shdup')
    prefer_list = []
    try:
        if isinstance(prefer, (list, tuple)):
            prefer_list = [x for x in prefer if x]
        elif prefer:
            prefer_list = [prefer]
    except Exception:
        prefer_list = [prefer] if prefer else []

    for want in prefer_list:
        try:
            sym = su._find_symbol_by_fullname(host_doc, want)
            if sym:
                return sym, placement_engine.format_family_type(sym)
        except Exception:
            continue

    # Auto-detect by keywords (project naming can differ)
    keys = [u'шдуп', u'shdup', u'пс_кр']
    best = None
    best_score = -999
    for bic in (
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_GenericModel,
    ):
        for s in placement_engine.iter_family_symbols(host_doc, category_bic=bic, limit=None):
            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''
            if not lbl:
                continue
            t = _norm(lbl)
            if not any(k in t for k in keys):
                continue
            sc = 0
            if bic == DB.BuiltInCategory.OST_ElectricalEquipment:
                sc += 20
            if 'eom' in t:
                sc += 10
            if u'(нагрузка)' in t:
                sc += 30
            if u'230' in t or u'230в' in t:
                sc += 10
            if sc > best_score:
                best = s
                best_score = sc

    if best:
        return best, placement_engine.format_family_type(best)

    # Manual selection
    items = []
    by_label = {}
    for bic in (
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_GenericModel,
    ):
        for s in placement_engine.iter_family_symbols(host_doc, category_bic=bic, limit=None):
            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''
            if not lbl:
                continue
            t = _norm(lbl)
            if t in by_label:
                continue
            by_label[t] = s
            items.append(lbl)

    items = sorted(items, key=lambda x: _norm(x))
    picked = forms.SelectFromList.show(
        items,
        title='Выберите тип ШДУП (Family : Type)',
        multiselect=False,
        button_name='Выбрать',
        allow_none=True,
    )
    if not picked:
        return None, None

    sym = by_label.get(_norm(picked))
    if not sym:
        return None, None
    return sym, placement_engine.format_family_type(sym)


def _collect_points_by_keywords_multi(link_doc, keys, bics, tag_bics=None):
    pts = []
    if link_doc is None or not keys:
        return pts

    for bic in (bics or []):
        try:
            pts.extend(su._collect_points_by_keywords(link_doc, keys, bic))
        except Exception:
            continue

    try:
        pts.extend(su._collect_textnote_points(link_doc, keys))
    except Exception:
        pass

    try:
        tag_pts = su._collect_independent_tag_points(link_doc, keys, allowed_bics=tag_bics)
        if (not tag_pts) and tag_bics:
            tag_pts = su._collect_independent_tag_points(link_doc, keys, allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts


def _collect_sink_points(link_doc, rules):
    keys = rules.get('sink_family_keywords', []) or [u'раков', u'умыв', u'sink', u'washbasin', u'мойк', u'basin', u'lavatory']
    bics = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericAnnotation,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    tag_bics = []
    for nm in (
        'OST_PlumbingFixtureTags',
        'OST_GenericModelTags',
        'OST_FurnitureTags',
        'OST_GenericAnnotation',
    ):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                tag_bics.append(bic)
        except Exception:
            continue
    return _collect_points_by_keywords_multi(link_doc, keys, bics, tag_bics=(tag_bics if tag_bics else None))


def _collect_tub_points(link_doc, rules):
    keys = rules.get('bath_keywords', None) or [u'ванн', u'bath', u'tub', u'jacuzzi', u'джакузи']
    bics = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericAnnotation,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    tag_bics = []
    for nm in (
        'OST_PlumbingFixtureTags',
        'OST_GenericModelTags',
        'OST_FurnitureTags',
        'OST_GenericAnnotation',
    ):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                tag_bics.append(bic)
        except Exception:
            continue
    return _collect_points_by_keywords_multi(link_doc, keys, bics, tag_bics=(tag_bics if tag_bics else None))


def main():
    output.print_md('# 07. ШДУП: Ванные')

    rules = config_loader.load_rules()
    cfg = script.get_config()

    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SHDUP'.format(comment_tag)

    height_ft = mm_to_ft(300)
    dedupe_ft = mm_to_ft(int(rules.get('dedupe_radius_mm', 300) or 300))
    if dedupe_ft < 0:
        dedupe_ft = 0.0
    batch_size = int(rules.get('batch_size', 25) or 25)

    validate_match_tol_ft = mm_to_ft(int(rules.get('shdup_validate_match_tol_mm', 2000) or 2000))
    validate_height_tol_ft = mm_to_ft(int(rules.get('shdup_validate_height_tol_mm', 20) or 20))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('shdup_validate_wall_dist_mm', 150) or 150))
    validate_between_pad_mm = int(rules.get('shdup_validate_between_pad_mm', 100) or 100)

    sym, sym_lbl = _pick_shdup_symbol(doc, cfg, rules)
    if not sym:
        alert('Не найден тип ШДУП. Загрузите семейство/тип в проект и повторите.')
        return

    try:
        su._store_symbol_id(cfg, 'last_shdup_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_shdup_symbol_uid', sym)
        script.save_config()
    except Exception:
        pass

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst:
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        return

    t = link_reader.get_total_transform(link_inst)

    raw_rooms = su._get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200))
    bath_rx = su._compile_patterns(rules.get('bath_room_name_patterns', []) or rules.get('wet_room_name_patterns', []))

    rooms = []
    for r in raw_rooms:
        try:
            if bath_rx and (not su._match_any(bath_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        rooms.append(r)

    if not rooms:
        alert('Нет подходящих помещений ванной (по паттернам).')
        return

    output.print_md('Найдено помещений ванных: **{0}** (из {1} всего отсканировано)'.format(
        len(rooms), len(raw_rooms)
    ))

    sinks_all = su._collect_sinks_points(link_doc, rules)
    used_sink_fallback = False
    if not sinks_all:
        sinks_all = _collect_sink_points(link_doc, rules)
        used_sink_fallback = True

    tub_data = su._collect_bathtubs_data(link_doc)
    tubs_all = [x[0] for x in tub_data] if tub_data else []
    used_tub_fallback = False
    if not tubs_all:
        tubs_all = _collect_tub_points(link_doc, rules)
        used_tub_fallback = True

    output.print_md('Раковины: **{0}**{1}; Ванны: **{2}**{3}'.format(
        len(sinks_all), ' (fallback)' if used_sink_fallback else '',
        len(tubs_all), ' (fallback)' if used_tub_fallback else ''
    ))

    # Allow script to continue if at least ONE type of fixture exists
    # (we now support bathrooms with only sink or only tub)
    if not sinks_all and not tubs_all:
        alert('Не найдено ни раковин, ни ванн в связи (AR).')
        return

    try:
        ids_before, _elems_before, existing_pts = _collect_tagged_instances(doc, comment_value, symbol_id=int(sym.Id.IntegerValue))
    except Exception:
        ids_before = set()
        existing_pts = []

    # Dedupe is only meant to prevent duplicates against pre-existing instances.
    # If we append planned points during the same run, every subsequent room can become a false duplicate.
    existing_pts_base = list(existing_pts or [])

    sym_flags = {}
    try:
        pt = sym.Family.FamilyPlacementType
        is_wp = (pt == DB.FamilyPlacementType.WorkPlaneBased)
        is_ol = (pt == DB.FamilyPlacementType.OneLevelBased)
        sym_flags[int(sym.Id.IntegerValue)] = (is_wp, is_ol)
    except Exception:
        sym_flags[int(sym.Id.IntegerValue)] = (False, False)

    sp_cache = {}
    pending = []
    plans = []

    created = created_face = created_wp = created_pt = 0
    skipped = 0
    skip_no_fixtures = 0
    skip_no_segs = 0
    skip_no_pair = 0
    skip_no_chosen = 0
    skip_geom = 0
    skip_vec = 0
    skip_dup = 0
    prepared = 0

    for room in rooms:
        base_z = su._room_level_elevation_ft(room, link_doc)

        sinks = _points_in_room(sinks_all, room)
        tubs = _points_in_room(tubs_all, room)

        if not sinks and not tubs:
            skipped += 1
            skip_no_fixtures += 1
            continue

        # Strategy:
        # 1. If both sink and tub exist -> place between them (original logic)
        # 2. If only sink exists -> place near sink
        # 3. If only tub exists -> place near tub

        best_s = None
        best_tb = None

        if sinks and tubs:
            # pick closest sink-tub pair
            best_d = None
            for s in sinks:
                for tb in tubs:
                    d = _dist_xy(s, tb)
                    if best_d is None or d < best_d:
                        best_s = s
                        best_tb = tb
                        best_d = d
        elif sinks:
            # Only sink - pick first one (or could pick closest to room center)
            best_s = sinks[0]
            best_tb = None
        elif tubs:
            # Only tub - pick first one
            best_s = None
            best_tb = tubs[0]

        if best_s is None and best_tb is None:
            skipped += 1
            skip_no_pair += 1
            continue

        segs = _get_wall_segments(room, link_doc)
        if not segs:
            skipped += 1
            skip_no_segs += 1
            continue

        seg_s, proj_s, _ = _nearest_segment(best_s, segs) if best_s else (None, None, None)
        seg_b, proj_b, _ = _nearest_segment(best_tb, segs) if best_tb else (None, None, None)

        chosen = None
        chosen_p0 = chosen_p1 = chosen_wall = None
        pfinal = None

        # Case 1: Both sink and tub exist - place between them
        if seg_s and seg_b and best_s and best_tb:
            try:
                if int(seg_s[2].Id.IntegerValue) == int(seg_b[2].Id.IntegerValue):
                    wall_id = int(seg_s[2].Id.IntegerValue)
                    segs_same = [sg for sg in segs if int(sg[2].Id.IntegerValue) == wall_id]
                    if proj_s and proj_b:
                        mid0 = DB.XYZ((proj_s.X + proj_b.X) * 0.5, (proj_s.Y + proj_b.Y) * 0.5, proj_s.Z)
                        chosen, _, _ = _nearest_segment(mid0, segs_same)
            except Exception:
                chosen = None

            if not chosen:
                best_sum = None
                for p0, p1, w in segs:
                    ps = _closest_point_on_segment_xy(best_s, p0, p1)
                    pb = _closest_point_on_segment_xy(best_tb, p0, p1)
                    if ps is None or pb is None:
                        continue
                    ssum = _dist_xy(best_s, ps) + _dist_xy(best_tb, pb)
                    if best_sum is None or ssum < best_sum:
                        best_sum = ssum
                        chosen = (p0, p1, w)

            if chosen:
                chosen_p0, chosen_p1, chosen_wall = chosen
                ps = _closest_point_on_segment_xy(best_s, chosen_p0, chosen_p1)
                pb = _closest_point_on_segment_xy(best_tb, chosen_p0, chosen_p1)
                if ps and pb:
                    mid = DB.XYZ((ps.X + pb.X) * 0.5, (ps.Y + pb.Y) * 0.5, ps.Z)
                    pfinal = _closest_point_on_segment_xy(mid, chosen_p0, chosen_p1)

        # Case 2: Only sink exists - place near sink (offset from fixture)
        elif seg_s and best_s:
            chosen = seg_s
            chosen_p0, chosen_p1, chosen_wall = chosen
            if proj_s:
                # Place at projection point (could add offset if needed)
                pfinal = proj_s

        # Case 3: Only tub exists - place near tub (offset from fixture)
        elif seg_b and best_tb:
            chosen = seg_b
            chosen_p0, chosen_p1, chosen_wall = chosen
            if proj_b:
                # Place at projection point (could add offset if needed)
                pfinal = proj_b

        if not chosen or not pfinal:
            skipped += 1
            skip_no_chosen += 1
            continue

        v = DB.XYZ(float(chosen_p1.X) - float(chosen_p0.X), float(chosen_p1.Y) - float(chosen_p0.Y), 0.0)
        if v.GetLength() <= 1e-9:
            skipped += 1
            skip_vec += 1
            continue
        v = v.Normalize()
        seg_len = chosen_p0.DistanceTo(chosen_p1)

        pt_link = DB.XYZ(float(pfinal.X), float(pfinal.Y), float(base_z) + float(height_ft))
        pt_host = t.OfPoint(pt_link) if t else pt_link

        # Existing dedupe
        has_dup = False
        if existing_pts_base and dedupe_ft and dedupe_ft > 1e-9:
            for ep in existing_pts_base:
                try:
                    if ep.DistanceTo(pt_host) <= dedupe_ft:
                        has_dup = True
                        break
                except Exception:
                    continue
        if has_dup:
            skipped += 1
            skip_dup += 1
            continue

        plans.append({
            'room_id': int(room.Id.IntegerValue),
            'room_name': su._room_text(room),
            'sink_pt': best_s,
            'tub_pt': best_tb,
            'seg_p0': chosen_p0,
            'seg_p1': chosen_p1,
            'expected_pt_host': pt_host,
        })

        pending.append((chosen_wall, pt_link, v, sym, seg_len))
        # Do not append to dedupe base within the same run (prevents false dup=all).
        prepared += 1

        if len(pending) >= batch_size:
            c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=True
            )
            created += int(c)
            created_face += int(cf)
            created_wp += int(cwp)
            created_pt += int(cpt)
            pending = []

    if pending:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=True
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)

    ids_after, elems_after, _pts_after = _collect_tagged_instances(doc, comment_value, symbol_id=int(sym.Id.IntegerValue))
    new_ids = set(ids_after or set()) - set(ids_before or set())
    try:
        elems_by_id = {int(e.Id.IntegerValue): e for e in (elems_after or [])}
    except Exception:
        elems_by_id = {}
    new_elems = [elems_by_id[i] for i in new_ids if i in elems_by_id]

    try:
        t_inv = t.Inverse if t else None
    except Exception:
        t_inv = None

    validation = []
    if plans:
        inst_items = []
        for e in (new_elems or []):
            pt = _get_instance_point(e)
            if pt is None:
                continue
            try:
                iid = int(e.Id.IntegerValue)
            except Exception:
                iid = None
            inst_items.append((iid, e, pt))

        used_inst = set()
        for pl in plans:
            best = None
            best_d = None
            for iid, e, pt in inst_items:
                if iid in used_inst:
                    continue
                d = _dist_xy(pt, pl['expected_pt_host'])
                if best_d is None or d < best_d:
                    best_d = d
                    best = (iid, e, pt)

            if best is None or best_d is None or (validate_match_tol_ft and best_d > validate_match_tol_ft):
                validation.append({
                    'status': 'missing',
                    'room_id': pl['room_id'],
                    'room_name': pl['room_name'],
                })
                continue

            iid, inst, inst_pt = best
            used_inst.add(iid)

            height_ok = (abs(float(inst_pt.Z) - float(pl['expected_pt_host'].Z)) <= float(validate_height_tol_ft or mm_to_ft(20)))
            try:
                inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
            except Exception:
                inst_pt_link = inst_pt

            on_wall_ok, between_ok, _dist_to_wall, _ts, _tb, _ti = _validate_between_sink_tub(
                pl['seg_p0'], pl['seg_p1'], pl['sink_pt'], pl['tub_pt'], inst_pt_link, validate_wall_dist_ft,
                between_pad_mm=validate_between_pad_mm
            )
            ok = bool(height_ok and on_wall_ok and between_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'room_id': pl['room_id'],
                'room_name': pl['room_name'],
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
                'between_ok': bool(between_ok),
            })

    output.print_md(
        'Тип: **{0}**\n\nПомещений обработано: **{1}**\nПодготовлено: **{2}**\nСоздано: **{3}** (Face: {4}, WorkPlane: {5}, Point: {6})\nПропущено: **{7}**'.format(
            sym_lbl or u'<ШДУП>', len(rooms), prepared, created, created_face, created_wp, created_pt, skipped
        )
    )

    if validation:
        okc = len([x for x in validation if x.get('status') == 'ok'])
        failc = len([x for x in validation if x.get('status') == 'fail'])
        missc = len([x for x in validation if x.get('status') == 'missing'])
        output.print_md('Проверка: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(okc, failc, missc))
        if failc or missc:
            output.print_md('Нарушения:')
            for x in validation:
                st = x.get('status')
                if st == 'ok':
                    continue
                rid = x.get('room_id')
                rnm = x.get('room_name')
                if st == 'missing':
                    output.print_md('- room #{0} {1}: не найден созданный экземпляр (tag={2})'.format(rid, rnm, comment_value))
                else:
                    iid = x.get('id')
                    output.print_md('- id {0} / room #{1} {2}: height={3}, on_wall={4}, between={5}'.format(
                        iid, rid, rnm, x.get('height_ok'), x.get('on_wall_ok'), x.get('between_ok')
                    ))

    if skipped:
        output.print_md('Причины пропусков (шт.): fixtures={0}, segs={1}, pair={2}, chosen={3}, geom={4}, vec={5}, dup={6}'.format(
            skip_no_fixtures, skip_no_segs, skip_no_pair, skip_no_chosen, skip_geom, skip_vec, skip_dup
        ))


try:
    main()
except Exception:
    log_exception('Error in 07_ShDUP')
