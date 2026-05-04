# -*- coding: utf-8 -*-
"""Отчётность и debug-вывод для расстановки выключателей."""

import math
import re

from domain import ft_to_mm


def _debug_value(debug_info, best_info, attr_name, legacy_key, default=None):
    if debug_info is not None:
        try:
            value = getattr(debug_info, attr_name)
            if value is not None:
                return value
        except Exception:
            pass
    try:
        return best_info.get(legacy_key, default)
    except Exception:
        return default


def print_selection_debug(
    output,
    created,
    room_name,
    is_wet,
    is_two_gang,
    best_info,
    debug_info,
    point,
    selected_candidate_index,
    link_transform,
):
    if created >= 3 and "спальн" not in room_name.lower():
        return

    output.print_md(u"")
    output.print_md(u"**{}** (wet={}, 2g={})".format(room_name, is_wet, is_two_gang))
    output.print_md(u"  door type: `{}`".format(best_info.get("type_name", "N/A")))
    output.print_md(u"  wall: {}".format("YES" if best_info["wall"] else "NO"))
    output.print_md(u"  HandFlipped: {}, FacingFlipped: {}".format(
        best_info.get("hand_flipped", "N/A"),
        best_info.get("facing_flipped", "N/A"),
    ))

    type_name = best_info.get("type_name", "") or ""
    type_lower = type_name.lower()
    if re.search(r'[_\s\-]лв(?:[_\s\-]|$)|лв$', type_lower):
        output.print_md(u"  **Handle source: TYPE NAME (Лв = LEFT)**")
    elif re.search(r'[_\s\-]пр(?:[_\s\-]|$)|пр$', type_lower):
        output.print_md(u"  **Handle source: TYPE NAME (Пр = RIGHT)**")
    elif re.search(r'[_\s\-]л(?:[_\s\-]|$)|(?<![а-я])л$', type_lower):
        output.print_md(u"  **Handle source: TYPE NAME (Л = LEFT)**")
    elif re.search(r'[_\s\-]п(?:[_\s\-]|$)|(?<![а-я])п$', type_lower):
        output.print_md(u"  **Handle source: TYPE NAME (П = RIGHT)**")
    elif best_info["hand"]:
        output.print_md(u"  Handle source: HandOrientation (inverted)")
    else:
        output.print_md(u"  Handle source: fallback/guess")

    if best_info["center"]:
        c = link_transform.OfPoint(best_info["center"])
        width_mm = ft_to_mm(best_info["width"])
        output.print_md(u"  door center: ({:.0f},{:.0f}), width={:.0f}mm".format(
            ft_to_mm(c.X), ft_to_mm(c.Y), width_mm
        ))
        if width_mm < 600 or width_mm > 1500:
            output.print_md(u"  ⚠️ WARNING: door width {:.0f}mm seems unusual!".format(width_mm))

    if best_info["hand"]:
        h = link_transform.OfVector(best_info["hand"])
        output.print_md(u"  hand direction: ({:.2f},{:.2f})".format(h.X, h.Y))

    if point:
        output.print_md(u"  switch: ({:.0f}, {:.0f}, {:.0f}) mm".format(
            ft_to_mm(point.X), ft_to_mm(point.Y), ft_to_mm(point.Z)
        ))
        if selected_candidate_index is not None:
            output.print_md(u"  selected candidate index: {}".format(selected_candidate_index))

        if best_info["center"]:
            c = link_transform.OfPoint(best_info["center"])
            dist = math.sqrt((point.X - c.X) ** 2 + (point.Y - c.Y) ** 2)
            output.print_md(u"  distance from door center: {:.0f}mm".format(ft_to_mm(dist)))
            expected = ft_to_mm(best_info["width"]) / 2.0 + 150
            output.print_md(u"  expected distance: {:.0f}mm (half_door={:.0f} + jamb=150)".format(
                expected, ft_to_mm(best_info["width"]) / 2.0
            ))

        wall_length = _debug_value(debug_info, best_info, "wall_length", "_debug_wall_length")
        if wall_length is not None:
            output.print_md(u"  DEBUG: wall_length={:.0f}mm, t_door_center={:.0f}mm".format(
                ft_to_mm(wall_length),
                ft_to_mm(_debug_value(debug_info, best_info, "t_door_center", "_debug_t_door_center", 0.0))
            ))
            output.print_md(u"  DEBUG: side={}, offset={:.0f}mm, t_raw={:.0f}mm, t_clamped={:.0f}mm".format(
                _debug_value(debug_info, best_info, "side_along_wall", "_debug_side_along_wall", "N/A"),
                ft_to_mm(_debug_value(debug_info, best_info, "offset_from_center", "_debug_offset_from_center", 0.0)),
                ft_to_mm(_debug_value(debug_info, best_info, "t_switch_raw", "_debug_t_switch_raw", 0.0)),
                ft_to_mm(_debug_value(debug_info, best_info, "t_switch_clamped", "_debug_t_switch_clamped", 0.0))
            ))
            remaining_after_host_mm = ft_to_mm(
                _debug_value(debug_info, best_info, "remaining_after_host", "_debug_remaining_after_host", 0.0)
            )
            adjacent_fmt = (
                u"  DEBUG: adjacent_wall={}, remaining={:.0f}mm, hops={}, "
                u"final_wall_id={}, raw_outside_host={}"
            )
            output.print_md(adjacent_fmt.format(
                _debug_value(debug_info, best_info, "used_adjacent_wall", "_debug_used_adjacent_wall", False),
                remaining_after_host_mm,
                _debug_value(debug_info, best_info, "chain_hops", "_debug_chain_hops", 0),
                _debug_value(debug_info, best_info, "final_wall_id", "_debug_final_wall_id", "N/A"),
                _debug_value(debug_info, best_info, "raw_outside_host", "_debug_raw_outside_host", False)
            ))
            output.print_md(u"  DEBUG: surface_source={}, surface_sign={}, has_target_room={}".format(
                _debug_value(debug_info, best_info, "surface_source", "_debug_surface_source", "N/A"),
                _debug_value(debug_info, best_info, "surface_sign", "_debug_surface_sign", "N/A"),
                _debug_value(debug_info, best_info, "has_target_room", "_debug_has_target_room", False)
            ))
            output.print_md(u"  DEBUG: ref_probe(+/−)=({}/{}), target_probe(+/−)=({}/{})".format(
                _debug_value(debug_info, best_info, "ref_probe_plus", "_debug_ref_probe_plus", "N/A"),
                _debug_value(debug_info, best_info, "ref_probe_minus", "_debug_ref_probe_minus", "N/A"),
                _debug_value(debug_info, best_info, "target_probe_plus", "_debug_target_probe_plus", "N/A"),
                _debug_value(debug_info, best_info, "target_probe_minus", "_debug_target_probe_minus", "N/A")
            ))
    else:
        output.print_md(u"  switch: NONE (no wall?)")


def _build_hub_result(created, skipped):
    try:
        from time_savings import calculate_time_saved, calculate_time_saved_range

        minutes = calculate_time_saved('switches_doors', created)
        minutes_min, minutes_max = calculate_time_saved_range('switches_doors', created)
        stats = {'total': created, 'processed': created, 'skipped': skipped, 'errors': 0}
        return {
            'stats': stats,
            'time_saved_minutes': minutes,
            'time_saved_minutes_min': minutes_min,
            'time_saved_minutes_max': minutes_max,
            'placed': created,
        }
    except Exception:
        return None


def publish_single_link_summary(output, created, skipped, report_time_saved_fn):
    output.print_md(u"---")
    output.print_md(u"## Результат")
    output.print_md(u"- Выключателей: **{}**".format(created))
    output.print_md(u"- Пропущено: {}".format(skipped))

    report_time_saved_fn(output, 'switches_doors', created)
    return _build_hub_result(created, skipped)
