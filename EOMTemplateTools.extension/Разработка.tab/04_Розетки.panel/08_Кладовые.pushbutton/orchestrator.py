# -*- coding: utf-8 -*-

import math
import re
from pyrevit import DB, forms, script
import link_reader
import magic_context
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
from utils_units import mm_to_ft, ft_to_mm


def alert(msg):
    """Показывает alert диалог"""
    try:
        forms.alert(msg)
    except Exception:
        pass


def compile_patterns(patterns):
    """Компилирует regex паттерны"""
    try:
        if not patterns:
            return None
        rx = [re.compile(p, re.IGNORECASE) for p in patterns]
        return rx
    except Exception:
        return None


def match_any(patterns, text):
    """Проверяет совпадение текста с любым паттерном"""
    try:
        if not patterns or not text:
            return False
        text_lower = str(text).lower()
        for p in patterns:
            if p.search(text_lower):
                return True
        return False
    except Exception:
        return False


def room_text(room):
    """Получает текст помещения для фильтрации"""
    try:
        name = room.Name
        if name:
            return name
        number = room.Number
        if number:
            return str(number)
        return ""
    except Exception:
        return ""


def run(doc, output):
    output.print_md('# 08. Кладовые: Расстановка оборудования')

    rules = adapters.get_rules()
    cfg = adapters.get_config()

    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    comment_value_panel = '{0}{1}:PANEL'.format(comment_tag, constants.COMMENT_SUFFIX)
    comment_value_switch = '{0}{1}:SWITCH'.format(comment_tag, constants.COMMENT_SUFFIX)
    comment_value_light = '{0}{1}:LIGHT'.format(comment_tag, constants.COMMENT_SUFFIX)

    panel_height_ft = mm_to_ft(rules.get('storage_panel_height_mm', constants.DEFAULT_PANEL_HEIGHT_MM))
    switch_height_ft = mm_to_ft(rules.get('storage_switch_height_mm', constants.DEFAULT_SWITCH_HEIGHT_MM))
    light_height_ft = mm_to_ft(rules.get('storage_light_height_mm', constants.DEFAULT_LIGHT_HEIGHT_MM))
    dedupe_ft = mm_to_ft(int(rules.get('dedupe_radius_mm', constants.DEFAULT_DEDUPE_MM) or constants.DEFAULT_DEDUPE_MM))
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    validate_match_tol_ft = mm_to_ft(int(rules.get('storage_validate_match_tol_mm', constants.DEFAULT_VALIDATE_MATCH_TOL_MM) or constants.DEFAULT_VALIDATE_MATCH_TOL_MM))
    validate_height_tol_ft = mm_to_ft(int(rules.get('storage_validate_height_tol_mm', constants.DEFAULT_VALIDATE_HEIGHT_TOL_MM) or constants.DEFAULT_VALIDATE_HEIGHT_TOL_MM))

    # Выбираем семейства
    light_sym, light_lbl = adapters.pick_storage_light_symbol(doc, cfg, rules)
    if not light_sym:
        alert('Не найден тип светильника. Загрузите семейство/тип в проект и повторите.')
        return

    switch_sym, switch_lbl = adapters.pick_switch_symbol(doc, cfg, rules)
    if not switch_sym:
        alert('Не найден тип выключателя. Загрузите семейство/тип в проект и повторите.')
        return

    panel_sym, panel_lbl = adapters.pick_panel_symbol(doc, cfg, rules)
    if not panel_sym:
        alert('Не найден тип щитка. Загрузите семейство/тип в проект и повторите.')
        return

    try:
        su._store_symbol_id(cfg, 'last_storage_light_symbol_id', light_sym)
        su._store_symbol_unique_id(cfg, 'last_storage_light_symbol_uid', light_sym)
        su._store_symbol_id(cfg, 'last_storage_switch_symbol_id', switch_sym)
        su._store_symbol_unique_id(cfg, 'last_storage_switch_symbol_uid', switch_sym)
        su._store_symbol_id(cfg, 'last_storage_panel_symbol_id', panel_sym)
        su._store_symbol_unique_id(cfg, 'last_storage_panel_symbol_uid', panel_sym)
        adapters.save_config()
    except Exception:
        pass

    force_selection = bool(getattr(magic_context, 'FORCE_SELECTION', False))
    link_inst = getattr(magic_context, 'SELECTED_LINK', None) if force_selection else None
    if link_inst is None:
        link_inst = link_reader.select_link_instance(doc)
    if not link_inst:
        return {}
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc:
        return {}

    selected_levels = list(getattr(magic_context, 'SELECTED_LEVELS', []) or []) if force_selection else []
    if not selected_levels:
        selected_levels = link_reader.select_levels_multi(
            link_doc,
            title=u'Выберите уровни для обработки',
            default_all=False
        )
    if not selected_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
        return {}

    selected_level_ids = set()
    for lvl in selected_levels:
        try:
            selected_level_ids.add(int(lvl.Id.IntegerValue))
        except Exception:
            continue
    if not selected_level_ids:
        output.print_md('**Отменено (уровни не выбраны).**')
        return {}

    t = adapters.get_total_transform(link_inst)

    raw_rooms = adapters.get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 5000) or 5000))
    storage_rx = compile_patterns(rules.get('storage_room_name_patterns') or constants.DEFAULT_STORAGE_ROOM_PATTERNS)

    rooms = []
    for r in raw_rooms:
        try:
            try:
                if int(r.LevelId.IntegerValue) not in selected_level_ids:
                    continue
            except Exception:
                continue
            if storage_rx and (not match_any(storage_rx, room_text(r))):
                continue
            rooms.append(r)
        except Exception:
            continue

    if not rooms:
        alert('Не найдено помещений кладовых (по паттернам).')
        return {}

    output.print_md('Найдено помещений кладовых: **{0}** (из {1} всего отсканировано)'.format(
        len(rooms), len(raw_rooms)
    ))

    # Получаем существующие элементы для дедупликации
    try:
        ids_before_panel, _, existing_pts_panel = adapters.collect_tagged_instances(doc, comment_value_panel)
        ids_before_switch, _, existing_pts_switch = adapters.collect_tagged_instances(doc, comment_value_switch)
        ids_before_light, _, existing_pts_light = adapters.collect_tagged_instances(doc, comment_value_light)
    except Exception:
        ids_before_panel = ids_before_switch = ids_before_light = set()
        existing_pts_panel = existing_pts_switch = existing_pts_light = []

    # Проверяем свойства семейств
    sym_flags = {}
    for sym_id, sym in [(int(light_sym.Id.IntegerValue), light_sym),
                         (int(switch_sym.Id.IntegerValue), switch_sym),
                         (int(panel_sym.Id.IntegerValue), panel_sym)]:
        try:
            pt = sym.Family.FamilyPlacementType
            is_wp = (pt == DB.FamilyPlacementType.WorkPlaneBased)
            is_ol = (pt == DB.FamilyPlacementType.OneLevelBased)
            sym_flags[sym_id] = (is_wp, is_ol)
        except Exception:
            sym_flags[sym_id] = (False, False)

    pending_panel = []
    pending_switch = []
    pending_light = []

    plans = []

    created_panel = created_switch = created_light = 0
    skipped = 0
    skip_no_door = 0
    skip_no_wall = 0
    skip_dup_panel = skip_dup_switch = skip_dup_light = 0

    with DB.Transaction(doc, 'Storage Room Equipment Placement') as trans:
        trans.Start()

        for room in rooms:
            base_z = su._room_level_elevation_ft(room, link_doc)
            room_center = domain.get_room_center(room)

            # Получаем двери в помещении
            doors = domain.get_doors_in_room(room, link_doc)

            if not doors:
                skipped += 1
                skip_no_door += 1
                continue

            # Берем первую дверь
            door_pt = domain.get_element_location_point(doors[0])

            # Получаем сегменты стен
            segs = domain.get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                skip_no_wall += 1
                continue

            # 1. Щиток - размещаем в центре помещения на высоте 1700мм
            panel_pt_link = DB.XYZ(float(room_center.X), float(room_center.Y), float(base_z) + float(panel_height_ft))
            panel_pt_host = t.OfPoint(panel_pt_link) if t else panel_pt_link

            # Проверяем дедупликацию
            has_dup = False
            if existing_pts_panel and dedupe_ft and dedupe_ft > 1e-9:
                for ep in existing_pts_panel:
                    try:
                        if ep.DistanceTo(panel_pt_host) <= dedupe_ft:
                            has_dup = True
                            break
                    except Exception:
                        continue

            if has_dup:
                skip_dup_panel += 1
            else:
                pending_panel.append((None, panel_pt_link, DB.XYZ(1, 0, 0), panel_sym, 1000))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': room_text(room),
                    'type': 'panel',
                    'expected_pt_host': panel_pt_host,
                })

            # 2. Выключатель - размещаем у двери на высоте 900мм
            # Находим ближайшую стену к двери
            switch_seg, switch_proj, _ = domain.nearest_segment(door_pt, segs)

            if switch_seg and switch_proj:
                # Выключатель размещаем на высоте 900мм
                switch_pt_link = DB.XYZ(float(switch_proj.X), float(switch_proj.Y), float(base_z) + float(switch_height_ft))
                switch_pt_host = t.OfPoint(switch_pt_link) if t else switch_pt_link

                has_dup = False
                if existing_pts_switch and dedupe_ft and dedupe_ft > 1e-9:
                    for ep in existing_pts_switch:
                        try:
                            if ep.DistanceTo(switch_pt_host) <= dedupe_ft:
                                has_dup = True
                                break
                        except Exception:
                            continue

                if has_dup:
                    skip_dup_switch += 1
                else:
                    pending_switch.append((None, switch_pt_link, DB.XYZ(1, 0, 0), switch_sym, 1000))
                    plans.append({
                        'room_id': int(room.Id.IntegerValue),
                        'room_name': room_text(room),
                        'type': 'switch',
                        'expected_pt_host': switch_pt_host,
                    })

            # 3. Светильник - размещаем в центре помещения на высоте 2700мм
            light_pt_link = DB.XYZ(float(room_center.X), float(room_center.Y), float(base_z) + float(light_height_ft))
            light_pt_host = t.OfPoint(light_pt_link) if t else light_pt_link

            has_dup = False
            if existing_pts_light and dedupe_ft and dedupe_ft > 1e-9:
                for ep in existing_pts_light:
                    try:
                        if ep.DistanceTo(light_pt_host) <= dedupe_ft:
                            has_dup = True
                            break
                    except Exception:
                        continue

            if has_dup:
                skip_dup_light += 1
            else:
                pending_light.append((None, light_pt_link, DB.XYZ(1, 0, 0), light_sym, 1000))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': room_text(room),
                    'type': 'light',
                    'expected_pt_host': light_pt_host,
                })

            # Батчинг
            if len(pending_panel) >= batch_size:
                c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                    doc, link_inst, t, pending_panel, sym_flags, {}, comment_value_panel, strict_hosting=False
                )
                created_panel += int(c)
                pending_panel = []

            if len(pending_switch) >= batch_size:
                c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                    doc, link_inst, t, pending_switch, sym_flags, {}, comment_value_switch, strict_hosting=False
                )
                created_switch += int(c)
                pending_switch = []

            if len(pending_light) >= batch_size:
                c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                    doc, link_inst, t, pending_light, sym_flags, {}, comment_value_light, strict_hosting=False
                )
                created_light += int(c)
                pending_light = []

        # Создаем оставшиеся элементы
        if pending_panel:
            c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                doc, link_inst, t, pending_panel, sym_flags, {}, comment_value_panel, strict_hosting=False
            )
            created_panel += int(c)

        if pending_switch:
            c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                doc, link_inst, t, pending_switch, sym_flags, {}, comment_value_switch, strict_hosting=False
            )
            created_switch += int(c)

        if pending_light:
            c, _cf, _cwp, _cpt, _snf, _snp, _cver = su._place_socket_batch(
                doc, link_inst, t, pending_light, sym_flags, {}, comment_value_light, strict_hosting=False
            )
            created_light += int(c)

        trans.Commit()

    # Отчет
    output.print_md(
        'Светильник: **{0}**\nВыключатель: **{1}**\nЩиток: **{2}**\n\n'
        'Помещений обработано: **{3}**\n'
        'Создано: Щитков={4}, Выключателей={5}, Светильников={6}\n'
        'Пропущено: всего={7} (нет дверей={8}, нет стен={9})\n'
        'Дубликаты: Щитков={10}, Выключателей={11}, Светильников={12}'.format(
            light_lbl or '<Светильник>',
            switch_lbl or '<Выключатель>',
            panel_lbl or '<Щиток>',
            len(rooms),
            created_panel, created_switch, created_light,
            skipped, skip_no_door, skip_no_wall,
            skip_dup_panel, skip_dup_switch, skip_dup_light
        )
    )

    # Валидация
    if plans and (created_panel or created_switch or created_light):
        validation_results = validate_created_elements(doc, plans, comment_value_panel, comment_value_switch, comment_value_light, validate_match_tol_ft, validate_height_tol_ft, t)

        if validation_results:
            ok_count = len([x for x in validation_results if x.get('status') == 'ok'])
            fail_count = len([x for x in validation_results if x.get('status') == 'fail'])
            missing_count = len([x for x in validation_results if x.get('status') == 'missing'])

            output.print_md('\nПроверка: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(ok_count, fail_count, missing_count))

            if fail_count or missing_count:
                output.print_md('Нарушения:')
                for x in validation_results:
                    st = x.get('status')
                    if st == 'ok':
                        continue
                    rnm = x.get('room_name')
                    typ = x.get('type')
                    if st == 'missing':
                        output.print_md('- {0} в {1}: не найден созданный экземпляр'.format(typ, rnm))
                    else:
                        output.print_md('- {0} в {1}: position={2}, height={3}'.format(
                            typ, rnm,
                            x.get('position_ok', False),
                            x.get('height_ok', False)
                        ))

    # Возвращаем статистику по комнатам
    result = {}
    for r in rooms:
        r_id = int(r.Id.IntegerValue)
        result[r_id] = {
            'room_name': room_text(r),
            'created': False
        }
        # Проверяем созданы ли элементы для этой комнаты
        for pl in plans:
            if pl.get('room_id') == r_id:
                result[r_id]['created'] = True
                break

    return result


def validate_created_elements(doc, plans, comment_panel, comment_switch, comment_light, match_tol, height_tol, t):
    """Валидирует созданные элементы"""
    try:
        validation = []

        # Собираем все созданные элементы
        ids_after_panel, elems_panel, _ = adapters.collect_tagged_instances(doc, comment_panel)
        ids_after_switch, elems_switch, _ = adapters.collect_tagged_instances(doc, comment_switch)
        ids_after_light, elems_light, _ = adapters.collect_tagged_instances(doc, comment_light)

        all_elems = elems_panel + elems_switch + elems_light

        # Создаем словарь элементов по точкам
        elem_items = []
        for e in all_elems:
            pt = adapters.get_element_center_point(e)
            if pt:
                elem_items.append((e, pt))

        for pl in plans:
            best = None
            best_dist = None

            for e, pt in elem_items:
                dist = domain.dist_xy(pt, pl['expected_pt_host'])
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best = (e, pt)

            if best is None or (match_tol and best_dist > match_tol):
                validation.append({
                    'status': 'missing',
                    'room_name': pl.get('room_name'),
                    'type': pl.get('type'),
                })
                continue

            elem, inst_pt = best
            height_ok = (abs(float(inst_pt.Z) - float(pl['expected_pt_host'].Z)) <= float(height_tol or mm_to_ft(20)))
            position_ok = (best_dist <= float(match_tol or mm_to_ft(2000)))

            validation.append({
                'status': 'ok' if (height_ok and position_ok) else 'fail',
                'room_name': pl.get('room_name'),
                'type': pl.get('type'),
                'height_ok': height_ok,
                'position_ok': position_ok,
            })

        return validation
    except Exception:
        return []
