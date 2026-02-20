# -*- coding: utf-8 -*-

from pyrevit import DB, revit

import adapters
import constants
import domain
from utils_units import ft_to_mm
from utils_revit import ensure_symbol_active, find_nearest_level, set_comments, tx


def _collect_doors(doc, uidoc):
    doors = []
    used_selection = False
    try:
        sel_ids = list(uidoc.Selection.GetElementIds()) if uidoc else []
    except Exception:
        sel_ids = []

    if sel_ids:
        for eid in sel_ids:
            try:
                el = doc.GetElement(eid)
            except Exception:
                el = None
            if el is not None and domain.is_door(el):
                doors.append(el)
        if doors:
            used_selection = True

    if not doors:
        try:
            col = DB.FilteredElementCollector(doc)
            col = col.OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
            doors = list(col)
        except Exception:
            doors = []

    return doors, used_selection


def _collect_existing_door_ids(doc):
    existing = set()
    elems = []
    try:
        elems.extend(list(DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()))
    except Exception:
        pass
    try:
        elems.extend(list(DB.FilteredElementCollector(doc).OfClass(DB.DirectShape).WhereElementIsNotElementType()))
    except Exception:
        pass

    for e in elems:
        try:
            comment = domain.get_string_param(
                e,
                bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS,
                name='Comments'
            )
            door_id = domain.parse_door_id_from_comment(comment, constants.PLACEHOLDER_TAG)
            if door_id is not None:
                existing.add(int(door_id))
        except Exception:
            continue

    return existing


def _inc(counter, key):
    key = str(key or 'unknown')
    counter[key] = int(counter.get(key, 0)) + 1


def _push_debug(rows, line):
    if line is None:
        return
    if len(rows) >= int(constants.DEBUG_PRINT_PER_DOOR_LIMIT):
        return
    rows.append(str(line))


def _median(values):
    nums = []
    for val in values or []:
        try:
            nums.append(float(val))
        except Exception:
            continue
    if not nums:
        return None
    nums = sorted(nums)
    n = len(nums)
    mid = n // 2
    if n % 2 == 1:
        return float(nums[mid])
    return 0.5 * (float(nums[mid - 1]) + float(nums[mid]))


def _empty_result(used_selection=False, errors=0):
    return {
        'created': 0,
        'skipped': 0,
        'errors': int(errors),
        'doors_on_pgp': 0,
        'doors_on_ceramic': 0,
        'doors_on_silicate': 0,
        'doors_on_other_material': 0,
        'doors_on_non_wall_host': 0,
        'skip_reasons': {},
        'error_reasons': ({'doc_is_none': 1} if errors else {}),
        'debug_samples': [],
        'lintel_symbol': '',
        'used_selection': bool(used_selection),
        'doors_total': 0,
        'used_lintel_types': {},
        'debug_lintel_cut_z_ft': None,
        'debug_lintel_bottom_z_ft': None,
        'debug_lintel_top_z_ft': None,
        'required_lintel_families': [],
        'missing_lintel_families': [],
    }


def run(doc, output=None):
    if doc is None:
        return _empty_result(used_selection=False, errors=1)

    uidoc = revit.uidoc
    doors, used_selection = _collect_doors(doc, uidoc)
    if not doors:
        return _empty_result(used_selection=used_selection, errors=0)

    required_lintel_families = adapters.get_required_lintel_family_names()
    missing_lintel_families = adapters.find_missing_lintel_families(doc)

    lintel_symbols = adapters.find_lintel_symbols(doc)
    lintel_catalog = adapters.collect_lintel_specs(lintel_symbols)

    lintel_symbol_name = ''
    if lintel_symbols:
        lintel_symbol_name = adapters.get_symbol_display_name(lintel_symbols[0])
        if len(lintel_symbols) > 1:
            lintel_symbol_name = '{0} (+{1} types)'.format(lintel_symbol_name, int(len(lintel_symbols) - 1))

    existing_door_ids = _collect_existing_door_ids(doc)

    created = 0
    skipped = 0
    errors = 0
    doors_on_pgp = 0
    doors_on_ceramic = 0
    doors_on_silicate = 0
    doors_on_other_material = 0
    doors_on_non_wall_host = 0
    skip_reasons = {}
    error_reasons = {}
    debug_samples = []
    used_lintel_types = {}
    created_center_zs = []
    created_bottom_zs = []
    created_top_zs = []

    missing_lintel_catalog = (not bool(lintel_catalog)) and (not bool(constants.ALLOW_DIRECTSHAPE_FALLBACK))
    if missing_lintel_catalog:
        errors = max(errors, 1)
        _inc(error_reasons, 'lintel_family_not_loaded')
        missing_text = ', '.join([x for x in missing_lintel_families if x]) if missing_lintel_families else ''
        required_text = ', '.join([x for x in required_lintel_families if x]) if required_lintel_families else ''
        if missing_text:
            _push_debug(
                debug_samples,
                "Не найдены семейства перемычек: {0}. Загрузите семейства: {1}".format(missing_text, missing_text)
            )
        else:
            _push_debug(
                debug_samples,
                "Не найдены типы перемычек в настроенных семействах. Проверьте загрузку семейств: {0}".format(
                    required_text or '<не указано>'
                )
            )

    with tx('Place Lintels Above Doors'):
        activated_symbol_ids = set()

        for door in doors:
            try:
                door_id = int(door.Id.IntegerValue)
            except Exception:
                door_id = None
            door_id_txt = str(door_id) if door_id is not None else '?'

            wall = None
            try:
                wall = getattr(door, 'Host', None)
            except Exception:
                wall = None
            if wall is None or not isinstance(wall, DB.Wall):
                skipped += 1
                doors_on_non_wall_host += 1
                _inc(skip_reasons, 'non_wall_host')
                _push_debug(debug_samples, 'door={0}: skipped (non_wall_host)'.format(door_id_txt))
                continue

            wall_plan = domain.lintel_plan_for_wall(wall)
            wall_reason = str(wall_plan.get('reason', 'unknown') or 'unknown')
            wall_name = str(wall_plan.get('wall_type_name', '') or '')
            wall_thickness_mm = wall_plan.get('thickness_mm', None)
            wall_kind = str(wall_plan.get('material_kind', '') or '').lower()
            use_two_pieces = bool(wall_plan.get('is_double', False))

            if wall_kind == 'pgp':
                doors_on_pgp += 1
            elif wall_kind == 'ceramic':
                doors_on_ceramic += 1
            elif wall_kind == 'silicate':
                doors_on_silicate += 1
            else:
                doors_on_other_material += 1

            if door_id is not None and door_id in existing_door_ids:
                skipped += 1
                _inc(skip_reasons, 'already_has_lintel')
                _push_debug(debug_samples, 'door={0}: skipped (already_has_lintel)'.format(door_id_txt))
                continue

            if not bool(wall_plan.get('eligible', False)):
                skipped += 1
                _inc(skip_reasons, wall_reason)
                _push_debug(
                    debug_samples,
                    "door={0}: skipped ({1}) wall='{2}' thickness_mm={3}".format(
                        door_id_txt,
                        wall_reason,
                        wall_name,
                        round(float(wall_thickness_mm), 1) if wall_thickness_mm is not None else 'n/a'
                    )
                )
                continue

            if missing_lintel_catalog:
                skipped += 1
                _inc(skip_reasons, 'lintel_family_not_loaded')
                _push_debug(
                    debug_samples,
                    "door={0}: skipped (lintel_family_not_loaded) wall='{1}' thickness_mm={2}".format(
                        door_id_txt,
                        wall_name,
                        round(float(wall_thickness_mm), 1) if wall_thickness_mm is not None else 'n/a'
                    )
                )
                continue

            center_xy = domain.get_location_point(door)
            head_z = domain.get_door_head_z(door)
            if center_xy is None or head_z is None:
                skipped += 1
                _inc(skip_reasons, 'door_geometry_unavailable')
                _push_debug(debug_samples, 'door={0}: skipped (door_geometry_unavailable)'.format(door_id_txt))
                continue

            wall_dir, wall_norm = domain.get_wall_axes(wall)
            door_dir, door_norm = domain.get_door_axes(door, wall)

            dir_wall = wall_dir or door_dir
            dir_norm = wall_norm or door_norm
            if dir_wall is None or dir_norm is None:
                skipped += 1
                _inc(skip_reasons, 'door_axes_unavailable')
                _push_debug(debug_samples, 'door={0}: skipped (door_axes_unavailable)'.format(door_id_txt))
                continue

            door_width_ft = domain.get_door_width_ft(door)
            if door_width_ft is None:
                door_width_ft = constants.DEFAULT_OPENING_WIDTH_FT
            door_height_ft = domain.get_door_height_ft(door)

            lintel_spec = domain.pick_lintel_spec_from_catalog(lintel_catalog, wall_plan, door_width_ft, door_height_ft)
            if lintel_spec is None:
                lintel_spec = domain.fallback_lintel_spec(door_width_ft, wall_plan=wall_plan)
                lintel_spec['count'] = 2 if use_two_pieces else 1

            spec_ft = domain.lintel_spec_to_ft(lintel_spec)
            lintel_mark = str(spec_ft.get('mark', '') or '')
            lintel_family_name = str(spec_ft.get('family_name', '') or '')
            lintel_count = int(spec_ft.get('count', 2 if use_two_pieces else 1) or (2 if use_two_pieces else 1))
            lintel_length_ft = float(spec_ft.get('length_ft', constants.LINTEL_WIDTH_FT))
            lintel_trim_length_ft = float(spec_ft.get('trim_length_ft', lintel_length_ft))
            lintel_width_ft = float(spec_ft.get('width_ft', constants.LINTEL_WIDTH_FT))
            lintel_height_ft = float(spec_ft.get('height_ft', constants.LINTEL_HEIGHT_FT))
            lintel_gap_ft = float(constants.LINTEL_GAP_ABOVE_OPENING_FT)
            lintel_used_length_ft = lintel_length_ft

            symbol_for_door = lintel_spec.get('symbol', None)
            if symbol_for_door is None:
                symbol_for_door = adapters.pick_lintel_symbol(
                    lintel_symbols,
                    lintel_length_ft,
                    mark=lintel_mark,
                    preferred_family_name=lintel_family_name
                )
            symbol_for_door_name = adapters.get_symbol_display_name(symbol_for_door) if symbol_for_door else ''

            if symbol_for_door is None and (not constants.ALLOW_DIRECTSHAPE_FALLBACK):
                errors += 1
                _inc(error_reasons, 'lintel_symbol_not_found_for_door')
                _push_debug(debug_samples, 'door={0}: error (lintel_symbol_not_found_for_door)'.format(door_id_txt))
                continue

            try:
                if wall.Width and float(wall.Width) > 0:
                    lintel_width_ft = min(lintel_width_ft, float(wall.Width))
            except Exception:
                pass

            lintel_bottom_z = float(head_z) + lintel_gap_ft
            c = DB.XYZ(float(center_xy.X), float(center_xy.Y), lintel_bottom_z + lintel_height_ft * 0.5)

            placed = None
            if symbol_for_door is not None:
                try:
                    sid = int(symbol_for_door.Id.IntegerValue)
                except Exception:
                    sid = None
                if sid is not None and sid not in activated_symbol_ids:
                    ensure_symbol_active(doc, symbol_for_door)
                    activated_symbol_ids.add(sid)

                level = find_nearest_level(doc, c.Z)
                inst = adapters.create_family_instance(doc, symbol_for_door, c, level=level, host=wall)
                if inst is not None:
                    adapters.rotate_element_to_direction(doc, inst, c, dir_wall)
                    if wall_kind == 'pgp':
                        if adapters.set_instance_length(inst, lintel_trim_length_ft):
                            lintel_used_length_ft = float(lintel_trim_length_ft)
                        else:
                            lintel_used_length_ft = float(lintel_length_ft)
                    else:
                        if adapters.set_instance_length(inst, lintel_length_ft):
                            lintel_used_length_ft = float(lintel_length_ft)
                    if wall_kind == 'pgp':
                        adapters.align_element_to_target(doc, inst, target_center=c, target_bottom_z=None)
                        host_wall_width_ft = None
                        try:
                            host_wall_width_ft = float(wall.Width)
                        except Exception:
                            host_wall_width_ft = None
                        adapters.set_instance_pa_pgp_offsets(
                            inst,
                            elevation_ft=lintel_bottom_z,
                            host_wall_width_ft=host_wall_width_ft
                        )
                    else:
                        adapters.align_element_to_target(doc, inst, target_center=c, target_bottom_z=lintel_bottom_z)
                    adapters.set_instance_piece_flags(inst, use_two_pieces=use_two_pieces)
                    adapters.try_join_and_cut_with_wall(
                        doc,
                        wall,
                        inst,
                        force=(wall_kind == 'pgp'),
                        allow_cut=False
                    )
                    placed = inst

            if placed is None and constants.ALLOW_DIRECTSHAPE_FALLBACK:
                solid = adapters.make_lintel_solid(
                    c, dir_wall, dir_norm, lintel_length_ft, lintel_width_ft, lintel_height_ft
                )
                if solid is not None:
                    placed = adapters.create_directshape(doc, solid, name=constants.PLACEHOLDER_TAG)

            if placed is None:
                errors += 1
                _inc(error_reasons, 'lintel_instance_create_failed')
                continue

            try:
                length_mm = ft_to_mm(lintel_length_ft)
                if wall_kind == 'pgp':
                    length_mm = ft_to_mm(lintel_used_length_ft)
                width_mm = ft_to_mm(lintel_width_ft)
                height_mm = ft_to_mm(lintel_height_ft)
                comment = domain.build_comment(
                    constants.PLACEHOLDER_TAG, door_id or 0, lintel_count, length_mm, width_mm, height_mm
                )
                set_comments(placed, comment)
            except Exception:
                pass

            created += 1
            try:
                used_lintel_types[symbol_for_door_name or lintel_mark or '?'] = int(
                    used_lintel_types.get(symbol_for_door_name or lintel_mark or '?', 0)
                ) + 1
            except Exception:
                pass

            try:
                bottom_z = float(lintel_bottom_z)
                top_z = float(lintel_bottom_z) + float(lintel_height_ft)
                center_z = float(c.Z)
                created_bottom_zs.append(bottom_z)
                created_top_zs.append(top_z)
                created_center_zs.append(center_z)
            except Exception:
                pass

            _push_debug(
                debug_samples,
                "door={0}: created=1 ({1}) wall='{2}' thickness_mm={3} wall_kind='{4}' piece_mode='{5}' door_w_mm={6} door_h_mm={7} mark='{8}' symbol='{9}' req_len_mm={10} z_bot_mm={11} z_top_mm={12} z_ctr_mm={13}".format(
                    door_id_txt,
                    wall_reason,
                    wall_name,
                    round(float(wall_thickness_mm), 1) if wall_thickness_mm is not None else 'n/a',
                    wall_kind or 'n/a',
                    '2шт' if use_two_pieces else '1шт',
                    round(float(ft_to_mm(door_width_ft)), 1) if door_width_ft is not None else 'n/a',
                    round(float(ft_to_mm(door_height_ft)), 1) if door_height_ft is not None else 'n/a',
                    lintel_mark or '?',
                    symbol_for_door_name or '?',
                    round(float(ft_to_mm(lintel_used_length_ft if wall_kind == 'pgp' else lintel_length_ft)), 1),
                    round(float(ft_to_mm(lintel_bottom_z)), 1),
                    round(float(ft_to_mm(lintel_bottom_z + lintel_height_ft)), 1),
                    round(float(ft_to_mm(lintel_bottom_z + lintel_height_ft * 0.5)), 1)
                )
            )

    cut_z_ft = _median(created_center_zs)
    bottom_z_ft = min(created_bottom_zs) if created_bottom_zs else None
    top_z_ft = max(created_top_zs) if created_top_zs else None

    return {
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'doors_on_pgp': doors_on_pgp,
        'doors_on_ceramic': doors_on_ceramic,
        'doors_on_silicate': doors_on_silicate,
        'doors_on_other_material': doors_on_other_material,
        'doors_on_non_wall_host': doors_on_non_wall_host,
        'skip_reasons': skip_reasons,
        'error_reasons': error_reasons,
        'debug_samples': debug_samples,
        'lintel_symbol': lintel_symbol_name,
        'used_selection': used_selection,
        'doors_total': len(doors),
        'used_lintel_types': used_lintel_types,
        'debug_lintel_cut_z_ft': cut_z_ft,
        'debug_lintel_bottom_z_ft': bottom_z_ft,
        'debug_lintel_top_z_ft': top_z_ft,
        'required_lintel_families': required_lintel_families,
        'missing_lintel_families': missing_lintel_families,
    }
