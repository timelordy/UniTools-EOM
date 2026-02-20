# -*- coding: utf-8 -*-
"""Расстановка выключателей в квартирах.

Требования:
- Высота установки 900мм
- Со стороны дверной ручки
- Спальня/гостиная: 2-клавишный, остальное: 1-клавишный
- Санузлы/ванные: выключатель в прихожей (снаружи)
- Остальные комнаты: выключатель внутри комнаты
"""
import math
import os
import sys

# pyRevit reuses IronPython engine; modules with generic names (adapters/constants/domain)
# can stay cached from another command. Force local modules from this pushbutton folder.
_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BUNDLE_DIR not in sys.path:
    sys.path.insert(0, _BUNDLE_DIR)


def _drop_foreign_module(module_name):
    mod = sys.modules.get(module_name)
    if mod is None:
        return

    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        try:
            del sys.modules[module_name]
        except Exception:
            pass
        return

    try:
        mod_dir = os.path.dirname(os.path.abspath(mod_file))
    except Exception:
        mod_dir = None

    if mod_dir != _BUNDLE_DIR:
        try:
            del sys.modules[module_name]
        except Exception:
            pass


for _module_name in (
    "adapters",
    "adapters_doors",
    "adapters_geometry",
    "adapters_outlets",
    "adapters_symbols",
    "adapters_switches",
    "constants",
    "domain",
):
    _drop_foreign_module(_module_name)

from pyrevit import DB, forms, revit, script
from time_savings import report_time_saved
try:
    import socket_utils as su
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su

from adapters import (
    calc_switch_position,
    calc_switch_position_from_separation_line,
    get_closest_level,
    get_door_info,
    get_room_name,
    get_room_separation_lines,
    get_switch_symbol,
    is_entrance_door,
    place_switch,
    prefer_farther_candidate,
)
from constants import (
    COMMENT_TAG,
    CORRIDOR_ROOMS,
    NON_APARTMENT_ROOMS,
    SKIP_ROOMS,
    SWITCH_1G_TYPE_ID,
    SWITCH_2G_TYPE_ID,
    TWO_GANG_ROOMS,
    WET_ROOMS,
)
from domain import contains_any, ft_to_mm


def main():
    import link_reader
    import magic_context

    if (not bool(getattr(magic_context, 'FORCE_SELECTION', False))
            and not bool(getattr(magic_context, 'IS_RUNNING', False))):
        doc = revit.doc
        output = script.get_output()
        pairs = link_reader.select_link_level_pairs(
            doc,
            link_title=u'Выберите связь(и) АР',
            level_title=u'Выберите этажи',
            default_all_links=True,
            default_all_levels=False,
            loaded_only=True
        )
        if not pairs:
            output.print_md('**Отменено (связи/уровни не выбраны).**')
            return 0

        total_created = 0
        old_force = bool(getattr(magic_context, 'FORCE_SELECTION', False))
        old_link = getattr(magic_context, 'SELECTED_LINK', None)
        old_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
        old_levels = list(getattr(magic_context, 'SELECTED_LEVELS', []) or [])
        try:
            for pair in pairs:
                link_inst = pair.get('link_instance')
                levels = list(pair.get('levels') or [])
                if link_inst is None or not levels:
                    continue

                try:
                    link_name = link_inst.Name
                except Exception:
                    link_name = u'<Связь>'
                output.print_md(u'## Обработка связи: `{0}`'.format(link_name))

                magic_context.FORCE_SELECTION = True
                magic_context.SELECTED_LINK = link_inst
                magic_context.SELECTED_LINKS = [link_inst]
                magic_context.SELECTED_LEVELS = levels

                total_created += int(main() or 0)
        finally:
            magic_context.FORCE_SELECTION = old_force
            magic_context.SELECTED_LINK = old_link
            magic_context.SELECTED_LINKS = old_links
            magic_context.SELECTED_LEVELS = old_levels

        output.print_md(u'---')
        output.print_md(u'Итог по выбранным связям: **{}** выключателей'.format(total_created))
        return total_created

    doc = revit.doc
    output = script.get_output()
    output.print_md(u"# Размещение выключателей")

    link_inst = link_reader.select_link_instance_auto(doc)
    if not link_inst:
        forms.alert(u"Связь АР не найдена", exitscript=True)
        return

    link_doc = link_inst.GetLinkDocument()
    if not link_doc:
        forms.alert(u"Связь не загружена", exitscript=True)
        return

    link_transform = link_inst.GetTotalTransform()

    # Select Levels
    selected_levels = link_reader.select_levels_multi(link_doc, title=u"Выберите этажи")
    if not selected_levels:
        return

    selected_level_ids = {l.Id.IntegerValue for l in selected_levels}

    sym_1g = get_switch_symbol(doc, two_gang=False)
    sym_2g = get_switch_symbol(doc, two_gang=True)

    if not sym_1g:
        forms.alert(
            u"Не найден тип 1-кл выключателя.\n"
            u"Загрузите подходящее семейство или укажите тип в config/rules.default.json "
            u"(family_type_names.switch_1g).",
            exitscript=True
        )
        return
    if not sym_2g:
        sym_2g = sym_1g

    try:
        name_1g = sym_1g.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except Exception:
        name_1g = str(sym_1g.Id.IntegerValue)
    try:
        name_2g = sym_2g.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except Exception:
        name_2g = str(sym_2g.Id.IntegerValue)

    output.print_md(u"- 1-кл: `{}`".format(name_1g))
    output.print_md(u"- 2-кл: `{}`".format(name_2g))

    rooms = [r for r in DB.FilteredElementCollector(link_doc)
             .OfCategory(DB.BuiltInCategory.OST_Rooms)
             if r.Area > 0 and r.LevelId.IntegerValue in selected_level_ids]

    doors = list(DB.FilteredElementCollector(link_doc)
                 .OfCategory(DB.BuiltInCategory.OST_Doors)
                 .WhereElementIsNotElementType())

    output.print_md(u"- Комнат: **{}**, дверей: **{}**".format(len(rooms), len(doors)))

    room_to_doors = {}
    for door in doors:
        info = get_door_info(door, link_doc, link_transform)
        for room in [info["from_room"], info["to_room"]]:
            if room and room.Id.IntegerValue not in room_to_doors:
                room_to_doors[room.Id.IntegerValue] = []
            if room:
                room_to_doors[room.Id.IntegerValue].append((door, info))

    created = 0
    skipped = 0

    # Дедупликация внутри запуска: один выключатель на одну комнату
    # (ключ: link_instance_id::room_id). Это исключает случай, когда в выборку rooms
    # попали дублирующиеся записи одной и той же комнаты.
    processed_room_keys = set()

    with DB.Transaction(doc, u"ЭОМ: Выключатели") as t:
        t.Start()

        for room in rooms:
            room_name = get_room_name(room)
            room_id = room.Id.IntegerValue

            # 1 room = 1 switch (dedupe by stable key)
            room_key = None
            try:
                room_key = u"{}::{}".format(link_inst.Id.IntegerValue, room_id)
            except Exception:
                room_key = None
            if room_key and room_key in processed_room_keys:
                continue

            if contains_any(room_name, SKIP_ROOMS):
                if room_key:
                    processed_room_keys.add(room_key)
                continue

            # Пропускаем общедомовые помещения (не квартирные)
            if contains_any(room_name, NON_APARTMENT_ROOMS):
                if room_key:
                    processed_room_keys.add(room_key)
                continue

            is_corridor = contains_any(room_name, CORRIDOR_ROOMS)
            
            # Проверяем наличие дверей
            has_doors = room_id in room_to_doors and room_to_doors[room_id]
            
            # Флаг для использования Room Separation Line
            use_separation_line = False
            sep_line_info = None
            
            if not has_doors:
                # Нет дверей - пробуем найти Room Separation Line
                sep_lines = get_room_separation_lines(link_doc, room, link_transform)
                if sep_lines:
                    # Берём первую (или самую длинную) линию
                    sep_line_info = max(sep_lines, key=lambda x: x["line_length"])
                    use_separation_line = True
                else:
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                    continue
            
            door_list = room_to_doors.get(room_id, [])

            # Если используем Room Separation Line (нет дверей)
            if use_separation_line:
                is_wet = contains_any(room_name, WET_ROOMS)
                is_two_gang = contains_any(room_name, TWO_GANG_ROOMS)
                best_info = None  # Нет двери

                symbol = sym_2g if is_two_gang else sym_1g

                point, rotation = calc_switch_position_from_separation_line(
                    sep_line_info, room, link_transform, link_doc, place_inside_room=(not is_wet)
                )

                if created < 3 or "кухн" in room_name.lower():
                    output.print_md(u"")
                    output.print_md(u"**{}** (via Room Separation Line)".format(room_name))
                    output.print_md(u"  line length: {:.0f}mm".format(ft_to_mm(sep_line_info["line_length"])))
                    if point:
                        output.print_md(u"  switch: ({:.0f}, {:.0f}, {:.0f}) mm".format(
                            ft_to_mm(point.X), ft_to_mm(point.Y), ft_to_mm(point.Z)))
                    else:
                        output.print_md(u"  switch: NONE (no wall found?)")

                if not point:
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                    continue

                level = get_closest_level(doc, point.Z)
                if not level:
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                    continue

                inst = place_switch(doc, symbol, point, rotation, level)
                if inst:
                    created += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                else:
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                continue  # Переходим к следующей комнате

            # Для прихожих/коридоров - ищем входную дверь
            is_wet = False
            is_two_gang = False
            place_inside = True
            symbol = sym_1g
            best_info = None
            point = None
            rotation = None
            best_distance_ft = None
            selected_candidate_index = None

            if is_corridor:
                # Среди входных дверей выбираем наиболее удалённую позицию выключателя
                # (если несколько валидных дверей/кандидатов).
                for door_idx, (door, info) in enumerate(door_list):
                    if not is_entrance_door(info):
                        continue
                    cand_point, cand_rotation = calc_switch_position(
                        info, True, room, link_transform, link_doc
                    )
                    if not cand_point:
                        continue

                    cand_distance_ft = None
                    if info.get("center"):
                        c = link_transform.OfPoint(info["center"])
                        dx = cand_point.X - c.X
                        dy = cand_point.Y - c.Y
                        cand_distance_ft = math.sqrt(dx * dx + dy * dy)

                    if best_info is None:
                        replace = True
                    else:
                        replace = prefer_farther_candidate(best_distance_ft, cand_distance_ft)

                    if replace:
                        best_info = info
                        point = cand_point
                        rotation = cand_rotation
                        best_distance_ft = cand_distance_ft
                        selected_candidate_index = door_idx

                if not best_info:
                    # Входная дверь/точка не найдена - пропускаем
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                    continue

                is_wet = False
                is_two_gang = False  # В прихожей 1-клавишный
                place_inside = True   # Внутри прихожей
                symbol = sym_1g
            else:
                # Для обычных комнат: считаем всех кандидатов.
                # Для санузлов (is_wet=True) допускаем только двери, ведущие в прихожую/коридор.
                is_wet = contains_any(room_name, WET_ROOMS)
                is_two_gang = contains_any(room_name, TWO_GANG_ROOMS)
                place_inside = not is_wet
                symbol = sym_2g if is_two_gang else sym_1g

                for door_idx, (door, info) in enumerate(door_list):
                    other = None
                    fr = info.get("from_room")
                    tr = info.get("to_room")
                    if fr and hasattr(fr, "Id") and fr.Id == room.Id:
                        other = tr
                    else:
                        other = fr
                    other_name = get_room_name(other) if other else u""
                    corridor_bonus = 1 if contains_any(other_name, CORRIDOR_ROOMS) else 0

                    # Ключевое правило: выключатель санузла снаружи размещаем ТОЛЬКО в прихожей/коридоре.
                    if is_wet and corridor_bonus == 0:
                        continue

                    cand_point, cand_rotation = calc_switch_position(
                        info, place_inside, room, link_transform, link_doc
                    )
                    if not cand_point:
                        continue

                    cand_distance_ft = None
                    if info.get("center"):
                        c = link_transform.OfPoint(info["center"])
                        dx = cand_point.X - c.X
                        dy = cand_point.Y - c.Y
                        cand_distance_ft = math.sqrt(dx * dx + dy * dy)

                    if best_info is None:
                        replace = True
                    else:
                        best_other = None
                        bfr = best_info.get("from_room")
                        btr = best_info.get("to_room")
                        if bfr and hasattr(bfr, "Id") and bfr.Id == room.Id:
                            best_other = btr
                        else:
                            best_other = bfr
                        best_other_name = get_room_name(best_other) if best_other else u""
                        best_corridor_bonus = 1 if contains_any(best_other_name, CORRIDOR_ROOMS) else 0

                        replace = False
                        if corridor_bonus > best_corridor_bonus:
                            replace = True
                        elif corridor_bonus == best_corridor_bonus:
                            replace = prefer_farther_candidate(best_distance_ft, cand_distance_ft)

                    if replace:
                        best_info = info
                        point = cand_point
                        rotation = cand_rotation
                        best_distance_ft = cand_distance_ft
                        selected_candidate_index = door_idx

                if not best_info:
                    skipped += 1
                    if room_key:
                        processed_room_keys.add(room_key)
                    continue

            if created < 3 or "спальн" in room_name.lower():
                output.print_md(u"")
                output.print_md(u"**{}** (wet={}, 2g={})".format(room_name, is_wet, is_two_gang))
                output.print_md(u"  door type: `{}`".format(best_info.get("type_name", "N/A")))
                output.print_md(u"  wall: {}".format("YES" if best_info["wall"] else "NO"))
                output.print_md(u"  HandFlipped: {}, FacingFlipped: {}".format(
                    best_info.get("hand_flipped", "N/A"),
                    best_info.get("facing_flipped", "N/A")))
                # Check which source was used for handle direction
                type_name = best_info.get("type_name", "") or ""
                type_lower = type_name.lower()
                import re as re_check
                if re_check.search(r'[_\s\-]лв(?:[_\s\-]|$)|лв$', type_lower):
                    output.print_md(u"  **Handle source: TYPE NAME (Лв = LEFT)**")
                elif re_check.search(r'[_\s\-]пр(?:[_\s\-]|$)|пр$', type_lower):
                    output.print_md(u"  **Handle source: TYPE NAME (Пр = RIGHT)**")
                elif re_check.search(r'[_\s\-]л(?:[_\s\-]|$)|(?<![а-я])л$', type_lower):
                    output.print_md(u"  **Handle source: TYPE NAME (Л = LEFT)**")
                elif re_check.search(r'[_\s\-]п(?:[_\s\-]|$)|(?<![а-я])п$', type_lower):
                    output.print_md(u"  **Handle source: TYPE NAME (П = RIGHT)**")
                elif best_info["hand"]:
                    output.print_md(u"  Handle source: HandOrientation (inverted)")
                else:
                    output.print_md(u"  Handle source: fallback/guess")
                if best_info["center"]:
                    c = link_transform.OfPoint(best_info["center"])
                    width_mm = ft_to_mm(best_info["width"])
                    output.print_md(u"  door center: ({:.0f},{:.0f}), width={:.0f}mm".format(
                        ft_to_mm(c.X), ft_to_mm(c.Y), width_mm))
                    # Warn if width seems wrong
                    if width_mm < 600 or width_mm > 1500:
                        output.print_md(u"  ⚠️ WARNING: door width {:.0f}mm seems unusual!".format(width_mm))
                if best_info["hand"]:
                    h = link_transform.OfVector(best_info["hand"])
                    output.print_md(u"  hand direction: ({:.2f},{:.2f})".format(h.X, h.Y))
                if point:
                    output.print_md(u"  switch: ({:.0f}, {:.0f}, {:.0f}) mm".format(
                        ft_to_mm(point.X), ft_to_mm(point.Y), ft_to_mm(point.Z)))
                    if selected_candidate_index is not None:
                        output.print_md(u"  selected candidate index: {}".format(selected_candidate_index))
                    if best_info["center"]:
                        c = link_transform.OfPoint(best_info["center"])
                        dist = math.sqrt((point.X - c.X) ** 2 + (point.Y - c.Y) ** 2)
                        output.print_md(u"  distance from door center: {:.0f}mm".format(ft_to_mm(dist)))
                        # Expected distance = half_door + jamb_offset
                        expected = ft_to_mm(best_info["width"]) / 2.0 + 150  # JAMB_OFFSET_MM
                        output.print_md(u"  expected distance: {:.0f}mm (half_door={:.0f} + jamb=150)".format(
                            expected, ft_to_mm(best_info["width"]) / 2.0))
                    # Debug info
                    if "_debug_wall_length" in best_info:
                        output.print_md(u"  DEBUG: wall_length={:.0f}mm, t_door_center={:.0f}mm".format(
                            ft_to_mm(best_info["_debug_wall_length"]),
                            ft_to_mm(best_info["_debug_t_door_center"])))
                        output.print_md(u"  DEBUG: side={}, offset={:.0f}mm, t_raw={:.0f}mm, t_clamped={:.0f}mm".format(
                            best_info["_debug_side_along_wall"],
                            ft_to_mm(best_info["_debug_offset_from_center"]),
                            ft_to_mm(best_info["_debug_t_switch_raw"]),
                            ft_to_mm(best_info["_debug_t_switch_clamped"])))
                        output.print_md(u"  DEBUG: adjacent_wall={}, remaining={:.0f}mm, hops={}, final_wall_id={}, raw_outside_host={}".format(
                            best_info.get("_debug_used_adjacent_wall", False),
                            ft_to_mm(best_info.get("_debug_remaining_after_host", 0.0)),
                            best_info.get("_debug_chain_hops", 0),
                            best_info.get("_debug_final_wall_id", "N/A"),
                            best_info.get("_debug_raw_outside_host", False)))
                        output.print_md(u"  DEBUG: surface_source={}, surface_sign={}, has_target_room={}".format(
                            best_info.get("_debug_surface_source", "N/A"),
                            best_info.get("_debug_surface_sign", "N/A"),
                            best_info.get("_debug_has_target_room", False)))
                        output.print_md(u"  DEBUG: ref_probe(+/−)=({}/{}), target_probe(+/−)=({}/{})".format(
                            best_info.get("_debug_ref_probe_plus", "N/A"),
                            best_info.get("_debug_ref_probe_minus", "N/A"),
                            best_info.get("_debug_target_probe_plus", "N/A"),
                            best_info.get("_debug_target_probe_minus", "N/A")))
                else:
                    output.print_md(u"  switch: NONE (no wall?)")

            if not point:
                skipped += 1
                if room_key:
                    processed_room_keys.add(room_key)
                continue

            level = get_closest_level(doc, point.Z)
            if not level:
                skipped += 1
                if room_key:
                    processed_room_keys.add(room_key)
                continue

            inst = place_switch(doc, symbol, point, rotation, level)
            if inst:
                created += 1
                if room_key:
                    processed_room_keys.add(room_key)
            else:
                skipped += 1
                if room_key:
                    processed_room_keys.add(room_key)

        t.Commit()

    output.print_md(u"---")
    output.print_md(u"## Результат")
    output.print_md(u"- Выключателей: **{}**".format(created))
    output.print_md(u"- Пропущено: {}".format(skipped))

    report_time_saved(output, 'switches_doors', created)
    try:
        from time_savings import calculate_time_saved, calculate_time_saved_range
        minutes = calculate_time_saved('switches_doors', created)
        minutes_min, minutes_max = calculate_time_saved_range('switches_doors', created)
        global EOM_HUB_RESULT
        stats = {'total': created, 'processed': created, 'skipped': skipped, 'errors': 0}
        EOM_HUB_RESULT = {
            'stats': stats,
            'time_saved_minutes': minutes,
            'time_saved_minutes_min': minutes_min,
            'time_saved_minutes_max': minutes_max,
            'placed': created,
        }
    except: pass

    if created > 0 and not bool(getattr(magic_context, 'FORCE_SELECTION', False)):
        forms.alert(u"Создано {} выключателей".format(created))
    return created


if __name__ == "__main__":
    main()
