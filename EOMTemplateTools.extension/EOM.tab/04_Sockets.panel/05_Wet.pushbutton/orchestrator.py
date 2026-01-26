# -*- coding: utf-8 -*-

import time
from pyrevit import DB, forms, script
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
from utils_revit import alert, log_exception, tx
from utils_units import mm_to_ft, ft_to_mm


def run(doc, output):
    output.print_md('# 05. Санузлы/Ванные/Постирочные')

    rules = adapters.get_rules()
    cfg = adapters.get_config()

    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value = '{0}{1}'.format(comment_tag, constants.COMMENT_SUFFIX)

    wet_patterns = rules.get('wet_room_name_patterns', None) or constants.DEFAULT_WET_PATTERNS
    wet_rx = su._compile_patterns(wet_patterns)

    total_target = int(rules.get('wet_total_sockets', constants.TOTAL_TARGET) or constants.TOTAL_TARGET)

    height_mm = int(rules.get('wet_general_height_mm', constants.DEFAULT_HEIGHT_MM) or constants.DEFAULT_HEIGHT_MM)
    height_ft = mm_to_ft(height_mm)

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', constants.SOCKET_DEDUPE_RADIUS_MM) or constants.SOCKET_DEDUPE_RADIUS_MM)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    validate_match_tol_ft = mm_to_ft(int(rules.get('wet_validate_match_tol_mm', constants.VALIDATE_MATCH_TOL_MM) or constants.VALIDATE_MATCH_TOL_MM))
    validate_height_tol_ft = mm_to_ft(int(rules.get('wet_validate_height_tol_mm', constants.VALIDATE_HEIGHT_TOL_MM) or constants.VALIDATE_HEIGHT_TOL_MM))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('wet_validate_wall_dist_mm', constants.VALIDATE_WALL_DIST_MM) or constants.VALIDATE_WALL_DIST_MM))
    debug_no_candidates_limit = int(rules.get('wet_debug_no_candidates_limit', constants.DEBUG_NO_CANDIDATES_LIMIT) or constants.DEBUG_NO_CANDIDATES_LIMIT)
    debug_skipped_rooms_limit = int(rules.get('wet_debug_skipped_rooms_limit', constants.DEBUG_SKIPPED_ROOMS_LIMIT) or constants.DEBUG_SKIPPED_ROOMS_LIMIT)
    existing_dedupe_mm = int(rules.get('wet_existing_dedupe_mm', constants.EXISTING_DEDUPE_MM) or constants.EXISTING_DEDUPE_MM)

    fams = rules.get('family_type_names', {})
    prefer = (
        fams.get('socket_wet')
        or fams.get('socket_wet_general')
        or fams.get('socket_ac')
        or fams.get('socket_general')
        or fams.get('power_socket')
    )
    sym, sym_lbl, top10 = adapters.pick_socket_symbol(doc, cfg, prefer)
    if not sym:
        def _try_pick_any(names):
            if not names: return None
            if not isinstance(names, (list, tuple)):
                names = [names]
            for n in names:
                if not n: continue
                try: sym0 = adapters.find_symbol_by_fullname(doc, n)
                except Exception: sym0 = None
                if sym0: return sym0
            return None

        sym = _try_pick_any(prefer)
        if sym:
            try: sym_lbl = adapters.format_family_type(sym)
            except Exception: sym_lbl = None
            output.print_md(u'**Внимание:** выбранный тип розетки не поддерживает размещение по грани/стене. Будет использован OneLevel/WorkPlane режим, если доступно.')
        else:
            alert('Не найден тип розетки для санузлов.')
            if top10:
                output.print_md('Доступные варианты:')
                for x in top10:
                    output.print_md('- {0}'.format(x))
            return

    try:
        su._store_symbol_id(cfg, 'last_socket_wet_general_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_socket_wet_general_symbol_uid', sym)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, u'Выберите связь АР')
    if not link_inst:
        return
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc:
        return
    t = adapters.get_total_transform(link_inst)
    t_inv = t.Inverse if t else None

    raw_rooms = adapters.get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200))
    rooms = []
    for r in (raw_rooms or []):
        try:
            if wet_rx and (not su._match_any(wet_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        rooms.append(r)

    if not rooms:
        alert('Нет помещений санузлов (по паттернам).')
        return

    # Collect fixtures
    bics_fixtures = []
    for cname in constants.FIXTURE_CATEGORIES:
        try:
            bic = getattr(DB.BuiltInCategory, cname)
            bics_fixtures.append(bic)
        except Exception:
            pass

    fixtures_all = []
    wm_kws = rules.get('washing_machine_keywords') or [u'стирал', u'washing', u'machine']
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, wm_kws, bics_fixtures, fixture_kind='wm'))
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, [u'раковин', u'мойк', u'sink', u'умывал'], bics_fixtures, fixture_kind='sink'))
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, [u'сушител', u'towel', u'полотен'], bics_fixtures, fixture_kind='rail'))
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, [u'бойлер', u'boiler', u'нагреват'], bics_fixtures, fixture_kind='boiler'))
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, [u'ванн', u'bath', u'душ', u'shower', u'поддон', u'кабин', u'джакуз'], bics_fixtures, fixture_kind='bath'))
    fixtures_all.extend(adapters.collect_fixture_candidates(link_doc, [u'унитаз', u'toilet', u'wc', u'биде'], bics_fixtures, fixture_kind='toilet'))

    door_pts = adapters.collect_door_points(link_doc)

    host_sockets = adapters.collect_host_socket_instances(doc)

    try:
        ids_before, _elems_before, _pts_before = domain.collect_tagged_instances(doc, comment_value)
    except Exception:
        ids_before = set()

    sym_flags = {}
    try:
        pt_enum = sym.Family.FamilyPlacementType
        sym_flags[int(sym.Id.IntegerValue)] = (
            pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
            pt_enum == DB.FamilyPlacementType.OneLevelBased,
        )
    except Exception:
        sym_flags[int(sym.Id.IntegerValue)] = (False, False)

    sp_cache = {}
    pending = []
    plans = []

    created = created_face = created_wp = created_pt = 0
    skipped = 0
    prepared = 0
    skipped_details = []
    
    debug_skipped_rooms_limit = int(rules.get('wet_debug_skipped_rooms_limit', constants.DEBUG_SKIPPED_ROOMS_LIMIT) or constants.DEBUG_SKIPPED_ROOMS_LIMIT)
    skipped_details_more = [0]

    def _push_skip(room, reason, details=None):
        try: lim = int(debug_skipped_rooms_limit or 0)
        except: lim = 0
        if lim <= 0: return
        if len(skipped_details) >= lim:
            skipped_details_more[0] += 1
            return
        try: rid = int(room.Id.IntegerValue)
        except: rid = None
        try: rnm = su._room_text(room)
        except: rnm = u''
        skipped_details.append({'room_id': rid, 'room_name': rnm, 'reason': reason, 'details': details or u''})

    with forms.ProgressBar(title='05. Санузлы...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            segs = domain.get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                _push_skip(room, 'segs', u'нет сегментов стен')
                continue

            base_z = su._room_level_elevation_ft(room, link_doc)
            
            # Existing check
            existing_link_pts = []
            existing_cnt = 0
            existing_idx = su._XYZIndex(cell_ft=1.0)
            existing_dedupe_ft = mm_to_ft(existing_dedupe_mm)
            
            if host_sockets and t_inv:
                for inst, pt_host in host_sockets:
                    try: pt_link = t_inv.OfPoint(pt_host)
                    except: continue
                    if not pt_link: continue
                    if domain.points_in_room([pt_link], room):
                        existing_link_pts.append(pt_link)
                        if not existing_idx.has_near(float(pt_link.X), float(pt_link.Y), float(pt_link.Z), float(existing_dedupe_ft)):
                            existing_cnt += 1
                            existing_idx.add(float(pt_link.X), float(pt_link.Y), float(pt_link.Z))

            if existing_cnt >= total_target:
                skipped += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток'.format(int(existing_cnt), int(total_target)))
                continue
            
            need = max(0, int(total_target) - int(existing_cnt))
            if need <= 0:
                skipped += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток'.format(int(existing_cnt), int(total_target)))
                continue

            fixtures_in_room = domain.fixtures_in_room(fixtures_all, room)
            candidates = domain.generate_candidates(room, segs, fixtures_in_room, door_pts, rules)
            
            if not candidates:
                skipped += 1
                _push_skip(room, 'candidates', u'нет подходящих точек')
                continue
                
            candidates.sort(key=lambda x: x.get('priority', 9))
            
            idx = su._XYZIndex(cell_ft=5.0)
            for ep in existing_link_pts:
                try: idx.add(float(ep.X), float(ep.Y), 0.0)
                except: continue

            picked = 0
            for cand in candidates:
                if picked >= need: break
                pt_xy = cand.get('pt')
                seg = cand.get('seg')
                kind = cand.get('kind')
                if pt_xy is None or seg is None: continue
                
                if idx.has_near(float(pt_xy.X), float(pt_xy.Y), 0.0, float(dedupe_ft or mm_to_ft(300))):
                    continue
                
                p0, p1, wall = seg
                proj = domain.closest_point_on_segment_xy(pt_xy, p0, p1)
                if proj is None: continue
                
                v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
                if v.GetLength() <= 1e-9: continue
                v = v.Normalize()
                seg_len = p0.DistanceTo(p1)

                idx.add(float(pt_xy.X), float(pt_xy.Y), 0.0)
                
                pt_link = DB.XYZ(float(proj.X), float(proj.Y), float(base_z) + float(height_ft))
                pt_host = t.OfPoint(pt_link) if t else pt_link

                pending.append((wall, pt_link, v, sym, seg_len))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'expected_pt_host': pt_host,
                    'kind': kind,
                    'seg_p0': p0,
                    'seg_p1': p1,
                })
                prepared += 1
                picked += 1

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

    ids_after, elems_after, _pts_after = domain.collect_tagged_instances(doc, comment_value)
    new_ids = set(ids_after or set()) - set(ids_before or set())
    try: elems_by_id = {int(e.Id.IntegerValue): e for e in (elems_after or [])}
    except: elems_by_id = {}
    new_elems = [elems_by_id[i] for i in sorted(new_ids) if i in elems_by_id]

    validation = []
    if plans:
        inst_items = []
        for e in (new_elems or []):
            pt = su._inst_center_point(e)
            if pt is None: continue
            try: iid = int(e.Id.IntegerValue)
            except: iid = None
            abs_z = None
            try: abs_z = su._get_abs_z_from_level_offset(e, doc)
            except: abs_z = None
            z_key = abs_z if abs_z is not None else float(pt.Z)
            inst_items.append((iid, e, pt, float(z_key)))

        used_inst = set()
        for pl in plans:
            exp_pt = pl.get('expected_pt_host')
            if exp_pt is None: continue
            try: exp_z = float(exp_pt.Z)
            except: exp_z = None

            best = None
            best_key = None
            best_dxy = None

            for iid, e, pt, z_key in inst_items:
                if iid in used_inst: continue
                dxy = domain.dist_xy(pt, exp_pt)
                if validate_match_tol_ft and dxy > validate_match_tol_ft: continue
                dz = abs(float(z_key) - float(exp_z)) if exp_z is not None else 0.0
                key = (float(dz), float(dxy))
                if best_key is None or key < best_key:
                    best_key = key
                    best_dxy = dxy
                    best = (iid, e, pt)

            if best is None or best_dxy is None:
                validation.append({
                    'status': 'missing',
                    'room_id': pl['room_id'],
                    'room_name': pl['room_name'],
                })
                continue

            iid, inst, inst_pt = best
            used_inst.add(iid)

            try: exp_z = float(pl['expected_pt_host'].Z)
            except: exp_z = float(inst_pt.Z)

            abs_z = None
            try: abs_z = su._get_abs_z_from_level_offset(inst, doc)
            except: abs_z = None
            z_to_check = abs_z if abs_z is not None else float(inst_pt.Z)
            height_ok = abs(float(z_to_check) - float(exp_z)) <= float(validate_height_tol_ft or mm_to_ft(20))

            try: inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
            except: inst_pt_link = inst_pt

            p0 = pl.get('seg_p0')
            p1 = pl.get('seg_p1')
            
            proj = domain.closest_point_on_segment_xy(inst_pt_link, p0, p1) if p0 and p1 else None
            dist_wall = domain.dist_xy(inst_pt_link, proj) if proj else None
            on_wall_ok = (dist_wall is not None) and (dist_wall <= float(validate_wall_dist_ft or mm_to_ft(150)))

            ok = bool(height_ok and on_wall_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'room_id': pl['room_id'],
                'room_name': pl['room_name'],
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
            })

    output.print_md(
        'Тип: **{0}**\n\nПодготовлено: **{1}**\nСоздано: **{2}** (Face: {3}, WorkPlane: {4}, Point: {5})\nПропущено: **{6}**'.format(
            sym_lbl or u'<Розетка>', prepared, created, created_face, created_wp, created_pt, skipped
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
                if st == 'ok': continue
                rid = x.get('room_id')
                rnm = x.get('room_name')
                if st == 'missing':
                    output.print_md('- room #{0} {1}: не найден созданный экземпляр (tag={2})'.format(rid, rnm, comment_value))
                else:
                    output.print_md('- id {0} / room #{1} {2}: height={3}, on_wall={4}'.format(
                        x.get('id'), rid, rnm,
                        x.get('height_ok'), x.get('on_wall_ok')
                    ))

    if skipped:
        output.print_md('Пропущенные (всего): {}'.format(skipped))

    if skipped_details:
        output.print_md('Пропущенные помещения (первые {0}):'.format(len(skipped_details)))
        for x in skipped_details:
            output.print_md('- room #{0} **{1}**: {2}{3}'.format(
                x.get('room_id'), x.get('room_name') or u'',
                x.get('reason') or u'',
                (u' — ' + x.get('details')) if x.get('details') else u''
            ))
        if skipped_details_more[0]:
            output.print_md('- …и еще пропущено: **{0}** (увеличьте wet_debug_skipped_rooms_limit)'.format(int(skipped_details_more[0])))
