# -*- coding: utf-8 -*-
import math

from pyrevit import DB, forms, revit, script

import adapters
import config_loader
import link_reader
import placement_engine
import logic as kup 
from utils_revit import alert, log_exception, tx
from utils_units import mm_to_ft
import socket_utils as su


doc = revit.doc
output = script.get_output()
logger = script.get_logger()


TOOL_ID = 'eom_sockets_kitchen_unit'
TOOL_VERSION = '0.1'


def _collect_fridge_by_visibility_param(link_doc):
    pts = []
    fridge_keywords = [u'холодильник', u'холод', u'fridge', u'refriger']
    bics = [
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    for bic in bics:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for e in col:
            try:
                params = e.Parameters
                for p in params:
                    if p is None:
                        continue
                    pname = ''
                    try:
                        pname = (p.Definition.Name or '').lower()
                    except Exception:
                        continue
                    is_fridge_param = False
                    for kw in fridge_keywords:
                        if kw in pname:
                            is_fridge_param = True
                            break
                    if not is_fridge_param:
                        continue
                    if p.StorageType == DB.StorageType.Integer:
                        if p.AsInteger() == 1:
                            loc = e.Location
                            if isinstance(loc, DB.LocationPoint):
                                pts.append(loc.Point)
                            break
            except Exception:
                pass
    return pts


def _collect_kitchen_unit_elements_by_room(link_doc, rules):
    if link_doc is None:
        return {}

    unit_keys = rules.get('kitchen_unit_element_keywords', None) or [
        u'кухн', u'столеш', u'гарнит', u'kitchen', u'counter', u'worktop'
    ]
    bics = [
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_DetailComponents,
    ]

    elems = []
    for bic in bics:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for e in col:
            try:
                t = su._elem_text(e)
            except Exception:
                t = u''
            if not t:
                continue
            try:
                if not su._text_has_any_keyword(t, unit_keys):
                    continue
            except Exception:
                continue
            elems.append(e)

    by_room = {}
    for e in elems:
        pt = None
        try:
            pt = su._inst_center_point(e)
        except Exception:
            pt = None
        if pt is None:
            try:
                bb = e.get_BoundingBox(None)
                if bb is not None:
                    pt = DB.XYZ(
                        (float(bb.Min.X) + float(bb.Max.X)) * 0.5,
                        (float(bb.Min.Y) + float(bb.Max.Y)) * 0.5,
                        (float(bb.Min.Z) + float(bb.Max.Z)) * 0.5,
                    )
            except Exception:
                pt = None
        if pt is None:
            continue

        r = adapters._try_get_room_at_point(link_doc, pt)
        if not r:
            continue
        try:
            rid = int(r.Id.IntegerValue)
        except Exception:
            continue
        if rid not in by_room:
            by_room[rid] = []
        by_room[rid].append(e)

    return by_room


def _unit_wall_ids_for_room(unit_elems, segs, max_dist_ft):
    ids = set()
    if not unit_elems or not segs:
        return ids

    for e in unit_elems:
        try:
            bb = e.get_BoundingBox(None)
        except Exception:
            bb = None
        if bb is None:
            continue
        try:
            cpt = DB.XYZ(
                (float(bb.Min.X) + float(bb.Max.X)) * 0.5,
                (float(bb.Min.Y) + float(bb.Max.Y)) * 0.5,
                (float(bb.Min.Z) + float(bb.Max.Z)) * 0.5,
            )
        except Exception:
            continue
        try:
            seg, _proj, dist = adapters._nearest_segment(cpt, segs)
        except Exception:
            seg, dist = None, None
        if not seg or dist is None:
            continue
        try:
            if max_dist_ft is not None and float(dist) > float(max_dist_ft):
                continue
        except Exception:
            pass
        try:
            ids.add(int(seg[2].Id.IntegerValue))
        except Exception:
            pass

    return ids


def _clamp_unit_candidate_to_unit_elems(cand, unit_elems, max_wall_dist_ft, end_clear_ft):
    if not cand or not unit_elems:
        return

    seg = cand.get('seg')
    pt = cand.get('pt')
    if not seg or pt is None:
        return

    try:
        p0, p1, wall = seg
    except Exception:
        return
    if not wall:
        return

    try:
        seg_len = float(kup.domain.dist_xy(p0, p1))
    except Exception:
        seg_len = 0.0
    if seg_len <= 1e-6:
        return

    lo = 0.0
    hi = seg_len
    try:
        lo = float(end_clear_ft) if end_clear_ft is not None else 0.0
        hi = float(seg_len) - float(end_clear_ft) if end_clear_ft is not None else float(seg_len)
    except Exception:
        lo = 0.0
        hi = seg_len
    if hi <= lo + 1e-6:
        return

    intervals = []
    for e in unit_elems:
        try:
            bb = e.get_BoundingBox(None)
        except Exception:
            bb = None
        if bb is None:
            continue

        try:
            cz = (float(bb.Min.Z) + float(bb.Max.Z)) * 0.5
        except Exception:
            cz = float(pt.Z) if hasattr(pt, 'Z') else 0.0

        try:
            cpt = DB.XYZ(
                (float(bb.Min.X) + float(bb.Max.X)) * 0.5,
                (float(bb.Min.Y) + float(bb.Max.Y)) * 0.5,
                cz,
            )
        except Exception:
            continue

        try:
            proj_c = kup.domain.closest_point_on_segment_xy(cpt, p0, p1)
            if proj_c is None:
                continue
            d_to_wall = float(kup.domain.dist_xy(cpt, proj_c))
        except Exception:
            continue

        try:
            if max_wall_dist_ft is not None and d_to_wall > float(max_wall_dist_ft):
                continue
        except Exception:
            pass

        corners = []
        try:
            corners = [
                DB.XYZ(float(bb.Min.X), float(bb.Min.Y), cz),
                DB.XYZ(float(bb.Min.X), float(bb.Max.Y), cz),
                DB.XYZ(float(bb.Max.X), float(bb.Min.Y), cz),
                DB.XYZ(float(bb.Max.X), float(bb.Max.Y), cz),
            ]
        except Exception:
            corners = []

        ds = []
        for c in corners:
            try:
                pr = kup.domain.closest_point_on_segment_xy(c, p0, p1)
            except Exception:
                pr = None
            if pr is None:
                continue
            try:
                ds.append(float(kup.domain.dist_xy(p0, pr)))
            except Exception:
                continue
        if not ds:
            continue

        intervals.append((min(ds), max(ds)))

    allowed = su._merge_intervals(intervals, lo, hi)
    if not allowed:
        return

    try:
        proj_pt = kup.domain.closest_point_on_segment_xy(pt, p0, p1) or pt
        d_pt = float(kup.domain.dist_xy(p0, proj_pt))
    except Exception:
        return

    for a, b in allowed:
        try:
            if float(a) <= d_pt <= float(b):
                return
        except Exception:
            continue

    best_d = None
    best = None
    for a, b in allowed:
        try:
            a = float(a)
            b = float(b)
        except Exception:
            continue
        if d_pt < a:
            cand_d = a
            dd = a - d_pt
        elif d_pt > b:
            cand_d = b
            dd = d_pt - b
        else:
            cand_d = d_pt
            dd = 0.0
        if best_d is None or dd < best_d:
            best_d = dd
            best = cand_d

    if best is None:
        return

    try:
        tt = float(best) / float(seg_len)
    except Exception:
        tt = 0.0
    tt = max(0.0, min(1.0, tt))

    try:
        cand['pt'] = DB.XYZ(
            float(p0.X) + (float(p1.X) - float(p0.X)) * tt,
            float(p0.Y) + (float(p1.Y) - float(p0.Y)) * tt,
            float(pt.Z),
        )
    except Exception:
        pass


def run(doc, output):
    output.print_md('# 02. Кухня: Гарнитур + Холодильник + Периметр (Всего 4)')

    rules = config_loader.load_rules()
    cfg = script.get_config()

    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value_unit = '{0}:SOCKET_KITCHEN_UNIT'.format(comment_tag)
    comment_value_fridge = '{0}:SOCKET_FRIDGE'.format(comment_tag)
    comment_value_general = '{0}:SOCKET_KITCHEN_GENERAL'.format(comment_tag)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or [u'кухня', u'kitchen']
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    # Max 4 sockets total as per new requirement
    total_target = 4

    height_mm = int(rules.get('kitchen_unit_height_mm', 1100) or 1100)
    height_ft = mm_to_ft(height_mm)
    
    fridge_height_mm = int(rules.get('kitchen_fridge_height_mm', 300) or 300)
    fridge_height_ft = mm_to_ft(fridge_height_mm)
    
    general_height_mm = int(rules.get('kitchen_general_height_mm', 300) or 300)
    general_height_ft = mm_to_ft(general_height_mm)

    fridge_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fridge_max_dist_mm', 1500) or 1500))

    clear_sink_mm = int(rules.get('kitchen_sink_clear_mm', 600) or 600)
    clear_stove_mm = int(rules.get('kitchen_stove_clear_mm', 600) or 600)
    clear_sink_ft = mm_to_ft(clear_sink_mm)
    clear_stove_ft = mm_to_ft(clear_stove_mm)

    offset_sink_mm = int(rules.get('kitchen_sink_offset_mm', 600) or 600)
    offset_stove_mm = int(rules.get('kitchen_stove_offset_mm', 600) or 600)
    offset_sink_ft = mm_to_ft(offset_sink_mm)
    offset_stove_ft = mm_to_ft(offset_stove_mm)

    wall_end_clear_mm = int(rules.get('kitchen_wall_end_clear_mm', 100) or 100)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    fixture_wall_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fixture_wall_max_dist_mm', 2000) or 2000))

    unit_wall_max_dist_ft = mm_to_ft(int(rules.get('kitchen_unit_wall_max_dist_mm', 800) or 800))

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', 300) or 300)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', 25) or 25)

    existing_dedupe_mm = int(rules.get('kitchen_existing_dedupe_mm', 200) or 200)

    fams = rules.get('family_type_names', {})
    prefer_unit = fams.get('socket_kitchen_unit') or (
        u'TSL_EF_Р_ОП_С_IP20_Встр_1P+N+PE_2м : TSL_EF_Р_ОП_С_IP20_Встр_1P+N+PE_2м'
    )
    if isinstance(prefer_unit, (list, tuple)):
        prefer_unit = sorted(prefer_unit, key=lambda x: (0 if u'_2м' in (x or u'') else 1))

    # Helper to pick symbols
    def _pick_sym(prefer_list, desc):
        sym, lbl, _ = su._pick_socket_symbol(doc, cfg, prefer_list, cache_prefix='socket_kitchen_' + desc)
        if not sym:
            def _try_pick_any(names):
                if not names: return None
                if not isinstance(names, (list, tuple)): names = [names]
                for n in names:
                    if not n: continue
                    try: 
                        s = su._find_symbol_by_fullname(doc, n)
                        if s: return s
                    except: continue
                return None
            sym = _try_pick_any(prefer_list)
        return sym, lbl

    sym_unit, sym_unit_lbl = _pick_sym(prefer_unit, 'unit')
    if not sym_unit:
        alert('Не найден тип розетки для кухни (гарнитур).')
        return

    prefer_fridge = fams.get('socket_kitchen_fridge') or (u'TSL_EF_Р_ОП_С_IP20_Встр_1P+N+PE')
    sym_fridge, sym_fridge_lbl = _pick_sym(prefer_fridge, 'fridge')
    if not sym_fridge: sym_fridge = sym_unit

    prefer_general = fams.get('socket_kitchen_general') or prefer_fridge
    sym_general, sym_general_lbl = _pick_sym(prefer_general, 'general')
    if not sym_general: sym_general = sym_fridge

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst: return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc: return

    level_ids = None 

    t = link_reader.get_total_transform(link_inst)
    raw_rooms = su._get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200), level_ids=level_ids)

    # --- sinks/stoves detection ---
    sinks_all = adapters.collect_sinks_points(link_doc, rules)
    stoves_all = adapters.collect_stoves_points(link_doc, rules)
    fridges_all = adapters.collect_fridges_points(link_doc, rules)
    fridges_all.extend(_collect_fridge_by_visibility_param(link_doc))

    unit_elems_by_room = _collect_kitchen_unit_elements_by_room(link_doc, rules)

    output.print_md('Мойки: **{0}**; Плиты: **{1}**; Холодильники: **{2}**'.format(
        len(sinks_all or []), len(stoves_all or []), len(fridges_all or [])))

    # Rooms selection
    rooms_by_id = {}
    for r in (raw_rooms or []):
        try:
            if kitchen_rx and (not su._match_any(kitchen_rx, su._room_text(r))):
                continue
        except: continue
        try: rooms_by_id[int(r.Id.IntegerValue)] = r
        except: continue

    for pt in (stoves_all or []):
        r = adapters._try_get_room_at_point(link_doc, pt)
        if r: rooms_by_id[int(r.Id.IntegerValue)] = r

    rooms = [rooms_by_id[k] for k in sorted(rooms_by_id.keys())]
    if not rooms:
        alert('Нет помещений кухни.')
        return

    host_sockets = adapters.collect_host_socket_instances(doc)

    sym_flags = {}
    for s in (sym_unit, sym_fridge, sym_general):
        try:
            pt_enum = s.Family.FamilyPlacementType
            sym_flags[int(s.Id.IntegerValue)] = (
                pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
                pt_enum == DB.FamilyPlacementType.OneLevelBased,
            )
        except:
            sym_flags[int(s.Id.IntegerValue)] = (False, False)

    sp_cache = {}
    pending_unit = []
    pending_fridge = []
    pending_general = []
    
    created = created_face = created_wp = created_pt = 0
    skipped = 0

    with forms.ProgressBar(title='02. Кухня Блок + Периметр (4шт)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled: break
            pb.update_progress(i, pb.max_value)

            segs = adapters._get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                continue

            sinks = adapters._points_in_room(sinks_all, room)
            stoves = adapters._points_in_room(stoves_all, room)
            fridges = adapters._points_in_room(fridges_all, room)
            
            # Strict filtering:
            # 1. If named "Kitchen", allow Sink OR Stove.
            # 2. If NOT named "Kitchen" (e.g. found via stove detection), require BOTH Sink AND Stove to avoid false positives.
            is_named_kitchen = False
            try:
                if kitchen_rx and su._match_any(kitchen_rx, su._room_text(room)):
                    is_named_kitchen = True
            except: pass

            if is_named_kitchen:
                if not sinks and not stoves:
                    skipped += 1
                    continue
            else:
                if not (sinks and stoves):
                    skipped += 1
                    continue

            def _pick_best_fixture_pt(pts, max_dist_ft=None):
                best = None
                best_d = None
                best_any = None
                best_any_d = None
                for p in (pts or []):
                    try:
                        _seg, _proj, _d = adapters._nearest_segment(p, segs)
                    except Exception:
                        _seg, _proj, _d = None, None, None
                    if _d is None:
                        continue
                    try:
                        dd = float(_d)
                    except Exception:
                        continue

                    if best_any_d is None or dd < best_any_d:
                        best_any = p
                        best_any_d = dd

                    try:
                        if max_dist_ft is not None and dd > float(max_dist_ft):
                            continue
                    except Exception:
                        pass

                    if best_d is None or dd < best_d:
                        best = p
                        best_d = dd

                return best or best_any

            best_sink = _pick_best_fixture_pt(sinks, max_dist_ft=fixture_wall_max_dist_ft)
            best_stove = _pick_best_fixture_pt(stoves, max_dist_ft=fixture_wall_max_dist_ft)
            best_fridge = _pick_best_fixture_pt(fridges, max_dist_ft=fixture_wall_max_dist_ft)

            base_z = su._room_level_elevation_ft(room, link_doc)

            unit_elems = []
            try:
                unit_elems = unit_elems_by_room.get(int(room.Id.IntegerValue), [])
            except Exception:
                unit_elems = []
            unit_wall_ids = _unit_wall_ids_for_room(unit_elems, segs, unit_wall_max_dist_ft) if unit_elems else set()

            segs_unit = segs
            if unit_wall_ids:
                try:
                    segs_unit = [s for s in segs if int(s[2].Id.IntegerValue) in unit_wall_ids]
                except Exception:
                    segs_unit = segs
                if not segs_unit:
                    segs_unit = segs

            # 1. Unit Sockets (Ideally 1 "between" socket)
            candidates, _, _, _, _ = kup.get_candidates(
                segs_unit, best_sink, best_stove, offset_sink_ft, offset_stove_ft,
                fixture_wall_max_dist_ft, wall_end_clear_ft
            )
            if (not candidates) and (segs_unit is not segs):
                candidates, _, _, _, _ = kup.get_candidates(
                    segs, best_sink, best_stove, offset_sink_ft, offset_stove_ft,
                    fixture_wall_max_dist_ft, wall_end_clear_ft
                )
            # Prioritize 'between' (0) and cap at 1
            candidates.sort(key=lambda x: x.get('priority', 9))
            # If we have 'between', keep only that one. If only offsets, keep 1 or 2? 
            # Requirement: "double between sink etc". So 1 point.
            if candidates:
                # If we have a priority 0 candidate (between), select it and discard others
                if candidates[0]['priority'] == 0:
                    candidates = [candidates[0]]
                else:
                    # If we only have offsets (sink/stove), maybe limit to 1?
                    # "Only 2 sockets on headset... at fridge and double between"
                    # If we can't do "between", maybe we shouldn't place anything or just 1 offset?
                    # Let's keep best offset.
                    candidates = [candidates[0]]

            if candidates and unit_elems:
                _clamp_unit_candidate_to_unit_elems(candidates[0], unit_elems, unit_wall_max_dist_ft, wall_end_clear_ft)

            # 2. Fridge Socket
            fridge_placed = False
            if best_fridge:
                seg_fr, proj_fr, dist_fr = adapters._nearest_segment(best_fridge, segs)
                if proj_fr and dist_fr < mm_to_ft(1000):
                    candidates.append({
                        'priority': 2,
                        'seg': seg_fr,
                        'pt': proj_fr,
                        'kind': u'fridge'
                    })
                    fridge_placed = True

            # 3. Perimeter Sockets (Remaining count to reach 4)
            # We have 1 Unit (Apron) + 1 Fridge (if exists). 
            # Total used = len(candidates) so far.
            used_count = len(candidates)
            needed_perimeter = max(0, total_target - used_count)
            
            # Enforce exactly 2 perimeter if we have standard set (1 apron + 1 fridge)
            # Or fill up to 4.
            # User said "add 2 more... total 4".
            
            if needed_perimeter > 0:
                perim_cands = kup.get_perimeter_candidates(
                    link_doc, segs, best_sink, best_stove, best_fridge, 
                    count=needed_perimeter, min_spacing_ft=mm_to_ft(3000)
                )
                for pc in perim_cands:
                    pc['kind'] = 'general'
                    candidates.append(pc)

            for cand in candidates:
                pt_xy = cand.get('pt')
                
                wall = cand.get('wall')
                if not wall and cand.get('seg'):
                    wall = cand['seg'][2]
                
                kind = cand.get('kind')
                
                if not wall or not pt_xy: continue

                h_ft = height_ft
                comm = comment_value_unit
                sym = sym_unit
                
                if kind == u'fridge':
                    h_ft = fridge_height_ft
                    comm = comment_value_fridge
                    sym = sym_fridge
                elif kind == 'general':
                    h_ft = general_height_ft
                    comm = comment_value_general
                    sym = sym_general

                # Vector logic
                v = cand.get('dir')
                if not v and cand.get('seg'):
                    p0, p1, _ = cand['seg']
                    v = DB.XYZ(p1.X - p0.X, p1.Y - p0.Y, 0).Normalize()
                if not v: v = DB.XYZ(1,0,0)

                pt_link = DB.XYZ(float(pt_xy.X), float(pt_xy.Y), float(base_z) + float(h_ft))
                
                if kind == 'fridge':
                    pending_fridge.append((wall, pt_link, v, sym, 0.0))
                elif kind == 'general':
                    pending_general.append((wall, pt_link, v, sym, 0.0))
                else:
                    pending_unit.append((wall, pt_link, v, sym, 0.0))

                if len(pending_unit) >= batch_size:
                    c, cf, cwp, cpt, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_unit, sym_flags, sp_cache, comment_value_unit)
                    created += c; pending_unit = []
                if len(pending_fridge) >= batch_size:
                    c, cf, cwp, cpt, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_fridge, sym_flags, sp_cache, comment_value_fridge)
                    created += c; pending_fridge = []
                if len(pending_general) >= batch_size:
                    c, cf, cwp, cpt, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_general, sym_flags, sp_cache, comment_value_general)
                    created += c; pending_general = []

    if pending_unit:
        c, _, _, _, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_unit, sym_flags, sp_cache, comment_value_unit)
        created += c
    if pending_fridge:
        c, _, _, _, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_fridge, sym_flags, sp_cache, comment_value_fridge)
        created += c
    if pending_general:
        c, _, _, _, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending_general, sym_flags, sp_cache, comment_value_general)
        created += c

    output.print_md('Создано розеток: **{0}**'.format(created))
    return created
