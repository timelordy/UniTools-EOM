# -*- coding: utf-8 -*-
"""Сервис выбора лучшего кандидата выключателя для комнаты."""

import math

from room_policy import (
    corridor_bonus,
    is_corridor_room,
    is_two_gang_room,
    is_wet_outside_allowed,
    is_wet_room,
    should_place_inside_room,
)


def _distance_from_door_center_ft(info, candidate_point, link_transform):
    center = info.get("center")
    if center is None:
        return None

    c = link_transform.OfPoint(center)
    dx = candidate_point.X - c.X
    dy = candidate_point.Y - c.Y
    return math.sqrt(dx * dx + dy * dy)


def _other_side_room(info, room):
    fr = info.get("from_room")
    tr = info.get("to_room")
    if fr and hasattr(fr, "Id") and fr.Id == room.Id:
        return tr
    return fr


def _room_name(target_room, get_room_name_fn):
    if target_room is None:
        return u""
    return get_room_name_fn(target_room)


def select_best_candidate_for_room(
    room,
    room_name,
    door_list,
    link_transform,
    link_doc,
    sym_1g,
    sym_2g,
    adapter_ports,
    diagnostics=None,
):
    if diagnostics is None:
        diagnostics = {}
    diagnostics.clear()

    is_corridor = is_corridor_room(room_name)

    is_wet = False
    is_two_gang = False
    place_inside = True
    symbol = sym_1g
    best_info = None
    point = None
    rotation = None
    best_debug = None
    best_distance_ft = None
    selected_candidate_index = None

    if is_corridor:
        entrance_rejected = 0
        no_point_rejected = 0
        for door_idx, (_, info) in enumerate(door_list):
            if not adapter_ports.is_entrance_door(info):
                entrance_rejected += 1
                continue

            cand_result = adapter_ports.calc_switch_position_with_debug(
                info, True, room, link_transform, link_doc
            )
            cand_point = cand_result.point
            if not cand_point:
                no_point_rejected += 1
                continue

            cand_distance_ft = _distance_from_door_center_ft(info, cand_point, link_transform)

            if best_info is None:
                replace = True
            else:
                replace = adapter_ports.prefer_farther_candidate(best_distance_ft, cand_distance_ft)

            if replace:
                best_info = info
                point = cand_point
                rotation = cand_result.rotation
                best_debug = cand_result.debug
                best_distance_ft = cand_distance_ft
                selected_candidate_index = door_idx

        if not best_info:
            if entrance_rejected == len(door_list):
                diagnostics["skip_reason"] = "NO_ENTRANCE_DOOR_IN_CORRIDOR"
            elif no_point_rejected > 0:
                diagnostics["skip_reason"] = "NO_VALID_POINT_FOR_ENTRANCE_DOOR"
            else:
                diagnostics["skip_reason"] = "NO_CANDIDATE_SELECTED"
            diagnostics["door_count"] = len(door_list)
            diagnostics["entrance_rejected"] = entrance_rejected
            diagnostics["no_point_rejected"] = no_point_rejected
            return None

        is_wet = False
        is_two_gang = False
        place_inside = True
        symbol = sym_1g
    else:
        is_wet = is_wet_room(room_name)
        is_two_gang = is_two_gang_room(room_name)
        place_inside = should_place_inside_room(room_name)
        symbol = sym_2g if is_two_gang else sym_1g

        wet_rejected = 0
        no_point_rejected = 0
        adjacent_rooms = []

        for door_idx, (_, info) in enumerate(door_list):
            other = _other_side_room(info, room)
            other_name = _room_name(other, adapter_ports.get_room_name)
            if other_name:
                adjacent_rooms.append(other_name)
            candidate_corridor_bonus = corridor_bonus(other_name)

            if not is_wet_outside_allowed(is_wet, other_name):
                wet_rejected += 1
                continue

            cand_result = adapter_ports.calc_switch_position_with_debug(
                info, place_inside, room, link_transform, link_doc
            )
            cand_point = cand_result.point
            if not cand_point:
                no_point_rejected += 1
                continue

            cand_distance_ft = _distance_from_door_center_ft(info, cand_point, link_transform)

            if best_info is None:
                replace = True
            else:
                best_other = _other_side_room(best_info, room)
                best_other_name = _room_name(best_other, adapter_ports.get_room_name)
                best_corridor_bonus = corridor_bonus(best_other_name)

                replace = False
                if candidate_corridor_bonus > best_corridor_bonus:
                    replace = True
                elif candidate_corridor_bonus == best_corridor_bonus:
                    replace = adapter_ports.prefer_farther_candidate(best_distance_ft, cand_distance_ft)

            if replace:
                best_info = info
                point = cand_point
                rotation = cand_result.rotation
                best_debug = cand_result.debug
                best_distance_ft = cand_distance_ft
                selected_candidate_index = door_idx

        if not best_info:
            if is_wet and wet_rejected == len(door_list) and len(door_list) > 0:
                diagnostics["skip_reason"] = "WET_ROOM_HAS_NO_CORRIDOR_ADJACENT_DOOR"
            elif no_point_rejected > 0 and (no_point_rejected + wet_rejected) >= len(door_list):
                diagnostics["skip_reason"] = "NO_VALID_SWITCH_POINT_FOR_ANY_CANDIDATE"
            elif len(door_list) == 0:
                diagnostics["skip_reason"] = "ROOM_HAS_NO_DOORS"
            else:
                diagnostics["skip_reason"] = "NO_CANDIDATE_SELECTED"
            diagnostics["door_count"] = len(door_list)
            diagnostics["is_wet"] = is_wet
            diagnostics["wet_rejected"] = wet_rejected
            diagnostics["no_point_rejected"] = no_point_rejected
            diagnostics["adjacent_rooms"] = sorted(set(adjacent_rooms))
            return None

    return {
        "is_wet": is_wet,
        "is_two_gang": is_two_gang,
        "symbol": symbol,
        "best_info": best_info,
        "debug_info": best_debug,
        "point": point,
        "rotation": rotation,
        "selected_candidate_index": selected_candidate_index,
    }
