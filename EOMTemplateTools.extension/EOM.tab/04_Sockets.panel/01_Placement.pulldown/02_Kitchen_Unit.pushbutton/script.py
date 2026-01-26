# -*- coding: utf-8 -*-
# from eom_hub_runner import hub_run
# Unified Kitchen Socket Placement Script
# Places: 1 double socket (1100mm) + 1 fridge socket (300mm) + 2 perimeter sockets (300mm)

from pyrevit import DB, forms, revit, script
import os
import sys

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception, tx
from time_savings import report_time_saved
from utils_units import mm_to_ft
import socket_utils as su
import imp
_this_dir = os.path.dirname(os.path.abspath(__file__))
_domain_path = os.path.join(_this_dir, 'domain.py')
domain = imp.load_source('kitchen_unit_domain', _domain_path)


doc = revit.doc
output = script.get_output()
logger = script.get_logger()


TOOL_ID = 'eom_sockets_kitchen_unit'
TOOL_ID = 'eom_sockets_kitchen_unified'

def main():
    output.print_md(u'# 02. \u041a\u0443\u0445\u043d\u044f: \u0413\u0430\u0440\u043d\u0438\u0442\u0443\u0440 (1100\u043c\u043c)')

    rules = config_loader.load_rules()
    cfg = script.get_config()

    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value_unit = '{0}:SOCKET_KITCHEN_UNIT'.format(comment_tag)
    comment_value_fridge = '{0}:SOCKET_FRIDGE'.format(comment_tag)
    comment_value_general = '{0}:SOCKET_KITCHEN_GENERAL'.format(comment_tag)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or [u'\u043a\u0443\u0445\u043d', u'kitchen', u'\u0441\u0442\u043e\u043b\u043e\u0432']
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    total_target = 10  # Increased limit to allow unit + fridge + 2 general

    height_mm = int(rules.get('kitchen_unit_height_mm', 1100) or 1100)
    height_ft = mm_to_ft(height_mm)
    fridge_height_mm = int(rules.get('kitchen_fridge_height_mm', rules.get('kitchen_general_height_mm', 300) or 300) or 300)
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
    
    unit_margin_ft = mm_to_ft(float(rules.get('kitchen_unit_margin_mm', 100) or 100))
    general_spacing_ft = mm_to_ft(float(rules.get('kitchen_general_spacing_mm', 3000) or 3000))
    # Total kitchen sockets = unit(1) + fridge(1) + general, so general = total - 2
    # This is a minimum count; perimeter length may increase it.
    kitchen_total_sockets = int(rules.get('kitchen_total_sockets', 4) or 4)
    general_sockets_count = max(0, kitchen_total_sockets - 2)  # minimum after subtracting unit + fridge
    # Clearances per PUE/SP standards
    avoid_door_ft = mm_to_ft(float(rules.get('kitchen_avoid_door_mm', 200) or 200))
    avoid_window_ft = mm_to_ft(float(rules.get('kitchen_avoid_window_mm', 100) or 100))

    wall_end_clear_mm = int(rules.get('kitchen_wall_end_clear_mm', 150) or 150)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    fixture_wall_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fixture_wall_max_dist_mm', 2000) or 2000))

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', 300) or 300)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', 25) or 25)

    validate_match_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_match_tol_mm', 2000) or 2000))
    validate_height_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_height_tol_mm', 20) or 20))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('kitchen_validate_wall_dist_mm', 150) or 150))
    validate_offset_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_offset_tol_mm', 100) or 100))
    debug_no_candidates_limit = int(rules.get('kitchen_debug_no_candidates_limit', 3) or 3)
    debug_skipped_rooms_limit = int(rules.get('kitchen_debug_skipped_rooms_limit', 20) or 20)
    existing_dedupe_mm = int(rules.get('kitchen_existing_dedupe_mm', 200) or 200)

    fams = rules.get('family_type_names', {})
    prefer_unit = fams.get('socket_kitchen_unit') or (
        u'TSL_EF_\u0442_\u0421\u0422_\u0432_IP20_\u0420\u0437\u0442_1P+N+PE_2\u043f : TSL_EF_\u0442_\u0421\u0422_\u0432_IP20_\u0420\u0437\u0442_1P+N+PE_2\u043f'
    )
    if isinstance(prefer_unit, (list, tuple)):
        prefer_unit = sorted(prefer_unit, key=lambda x: (0 if u'_2\u043f' in (x or u'') else 1))

    def _try_pick_any(names):
        if not names:
            return None
        if not isinstance(names, (list, tuple)):
            names = [names]
        for n in names:
            if not n:
                continue
            try:
                sym0 = su._find_symbol_by_fullname(doc, n)
            except Exception:
                sym0 = None
            if sym0:
                return sym0
        return None

    sym_unit, sym_unit_lbl, top10 = su._pick_socket_symbol(doc, cfg, prefer_unit, cache_prefix='socket_kitchen_unit')
    if not sym_unit:
        sym_unit = _try_pick_any(prefer_unit)
        if sym_unit:
            try:
                sym_unit_lbl = placement_engine.format_family_type(sym_unit)
            except Exception:
                sym_unit_lbl = None
            output.print_md(u'Warning: unit socket type does not support face placement; fallback used.')
        else:
            alert(u'\u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0442\u0438\u043f \u0440\u043e\u0437\u0435\u0442\u043a\u0438 \u0434\u043b\u044f \u043a\u0443\u0445\u043d\u0438 (\u0433\u0430\u0440\u043d\u0438\u0442\u0443\u0440).')
            if top10:
                output.print_md(u'\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0432\u0430\u0440\u0438\u0430\u043d\u0442\u044b:')
                for x in top10:
                    output.print_md(u'- {0}'.format(x))
            return

    prefer_fridge = fams.get('socket_kitchen_fridge') or (
        u'TSL_EF_\u0442_\u0421\u0422_\u0432_IP20_\u0420\u0437\u0442_1P+N+PE'
    )
    sym_fridge, sym_fridge_lbl, _top10f = su._pick_socket_symbol(doc, cfg, prefer_fridge, cache_prefix='socket_kitchen_fridge')
    if not sym_fridge:
        sym_fridge = _try_pick_any(prefer_fridge)
        if sym_fridge:
            try:
                sym_fridge_lbl = placement_engine.format_family_type(sym_fridge)
            except Exception:
                sym_fridge_lbl = None
    if not sym_fridge:
        sym_fridge = sym_unit
        sym_fridge_lbl = sym_unit_lbl
        output.print_md(u'Warning: fridge socket type not found; using unit socket type.')
        
    prefer_general = fams.get('socket_kitchen_general') or (
        u'TSL_EF_\u0442_\u0421\u0422_\u0432_IP20_\u0420\u0437\u0442_1P+N+PE'
    )
    sym_general, sym_general_lbl, _top10g = su._pick_socket_symbol(doc, cfg, prefer_general, cache_prefix='socket_kitchen_general')
    if not sym_general:
        sym_general = _try_pick_any(prefer_general)
    if not sym_general:
        sym_general = sym_fridge  # Fallback to fridge (single) socket
        sym_general_lbl = sym_fridge_lbl

    try:
        su._store_symbol_id(cfg, 'last_socket_kitchen_unit_symbol_id', sym_unit)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_unit_symbol_uid', sym_unit)
        su._store_symbol_id(cfg, 'last_socket_kitchen_fridge_symbol_id', sym_fridge)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_fridge_symbol_uid', sym_fridge)
        su._store_symbol_id(cfg, 'last_socket_kitchen_general_symbol_id', sym_general)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_general_symbol_uid', sym_general)
        script.save_config()
    except Exception:
        pass
    link_inst = su._select_link_instance_ru(doc, u'\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0432\u044f\u0437\u044c \u0410\u0420')
    if not link_inst:
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        return

    t = link_reader.get_total_transform(link_inst)
    try:
        t_inv = t.Inverse if t else None
    except Exception:
        t_inv = None

    raw_rooms = su._get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200))

    # --- sinks/stoves detection ---
    sinks_all = []
    try:
        # Try last picked sink symbol in link (stored in pyRevit config)
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
                sinks_all = domain._collect_family_instance_points_by_symbol_id(link_doc, int(sink_sym.Id.IntegerValue))
            except Exception:
                sinks_all = []
    except Exception:
        sinks_all = []

    if not sinks_all:
        sinks_all = su._collect_sinks_points(link_doc, rules)

    if not sinks_all:
        # Fallback: ask user to pick one sink instance in the link to learn its type.
        try:
            pick = forms.alert(
                u'\u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e \u0440\u0430\u043a\u043e\u0432\u0438\u043d \u0432 \u0441\u0432\u044f\u0437\u0438 \u0410\u0420.\n\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u041e\u0414\u041d\u0423 \u043c\u043e\u0439\u043a\u0443 \u0432 \u0441\u0432\u044f\u0437\u0438, \u0447\u0442\u043e\u0431\u044b \u0441\u043a\u0440\u0438\u043f\u0442 \u0441\u043c\u043e\u0433 \u043d\u0430\u0439\u0442\u0438 \u0432\u0441\u0435 \u0442\u0430\u043a\u0438\u0435 \u043c\u043e\u0439\u043a\u0438 (\u043f\u043e \u0442\u0438\u043f\u0443).',
                yes=True, no=True
            )
        except Exception:
            pick = False
        if pick:
            e = domain._pick_linked_element_any(link_inst, u'\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043c\u043e\u0439\u043a\u0443 (\u0441\u0432\u044f\u0437\u044c \u0410\u0420)')
            if e is not None and isinstance(e, DB.FamilyInstance):
                try:
                    sym0 = e.Symbol
                except Exception:
                    sym0 = None
                if sym0 is not None:
                    try:
                        sinks_all = domain._collect_family_instance_points_by_symbol_id(link_doc, int(sym0.Id.IntegerValue))
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
                            script.save_config()
                        except Exception:
                            pass

    stoves_all = su._collect_stoves_points(link_doc, rules)

    fridges_all = su._collect_fridges_points(link_doc, rules)
    try:
        if hasattr(domain, '_collect_fridge_by_visibility_param'):
            fridges_all.extend(domain._collect_fridge_by_visibility_param(link_doc))
    except Exception:
        pass

    output.print_md(u'\u0420\u0430\u043a\u043e\u0432\u0438\u043d\u044b: **{0}**; \u042d\u043b\u0435\u043a\u0442\u0440\u043e\u043f\u043b\u0438\u0442\u044b: **{1}**; \u0425\u043e\u043b\u043e\u0434\u0438\u043b\u044c\u043d\u0438\u043a\u0438: **{2}**'.format(
        len(sinks_all or []), len(stoves_all or []), len(fridges_all or [])))

    # Rooms selection:
    # 1) rooms by name patterns (fast, limited scan)
    # 2) rooms that contain a stove (kitchen-living can be named "Гостиная")
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
        r = domain._try_get_room_at_point(link_doc, pt)
        if r is None:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    # Also include sink-rooms only if they match kitchen patterns (avoid bathrooms)
    for pt in (sinks_all or []):
        r = domain._try_get_room_at_point(link_doc, pt)
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
        alert(u'\u041d\u0435\u0442 \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u0439 \u043a\u0443\u0445\u043d\u0438 (\u043f\u043e \u043f\u0430\u0442\u0442\u0435\u0440\u043d\u0430\u043c \u0438/\u0438\u043b\u0438 \u043f\u043e \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043f\u043b\u0438\u0442\u0435).')
        return

    host_sockets = domain._collect_host_socket_instances(doc)

    try:
        ids_before_unit, _elems_before_unit, _pts_before_unit = domain._collect_tagged_instances(doc, comment_value_unit)
    except Exception:
        ids_before_unit = set()
    try:
        ids_before_fridge, _elems_before_fridge, _pts_before_fridge = domain._collect_tagged_instances(doc, comment_value_fridge)
    except Exception:
        ids_before_fridge = set()
    try:
        ids_before_general, _elems_before_general, _pts_before_general = domain._collect_tagged_instances(doc, comment_value_general)
    except Exception:
        ids_before_general = set()

    # Fix height for already placed kitchen-unit sockets (tagged)
    fixed_existing_unit = 0
    fixed_existing_fridge = 0
    try:
        _ids0, elems0, _pts0 = domain._collect_tagged_instances(doc, comment_value_unit)
    except Exception:
        elems0 = []
    try:
        _ids1, elems1, _pts1 = domain._collect_tagged_instances(doc, comment_value_fridge)
    except Exception:
        elems1 = []
    if elems0 or elems1:
        try:
            with tx(u'\u042d\u041e\u041c: \u041a\u0443\u0445\u043d\u044f \u0433\u0430\u0440\u043d\u0438\u0442\u0443\u0440 - \u0438\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0432\u044b\u0441\u043e\u0442\u0443', doc=doc, swallow_warnings=True):
                for e0 in elems0:
                    if domain._try_set_offset_from_level(e0, height_ft):
                        fixed_existing_unit += 1
                for e1 in elems1:
                    if domain._try_set_offset_from_level(e1, fridge_height_ft):
                        fixed_existing_fridge += 1
        except Exception:
            fixed_existing_unit = 0
            fixed_existing_fridge = 0

    sym_flags = {}

    def _register_sym_flags(sym):
        if sym is None:
            return
        try:
            pt_enum = sym.Family.FamilyPlacementType
            sym_flags[int(sym.Id.IntegerValue)] = (
                pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
                pt_enum == DB.FamilyPlacementType.OneLevelBased,
            )
        except Exception:
            try:
                sym_flags[int(sym.Id.IntegerValue)] = (False, False)
            except Exception:
                pass

    _register_sym_flags(sym_unit)
    _register_sym_flags(sym_fridge)
    _register_sym_flags(sym_general)

    strict_hosting_mode_unit = True
    try:
        if sym_unit and sym_flags.get(int(sym_unit.Id.IntegerValue), (False, False))[1]:
            strict_hosting_mode_unit = False
            output.print_md(u'**\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435:** \u0422\u0438\u043f \u0440\u043e\u0437\u0435\u0442\u043a\u0438 OneLevelBased (Unit) - \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c \u0440\u0435\u0436\u0438\u043c \u0431\u0435\u0437 \u0445\u043e\u0441\u0442\u0430.')
    except Exception:
        pass

    strict_hosting_mode_fridge = True
    try:
        if sym_fridge and sym_flags.get(int(sym_fridge.Id.IntegerValue), (False, False))[1]:
            strict_hosting_mode_fridge = False
            output.print_md(u'**\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435:** \u0422\u0438\u043f \u0440\u043e\u0437\u0435\u0442\u043a\u0438 OneLevelBased (Fridge) - \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c \u0440\u0435\u0436\u0438\u043c \u0431\u0435\u0437 \u0445\u043e\u0441\u0442\u0430.')
    except Exception:
        pass
        pass
    
    strict_hosting_mode_general = True
    try:
        if sym_general and sym_flags.get(int(sym_general.Id.IntegerValue), (False, False))[1]:
            strict_hosting_mode_general = False
            output.print_md(u'**\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435:** \u0422\u0438\u043f \u0440\u043e\u0437\u0435\u0442\u043a\u0438 OneLevelBased (General) - \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c \u0440\u0435\u0436\u0438\u043c \u0431\u0435\u0437 \u0445\u043e\u0441\u0442\u0430.')
    except Exception:
        pass

    sp_cache = {}
    pending_unit = []
    pending_fridge = []
    pending_general = []
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

    with forms.ProgressBar(title=u'02. \u041a\u0443\u0445\u043d\u044f (\u0433\u0430\u0440\u043d\u0438\u0442\u0443\u0440)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            segs = domain._get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                skip_no_segs += 1
                _push_skip(room, 'segs', u'\u043d\u0435\u0442 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432 \u0441\u0442\u0435\u043d')
                continue

            sinks = domain._points_in_room(sinks_all, room)
            stoves = domain._points_in_room(stoves_all, room)
            fridges = domain._points_in_room(fridges_all, room)
            if not sinks and not stoves:
                skipped += 1
                skip_no_fixtures += 1
                _push_skip(room, 'fixtures', u'\u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b \u043c\u043e\u0439\u043a\u0430/\u043f\u043b\u0438\u0442\u0430')
                continue

            # For rooms that don't look like a kitchen by name (e.g. "Гостиная"),
            # only proceed when BOTH sink and stove are detected in-room.
            # This prevents placing "kitchen unit" sockets in plain living rooms.
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
                    u'\u043d\u0435 \u043a\u0443\u0445\u043d\u044f \u043f\u043e \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044e \u0438 \u043d\u0435\u0442 \u043f\u0430\u0440\u044b (\u043c\u043e\u0439\u043a\u0430+\u043f\u043b\u0438\u0442\u0430); sinks={0}, stoves={1}'.format(len(sinks or []), len(stoves or []))
                )
                continue

            # Choose best sink-stove pair if both exist
            best_sink = sinks[0] if sinks else None
            best_stove = stoves[0] if stoves else None
            if sinks and stoves:
                best_d = None
                for s in sinks:
                    for p in stoves:
                        d = domain._dist_xy(s, p)
                        if best_d is None or d < best_d:
                            best_d = d
                            best_sink = s
                            best_stove = p

            # Choose best fridge (closest to stove if possible)
            best_fridge = fridges[0] if fridges else None
            if fridges and best_stove:
                try:
                    fr_sorted = sorted(fridges, key=lambda x: domain._dist_xy(x, best_stove))
                    best_fridge = fr_sorted[0] if fr_sorted else best_fridge
                except Exception:
                    pass

            base_z = su._room_level_elevation_ft(room, link_doc)

            # Count existing sockets in this kitchen room (all sockets, incl. out of unit zone)
            # Dedupe near-coincident sockets (e.g., double sockets made of two shared instances)
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
                    if domain._points_in_room([pt_link], room):
                        existing_link_pts.append(pt_link)
                        if not existing_idx.has_near(float(pt_link.X), float(pt_link.Y), float(pt_link.Z), float(existing_dedupe_ft)):
                            existing_cnt += 1
                            existing_idx.add(float(pt_link.X), float(pt_link.Y), float(pt_link.Z))

            # Requirement: one socket between sink+stove (top) and one near fridge (bottom).
            need_unit = 1
            need_fridge = 1  # Always need fridge socket (300mm) in kitchen
            capacity = max(0, int(total_target) - int(existing_cnt))
            if need_unit and need_fridge:
                capacity = max(int(capacity), 2)
            elif (need_unit or need_fridge) and int(capacity) <= 0:
                capacity = 1
            need = min(int(capacity), int(need_unit + need_fridge))
            if need <= 0:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'\u0443\u0436\u0435 {0}/{1} \u0440\u043e\u0437\u0435\u0442\u043e\u043a \u0432 \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u0438'.format(int(existing_cnt), int(total_target)))
                continue

            # Build dedupe index in link XY
            idx = su._XYZIndex(cell_ft=5.0)
            for ep in existing_link_pts:
                try:
                    idx.add(float(ep.X), float(ep.Y), 0.0)
                except Exception:
                    continue

            seg_sink, proj_sink, _ = domain._nearest_segment(best_sink, segs) if best_sink else (None, None, None)
            seg_stove, proj_stove, _ = domain._nearest_segment(best_stove, segs) if best_stove else (None, None, None)
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

            seg_fr, proj_fr, _ = domain._nearest_segment(best_fridge, segs) if best_fridge else (None, None, None)
            fridge_wall_id = None
            try:
                fridge_wall_id = int(seg_fr[2].Id.IntegerValue) if seg_fr and seg_fr[2] else None
            except Exception:
                fridge_wall_id = None

            candidates = []

            if seg_sink and seg_stove:
                try:
                    if int(seg_sink[2].Id.IntegerValue) == int(seg_stove[2].Id.IntegerValue):
                        seg_between = seg_sink
                        try:
                            if domain._dist_xy(seg_stove[0], seg_stove[1]) > domain._dist_xy(seg_sink[0], seg_sink[1]):
                                seg_between = seg_stove
                        except Exception:
                            seg_between = seg_sink
                        p0b, p1b, _wb = seg_between
                        # pt_between = kup.midpoint_between_projections_xy(
                        #     best_sink,
                        #     best_stove,
                        #     p0b,
                        #     p1b,
                        #     end_clear=wall_end_clear_ft,
                        #     point_factory=DB.XYZ,
                        # )
                        pt_between = None  # Temporary disable kup usage
                        if pt_between:
                            candidates.append({
                                'priority': 0,
                                'seg': seg_between,
                                'pt': pt_between,
                                'kind': u'between',
                                'height_ft': float(height_ft),
                                'comment_value': comment_value_unit,
                            })
                except Exception:
                    pass

            def _seg_dir(p0, p1):
                try:
                    v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
                    if v.GetLength() <= 1e-9:
                        return None
                    return v.Normalize()
                except Exception:
                    return None

            def _offset_candidates_for_fixture(src_pt, seg0, offset_ft, prefer_sign=None, priority=0, kind=u''):
                if src_pt is None or not seg0:
                    return
                # Try all boundary segments of the same wall (room boundary can split wall into small pieces).
                segs_try = []
                try:
                    wid0 = int(seg0[2].Id.IntegerValue) if seg0[2] else None
                except Exception:
                    wid0 = None
                if wid0 is not None:
                    for sg in segs or []:
                        try:
                            if int(sg[2].Id.IntegerValue) == wid0:
                                segs_try.append(sg)
                        except Exception:
                            continue
                if not segs_try:
                    segs_try = [seg0]

                scored = []
                for sg in segs_try:
                    p0, p1, wall = sg
                    proj = domain._closest_point_on_segment_xy(src_pt, p0, p1)
                    if proj is None:
                        continue
                    try:
                        dperp = domain._dist_xy(src_pt, proj)
                    except Exception:
                        dperp = None
                    if dperp is not None and fixture_wall_max_dist_ft and dperp > float(fixture_wall_max_dist_ft):
                        continue
                    scored.append((dperp if dperp is not None else 1e9, sg, proj))

                scored.sort(key=lambda x: x[0])
                for _dperp, sg, proj in scored:
                    p0, p1, wall = sg
                    try:
                        seg_len = domain._dist_xy(p0, p1)
                    except Exception:
                        seg_len = 0.0
                    if seg_len <= 1e-6:
                        continue
                    try:
                        t0 = domain._dist_xy(p0, proj) / seg_len
                    except Exception:
                        continue
                    dt = float(offset_ft or 0.0) / float(seg_len)
                    if dt <= 1e-9:
                        continue
                    end_tol = float(wall_end_clear_ft or 0.0) / float(seg_len) if seg_len > 1e-6 else 0.0

                    signs = []
                    if prefer_sign in (-1, 1):
                        signs = [int(prefer_sign), int(-prefer_sign)]
                    else:
                        signs = [-1, 1]

                    added = False
                    for sgn in signs:
                        tt = float(t0) + float(sgn) * dt
                        if tt < (0.0 + end_tol) or tt > (1.0 - end_tol):
                            continue
                        try:
                            pt = DB.XYZ(
                                float(p0.X) + (float(p1.X) - float(p0.X)) * tt,
                                float(p0.Y) + (float(p1.Y) - float(p0.Y)) * tt,
                                float(proj.Z)
                            )
                        except Exception:
                            continue
                        candidates.append({
                            'priority': priority,
                            'seg': sg,
                            'pt': pt,
                            'kind': kind,
                            'height_ft': float(height_ft),
                            'comment_value': comment_value_unit,
                        })
                        added = True
                    if added:
                        break

            # Offset candidates near sink/stove
            if seg_sink and proj_sink:
                prefer_sign = None
                if seg_stove and proj_stove:
                    try:
                        if int(seg_sink[2].Id.IntegerValue) == int(seg_stove[2].Id.IntegerValue):
                            v = _seg_dir(seg_sink[0], seg_sink[1])
                            if v:
                                d = (proj_stove - proj_sink).DotProduct(v)
                                prefer_sign = -1 if d > 0 else 1
                    except Exception:
                        prefer_sign = None
                _offset_candidates_for_fixture(best_sink, seg_sink, offset_sink_ft, prefer_sign=prefer_sign, priority=0, kind=u'sink')

            if seg_stove and proj_stove:
                prefer_sign = None
                if seg_sink and proj_sink:
                    try:
                        if int(seg_sink[2].Id.IntegerValue) == int(seg_stove[2].Id.IntegerValue):
                            v = _seg_dir(seg_stove[0], seg_stove[1])
                            if v:
                                d = (proj_sink - proj_stove).DotProduct(v)
                                prefer_sign = -1 if d > 0 else 1
                    except Exception:
                        prefer_sign = None
                _offset_candidates_for_fixture(best_stove, seg_stove, offset_stove_ft, prefer_sign=prefer_sign, priority=1, kind=u'stove')

            # Fridge socket candidate (300mm height)
            if seg_fr and proj_fr:
                # Fridge found - place socket near it
                candidates.append({
                    'priority': 2,
                    'seg': seg_fr,
                    'pt': proj_fr,
                    'kind': u'fridge',
                    'height_ft': float(fridge_height_ft),
                    'comment_value': comment_value_fridge,
                })
            else:
                # No fridge found - place socket at opposite end of kitchen wall from sink/stove
                # Use the same wall as sink/stove but at the far end
                fridge_seg = None
                fridge_pt = None
                ref_seg = seg_stove if seg_stove else seg_sink
                ref_proj = proj_stove if proj_stove else proj_sink
                if ref_seg and ref_proj:
                    p0, p1, wall = ref_seg
                    try:
                        seg_len = domain._dist_xy(p0, p1)
                        if seg_len and seg_len > 1e-6:
                            # Find which end is farther from ref_proj
                            d0 = domain._dist_xy(ref_proj, p0)
                            d1 = domain._dist_xy(ref_proj, p1)
                            end_tol = float(wall_end_clear_ft or 0.0)
                            if d0 > d1:
                                # p0 is farther, place near p0
                                t_fridge = end_tol / seg_len if seg_len > 1e-6 else 0.1
                                t_fridge = max(0.05, min(t_fridge, 0.4))
                            else:
                                # p1 is farther, place near p1
                                t_fridge = 1.0 - (end_tol / seg_len if seg_len > 1e-6 else 0.1)
                                t_fridge = max(0.6, min(t_fridge, 0.95))
                            fridge_pt = DB.XYZ(
                                float(p0.X) + (float(p1.X) - float(p0.X)) * t_fridge,
                                float(p0.Y) + (float(p1.Y) - float(p0.Y)) * t_fridge,
                                float(ref_proj.Z)
                            )
                            fridge_seg = ref_seg
                    except Exception:
                        fridge_seg = None
                        fridge_pt = None
                if fridge_seg and fridge_pt:
                    candidates.append({
                        'priority': 2,
                        'seg': fridge_seg,
                        'pt': fridge_pt,
                        'kind': u'fridge',
                        'height_ft': float(fridge_height_ft),
                        'comment_value': comment_value_fridge,
                    })

            if not candidates:
                skipped += 1
                skip_no_candidates += 1
                _push_skip(room, 'candidates', u'\u043d\u0435\u0442 \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0445 \u0442\u043e\u0447\u0435\u043a \u0434\u043b\u044f \u0440\u0430\u0437\u043c\u0435\u0449\u0435\u043d\u0438\u044f (\u043f\u043e\u0441\u043b\u0435 \u0444\u0438\u043b\u044c\u0442\u0440\u043e\u0432)')
                if debug_no_candidates_shown < debug_no_candidates_limit:
                    try:
                        output.print_md(u'\u041d\u0435\u0442 \u043a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u043e\u0432: room #{0} **{1}**'.format(int(room.Id.IntegerValue), su._room_text(room)))
                        if best_stove and seg_stove:
                            p0, p1, _w = seg_stove
                            seg_len = domain._dist_xy(p0, p1)
                            proj0 = domain._closest_point_on_segment_xy(best_stove, p0, p1)
                            t0 = (domain._dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_stove_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md(u'- stove: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                        if best_sink and seg_sink:
                            p0, p1, _w = seg_sink
                            seg_len = domain._dist_xy(p0, p1)
                            proj0 = domain._closest_point_on_segment_xy(best_sink, p0, p1)
                            t0 = (domain._dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_sink_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md(u'- sink: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                    except Exception:
                        pass
                    debug_no_candidates_shown += 1
                continue

            # Sort by priority and keep unique-ish by XY
            candidates = sorted(candidates, key=lambda x: (x.get('priority', 9)))

            picked = 0
            picked_unit = 0
            picked_fridge = 0
            for cand in candidates:
                if picked >= need:
                    break
                pt_xy = cand.get('pt')
                seg = cand.get('seg')
                kind = cand.get('kind')
                if pt_xy is None or seg is None:
                    continue

                if kind == u'fridge':
                    if picked_fridge >= need_fridge:
                        continue
                else:
                    if picked_unit >= need_unit:
                        continue

                # clearance checks (>= 600mm by default)
                if kind != u'fridge':
                    if best_sink and clear_sink_ft and (domain._dist_xy(pt_xy, best_sink) + 1e-9) < float(clear_sink_ft):
                        continue
                    if best_stove and clear_stove_ft and (domain._dist_xy(pt_xy, best_stove) + 1e-9) < float(clear_stove_ft):
                        continue

                # on-wall proximity (segment projection)
                p0, p1, wall = seg
                proj = domain._closest_point_on_segment_xy(pt_xy, p0, p1)
                if proj is None:
                    continue
                if domain._dist_xy(pt_xy, proj) > float(validate_wall_dist_ft or mm_to_ft(150)):
                    continue

                # dedupe (XY) - skip for fridge since it's at different height (300mm vs 1100mm)
                # and should be placed even if unit socket is nearby
                if kind != u'fridge' and idx.has_near(float(pt_xy.X), float(pt_xy.Y), 0.0, float(dedupe_ft or mm_to_ft(300))):
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
                height_ft_cand = float(cand.get('height_ft', height_ft))
                comment_value_cand = cand.get('comment_value', comment_value_unit)

                pt_link = DB.XYZ(float(proj.X), float(proj.Y), float(base_z) + float(height_ft_cand))
                pt_host = t.OfPoint(pt_link) if t else pt_link

                sym_cand = sym_fridge if comment_value_cand == comment_value_fridge else sym_unit
                if sym_cand is None:
                    continue
                if comment_value_cand == comment_value_fridge:
                    pending_fridge.append((wall, pt_link, v, sym_cand, seg_len))
                else:
                    pending_unit.append((wall, pt_link, v, sym_cand, seg_len))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'expected_pt_host': pt_host,
                    'kind': kind,
                    'offset_ft': float(offset_ft),
                    'height_ft': float(height_ft_cand),
                    'comment_value': comment_value_cand,
                    'wall_id': wall_id,
                    'sink_wall_id': sink_wall_id,
                    'stove_wall_id': stove_wall_id,
                    'fridge_wall_id': fridge_wall_id,
                    'sink_pt': best_sink,
                    'stove_pt': best_stove,
                    'fridge_pt': best_fridge,
                    'seg_p0': p0,
                    'seg_p1': p1,
                })
                prepared += 1
                picked += 1
                if kind == u'fridge':
                    picked_fridge += 1
                else:
                    picked_unit += 1

                if len(pending_unit) >= batch_size:
                    c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                        doc, link_inst, t, pending_unit, sym_flags, sp_cache, comment_value_unit, strict_hosting=strict_hosting_mode_unit
                    )
                    created += int(c)
                    created_face += int(cf)
                    created_wp += int(cwp)
                    created_pt += int(cpt)
                    pending_unit = []
                if len(pending_fridge) >= batch_size:
                    c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                        doc, link_inst, t, pending_fridge, sym_flags, sp_cache, comment_value_fridge, strict_hosting=strict_hosting_mode_fridge
                    )
                    created += int(c)
                    created_face += int(cf)
                    created_wp += int(cwp)
                    created_pt += int(cpt)
                    pending_fridge = []

            # --- Perimeter / General Sockets Logic ---
            unit_bboxes = domain._collect_kitchen_unit_bboxes(link_doc, room, segs)
            p_allowed, p_len = domain._calculate_perimeter_allowed_path(
                link_doc, room, segs, avoid_door_ft, avoid_window_ft, 
                {}, 
                unit_bboxes, unit_margin_ft
            )
            
            actual_general_count = max(general_sockets_count, int(p_len / float(general_spacing_ft or 1.0)))
            output.print_md(
                u'Периметр кухни: **{0:.2f} ft**, general min={1}, spacing={2:.2f} ft, расчет={3}'.format(
                    float(p_len or 0.0),
                    int(general_sockets_count),
                    float(general_spacing_ft or 0.0),
                    int(actual_general_count)
                )
            )
            p_cands = domain._generate_perimeter_candidates(
                p_allowed,
                p_len,
                general_spacing_ft,
                wall_end_clear_ft,
                num_sockets=actual_general_count
            )

            general_idx = su._XYZIndex(cell_ft=max(1.0, float(general_spacing_ft or 0.0)))
            for gen_pt_host in (_pts_before_general or []):
                try:
                    gen_pt_link = t_inv.OfPoint(gen_pt_host) if t_inv else gen_pt_host
                except Exception:
                    continue
                if gen_pt_link is None:
                    continue
                try:
                    general_idx.add(float(gen_pt_link.X), float(gen_pt_link.Y), 0.0)
                except Exception:
                    continue

            for wall, pt, v in p_cands:
                if idx.has_near(float(pt.X), float(pt.Y), 0.0, float(dedupe_ft)):
                    continue
                if general_idx.has_near(float(pt.X), float(pt.Y), 0.0, float(dedupe_ft)):
                    continue
                if best_sink and clear_sink_ft and (domain._dist_xy(pt, best_sink) < float(clear_sink_ft)):
                    continue
                if best_stove and clear_stove_ft and (domain._dist_xy(pt, best_stove) < float(clear_stove_ft)):
                    continue
                idx.add(float(pt.X), float(pt.Y), 0.0)
                general_idx.add(float(pt.X), float(pt.Y), 0.0)
                
                try: wall_id = int(wall.Id.IntegerValue)
                except: wall_id = None
                
                pt_link = DB.XYZ(float(pt.X), float(pt.Y), float(base_z) + float(general_height_ft))
                
                pending_general.append((wall, pt_link, v, sym_general, 0.0))
                
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'kind': u'general',
                    'comment_value': comment_value_general,
                    'height_ft': float(general_height_ft),
                    'wall_id': wall_id
                })
                prepared += 1
                
                if len(pending_general) >= batch_size:
                    c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                        doc, link_inst, t, pending_general, sym_flags, sp_cache, comment_value_general, strict_hosting=strict_hosting_mode_general
                    )
                    created += int(c)
                    created_face += int(cf)
                    created_wp += int(cwp)
                    created_pt += int(cpt)
                    pending_general = []


    if pending_unit:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending_unit, sym_flags, sp_cache, comment_value_unit, strict_hosting=strict_hosting_mode_unit
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)
    if pending_fridge:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending_fridge, sym_flags, sp_cache, comment_value_fridge, strict_hosting=strict_hosting_mode_fridge
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)
    if pending_general:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending_general, sym_flags, sp_cache, comment_value_general, strict_hosting=strict_hosting_mode_general
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)

    # Fridge sockets moved to 02_Kitchen script (SOCKET_FRIDGE)

    ids_after_unit, elems_after_unit, _pts_after_unit = domain._collect_tagged_instances(doc, comment_value_unit)
    ids_after_fridge, elems_after_fridge, _pts_after_fridge = domain._collect_tagged_instances(doc, comment_value_fridge)
    ids_after_general, elems_after_general, _pts_after_general = domain._collect_tagged_instances(doc, comment_value_general)
    new_ids_unit = set(ids_after_unit or set()) - set(ids_before_unit or set())
    new_ids_fridge = set(ids_after_fridge or set()) - set(ids_before_fridge or set())
    new_ids_general = set(ids_after_general or set()) - set(ids_before_general or set())
    new_ids = set(new_ids_unit or set()) | set(new_ids_fridge or set()) | set(new_ids_general or set())
    try:
        elems_by_id = {int(e.Id.IntegerValue): e for e in ((elems_after_unit or []) + (elems_after_fridge or []) + (elems_after_general or []))}
    except Exception:
        elems_by_id = {}
    new_elems = [elems_by_id[i] for i in sorted(new_ids) if i in elems_by_id]

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

            abs_z = None
            try:
                abs_z = domain._get_abs_z_from_level_offset(e, doc)
            except Exception:
                abs_z = None
            z_key = abs_z if abs_z is not None else float(pt.Z)

            inst_items.append((iid, e, pt, float(z_key)))

        used_inst = set()
        for pl in plans:
            exp_pt = pl.get('expected_pt_host')
            if exp_pt is None:
                continue
            try:
                exp_z = float(exp_pt.Z)
            except Exception:
                exp_z = None

            best = None
            best_key = None  # (dZ, dXY)
            best_dxy = None

            for iid, e, pt, z_key in inst_items:
                if iid in used_inst:
                    continue
                dxy = domain._dist_xy(pt, exp_pt)
                if validate_match_tol_ft and dxy > validate_match_tol_ft:
                    continue
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

            try:
                exp_z = float(pl['expected_pt_host'].Z)
            except Exception:
                exp_z = float(inst_pt.Z)

            abs_z = None
            try:
                abs_z = domain._get_abs_z_from_level_offset(inst, doc)
            except Exception:
                abs_z = None
            z_to_check = abs_z if abs_z is not None else float(inst_pt.Z)
            height_ok = abs(float(z_to_check) - float(exp_z)) <= float(validate_height_tol_ft or mm_to_ft(20))

            try:
                inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
            except Exception:
                inst_pt_link = inst_pt

            p0 = pl.get('seg_p0')
            p1 = pl.get('seg_p1')
            try:
                seg_len = domain._dist_xy(p0, p1) if p0 and p1 else 0.0
            except Exception:
                seg_len = 0.0

            # On-wall check vs planned segment
            proj = domain._closest_point_on_segment_xy(inst_pt_link, p0, p1) if p0 and p1 else None
            dist_wall = domain._dist_xy(inst_pt_link, proj) if proj else None
            on_wall_ok = (dist_wall is not None) and (dist_wall <= float(validate_wall_dist_ft or mm_to_ft(150)))

            # Compute position along segment
            ti = None
            if proj and seg_len and seg_len > 1e-6:
                try:
                    ti = domain._dist_xy(p0, proj) / seg_len
                except Exception:
                    ti = None

            wall_id = pl.get('wall_id')

            def _axis_dist_ft(axis_pt):
                if axis_pt is None:
                    return None
                if not (p0 and p1) or (not seg_len) or seg_len <= 1e-6 or ti is None:
                    return None
                proj_a = domain._closest_point_on_segment_xy(axis_pt, p0, p1)
                if proj_a is None:
                    return None
                try:
                    ta = domain._dist_xy(p0, proj_a) / seg_len
                except Exception:
                    return None
                try:
                    return abs(float(ti) - float(ta)) * float(seg_len)
                except Exception:
                    return None

            # Clearance checks (по оси вдоль стены, если ось на этой же стене)
            sink_clear_ok = True
            stove_clear_ok = True

            sink_pt = pl.get('sink_pt')
            stove_pt = pl.get('stove_pt')

            if sink_pt is not None:
                sink_d = None
                if wall_id is not None and pl.get('sink_wall_id') == wall_id:
                    sink_d = _axis_dist_ft(sink_pt)
                if sink_d is None:
                    sink_d = domain._dist_xy(inst_pt_link, sink_pt)
                sink_clear_ok = (sink_d + 1e-9) >= float(clear_sink_ft)

            if stove_pt is not None:
                stove_d = None
                if wall_id is not None and pl.get('stove_wall_id') == wall_id:
                    stove_d = _axis_dist_ft(stove_pt)
                if stove_d is None:
                    stove_d = domain._dist_xy(inst_pt_link, stove_pt)
                stove_clear_ok = (stove_d + 1e-9) >= float(clear_stove_ft)

            # Offset check: 600мм от оси «своего» прибора (вдоль стены)
            offset_ok = True
            kind = pl.get('kind')
            want_offset = float(pl.get('offset_ft') or 0.0)
            if kind == u'sink' and sink_pt is not None:
                d = _axis_dist_ft(sink_pt) if (wall_id is not None and pl.get('sink_wall_id') == wall_id) else None
                if d is not None:
                    offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))
            elif kind == u'stove' and stove_pt is not None:
                d = _axis_dist_ft(stove_pt) if (wall_id is not None and pl.get('stove_wall_id') == wall_id) else None
                if d is not None:
                    offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))

            fridge_ok = True
            if kind == u'fridge':
                fp = pl.get('fridge_pt')
                if fp is None:
                    fridge_ok = False
                else:
                    try:
                        fridge_ok = domain._dist_xy(inst_pt_link, fp) <= float(fridge_max_dist_ft or mm_to_ft(1500))
                    except Exception:
                        fridge_ok = False

            if kind == u'fridge':
                ok = bool(height_ok and on_wall_ok and fridge_ok)
            else:
                ok = bool(height_ok and on_wall_ok and sink_clear_ok and stove_clear_ok and offset_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'room_id': pl['room_id'],
                'room_name': pl['room_name'],
                'kind': kind,
                'comment_value': pl.get('comment_value'),
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
                'sink_clear_ok': bool(sink_clear_ok),
                'stove_clear_ok': bool(stove_clear_ok),
                'offset_ok': bool(offset_ok),
                'fridge_ok': bool(fridge_ok),
            })

    output.print_md(
        u'Types: unit={0}; fridge={1}; general={2}\n\nPrepared: **{3}**\nCreated: **{4}** (Face: {5}, WorkPlane: {6}, Point: {7})\nSkipped: **{8}**'.format(
            sym_unit_lbl or u'<Socket>',
            sym_fridge_lbl or sym_unit_lbl or u'<Socket>',
            sym_general_lbl or sym_fridge_lbl or u'<Socket>',
            prepared, created, created_face, created_wp, created_pt, skipped
        )
    )

    if fixed_existing_unit:
        output.print_md(u'Fixed existing unit sockets: **{0}**'.format(fixed_existing_unit))
    if fixed_existing_fridge:
        output.print_md(u'Fixed existing fridge sockets: **{0}**'.format(fixed_existing_fridge))

    if validation:
        okc = len([x for x in validation if x.get('status') == 'ok'])
        failc = len([x for x in validation if x.get('status') == 'fail'])
        missc = len([x for x in validation if x.get('status') == 'missing'])
        output.print_md(u'\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(okc, failc, missc))
        if failc or missc:
            output.print_md(u'\u041d\u0430\u0440\u0443\u0448\u0435\u043d\u0438\u044f:')
            for x in validation:
                st = x.get('status')
                if st == 'ok':
                    continue
                rid = x.get('room_id')
                rnm = x.get('room_name')
                if st == 'missing':
                    output.print_md(u'- room #{0} {1}: missing created instance (tag={2})'.format(rid, rnm, x.get('comment_value')))
                else:
                    kind = x.get('kind')
                    if kind == 'fridge':
                        output.print_md(u'- id {0} / room #{1} {2} ({3}): height={4}, on_wall={5}, fridge={6}'.format(
                            x.get('id'), rid, rnm, kind,
                            x.get('height_ok'), x.get('on_wall_ok'), x.get('fridge_ok')
                        ))
                    else:
                        output.print_md(u'- id {0} / room #{1} {2} ({3}): height={4}, on_wall={5}, offset={6}, sink_clear={7}, stove_clear={8}'.format(
                            x.get('id'), rid, rnm, kind,
                            x.get('height_ok'), x.get('on_wall_ok'), x.get('offset_ok'), x.get('sink_clear_ok'), x.get('stove_clear_ok')
                        ))
    if skipped:
        output.print_md(u'\u041f\u0440\u0438\u0447\u0438\u043d\u044b \u043f\u0440\u043e\u043f\u0443\u0441\u043a\u043e\u0432 (\u0448\u0442.): segs={0}, full={1}, fixtures={2}, candidates={3}'.format(
            skip_no_segs, skip_full, (skip_no_fixtures + skip_not_kitchen), skip_no_candidates
        ))

    if skipped_details:
        output.print_md(u'\u041f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043d\u044b\u0435 \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u044f (\u043f\u0435\u0440\u0432\u044b\u0435 {0}):'.format(len(skipped_details)))
        for x in skipped_details:
            output.print_md(u'- room #{0} **{1}**: {2}{3}'.format(
                x.get('room_id'), x.get('room_name') or u'',
                x.get('reason') or u'',
                (u' — ' + x.get('details')) if x.get('details') else u''
            ))
        if skipped_details_more[0]:
            output.print_md(u'More skipped rooms: **{0}** (limit kitchen_debug_skipped_rooms_limit)'.format(int(skipped_details_more[0])))

    report_time_saved(output, 'sockets_kitchen_unit')


def _legacy():
    try:
        main()
    except Exception:
        log_exception('Error in 02_Kitchen_Unit')


if __name__ == '__main__':
    _legacy()

