# -*- coding: utf-8 -*-

from pyrevit import DB
import adapters
import constants
import domain
try:
    import socket_utils as su
except ImportError:
    import sys, os
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su
from utils_units import mm_to_ft


def run(doc, output):
    output.print_md('# 07. ШДУП: Ванные')

    rules = adapters.get_rules()
    cfg = adapters.get_config()

    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value = '{0}{1}'.format(comment_tag, constants.COMMENT_SUFFIX)

    height_ft = mm_to_ft(constants.DEFAULT_SHDUP_HEIGHT_MM)
    dedupe_ft = mm_to_ft(int(rules.get('dedupe_radius_mm', constants.DEFAULT_DEDUPE_MM) or constants.DEFAULT_DEDUPE_MM))
    if dedupe_ft < 0:
        dedupe_ft = 0.0
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    validate_match_tol_ft = mm_to_ft(int(rules.get('shdup_validate_match_tol_mm', constants.DEFAULT_VALIDATE_MATCH_TOL_MM) or constants.DEFAULT_VALIDATE_MATCH_TOL_MM))
    validate_height_tol_ft = mm_to_ft(int(rules.get('shdup_validate_height_tol_mm', constants.DEFAULT_VALIDATE_HEIGHT_TOL_MM) or constants.DEFAULT_VALIDATE_HEIGHT_TOL_MM))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('shdup_validate_wall_dist_mm', constants.DEFAULT_VALIDATE_WALL_DIST_MM) or constants.DEFAULT_VALIDATE_WALL_DIST_MM))
    validate_between_pad_mm = int(rules.get('shdup_validate_between_pad_mm', constants.DEFAULT_VALIDATE_BETWEEN_PAD_MM) or constants.DEFAULT_VALIDATE_BETWEEN_PAD_MM)

    sym, sym_lbl = adapters.pick_shdup_symbol(doc, cfg, rules)
    if not sym:
        output.print_md('**Ошибка:** Не найден тип ШДУП. Загрузите семейство/тип в проект и повторите.')
        return 0

    try:
        su._store_symbol_id(cfg, 'last_shdup_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_shdup_symbol_uid', sym)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, 'Выберите связь АР')
    if not link_inst:
        return 0
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc:
        return 0

    t = adapters.get_total_transform(link_inst)

    import link_reader
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни')
    if not selected_levels:
        return 0
    level_ids = [lvl.Id for lvl in selected_levels if getattr(lvl, 'Id', None) is not None]
    if not level_ids:
        return 0

    raw_rooms = adapters.get_all_linked_rooms(
        link_doc,
        limit=int(rules.get('scan_limit_rooms', 200) or 200),
        level_ids=level_ids
    )
    bath_rx = su._compile_patterns(rules.get('bath_room_name_patterns', []) or rules.get('wet_room_name_patterns', []) or constants.DEFAULT_BATH_PATTERNS)

    rooms = []
    for r in raw_rooms:
        try:
            if bath_rx and (not su._match_any(bath_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        rooms.append(r)

    global LAST_ROOM_COUNT
    try:
        LAST_ROOM_COUNT = len(rooms)
    except Exception:
        LAST_ROOM_COUNT = None

    if not rooms:
        output.print_md('Связь пропущена: нет подходящих помещений ванной (по паттернам).')
        return 0

    output.print_md('Найдено помещений ванных: **{0}** (из {1} всего отсканировано)'.format(
        len(rooms), len(raw_rooms)
    ))

    sinks_all = su._collect_sinks_points(link_doc, rules)
    used_sink_fallback = False
    if not sinks_all:
        sinks_all = adapters.collect_sink_points(link_doc, rules)
        used_sink_fallback = True

    tub_data = su._collect_bathtubs_data(link_doc)
    # tub_data is now [(center, min, max, faucet_pt), ...]
    # Map center points to full data for lookup later
    tubs_all = []
    tubs_map = {}
    if tub_data:
        for item in tub_data:
            c_pt = item[0]
            tubs_all.append(c_pt)
            tubs_map[c_pt] = item
    used_tub_fallback = False
    if not tubs_all:
        tubs_all = adapters.collect_tub_points(link_doc, rules)
        used_tub_fallback = True

    # Собираем унитазы для определения правильного угла ванны
    toilets_all = adapters.collect_toilet_points(link_doc, rules)

    output.print_md('Раковины: **{0}**{1}; Ванны: **{2}**{3}; Унитазы: **{4}**'.format(
        len(sinks_all), ' (fallback)' if used_sink_fallback else '',
        len(tubs_all), ' (fallback)' if used_tub_fallback else '',
        len(toilets_all)
    ))

    if not sinks_all and not tubs_all:
        output.print_md('Связь пропущена: не найдено ни раковин, ни ванн в связи (AR).')
        return 0

    try:
        ids_before, _elems_before, existing_pts = adapters.collect_tagged_instances(doc, comment_value, symbol_id=int(sym.Id.IntegerValue))
    except Exception:
        ids_before = set()
        existing_pts = []

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

        sinks = domain.points_in_room(sinks_all, room)
        tubs = domain.points_in_room(tubs_all, room)
        toilets = domain.points_in_room(toilets_all, room)

        if not sinks and not tubs:
            skipped += 1
            skip_no_fixtures += 1
            continue

        best_s = None
        best_tb = None

        if sinks and tubs:
            best_d = None
            for s in sinks:
                for tb in tubs:
                    d = domain.dist_xy(s, tb)
                    if best_d is None or d < best_d:
                        best_s = s
                        best_tb = tb
                        best_d = d
        elif sinks:
            best_s = sinks[0]
            best_tb = None
        elif tubs:
            best_s = None
            best_tb = tubs[0]

        if best_s is None and best_tb is None:
            skipped += 1
            skip_no_pair += 1
            continue

        # Собираем все сантехприборы в комнате (кроме ванн) для поиска ближайшего
        fixtures_in_room = []
        if sinks:
            fixtures_in_room.extend(sinks)
        if toilets:
            fixtures_in_room.extend(toilets)

        # Найти УГОЛ ванной, ближайший к БЛИЖАЙШЕМУ сантехприбору (раковина или унитаз)
        target_tub_pt = best_tb
        tub_corner_pts = []
        if best_tb and (best_tb in tubs_map):
            tub_item = tubs_map[best_tb]
            # item format: (center, min, max, faucet_pt)
            if len(tub_item) >= 3:
                tub_min = tub_item[1]  # min point of bbox
                tub_max = tub_item[2]  # max point of bbox
                if tub_min and tub_max:
                    # 4 угла ванной
                    tub_corner_pts = [
                        DB.XYZ(float(tub_min.X), float(tub_min.Y), float(tub_min.Z)),
                        DB.XYZ(float(tub_max.X), float(tub_min.Y), float(tub_min.Z)),
                        DB.XYZ(float(tub_min.X), float(tub_max.Y), float(tub_min.Z)),
                        DB.XYZ(float(tub_max.X), float(tub_max.Y), float(tub_min.Z)),
                    ]

        segs = domain.get_wall_segments(room, link_doc)
        if not segs:
            skipped += 1
            skip_no_segs += 1
            continue

        # Найти угол ванной, ближайший к БЛИЖАЙШЕМУ сантехприбору
        best_corner = None
        best_corner_dist = None
        
        if tub_corner_pts and fixtures_in_room:
            for corner in tub_corner_pts:
                for fixture in fixtures_in_room:
                    dist = domain.dist_xy(corner, fixture)
                    if best_corner_dist is None or dist < best_corner_dist:
                        best_corner = corner
                        best_corner_dist = dist
        
        # Используем ближайший угол к сантехприбору
        if best_corner:
            target_tub_pt = best_corner
        
        seg_b, proj_b, _ = domain.nearest_segment(target_tub_pt, segs) if best_tb else (None, None, None)
        seg_s, proj_s, _ = domain.nearest_segment(best_s, segs) if best_s else (None, None, None)

        chosen = None
        chosen_p0 = chosen_p1 = chosen_wall = None
        pfinal = None

        # Алгоритм размещения ШДУП:
        # ШДУП размещается В УГЛУ ВАННОЙ, ближайшем к сантехприбору (раковина/унитаз)
        # Проецируем этот угол на ближайшую стену
        
        if best_tb and seg_b:
            # Стена ванны
            chosen = seg_b
            chosen_p0, chosen_p1, chosen_wall = chosen
            
            # Проекция угла ванны на стену - это точка размещения ШДУП
            pfinal = domain.closest_point_on_segment_xy(target_tub_pt, chosen_p0, chosen_p1)
        
        elif best_s and seg_s:
            # Fallback: только раковина (нет ванны)
            chosen = seg_s
            chosen_p0, chosen_p1, chosen_wall = chosen
            pfinal = domain.closest_point_on_segment_xy(best_s, chosen_p0, chosen_p1)

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

    # Убираем фильтр по symbol_id для валидации, чтобы гарантированно найти созданные элементы
    # (иногда ID типа может не совпадать или быть неважным для проверки факта создания)
    ids_after, elems_after, _pts_after = adapters.collect_tagged_instances(doc, comment_value, symbol_id=None)
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
            pt = su._inst_center_point(e)
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
                d = domain.dist_xy(pt, pl['expected_pt_host'])
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

            on_wall_ok, between_ok, _dist_to_wall, _ts, _tb, _ti = domain.validate_between_sink_tub(
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

    return created
