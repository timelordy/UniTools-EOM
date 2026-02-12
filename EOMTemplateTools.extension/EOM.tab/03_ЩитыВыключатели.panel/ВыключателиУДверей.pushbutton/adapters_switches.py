# -*- coding: utf-8 -*-
import math
import re

from pyrevit import DB

from constants import COMMENT_TAG, JAMB_OFFSET_MM, SWITCH_HEIGHT_MM
from domain import mm_to_ft
from adapters_geometry import (
    _is_point_in_room_host,
    _walk_along_connected_walls,
    find_wall_near_point,
    get_room_center,
)


def prefer_farther_candidate(current_distance_ft, new_distance_ft, tolerance_ft=None):
    """Return True when a new switch candidate is meaningfully farther from door center.

    Args:
        current_distance_ft: Existing/baseline candidate XY distance in feet.
        new_distance_ft: New candidate XY distance in feet.
        tolerance_ft: Minimal delta to treat distances as different.

    Notes:
        If distances are equal (within tolerance), keep existing candidate to avoid churn.
    """
    if tolerance_ft is None:
        tolerance_ft = mm_to_ft(20)

    if new_distance_ft is None:
        return False
    if current_distance_ft is None:
        return True

    try:
        return float(new_distance_ft) > (float(current_distance_ft) + float(tolerance_ft))
    except Exception:
        return False


def calc_switch_position(door_info, place_inside_room, reference_room, link_transform, link_doc=None):
    center = door_info["center"]
    hand = door_info["hand"]
    facing = door_info["facing"]
    wall_p0 = door_info["wall_p0"]
    wall_p1 = door_info["wall_p1"]
    wall_width = door_info["wall_width"]

    if not center:
        return None, None

    center_host = link_transform.OfPoint(center)

    if wall_p0 and wall_p1 and wall_width:
        dx = wall_p1.X - wall_p0.X
        dy = wall_p1.Y - wall_p0.Y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-9:
            return None, None

        wall_dir = DB.XYZ(dx / length, dy / length, 0)
        wall_normal = DB.XYZ(-wall_dir.Y, wall_dir.X, 0)

        # Determine door hand from type name
        # Common patterns in Russian door naming:
        #   "Лв" or "Л" = Left (левая) - handle on left
        #   "Пр" or "П" = Right (правая) - handle on right
        # Examples: ДД_Гл_810х2080_Лв, ДД_Гл_810х2080_Пр
        type_name = door_info.get("type_name", "") or ""
        type_name_lower = type_name.lower()

        door_hand_from_name = None
        # Priority 1: Check for "Лв" (left) or "Пр" (right) - most specific
        # Pattern: _Лв, -Лв, Лв at end, or _Пр, -Пр, Пр at end
        if re.search(r'[_\s\-]лв(?:[_\s\-]|$)|лв$', type_name_lower):
            door_hand_from_name = "left"
        elif re.search(r'[_\s\-]пр(?:[_\s\-]|$)|пр$', type_name_lower):
            door_hand_from_name = "right"
        # Priority 2: Check for single "Л" or "П" - less specific, fallback
        elif re.search(r'[_\s\-]л(?:[_\s\-]|$)|(?<![а-я])л$', type_name_lower):
            door_hand_from_name = "left"
        elif re.search(r'[_\s\-]п(?:[_\s\-]|$)|(?<![а-я])п$', type_name_lower):
            door_hand_from_name = "right"

        # Determine side_along_wall based on door HANDLE position
        # PRIORITY 1: Type name contains Л (left handle) or П (right handle)
        # PRIORITY 2: HandOrientation (points to HINGES, handle is opposite!)

        hand_flipped = door_info.get("hand_flipped", False)

        if door_hand_from_name:
            # PRIORITY 1: Use door type name (Л/П) - this directly indicates handle side
            # Л = левая = handle on LEFT when looking at door from facing side
            # П = правая = handle on RIGHT when looking at door from facing side
            if facing:
                facing_host = link_transform.OfVector(facing)
                # Left (Л): handle is 90° CCW from facing direction
                # Right (П): handle is 90° CW from facing direction
                if door_hand_from_name == "left":
                    handle_dir = DB.XYZ(-facing_host.Y, facing_host.X, 0)  # rotate CCW
                else:  # right
                    handle_dir = DB.XYZ(facing_host.Y, -facing_host.X, 0)  # rotate CW
            else:
                # No facing info - use wall direction as approximation
                handle_dir = wall_dir if door_hand_from_name == "right" else DB.XYZ(-wall_dir.X, -wall_dir.Y, 0)
            handle_dot = handle_dir.X * wall_dir.X + handle_dir.Y * wall_dir.Y
            side_along_wall = 1 if handle_dot >= 0 else -1
        elif hand:
            # PRIORITY 2: HandOrientation points to HINGES side
            # Handle is on the OPPOSITE side from hinges
            hand_host = link_transform.OfVector(hand)
            # INVERT to get handle direction (handle is opposite to hinges)
            handle_dir = DB.XYZ(-hand_host.X, -hand_host.Y, 0)

            handle_dot = handle_dir.X * wall_dir.X + handle_dir.Y * wall_dir.Y
            side_along_wall = 1 if handle_dot >= 0 else -1
        else:
            # Last fallback: use facing to make a guess
            if facing:
                facing_host = link_transform.OfVector(facing)
                handle_dir = DB.XYZ(-facing_host.Y, facing_host.X, 0)
            else:
                handle_dir = wall_dir
            handle_dot = handle_dir.X * wall_dir.X + handle_dir.Y * wall_dir.Y
            side_along_wall = 1 if handle_dot >= 0 else -1

        to_center_x = center_host.X - wall_p0.X
        to_center_y = center_host.Y - wall_p0.Y
        t_door_center = (to_center_x * wall_dir.X + to_center_y * wall_dir.Y)

        door_width = door_info["width"]
        # If door width seems too small, use standard 900mm (most common door width)
        if door_width < mm_to_ft(600):
            door_width = mm_to_ft(900)

        half_door = door_width / 2.0
        jamb_offset = mm_to_ft(JAMB_OFFSET_MM)
        offset_from_center = half_door + jamb_offset

        t_switch_raw = t_door_center + side_along_wall * offset_from_center

        # Минимальный отступ от края стены
        min_edge_offset = mm_to_ft(50)
        if length > 2 * min_edge_offset:
            t_switch_clamped = max(min_edge_offset, min(length - min_edge_offset, t_switch_raw))
        else:
            # Для очень коротких стен не инвертируем диапазон clamp
            t_switch_clamped = max(0.0, min(length, t_switch_raw))

        # По умолчанию ставим на host-стене
        place_wall_p0 = wall_p0
        place_wall_p1 = wall_p1
        place_wall_width = wall_width
        place_wall_length = length
        place_wall_dir = wall_dir
        t_switch = t_switch_clamped

        used_adjacent_wall = False
        remaining_after_host = 0.0
        chain_hops = 0
        raw_outside_host = (t_switch_raw < 0.0 or t_switch_raw > length)

        # Если смещение не помещается в host-стену, пробуем продолжить по смежным стенам
        if (t_switch_raw < min_edge_offset or t_switch_raw > (length - min_edge_offset)) and link_doc:
            try:
                wall_obj = door_info.get("wall")
                if wall_obj:
                    t_door_center_clamped = max(0.0, min(length, t_door_center))
                    travel_sign = 1 if side_along_wall >= 0 else -1
                    dist_to_joint = (length - t_door_center_clamped) if travel_sign > 0 else t_door_center_clamped
                    remaining = offset_from_center - dist_to_joint

                    # Пробуем продолжить по смежной стене при ЛЮБОМ выходе за границы host
                    if remaining > 1e-9:
                        start_joint = wall_p1 if travel_sign > 0 else wall_p0
                        travel_dir = wall_dir if travel_sign > 0 else DB.XYZ(-wall_dir.X, -wall_dir.Y, 0)

                        walk_result = _walk_along_connected_walls(
                            wall_obj,
                            start_joint,
                            remaining,
                            link_doc,
                            link_transform,
                            travel_dir,
                        )

                        if walk_result:
                            place_wall_p0 = walk_result["wall_p0"]
                            place_wall_p1 = walk_result["wall_p1"]
                            place_wall_width = walk_result["wall_width"]
                            place_wall_length = walk_result["wall_length"]
                            place_wall_dir = walk_result["wall_dir"]
                            t_switch = walk_result["t_on_wall"]
                            used_adjacent_wall = True
                            remaining_after_host = remaining
                            chain_hops = walk_result.get("hops", 0)
                            door_info["_debug_final_wall_id"] = walk_result.get("wall_id")
            except Exception:
                pass

        # Переопределяем рабочую стену (может быть смежная)
        wall_dir = place_wall_dir
        wall_normal = DB.XYZ(-wall_dir.Y, wall_dir.X, 0)

        # На смежной стене стараемся сохранить остаток дистанции максимально точно
        if used_adjacent_wall:
            if place_wall_length > 0:
                t_switch = max(0.0, min(place_wall_length, t_switch))
        else:
            if place_wall_length > 2 * min_edge_offset:
                t_switch = max(min_edge_offset, min(place_wall_length - min_edge_offset, t_switch))
            else:
                t_switch = max(0.0, min(place_wall_length, t_switch))

        axis_x = place_wall_p0.X + wall_dir.X * t_switch
        axis_y = place_wall_p0.Y + wall_dir.Y * t_switch

        half_width = (place_wall_width / 2.0) if place_wall_width else mm_to_ft(100)

        # DEBUG: сохраняем для диагностики
        door_info["_debug_wall_length"] = length
        door_info["_debug_t_door_center"] = t_door_center
        door_info["_debug_t_switch_raw"] = t_switch_raw
        door_info["_debug_t_switch_clamped"] = t_switch_clamped
        door_info["_debug_side_along_wall"] = side_along_wall
        door_info["_debug_offset_from_center"] = offset_from_center
        door_info["_debug_used_adjacent_wall"] = used_adjacent_wall
        door_info["_debug_remaining_after_host"] = remaining_after_host
        door_info["_debug_chain_hops"] = chain_hops
        door_info["_debug_raw_outside_host"] = raw_outside_host
        if not used_adjacent_wall:
            try:
                door_info["_debug_final_wall_id"] = door_info.get("wall").Id.IntegerValue if door_info.get("wall") else None
            except Exception:
                door_info["_debug_final_wall_id"] = None

        # Get rooms from door info
        from_room = door_info.get("from_room")
        to_room = door_info.get("to_room")

        # Get centers of both rooms
        from_center = get_room_center(from_room) if from_room else None
        to_center = get_room_center(to_room) if to_room else None

        # Determine target room for placement:
        # - If place_inside_room=True: use reference_room's side
        # - If place_inside_room=False: use the OTHER room's side (corridor for wet rooms)
        target_center = None

        if place_inside_room:
            # Place inside current room - use reference_room's center
            target_center = get_room_center(reference_room) if reference_room else None
        else:
            # Place outside current room - use the OTHER room's center
            if reference_room and from_room and from_room.Id == reference_room.Id:
                # reference_room is from_room, use to_room for placement
                target_center = to_center
            elif reference_room and to_room and to_room.Id == reference_room.Id:
                # reference_room is to_room, use from_room for placement
                target_center = from_center

            # Fallback: try any available other room center
            if not target_center:
                if from_center and (not reference_room or not from_room or from_room.Id != reference_room.Id):
                    target_center = from_center
                elif to_center and (not reference_room or not to_room or to_room.Id != reference_room.Id):
                    target_center = to_center

        surface_sign = 1  # default
        surface_source = "default"

        # --- Robust side selection by geometric probe ---
        # Проверяем обе стороны стены через IsPointInRoom, чтобы не зависеть от
        # from/to room assignment и ошибок в центр-точках комнат.
        probe_eps = max(mm_to_ft(120), half_width + mm_to_ft(20))
        probe_plus = DB.XYZ(
            axis_x + wall_normal.X * probe_eps,
            axis_y + wall_normal.Y * probe_eps,
            center_host.Z,
        )
        probe_minus = DB.XYZ(
            axis_x - wall_normal.X * probe_eps,
            axis_y - wall_normal.Y * probe_eps,
            center_host.Z,
        )

        ref_plus = _is_point_in_room_host(reference_room, probe_plus, link_transform)
        ref_minus = _is_point_in_room_host(reference_room, probe_minus, link_transform)

        target_room = None
        if not place_inside_room and reference_room:
            if from_room and from_room.Id == reference_room.Id:
                target_room = to_room
            elif to_room and to_room.Id == reference_room.Id:
                target_room = from_room
            if not target_room:
                if from_room and (not reference_room or from_room.Id != reference_room.Id):
                    target_room = from_room
                elif to_room and (not reference_room or to_room.Id != reference_room.Id):
                    target_room = to_room

        target_plus = _is_point_in_room_host(target_room, probe_plus, link_transform) if target_room else None
        target_minus = _is_point_in_room_host(target_room, probe_minus, link_transform) if target_room else None

        # 1) Основной выбор через probe + reference room
        if reference_room:
            if place_inside_room:
                # Должно быть ВНУТРИ reference_room
                if ref_plus is True and ref_minus is not True:
                    surface_sign = 1
                    surface_source = "probe_ref_inside_plus"
                elif ref_minus is True and ref_plus is not True:
                    surface_sign = -1
                    surface_source = "probe_ref_inside_minus"
            else:
                # Должно быть СНАРУЖИ reference_room
                if ref_plus is False and ref_minus is not False:
                    surface_sign = 1
                    surface_source = "probe_ref_outside_plus"
                elif ref_minus is False and ref_plus is not False:
                    surface_sign = -1
                    surface_source = "probe_ref_outside_minus"

        # 2) Если reference probe двусмысленный - пробуем целевую комнату
        if surface_source == "default" and target_room:
            if place_inside_room:
                if target_plus is True and target_minus is not True:
                    surface_sign = 1
                    surface_source = "probe_target_inside_plus"
                elif target_minus is True and target_plus is not True:
                    surface_sign = -1
                    surface_source = "probe_target_inside_minus"
            else:
                if target_plus is True and target_minus is not True:
                    surface_sign = 1
                    surface_source = "probe_target_plus"
                elif target_minus is True and target_plus is not True:
                    surface_sign = -1
                    surface_source = "probe_target_minus"

        # 3) Старые fallback-правила по центрам/ориентации, если геометрический probe не помог
        if surface_source == "default":
            if not place_inside_room:
                # Для влажных помещений приоритетно ставим СНАРУЖИ reference_room
                ref_center = get_room_center(reference_room) if reference_room else None
                if ref_center:
                    ref_center_host = link_transform.OfPoint(ref_center)
                    to_ref_x = ref_center_host.X - axis_x
                    to_ref_y = ref_center_host.Y - axis_y
                    ref_dot = to_ref_x * wall_normal.X + to_ref_y * wall_normal.Y
                    ref_side = 1 if ref_dot >= 0 else -1
                    surface_sign = -ref_side
                    surface_source = "ref_outside"
                elif target_center:
                    # Fallback: используем центр целевой комнаты (другая сторона двери)
                    target_center_host = link_transform.OfPoint(target_center)
                    to_target_x = target_center_host.X - axis_x
                    to_target_y = target_center_host.Y - axis_y
                    target_dot = to_target_x * wall_normal.X + to_target_y * wall_normal.Y
                    surface_sign = 1 if target_dot >= 0 else -1
                    surface_source = "target_center"
                elif facing:
                    # Последний fallback
                    facing_host = link_transform.OfVector(facing)
                    facing_dot = facing_host.X * wall_normal.X + facing_host.Y * wall_normal.Y
                    surface_sign = 1 if facing_dot >= 0 else -1
                    surface_source = "facing"
            else:
                # Для обычных комнат: внутри reference_room / target_room
                if target_center:
                    target_center_host = link_transform.OfPoint(target_center)
                    to_target_x = target_center_host.X - axis_x
                    to_target_y = target_center_host.Y - axis_y
                    target_dot = to_target_x * wall_normal.X + to_target_y * wall_normal.Y
                    surface_sign = 1 if target_dot >= 0 else -1
                    surface_source = "target_center"
                elif reference_room:
                    ref_center = get_room_center(reference_room)
                    if ref_center:
                        ref_center_host = link_transform.OfPoint(ref_center)
                        to_ref_x = ref_center_host.X - axis_x
                        to_ref_y = ref_center_host.Y - axis_y
                        ref_dot = to_ref_x * wall_normal.X + to_ref_y * wall_normal.Y
                        surface_sign = 1 if ref_dot >= 0 else -1
                        surface_source = "ref_inside"

        surface_x = axis_x + wall_normal.X * half_width * surface_sign
        surface_y = axis_y + wall_normal.Y * half_width * surface_sign
        surface_z = center_host.Z + mm_to_ft(SWITCH_HEIGHT_MM)

        point = DB.XYZ(surface_x, surface_y, surface_z)

        # Жесткая валидация стороны: если для outside placement точка всё ещё в reference_room,
        # принудительно переворачиваем на противоположную грань стены.
        forced_flip = False
        if not place_inside_room and reference_room:
            try:
                in_ref_final = _is_point_in_room_host(reference_room, point, link_transform)
            except Exception:
                in_ref_final = None

            if in_ref_final is True:
                alt_sign = -surface_sign
                alt_point = DB.XYZ(
                    axis_x + wall_normal.X * half_width * alt_sign,
                    axis_y + wall_normal.Y * half_width * alt_sign,
                    surface_z,
                )

                alt_ok = True
                if target_room:
                    try:
                        alt_ok = _is_point_in_room_host(target_room, alt_point, link_transform) is True
                    except Exception:
                        alt_ok = True

                if alt_ok:
                    surface_sign = alt_sign
                    point = alt_point
                    forced_flip = True
                    surface_source = "forced_flip_outside"

        rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2

        # DEBUG: side-choice diagnostics
        door_info["_debug_surface_sign"] = surface_sign
        door_info["_debug_surface_source"] = surface_source
        door_info["_debug_ref_probe_plus"] = ref_plus
        door_info["_debug_ref_probe_minus"] = ref_minus
        door_info["_debug_target_probe_plus"] = target_plus
        door_info["_debug_target_probe_minus"] = target_minus
        door_info["_debug_has_target_room"] = bool(target_room)
        door_info["_debug_forced_flip_outside"] = forced_flip

        return point, rotation

    return None, None


def place_switch(doc, symbol, point, rotation, level):
    try:
        inst = doc.Create.NewFamilyInstance(
            point, symbol, level,
            DB.Structure.StructuralType.NonStructural,
        )
        if rotation and inst:
            axis = DB.Line.CreateBound(point, DB.XYZ(point.X, point.Y, point.Z + 1))
            DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, rotation)
        try:
            p = inst.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p:
                p.Set(COMMENT_TAG)
        except Exception:
            pass
        return inst
    except Exception:
        return None


def get_closest_level(doc, z):
    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    closest = None
    min_dist = float("inf")
    for lvl in levels:
        dist = abs(lvl.Elevation - z)
        if dist < min_dist:
            min_dist = dist
            closest = lvl
    return closest


def calc_switch_position_from_separation_line(sep_line_info, room, link_transform, link_doc, place_inside_room=True):
    """
    Вычисляет позицию выключателя для комнаты без двери,
    используя Room Separation Line как виртуальный вход.

    Args:
        place_inside_room: True = внутри комнаты, False = снаружи комнаты.
    """
    line_center = sep_line_info["line_center"]
    line_dir = sep_line_info["line_direction"]
    line_length = sep_line_info["line_length"]

    # Ищем стену рядом с Room Separation Line
    wall, wall_p0, wall_p1, wall_width = find_wall_near_point(
        link_doc, link_transform, line_center, search_radius_mm=1000
    )

    if not wall or not wall_p0 or not wall_p1:
        return None, None

    # Направление стены
    dx = wall_p1.X - wall_p0.X
    dy = wall_p1.Y - wall_p0.Y
    wall_length = math.sqrt(dx * dx + dy * dy)
    if wall_length < 1e-9:
        return None, None

    wall_dir = DB.XYZ(dx / wall_length, dy / wall_length, 0)
    wall_normal = DB.XYZ(-wall_dir.Y, wall_dir.X, 0)

    # Проекция центра линии разделения на стену
    to_center_x = line_center.X - wall_p0.X
    to_center_y = line_center.Y - wall_p0.Y
    t_center = (to_center_x * wall_dir.X + to_center_y * wall_dir.Y)

    # Offset от центра линии (150мм как для двери)
    jamb_offset = mm_to_ft(JAMB_OFFSET_MM)
    half_opening = line_length / 2.0

    # Выбираем сторону (ближе к началу или концу стены)
    t_option1 = t_center - half_opening - jamb_offset
    t_option2 = t_center + half_opening + jamb_offset

    # Выбираем позицию, которая лучше вписывается в стену
    min_edge = mm_to_ft(50)

    if t_option1 >= min_edge and t_option1 <= wall_length - min_edge:
        t_switch = t_option1
    elif t_option2 >= min_edge and t_option2 <= wall_length - min_edge:
        t_switch = t_option2
    else:
        # Clamp к границам
        t_switch = max(min_edge, min(wall_length - min_edge, t_center))

    axis_x = wall_p0.X + wall_dir.X * t_switch
    axis_y = wall_p0.Y + wall_dir.Y * t_switch

    half_width = wall_width / 2.0 if wall_width else mm_to_ft(100)

    # Определяем сторону стены (внутри/снаружи комнаты)
    room_center = get_room_center(room)
    surface_sign = 1

    # Приоритет: геометрическая проверка обеих сторон через IsPointInRoom
    probe_eps = max(mm_to_ft(120), half_width + mm_to_ft(20))
    probe_plus = DB.XYZ(
        axis_x + wall_normal.X * probe_eps,
        axis_y + wall_normal.Y * probe_eps,
        line_center.Z,
    )
    probe_minus = DB.XYZ(
        axis_x - wall_normal.X * probe_eps,
        axis_y - wall_normal.Y * probe_eps,
        line_center.Z,
    )

    in_plus = _is_point_in_room_host(room, probe_plus, link_transform)
    in_minus = _is_point_in_room_host(room, probe_minus, link_transform)

    if place_inside_room:
        if in_plus is True and in_minus is not True:
            surface_sign = 1
        elif in_minus is True and in_plus is not True:
            surface_sign = -1
        elif room_center:
            room_center_t = link_transform.OfPoint(room_center)
            to_room_x = room_center_t.X - axis_x
            to_room_y = room_center_t.Y - axis_y
            room_dot = to_room_x * wall_normal.X + to_room_y * wall_normal.Y
            surface_sign = 1 if room_dot >= 0 else -1
    else:
        if in_plus is False and in_minus is not False:
            surface_sign = 1
        elif in_minus is False and in_plus is not False:
            surface_sign = -1
        elif room_center:
            room_center_t = link_transform.OfPoint(room_center)
            to_room_x = room_center_t.X - axis_x
            to_room_y = room_center_t.Y - axis_y
            room_dot = to_room_x * wall_normal.X + to_room_y * wall_normal.Y
            room_side = 1 if room_dot >= 0 else -1
            surface_sign = -room_side

    surface_x = axis_x + wall_normal.X * half_width * surface_sign
    surface_y = axis_y + wall_normal.Y * half_width * surface_sign
    surface_z = line_center.Z + mm_to_ft(SWITCH_HEIGHT_MM)

    point = DB.XYZ(surface_x, surface_y, surface_z)
    rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2

    return point, rotation
