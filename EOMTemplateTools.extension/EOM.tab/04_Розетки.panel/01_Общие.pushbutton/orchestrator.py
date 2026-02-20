# -*- coding: utf-8 -*-

import math
from pyrevit import DB, script, forms
import adapters
import domain
import constants
try:
    import socket_utils as su
except ImportError:
    import sys, os
    # Fix path resolution: orchestrator.py is in .../01_General.pushbutton, so we need 4 dirnames to get to .extension
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su
from utils_revit import alert, log_exception
from utils_units import mm_to_ft


def run(doc, output):
    output.print_md('# 01. Розетки: Общие (жилые/коридоры)')

    rules = adapters.get_rules()
    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value = '{0}{1}'.format(comment_tag, constants.COMMENT_SUFFIX)

    spacing_mm = float(
        rules.get(
            'socket_general_spacing_mm',
            rules.get('socket_spacing_mm', constants.DEFAULT_SPACING_MM),
        )
    )
    height_mm = float(rules.get('socket_height_mm', constants.DEFAULT_HEIGHT_MM))
    avoid_door_mm = float(rules.get('avoid_door_mm', constants.AVOID_DOOR_MM))
    avoid_radiator_mm = float(rules.get('avoid_radiator_mm', constants.AVOID_RADIATOR_MM))
    dedupe_mm = float(rules.get('socket_dedupe_radius_mm', constants.DEDUPE_MM))
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)
    host_wall_search_mm = float(rules.get('host_wall_search_mm', constants.HOST_WALL_SEARCH_MM) or constants.HOST_WALL_SEARCH_MM)

    opening_offset_mm = avoid_door_mm
    try:
        default_txt = str(int(round(opening_offset_mm)))
    except Exception:
        default_txt = str(avoid_door_mm)
    try:
        prompt = u'Отступ от углов/окон/дверей (мм)'
        title = u'Параметры размещения розеток'
        user_val = forms.ask_for_string(prompt=prompt, title=title, default=default_txt)
        if user_val is None:
            return
        user_val = user_val.strip()
        if user_val:
            try:
                opening_offset_mm = float(user_val.replace(',', '.'))
                if opening_offset_mm < 0:
                    opening_offset_mm = avoid_door_mm
            except Exception:
                forms.alert(u'Неверный формат числа. Использую значение по умолчанию: {0} мм'.format(default_txt))
                opening_offset_mm = avoid_door_mm
    except Exception:
        opening_offset_mm = avoid_door_mm

    spacing_ft = mm_to_ft(spacing_mm)
    height_ft = mm_to_ft(height_mm)
    avoid_door_ft = mm_to_ft(opening_offset_mm)
    avoid_radiator_ft = mm_to_ft(avoid_radiator_mm)
    dedupe_ft = mm_to_ft(dedupe_mm)
    window_offset_ft = avoid_door_ft
    corner_offset_ft = avoid_door_ft
    host_wall_search_ft = mm_to_ft(host_wall_search_mm)
    wall_filter = domain.build_wall_filter(rules)

    cfg = adapters.get_config()
    fams = rules.get('family_type_names', {})
    fam_gen = fams.get('socket_general') or fams.get('power_socket')
    sym_gen, lbl_gen, _ = adapters.pick_socket_symbol(doc, cfg, fam_gen)

    if not sym_gen:
        # Auto-pick fallback
        sym_auto, lbl_auto, _ = adapters.auto_pick_socket_symbol(doc)
        if sym_auto:
            sym_gen = sym_auto
            lbl_gen = lbl_auto
            output.print_md('**Auto-pick:** {0}'.format(lbl_gen or '<unnamed>'))
            adapters.save_default_rule('socket_general', lbl_gen)
        else:
            alert('Socket type not found (General). Check config.')
            return

    su._store_symbol_id(cfg, 'last_socket_general_symbol_id', sym_gen)
    su._store_symbol_unique_id(cfg, 'last_socket_general_symbol_uid', sym_gen)
    adapters.save_config()

    link_inst = adapters.select_link_instance(doc, 'Выберите связь АР')
    if not link_inst: return
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc: return

    import link_reader
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни')
    if not selected_levels:
        return
    
    level_ids = [l.Id for l in selected_levels]
    raw_rooms = adapters.get_all_linked_rooms(link_doc, level_ids=level_ids)

    hallway_rx = domain.compile_patterns(rules.get('hallway_room_name_patterns', constants.DEFAULT_HALLWAY_PATTERNS))
    wet_rx = domain.compile_patterns(rules.get('wet_room_name_patterns', constants.DEFAULT_WET_PATTERNS))
    kitchen_rx = domain.compile_patterns(constants.DEFAULT_KITCHEN_PATTERNS)
    exclude_rx = domain.compile_patterns(rules.get('exclude_room_name_patterns', constants.DEFAULT_EXCLUDE_PATTERNS))
    wardrobe_rx = domain.compile_patterns(rules.get('wardrobe_room_name_patterns', constants.DEFAULT_WARDROBE_PATTERNS))
    wardrobe_skip_sqm = float(rules.get('wardrobe_skip_area_sqm', constants.WARDROBE_SKIP_AREA_SQM) or constants.WARDROBE_SKIP_AREA_SQM)
    sliding_rx = domain.compile_patterns(rules.get('sliding_door_name_patterns', constants.DEFAULT_SLIDING_DOOR_PATTERNS))

    apt_pats = list(rules.get('entrance_apartment_room_name_patterns', constants.DEFAULT_APARTMENT_PATTERNS) or [])
    # Ensure corridors included
    for p in (u'корид', u'hall', u'corridor'):
        if p not in apt_pats:
            apt_pats.append(p)
    apt_rx = domain.compile_patterns(apt_pats)

    pub_pats = list(rules.get('entrance_public_room_name_patterns', constants.DEFAULT_PUBLIC_PATTERNS) or [])
    # Remove apartments corridors from public exclusion if present
    pub_pats = [p for p in pub_pats if p and (u'корид' not in p) and (u'hall' not in p)]
    public_rx = domain.compile_patterns(pub_pats)

    rooms = domain.filter_rooms(raw_rooms, rules, apt_rx, public_rx, wet_rx, kitchen_rx, exclude_rx)

    global LAST_ROOM_COUNT
    try:
        LAST_ROOM_COUNT = len(rooms)
    except Exception:
        LAST_ROOM_COUNT = None

    if not rooms:
        alert('Нет подходящих помещений (исключены кухни и санузлы).')
        return

    openings_cache = {}
    radiator_pts = adapters.collect_radiator_points(link_doc)
    radiator_idx = None
    if radiator_pts:
        radiator_idx = su._XYZIndex(cell_ft=5.0)
        for p in radiator_pts: radiator_idx.add(p.X, p.Y, 0.0)

    sliding_doors = []
    try:
        for d in link_reader.iter_doors(link_doc):
            try:
                txt = su._elem_text(d)
            except Exception:
                txt = u''
            if not domain.is_sliding_door_text(txt, sliding_rx):
                continue
            try:
                pt = su._door_center_point(d)
            except Exception:
                pt = None
            if pt is None:
                continue
            try:
                w = su._get_opening_width_ft(d, primary_bip=DB.BuiltInParameter.DOOR_WIDTH, fallback_width_mm=900)
            except Exception:
                w = None
            try:
                half = (float(w) * 0.5) if w else (mm_to_ft(900) * 0.5)
            except Exception:
                half = mm_to_ft(900) * 0.5
            sliding_doors.append((pt, half))
    except Exception:
        sliding_doors = []

    t = adapters.get_total_transform(link_inst)
    idx = su._XYZIndex(cell_ft=5.0)

    sym_flags = {}
    sid = sym_gen.Id.IntegerValue
    pt_enum = None
    try: pt_enum = sym_gen.Family.FamilyPlacementType
    except: pass
    is_wp = (pt_enum == DB.FamilyPlacementType.WorkPlaneBased)
    is_ol = (pt_enum == DB.FamilyPlacementType.OneLevelBased)
    sym_flags[sid] = (is_wp, is_ol)
    strict_hosting_mode = bool(rules.get('socket_general_require_wall_hosting', constants.DEFAULT_REQUIRE_WALL_HOSTING))
    if is_ol:
        if strict_hosting_mode:
            output.print_md(u'**Внимание:** тип розетки OneLevelBased — включена строгая проверка привязки к стене.')
        else:
            output.print_md(u'**Внимание:** тип розетки OneLevelBased — размещение будет без хоста.')

    sp_cache = {}
    pending = []
    created = 0
    boundary_opts = DB.SpatialElementBoundaryOptions()

    with adapters.create_progress_bar('01. Общие розетки...', len(rooms)) as pb:
        for i, r in enumerate(rooms):
            if pb.cancelled: break
            pb.update_progress(i, pb.max_value)

            txt_r = su._room_text(r)
            is_hallway_room = domain.is_hallway(txt_r, hallway_rx)

            allowed_path, effective_len_ft = domain.calculate_allowed_path(
                link_doc,
                r,
                boundary_opts,
                avoid_door_ft,
                openings_cache,
                window_offset_ft=window_offset_ft,
                corner_offset_ft=corner_offset_ft,
                wall_filter=wall_filter,
            )

            if effective_len_ft <= 1e-6: continue

            # Determine candidates based on room type
            room_area_sqm = 0.0
            try: room_area_sqm = r.Area * 0.092903
            except: pass

            candidates = []
            if domain.should_skip_wardrobe(room_area_sqm, txt_r, wardrobe_rx, min_area_sqm=wardrobe_skip_sqm):
                output.print_md(u'Комната: {0}; гардеробная {1:.1f} м² < {2:.1f} м² — розетки не ставятся'.format(
                    txt_r, float(room_area_sqm or 0.0), float(wardrobe_skip_sqm or 0.0)
                ))
                continue
            if is_hallway_room:
                candidates = domain.generate_candidates_hallway(allowed_path, room_area_sqm)
                try:
                    target_count = 1 if room_area_sqm <= 10.0 else 2
                except Exception:
                    target_count = len(candidates)
                summary = domain.format_room_socket_summary(
                    txt_r,
                    effective_len_ft,
                    target_count,
                    None,
                    is_hallway=True,
                    room_area_sqm=room_area_sqm,
                )
            else:
                count_len_ft = effective_len_ft
                count_breakdown = domain.new_general_breakdown()
                try:
                    _, count_len_ft = domain.calculate_allowed_path(
                        link_doc,
                        r,
                        boundary_opts,
                        0.0,
                        openings_cache,
                        window_offset_ft=0.0,
                        corner_offset_ft=0.0,
                        wall_filter=wall_filter,
                        breakdown=count_breakdown,
                    )
                except Exception:
                    count_len_ft = effective_len_ft
                    count_breakdown = None

                num, _ = domain.calc_general_socket_count_and_step_for_lengths(
                    count_len_ft,
                    effective_len_ft,
                    spacing_ft,
                )
                candidates = domain.generate_candidates_general_with_count(
                    allowed_path,
                    effective_len_ft,
                    num,
                )
                summary = domain.format_room_socket_breakdown(txt_r, count_breakdown, spacing_ft, num)

            if summary:
                output.print_md(summary)

            base_z = su._room_level_elevation_ft(r, link_doc)

            # Queue placement
            for w, pt, v in candidates:
                p_link = DB.XYZ(pt.X, pt.Y, base_z + height_ft)

                # Radiator check
                if radiator_idx and radiator_idx.has_near(p_link.X, p_link.Y, 0.0, avoid_radiator_ft):
                    continue

                # Sliding door check (avoid placing on sliding doors)
                if sliding_doors and domain.is_point_near_sliding_doors(p_link, sliding_doors, extra_ft=avoid_door_ft):
                    continue

                # Dedupe
                if idx.has_near(p_link.X, p_link.Y, p_link.Z, dedupe_ft):
                    continue

                idx.add(p_link.X, p_link.Y, p_link.Z)
                pending.append((w, p_link, v, sym_gen, 0.0))

                if len(pending) >= batch_size:
                    c0, _, _, _, _, _, _ = adapters.place_socket_batch(
                        doc,
                        link_inst,
                        t,
                        pending,
                        sym_flags,
                        sp_cache,
                        comment_value,
                        strict_hosting=strict_hosting_mode,
                        wall_search_ft=host_wall_search_ft,
                    )
                    created += c0
                    pending = []

    if pending:
        c0, _, _, _, _, _, _ = adapters.place_socket_batch(
            doc,
            link_inst,
            t,
            pending,
            sym_flags,
            sp_cache,
            comment_value,
            strict_hosting=strict_hosting_mode,
            wall_search_ft=host_wall_search_ft,
        )
        created += c0

    output.print_md(u'Готово. Создано розеток: **{0}**'.format(created))
    return created
