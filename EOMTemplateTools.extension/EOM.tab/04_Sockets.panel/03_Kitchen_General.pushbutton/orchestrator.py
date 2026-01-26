# -*- coding: utf-8 -*-

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
from utils_units import mm_to_ft


def run(doc, output):
    output.print_md('# 03. Кухня: Общие (по периметру, 300мм)')

    rules = adapters.get_rules()
    cfg = adapters.get_config()

    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value = '{0}{1}'.format(comment_tag, constants.COMMENT_SUFFIX)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or constants.DEFAULT_KITCHEN_PATTERNS
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    unit_margin_mm = float(rules.get('kitchen_unit_margin_mm', constants.KITCHEN_UNIT_MARGIN_MM) or constants.KITCHEN_UNIT_MARGIN_MM)
    unit_margin_ft = mm_to_ft(unit_margin_mm)

    spacing_mm = float(rules.get('kitchen_general_spacing_mm', constants.SPACING_MM) or constants.SPACING_MM)
    spacing_ft = mm_to_ft(spacing_mm)

    height_mm = int(rules.get('kitchen_general_height_mm', constants.DEFAULT_HEIGHT_MM) or constants.DEFAULT_HEIGHT_MM)
    height_ft = mm_to_ft(height_mm)

    avoid_door_mm = float(rules.get('kitchen_avoid_door_mm', constants.AVOID_DOOR_MM) or constants.AVOID_DOOR_MM)
    avoid_door_ft = mm_to_ft(avoid_door_mm)

    avoid_window_mm = float(rules.get('kitchen_avoid_window_mm', constants.AVOID_WINDOW_MM) or constants.AVOID_WINDOW_MM)
    avoid_window_ft = mm_to_ft(avoid_window_mm)

    wall_end_clear_mm = float(rules.get('kitchen_wall_end_clear_mm', constants.WALL_END_CLEAR_MM) or constants.WALL_END_CLEAR_MM)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    dedupe_mm = float(rules.get('socket_dedupe_radius_mm', constants.DEDUPE_MM) or constants.DEDUPE_MM)
    dedupe_ft = mm_to_ft(dedupe_mm)

    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    fams = rules.get('family_type_names', {})
    prefer = (
        fams.get('socket_kitchen_general')
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
            output.print_md(u'**Внимание:** тип розетки OneLevel/WorkPlane.')
        else:
            alert('Не найден тип розетки для кухни.')
            if top10:
                output.print_md('Доступные варианты:')
                for x in top10:
                    output.print_md('- {0}'.format(x))
            return

    try:
        su._store_symbol_id(cfg, 'last_socket_kitchen_general_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_general_symbol_uid', sym)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, 'Выберите связь АР')
    if not link_inst: return
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc: return

    t = adapters.get_total_transform(link_inst)
    try:
        t_inv = t.Inverse if t else None
    except Exception:
        t_inv = None

    raw_rooms = adapters.get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 500) or 500))
    rooms = []
    for r in (raw_rooms or []):
        txt = su._room_text(r)
        if kitchen_rx and su._match_any(kitchen_rx, txt):
            rooms.append(r)
    if not rooms:
        alert('Нет помещений кухни (по паттернам).')
        return

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
    except Exception:
        pass

    sp_cache = {}
    openings_cache = {}
    pending = []

    created = created_face = created_wp = created_pt = 0
    skipped = 0

    idx = su._XYZIndex(cell_ft=5.0)

    with forms.ProgressBar(title='03. Кухня (общие)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            unit_bboxes = domain.collect_kitchen_unit_bboxes(link_doc, room, None)

            allowed_path, effective_len_ft = domain.calculate_allowed_path(
                link_doc, room, avoid_door_ft, avoid_window_ft, openings_cache, unit_bboxes, unit_margin_ft
            )

            if effective_len_ft <= 1e-6:
                skipped += 1
                continue

            candidates = domain.generate_candidates(allowed_path, effective_len_ft, spacing_ft, wall_end_clear_ft)

            if not candidates:
                skipped += 1
                continue

            base_z = su._room_level_elevation_ft(room, link_doc)

            for wall, pt, v in candidates:
                p_link = DB.XYZ(float(pt.X), float(pt.Y), float(base_z) + float(height_ft))

                if idx.has_near(float(p_link.X), float(p_link.Y), float(p_link.Z), float(dedupe_ft)):
                    continue
                idx.add(float(p_link.X), float(p_link.Y), float(p_link.Z))

                pending.append((wall, p_link, v, sym, 0.0))

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

    output.print_md(
        'Тип: **{0}**\n\nШаг: **{1}м** | Высота: **{2}мм**\n\nСоздано: **{3}** (Face: {4}, WP: {5}, Pt: {6})\nПропущено комнат: **{7}**'.format(
            sym_lbl or u'<Розетка>',
            int(spacing_mm / 1000),
            int(height_mm),
            created, created_face, created_wp, created_pt,
            skipped
        )
    )
