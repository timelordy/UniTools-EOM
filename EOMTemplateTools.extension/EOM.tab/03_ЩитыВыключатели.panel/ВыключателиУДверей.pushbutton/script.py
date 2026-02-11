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

from pyrevit import DB, forms, revit, script
from time_savings import report_time_saved
try:
    import socket_utils as su
except ImportError:
    import sys, os
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
    doc = revit.doc
    output = script.get_output()
    output.print_md(u"# Размещение выключателей")

    import link_reader
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

    with DB.Transaction(doc, u"ЭОМ: Выключатели") as t:
        t.Start()

        for room in rooms:
            room_name = get_room_name(room)
            room_id = room.Id.IntegerValue

            if contains_any(room_name, SKIP_ROOMS):
                continue

            # Пропускаем общедомовые помещения (не квартирные)
            if contains_any(room_name, NON_APARTMENT_ROOMS):
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
                    continue
                
                level = get_closest_level(doc, point.Z)
                if not level:
                    skipped += 1
                    continue
                
                inst = place_switch(doc, symbol, point, rotation, level)
                if inst:
                    created += 1
                else:
                    skipped += 1
                continue  # Переходим к следующей комнате

            # Для прихожих/коридоров - ищем входную дверь
            if is_corridor:
                entrance_door = None
                entrance_info = None
                
                for door, info in door_list:
                    if is_entrance_door(info):
                        entrance_door = door
                        entrance_info = info
                        break
                
                if not entrance_door:
                    # Входная дверь не найдена - пропускаем
                    skipped += 1
                    continue
                
                # Ставим выключатель около входной двери (внутри прихожей)
                best_door = entrance_door
                best_info = entrance_info
                other_room = None  # Снаружи - не комната
                is_wet = False
                is_two_gang = False  # В прихожей 1-клавишный
                place_inside = True  # Внутри прихожей
            else:
                # Для обычных комнат - ищем дверь в коридор
                best_door = None
                best_info = None
                other_room = None

                for door, info in door_list:
                    fr = info["from_room"]
                    tr = info["to_room"]
                    other = tr if (fr and fr.Id == room.Id) else fr
                    other_name = get_room_name(other) if other else u""

                    if contains_any(other_name, CORRIDOR_ROOMS):
                        best_door = door
                        best_info = info
                        other_room = other
                        break

                if not best_door:
                    best_door, best_info = door_list[0]
                    fr = best_info["from_room"]
                    tr = best_info["to_room"]
                    other_room = tr if (fr and fr.Id == room.Id) else fr

                is_wet = contains_any(room_name, WET_ROOMS)
                is_two_gang = contains_any(room_name, TWO_GANG_ROOMS)
                place_inside = not is_wet

            symbol = sym_2g if is_two_gang else sym_1g

            point, rotation = calc_switch_position(
                best_info, place_inside, room, link_transform, link_doc
            )

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
                continue

            level = get_closest_level(doc, point.Z)
            if not level:
                skipped += 1
                continue

            inst = place_switch(doc, symbol, point, rotation, level)
            if inst:
                created += 1
            else:
                skipped += 1

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

    if created > 0:
        forms.alert(u"Создано {} выключателей".format(created))


if __name__ == "__main__":
    main()
