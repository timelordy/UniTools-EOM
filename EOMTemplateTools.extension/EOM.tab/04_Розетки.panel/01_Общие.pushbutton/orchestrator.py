# -*- coding: utf-8 -*-

import math
from pyrevit import DB, script
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

    spacing_mm = float(rules.get('socket_spacing_mm', constants.DEFAULT_SPACING_MM))
    height_mm = float(rules.get('socket_height_mm', constants.DEFAULT_HEIGHT_MM))
    avoid_door_mm = float(rules.get('avoid_door_mm', constants.AVOID_DOOR_MM))
    avoid_radiator_mm = float(rules.get('avoid_radiator_mm', constants.AVOID_RADIATOR_MM))
    dedupe_mm = float(rules.get('socket_dedupe_radius_mm', constants.DEDUPE_MM))
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    spacing_ft = mm_to_ft(spacing_mm)
    height_ft = mm_to_ft(height_mm)
    avoid_door_ft = mm_to_ft(avoid_door_mm)
    avoid_radiator_ft = mm_to_ft(avoid_radiator_mm)
    dedupe_ft = mm_to_ft(dedupe_mm)

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

    raw_rooms = adapters.get_all_linked_rooms(link_doc)

    hallway_rx = domain.compile_patterns(rules.get('hallway_room_name_patterns', constants.DEFAULT_HALLWAY_PATTERNS))
    wet_rx = domain.compile_patterns(rules.get('wet_room_name_patterns', constants.DEFAULT_WET_PATTERNS))
    kitchen_rx = domain.compile_patterns(constants.DEFAULT_KITCHEN_PATTERNS)
    exclude_rx = domain.compile_patterns(rules.get('exclude_room_name_patterns', constants.DEFAULT_EXCLUDE_PATTERNS))

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

    if not rooms:
        alert('Нет подходящих помещений (исключены кухни и санузлы).')
        return

    openings_cache = {}
    radiator_pts = adapters.collect_radiator_points(link_doc)
    radiator_idx = None
    if radiator_pts:
        radiator_idx = su._XYZIndex(cell_ft=5.0)
        for p in radiator_pts: radiator_idx.add(p.X, p.Y, 0.0)

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
    strict_hosting_mode = not is_ol
    if is_ol:
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

            allowed_path, effective_len_ft = domain.calculate_allowed_path(link_doc, r, boundary_opts, avoid_door_ft, openings_cache)

            if effective_len_ft <= 1e-6: continue

            # Determine candidates based on room type
            room_area_sqm = 0.0
            try: room_area_sqm = r.Area * 0.092903
            except: pass

            candidates = []
            if is_hallway_room:
                candidates = domain.generate_candidates_hallway(allowed_path, room_area_sqm)
            else:
                candidates = domain.generate_candidates_general(allowed_path, effective_len_ft, spacing_ft)

            base_z = su._room_level_elevation_ft(r, link_doc)

            # Queue placement
            for w, pt, v in candidates:
                p_link = DB.XYZ(pt.X, pt.Y, base_z + height_ft)

                # Radiator check
                if radiator_idx and radiator_idx.has_near(p_link.X, p_link.Y, 0.0, avoid_radiator_ft):
                    continue

                # Dedupe
                if idx.has_near(p_link.X, p_link.Y, p_link.Z, dedupe_ft):
                    continue

                idx.add(p_link.X, p_link.Y, p_link.Z)
                pending.append((w, p_link, v, sym_gen, 0.0))

                if len(pending) >= batch_size:
                    c0, _, _, _, _, _, _ = adapters.place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
                    created += c0
                    pending = []

    if pending:
        c0, _, _, _, _, _, _ = adapters.place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
        created += c0

    output.print_md(u'Готово. Создано розеток: **{0}**'.format(created))
    return created
