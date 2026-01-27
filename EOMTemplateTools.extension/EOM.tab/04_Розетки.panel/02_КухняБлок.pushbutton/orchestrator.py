# -*- coding: utf-8 -*-

import math
from pyrevit import DB, forms, script
import adapters
import constants
import domain
import logic
import validator
try:
    import socket_utils as su
except ImportError:
    import sys, os
    # Orchestrator is in .../02_Kitchen_Unit.pushbutton, so needs 4 levels up to reach extension root where 'lib' is located
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su
from utils_revit import alert, log_exception, tx
from utils_units import mm_to_ft


def run(doc, output):
    output.print_md('# 02. �����: �������� (1100��)')

    rules = adapters.get_rules()
    cfg = adapters.get_config()

    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value = '{0}{1}'.format(comment_tag, constants.COMMENT_SUFFIX)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or constants.DEFAULT_KITCHEN_PATTERNS
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    total_target = int(rules.get('kitchen_total_sockets', constants.TOTAL_TARGET) or constants.TOTAL_TARGET)

    height_mm = int(rules.get('kitchen_unit_height_mm', constants.DEFAULT_HEIGHT_MM) or constants.DEFAULT_HEIGHT_MM)
    height_ft = mm_to_ft(height_mm)

    clear_sink_mm = int(rules.get('kitchen_sink_clear_mm', constants.CLEAR_SINK_MM) or constants.CLEAR_SINK_MM)
    clear_stove_mm = int(rules.get('kitchen_stove_clear_mm', constants.CLEAR_STOVE_MM) or constants.CLEAR_STOVE_MM)
    clear_sink_ft = mm_to_ft(clear_sink_mm)
    clear_stove_ft = mm_to_ft(clear_stove_mm)

    offset_sink_mm = int(rules.get('kitchen_sink_offset_mm', constants.OFFSET_SINK_MM) or constants.OFFSET_SINK_MM)
    offset_stove_mm = int(rules.get('kitchen_stove_offset_mm', constants.OFFSET_STOVE_MM) or constants.OFFSET_STOVE_MM)
    offset_sink_ft = mm_to_ft(offset_sink_mm)
    offset_stove_ft = mm_to_ft(offset_stove_mm)

    wall_end_clear_mm = int(rules.get('kitchen_wall_end_clear_mm', constants.WALL_END_CLEAR_MM) or constants.WALL_END_CLEAR_MM)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    fixture_wall_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fixture_wall_max_dist_mm', constants.FIXTURE_WALL_MAX_DIST_MM) or constants.FIXTURE_WALL_MAX_DIST_MM))

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', constants.DEDUPE_MM) or constants.DEDUPE_MM)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    validate_match_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_match_tol_mm', constants.VALIDATE_MATCH_TOL_MM) or constants.VALIDATE_MATCH_TOL_MM))
    validate_height_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_height_tol_mm', constants.VALIDATE_HEIGHT_TOL_MM) or constants.VALIDATE_HEIGHT_TOL_MM))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('kitchen_validate_wall_dist_mm', constants.VALIDATE_WALL_DIST_MM) or constants.VALIDATE_WALL_DIST_MM))
    validate_offset_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_offset_tol_mm', constants.VALIDATE_OFFSET_TOL_MM) or constants.VALIDATE_OFFSET_TOL_MM))
    debug_no_candidates_limit = int(rules.get('kitchen_debug_no_candidates_limit', constants.DEBUG_NO_CANDIDATES_LIMIT) or constants.DEBUG_NO_CANDIDATES_LIMIT)
    debug_skipped_rooms_limit = int(rules.get('kitchen_debug_skipped_rooms_limit', constants.DEBUG_SKIPPED_ROOMS_LIMIT) or constants.DEBUG_SKIPPED_ROOMS_LIMIT)
    existing_dedupe_mm = int(rules.get('kitchen_existing_dedupe_mm', constants.EXISTING_DEDUPE_MM) or constants.EXISTING_DEDUPE_MM)

    fams = rules.get('family_type_names', {})
    prefer = fams.get('socket_kitchen_unit') or constants.DEFAULT_FAMILY_NAMES[0]

    if isinstance(prefer, (list, tuple)):
        prefer = sorted(prefer, key=lambda x: (0 if u'_2�' in (x or u'') else 1))
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
            output.print_md(u'**��������:** ��������� ��� ������� �� ������������ ���������� �� �����/�����. ����� ����������� OneLevel/WorkPlane �����, ���� ��������.')
        else:
            alert('�� ������ ��� ������� ��� ����� (��������).')
            if top10:
                output.print_md('��������� ��������:')
                for x in top10:
                    output.print_md('- {0}'.format(x))
            return

    try:
        su._store_symbol_id(cfg, 'last_socket_kitchen_unit_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_unit_symbol_uid', sym)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, '�������� ����� ��')
    if not link_inst: return
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc: return

    t = adapters.get_total_transform(link_inst)
    try:
        t_inv = t.Inverse if t else None
    except Exception:
        t_inv = None

    raw_rooms = adapters.get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200))

    # --- sinks/stoves detection ---
    sinks_all = []
    try:
        sink_sym_uid = getattr(cfg, 'kitchen_sink_link_symbol_uid', None)
        sink_sym_id = getattr(cfg, 'kitchen_sink_link_symbol_id', None)
        sink_sym = None
        if sink_sym_uid:
            try:
                sink_sym = link_doc.GetElement(str(sink_sym_uid))
            except Exception:
                sink_sym = None
        if (sink_sym is None) and sink_sym_id is not None:
            try:
                sink_sym = link_doc.GetElement(DB.ElementId(int(sink_sym_id)))
            except Exception:
                sink_sym = None
        if sink_sym is not None:
            try:
                sinks_all = adapters.collect_family_instance_points_by_symbol_id(link_doc, int(sink_sym.Id.IntegerValue))
            except Exception:
                sinks_all = []
    except Exception:
        sinks_all = []

    if not sinks_all:
        sinks_all = adapters.collect_sinks_points(link_doc, rules)

    if not sinks_all:
        try:
            pick = forms.alert(
                '�� ������� ������� � ����� ��.\n\n�������� ���� ����� � �����, ����� ������ ���� ����� ��� ����� ����� (�� ����).',
                yes=True, no=True
            )
        except Exception:
            pick = False
        if pick:
            e = adapters.pick_linked_element_any(link_inst, '�������� ����� (����� ��)')
            if e is not None and isinstance(e, DB.FamilyInstance):
                try:
                    sym0 = e.Symbol
                except Exception:
                    sym0 = None
                if sym0 is not None:
                    try:
                        sinks_all = adapters.collect_family_instance_points_by_symbol_id(link_doc, int(sym0.Id.IntegerValue))
                    except Exception:
                        sinks_all = []
                    if sinks_all:
                        try:
                            setattr(cfg, 'kitchen_sink_link_symbol_id', int(sym0.Id.IntegerValue))
                        except Exception:
                            pass
                        try:
                            setattr(cfg, 'kitchen_sink_link_symbol_uid', str(sym0.UniqueId))
                        except Exception:
                            pass
                        try:
                            adapters.save_config()
                        except Exception:
                            pass

    stoves_all = adapters.collect_stoves_points(link_doc, rules)

    output.print_md('��������: **{0}**; ������������: **{1}**'.format(len(sinks_all or []), len(stoves_all or [])))

    # Rooms selection
    rooms_by_id = {}

    for r in (raw_rooms or []):
        try:
            if kitchen_rx and (not su._match_any(kitchen_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    for pt in (stoves_all or []):
        r = domain.try_get_room_at_point(link_doc, pt)
        if r is None:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    for pt in (sinks_all or []):
        r = domain.try_get_room_at_point(link_doc, pt)
        if r is None:
            continue
        try:
            if kitchen_rx and (not su._match_any(kitchen_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    rooms = [rooms_by_id[k] for k in sorted(rooms_by_id.keys())]

    if not rooms:
        alert('��� ��������� ����� (�� ��������� �/��� �� ������������).')
        return

    host_sockets = adapters.collect_host_socket_instances(doc)

    try:
        ids_before, _elems_before, _pts_before = domain.collect_tagged_instances(doc, comment_value)
    except Exception:
        ids_before = set()

    fixed_existing = 0
    try:
        _ids0, elems0, _pts0 = domain.collect_tagged_instances(doc, comment_value)
    except Exception:
        elems0 = []
    if elems0:
        try:
            with tx('���: ����� �������� � ��������� ������', doc=doc, swallow_warnings=True):
                for e0 in elems0:
                    if su._try_set_offset_from_level(e0, height_ft):
                        fixed_existing += 1
        except Exception:
            fixed_existing = 0

    sym_flags = {}
    try:
        pt_enum = sym.Family.FamilyPlacementType
        sym_flags[int(sym.Id.IntegerValue)] = (
            pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
            pt_enum == DB.FamilyPlacementType.OneLevelBased,
        )
    except Exception:
        sym_flags[int(sym.Id.IntegerValue)] = (False, False)

    strict_hosting_mode = True
    try:
        if sym_flags.get(int(sym.Id.IntegerValue), (False, False))[1]:
            strict_hosting_mode = False
            output.print_md(u'**��������:** ��� ������� OneLevelBased - ���������� ����� ��� �����.')
    except Exception:
        pass

    sp_cache = {}
    pending = []
    plans = []

    debug_no_candidates_shown = 0

    created = created_face = created_wp = created_pt = 0
    skipped = 0
    skip_no_segs = 0
    skip_full = 0
    skip_no_fixtures = 0
    skip_not_kitchen = 0
    skip_no_candidates = 0
    prepared = 0

    skipped_details = []
    skipped_details_more = [0]

    def _push_skip(room, reason, details=None):
        try:
            lim = int(debug_skipped_rooms_limit or 0)
        except Exception:
            lim = 0
        if lim <= 0:
            return
        if len(skipped_details) >= lim:
            skipped_details_more[0] += 1
            return
        try:
            rid = int(room.Id.IntegerValue)
        except Exception:
            rid = None
        try:
            rnm = su._room_text(room)
        except Exception:
            rnm = u''
        skipped_details.append({
            'room_id': rid,
            'room_name': rnm,
            'reason': reason,
            'details': details or u''
        })

    with forms.ProgressBar(title='02. ����� (��������)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            segs = domain.get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                skip_no_segs += 1
                _push_skip(room, 'segs', u'��� ��������� ����')
                continue

            sinks = domain.points_in_room(sinks_all, room)
            stoves = domain.points_in_room(stoves_all, room)
            if not sinks and not stoves:
                skipped += 1
                skip_no_fixtures += 1
                _push_skip(room, 'fixtures', u'�� ������� �����/�����')
                continue

            is_named_kitchen = True
            try:
                is_named_kitchen = (not kitchen_rx) or su._match_any(kitchen_rx, su._room_text(room))
            except Exception:
                is_named_kitchen = True
            if (not is_named_kitchen) and (not (sinks and stoves)):
                skipped += 1
                skip_not_kitchen += 1
                _push_skip(
                    room,
                    'fixtures',
                    u'�� ����� �� �������� � ��� ���� (�����+�����); sinks={0}, stoves={1}'.format(len(sinks or []), len(stoves or []))
                )
                continue

            best_sink = sinks[0] if sinks else None
            best_stove = stoves[0] if stoves else None
            if sinks and stoves:
                best_d = None
                for s in sinks:
                    for p in stoves:
                        d = domain.dist_xy(s, p)
                        if best_d is None or d < best_d:
                            best_d = d
                            best_sink = s
                            best_stove = p

            base_z = su._room_level_elevation_ft(room, link_doc)

            existing_link_pts = []
            existing_cnt = 0
            existing_idx = su._XYZIndex(cell_ft=1.0)
            existing_dedupe_ft = mm_to_ft(existing_dedupe_mm)
            if host_sockets and t_inv:
                for inst, pt_host in host_sockets:
                    try:
                        pt_link = t_inv.OfPoint(pt_host)
                    except Exception:
                        continue
                    if not pt_link:
                        continue
                    if domain.points_in_room([pt_link], room):
                        existing_link_pts.append(pt_link)
                        if not existing_idx.has_near(float(pt_link.X), float(pt_link.Y), float(pt_link.Z), float(existing_dedupe_ft)):
                            existing_cnt += 1
                            existing_idx.add(float(pt_link.X), float(pt_link.Y), float(pt_link.Z))

            if existing_cnt >= total_target:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'��� {0}/{1} ������� � ���������'.format(int(existing_cnt), int(total_target)))
                continue
            need = max(0, int(total_target) - int(existing_cnt))
            if need <= 0:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'��� {0}/{1} ������� � ���������'.format(int(existing_cnt), int(total_target)))
                continue

            idx = su._XYZIndex(cell_ft=5.0)
            for ep in existing_link_pts:
                try:
                    idx.add(float(ep.X), float(ep.Y), 0.0)
                except Exception:
                    continue

            seg_sink, proj_sink, _ = domain.nearest_segment(best_sink, segs) if best_sink else (None, None, None)
            seg_stove, proj_stove, _ = domain.nearest_segment(best_stove, segs) if best_stove else (None, None, None)
            sink_wall_id = None
            stove_wall_id = None
            try:
                sink_wall_id = int(seg_sink[2].Id.IntegerValue) if seg_sink and seg_sink[2] else None
            except Exception:
                sink_wall_id = None
            try:
                stove_wall_id = int(seg_stove[2].Id.IntegerValue) if seg_stove and seg_stove[2] else None
            except Exception:
                stove_wall_id = None

            candidates, seg_sink, seg_stove, proj_sink, proj_stove = logic.get_candidates(
                segs, best_sink, best_stove, offset_sink_ft, offset_stove_ft, 
                fixture_wall_max_dist_ft, wall_end_clear_ft
            )

            if not candidates:
                skipped += 1
                skip_no_candidates += 1
                _push_skip(room, 'candidates', u'��� ���������� ����� ��� ���������� (����� ��������)')
                if debug_no_candidates_shown < debug_no_candidates_limit:
                    try:
                        output.print_md('��� ����������: room #{0} **{1}**'.format(int(room.Id.IntegerValue), su._room_text(room)))
                        if best_stove and seg_stove:
                            p0, p1, _w = seg_stove
                            seg_len = domain.dist_xy(p0, p1)
                            proj0 = domain.closest_point_on_segment_xy(best_stove, p0, p1)
                            t0 = (domain.dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_stove_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md('- stove: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                        if best_sink and seg_sink:
                            p0, p1, _w = seg_sink
                            seg_len = domain.dist_xy(p0, p1)
                            proj0 = domain.closest_point_on_segment_xy(best_sink, p0, p1)
                            t0 = (domain.dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_sink_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md('- sink: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                    except Exception:
                        pass
                    debug_no_candidates_shown += 1
                continue

            candidates = sorted(candidates, key=lambda x: (x.get('priority', 9)))

            picked = 0
            for cand in candidates:
                if picked >= need:
                    break
                pt_xy = cand.get('pt')
                seg = cand.get('seg')
                kind = cand.get('kind')
                if pt_xy is None or seg is None:
                    continue

                if best_sink and clear_sink_ft and (domain.dist_xy(pt_xy, best_sink) + 1e-9) < float(clear_sink_ft):
                    continue
                if best_stove and clear_stove_ft and (domain.dist_xy(pt_xy, best_stove) + 1e-9) < float(clear_stove_ft):
                    continue

                p0, p1, wall = seg
                proj = domain.closest_point_on_segment_xy(pt_xy, p0, p1)
                if proj is None:
                    continue
                if domain.dist_xy(pt_xy, proj) > float(validate_wall_dist_ft or mm_to_ft(150)):
                    continue

                if idx.has_near(float(pt_xy.X), float(pt_xy.Y), 0.0, float(dedupe_ft or mm_to_ft(300))):
                    continue

                idx.add(float(pt_xy.X), float(pt_xy.Y), 0.0)

                v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
                if v.GetLength() <= 1e-9:
                    continue
                v = v.Normalize()
                seg_len = p0.DistanceTo(p1)

                try:
                    wall_id = int(wall.Id.IntegerValue)
                except Exception:
                    wall_id = None
                offset_ft = float(offset_sink_ft) if kind == u'sink' else (float(offset_stove_ft) if kind == u'stove' else 0.0)

                pt_link = DB.XYZ(float(proj.X), float(proj.Y), float(base_z) + float(height_ft))
                pt_host = t.OfPoint(pt_link) if t else pt_link

                pending.append((wall, pt_link, v, sym, seg_len))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'expected_pt_host': pt_host,
                    'kind': kind,
                    'offset_ft': float(offset_ft),
                    'wall_id': wall_id,
                    'sink_wall_id': sink_wall_id,
                    'stove_wall_id': stove_wall_id,
                    'sink_pt': best_sink,
                    'stove_pt': best_stove,
                    'seg_p0': p0,
                    'seg_p1': p1,
                })
                prepared += 1
                picked += 1

                if len(pending) >= batch_size:
                    c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                        doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode
                    )
                    created += int(c)
                    created_face += int(cf)
                    created_wp += int(cwp)
                    created_pt += int(cpt)
                    pending = []

    if pending:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)

    ids_after, elems_after, _pts_after = domain.collect_tagged_instances(doc, comment_value)
    new_ids = set(ids_after or set()) - set(ids_before or set())
    try:
        elems_by_id = {int(e.Id.IntegerValue): e for e in (elems_after or [])}
    except Exception:
        elems_by_id = {}
    new_elems = [elems_by_id[i] for i in sorted(new_ids) if i in elems_by_id]

    validation = validator.validate_results(
        doc, plans, new_elems, 
        validate_match_tol_ft, validate_height_tol_ft, validate_wall_dist_ft, validate_offset_tol_ft, 
        clear_sink_ft, clear_stove_ft, t_inv
    )

    output.print_md(
        '���: **{0}**\n\n������������: **{1}**\n�������: **{2}** (Face: {3}, WorkPlane: {4}, Point: {5})\n���������: **{6}**'.format(
            sym_lbl or u'<�������>', prepared, created, created_face, created_wp, created_pt, skipped
        )
    )

    if fixed_existing:
        output.print_md('���������� ����� (������������): **{0}**'.format(fixed_existing))

    if validation:
        okc = len([x for x in validation if x.get('status') == 'ok'])
        failc = len([x for x in validation if x.get('status') == 'fail'])
        missc = len([x for x in validation if x.get('status') == 'missing'])
        output.print_md('��������: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(okc, failc, missc))
        if failc or missc:
            output.print_md('���������:')
            for x in validation:
                st = x.get('status')
                if st == 'ok':
                    continue
                rid = x.get('room_id')
                rnm = x.get('room_name')
                if st == 'missing':
                    output.print_md('- room #{0} {1}: �� ������ ��������� ��������� (tag={2})'.format(rid, rnm, comment_value))
                else:
                    output.print_md('- id {0} / room #{1} {2}: height={3}, on_wall={4}, offset={5}, sink_clear={6}, stove_clear={7}'.format(
                        x.get('id'), rid, rnm,
                        x.get('height_ok'), x.get('on_wall_ok'), x.get('offset_ok'), x.get('sink_clear_ok'), x.get('stove_clear_ok')
                    ))

    if skipped:
        output.print_md('������� ��������� (��.): segs={0}, full={1}, fixtures={2}, candidates={3}'.format(
            skip_no_segs, skip_full, (skip_no_fixtures + skip_not_kitchen), skip_no_candidates
        ))

    if skipped_details:
        output.print_md('����������� ��������� (������ {0}):'.format(len(skipped_details)))
        for x in skipped_details:
            output.print_md('- room #{0} **{1}**: {2}{3}'.format(
                x.get('room_id'), x.get('room_name') or u'',
                x.get('reason') or u'',
                (u' � ' + x.get('details')) if x.get('details') else u''
            ))
        if skipped_details_more[0]:
            output.print_md('- �� ��� ���������: **{0}** (��������� kitchen_debug_skipped_rooms_limit)'.format(int(skipped_details_more[0])))

