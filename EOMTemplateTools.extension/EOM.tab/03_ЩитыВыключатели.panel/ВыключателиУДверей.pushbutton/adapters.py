# -*- coding: utf-8 -*-
import math
import re

from pyrevit import DB

from constants import (
    COMMENT_TAG,
    COMMENT_TAG_OUTLET,
    ENTRANCE_DOOR_PATTERNS,
    JAMB_OFFSET_MM,
    OUTLET_HEIGHT_MM,
    OUTLET_TYPE_ID,
    SWITCH_1G_TYPE_ID,
    SWITCH_2G_TYPE_ID,
    SWITCH_HEIGHT_MM,
)
from domain import mm_to_ft


def get_room_name(room):
    try:
        param = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        return param.AsString() if param else u""
    except Exception:
        return u""


def get_room_center(room):
    # Try Location.Point first (guaranteed to be inside the room)
    try:
        loc = room.Location
        if loc and hasattr(loc, 'Point') and loc.Point:
            return loc.Point
    except Exception:
        pass
    # Fallback to bounding box center (may be outside for L-shaped rooms)
    try:
        bb = room.get_BoundingBox(None)
        if bb:
            return DB.XYZ(
                (bb.Min.X + bb.Max.X) / 2,
                (bb.Min.Y + bb.Max.Y) / 2,
                bb.Min.Z,
            )
    except Exception:
        pass
    return None


def get_door_host_wall(door):
    try:
        host = door.Host
        if host and isinstance(host, DB.Wall):
            return host
    except Exception:
        pass
    return None


def get_wall_curve_and_width(wall):
    try:
        loc = wall.Location
        if isinstance(loc, DB.LocationCurve):
            curve = loc.Curve
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)

            width = mm_to_ft(200)
            try:
                if hasattr(wall, 'Width'):
                    width = wall.Width
                elif hasattr(wall, 'WallType') and wall.WallType:
                    width = wall.WallType.Width
            except Exception:
                pass

            return p0, p1, width
    except Exception:
        pass
    return None, None, None


def find_adjacent_wall(current_wall, link_doc, link_transform, direction):
    """
    Find an adjacent wall that continues in the same direction.
    
    Args:
        current_wall: The current wall element
        link_doc: Link document containing walls
        link_transform: Transform to apply to coordinates
        direction: 1 = search from p1 (end), -1 = search from p0 (start)
    
    Returns:
        (wall, p0, p1, width) of adjacent wall or (None, None, None, None)
    """
    try:
        p0, p1, width = get_wall_curve_and_width(current_wall)
        if not p0 or not p1:
            return None, None, None, None
        
        # Get wall direction
        dx = p1.X - p0.X
        dy = p1.Y - p0.Y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-9:
            return None, None, None, None
        
        wall_dir = DB.XYZ(dx / length, dy / length, 0)
        
        # Point to search from
        search_point = p1 if direction > 0 else p0
        search_point_transformed = link_transform.OfPoint(search_point)
        
        # Tolerance for finding adjacent walls (50mm)
        tolerance = mm_to_ft(50)
        # Tolerance for direction alignment (cos of 5 degrees ~ 0.996)
        dir_tolerance = 0.99
        
        # Search for walls in the link
        walls = DB.FilteredElementCollector(link_doc) \
            .OfCategory(DB.BuiltInCategory.OST_Walls) \
            .WhereElementIsNotElementType() \
            .ToElements()
        
        for wall in walls:
            if wall.Id == current_wall.Id:
                continue
            
            wp0, wp1, wwidth = get_wall_curve_and_width(wall)
            if not wp0 or not wp1:
                continue
            
            # Check if wall is aligned (same direction)
            wdx = wp1.X - wp0.X
            wdy = wp1.Y - wp0.Y
            wlength = math.sqrt(wdx * wdx + wdy * wdy)
            if wlength < 1e-9:
                continue
            
            w_dir = DB.XYZ(wdx / wlength, wdy / wlength, 0)
            
            # Check direction alignment (parallel, same or opposite direction)
            dot = abs(wall_dir.X * w_dir.X + wall_dir.Y * w_dir.Y)
            if dot < dir_tolerance:
                continue
            
            # Check if one of the wall's endpoints is close to our search point
            wp0_t = link_transform.OfPoint(wp0)
            wp1_t = link_transform.OfPoint(wp1)
            
            dist_to_p0 = math.sqrt(
                (search_point_transformed.X - wp0_t.X) ** 2 + 
                (search_point_transformed.Y - wp0_t.Y) ** 2
            )
            dist_to_p1 = math.sqrt(
                (search_point_transformed.X - wp1_t.X) ** 2 + 
                (search_point_transformed.Y - wp1_t.Y) ** 2
            )
            
            if dist_to_p0 < tolerance:
                # Adjacent wall starts at our search point
                return wall, wp0_t, wp1_t, wwidth
            elif dist_to_p1 < tolerance:
                # Adjacent wall ends at our search point - flip it for consistency
                return wall, wp1_t, wp0_t, wwidth
        
    except Exception:
        pass
    
    return None, None, None, None


def get_door_info(door, link_doc, link_transform):
    info = {
        "center": None,
        "width": mm_to_ft(900),
        "hand": None,
        "facing": None,
        "from_room": None,
        "to_room": None,
        "wall": None,
        "wall_p0": None,
        "wall_p1": None,
        "wall_width": None,
        "door_bb_min": None,
        "door_bb_max": None,
        "type_name": None,
    }

    # Get door type/family name for hand detection (л/п)
    try:
        if door.Symbol:
            type_name = door.Symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
            if type_name:
                info["type_name"] = type_name.AsString()
            if not info["type_name"]:
                family_name = door.Symbol.get_Parameter(DB.BuiltInParameter.ALL_MODEL_FAMILY_NAME)
                if family_name:
                    info["type_name"] = family_name.AsString()
    except Exception:
        pass

    # Получаем BoundingBox для определения центра двери
    # Location.Point - это точка вставки (обычно у петель), а не центр проёма!
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            info["door_bb_min"] = link_transform.OfPoint(bb.Min)
            info["door_bb_max"] = link_transform.OfPoint(bb.Max)
            # Центр BoundingBox - это реальный центр дверного проёма
            info["center"] = DB.XYZ(
                (bb.Min.X + bb.Max.X) / 2,
                (bb.Min.Y + bb.Max.Y) / 2,
                bb.Min.Z,
            )
    except Exception:
        pass

    # Fallback: Location.Point если BoundingBox недоступен
    if not info["center"]:
        try:
            loc = door.Location
            if hasattr(loc, "Point"):
                info["center"] = loc.Point
        except Exception:
            pass

    try:
        p = door.Symbol.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
        if p:
            w = p.AsDouble()
            if w and w > mm_to_ft(300):  # Sanity check - door should be > 300mm
                info["width"] = w
    except Exception:
        pass
    
    # Fallback: try to get width from instance parameter
    if info["width"] < mm_to_ft(500):
        try:
            p = door.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
            if p:
                w = p.AsDouble()
                if w and w > mm_to_ft(300):
                    info["width"] = w
        except Exception:
            pass
    
    # Fallback: estimate from bounding box
    if info["width"] < mm_to_ft(500):
        try:
            bb = door.get_BoundingBox(None)
            if bb:
                dx = abs(bb.Max.X - bb.Min.X)
                dy = abs(bb.Max.Y - bb.Min.Y)
                # Door width is the LARGER of X/Y dimensions in plan
                # (the smaller is door thickness ~50-100mm)
                estimated_width = max(dx, dy)
                if estimated_width > mm_to_ft(300) and estimated_width < mm_to_ft(2500):
                    info["width"] = estimated_width
        except Exception:
            pass

    try:
        info["hand"] = door.HandOrientation
        info["facing"] = door.FacingOrientation
        # HandFlipped/FacingFlipped tell us if door is mirrored
        info["hand_flipped"] = door.HandFlipped
        info["facing_flipped"] = door.FacingFlipped
    except Exception:
        pass

    try:
        phases = list(link_doc.Phases)
        if phases:
            phase = phases[-1]
            info["from_room"] = door.get_FromRoom(phase)
            info["to_room"] = door.get_ToRoom(phase)
    except Exception:
        pass

    wall = get_door_host_wall(door)
    if wall:
        info["wall"] = wall
        p0, p1, width = get_wall_curve_and_width(wall)
        if p0 and p1:
            info["wall_p0"] = link_transform.OfPoint(p0)
            info["wall_p1"] = link_transform.OfPoint(p1)
            info["wall_width"] = width

    return info


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

        t_switch = t_door_center + side_along_wall * offset_from_center
        
        # Ограничиваем только если выходим за пределы стены
        # Минимальный отступ от края стены - 50мм (раньше было 100мм)
        min_edge_offset = mm_to_ft(50)
        t_switch_clamped = max(min_edge_offset, min(length - min_edge_offset, t_switch))
        
        # DEBUG: сохраняем для диагностики
        door_info["_debug_wall_length"] = length
        door_info["_debug_t_door_center"] = t_door_center
        door_info["_debug_t_switch_raw"] = t_switch
        door_info["_debug_t_switch_clamped"] = t_switch_clamped
        door_info["_debug_side_along_wall"] = side_along_wall
        door_info["_debug_offset_from_center"] = offset_from_center
        
        t_switch = t_switch_clamped

        axis_x = wall_p0.X + wall_dir.X * t_switch
        axis_y = wall_p0.Y + wall_dir.Y * t_switch

        half_width = wall_width / 2.0

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
        
        if not place_inside_room and facing:
            # FOR WET ROOMS: facing direction is most reliable
            # Wet room doors open OUTWARD → facing points to corridor/bedroom
            # So switch goes on SAME side as facing
            facing_host = link_transform.OfVector(facing)
            facing_dot = facing_host.X * wall_normal.X + facing_host.Y * wall_normal.Y
            surface_sign = 1 if facing_dot >= 0 else -1
        elif target_center:
            # For regular rooms or as fallback: use target room center
            target_center_host = link_transform.OfPoint(target_center)
            to_target_x = target_center_host.X - axis_x
            to_target_y = target_center_host.Y - axis_y
            target_dot = to_target_x * wall_normal.X + to_target_y * wall_normal.Y
            surface_sign = 1 if target_dot >= 0 else -1
        elif reference_room:
            # Fallback: use current room's center
            ref_center = get_room_center(reference_room)
            if ref_center:
                ref_center_host = link_transform.OfPoint(ref_center)
                to_ref_x = ref_center_host.X - axis_x
                to_ref_y = ref_center_host.Y - axis_y
                ref_dot = to_ref_x * wall_normal.X + to_ref_y * wall_normal.Y
                ref_side = 1 if ref_dot >= 0 else -1
                surface_sign = ref_side if place_inside_room else -ref_side

        surface_x = axis_x + wall_normal.X * half_width * surface_sign
        surface_y = axis_y + wall_normal.Y * half_width * surface_sign
        surface_z = center_host.Z + mm_to_ft(SWITCH_HEIGHT_MM)

        point = DB.XYZ(surface_x, surface_y, surface_z)
        rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2

        return point, rotation

    return None, None


def get_switch_symbol(doc, two_gang=False):
    type_id = SWITCH_2G_TYPE_ID if two_gang else SWITCH_1G_TYPE_ID
    try:
        elem = doc.GetElement(DB.ElementId(type_id))
        if elem and isinstance(elem, DB.FamilySymbol):
            if not elem.IsActive:
                elem.Activate()
            return elem
    except Exception:
        pass
    return None


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


def is_entrance_door(door_info):
    """Проверяет, является ли дверь входной по имени типа."""
    type_name = door_info.get("type_name", "") or ""
    type_name_lower = type_name.lower()
    
    for pattern in ENTRANCE_DOOR_PATTERNS:
        if pattern.lower() in type_name_lower:
            return True
    
    # Также проверяем: входная дверь обычно имеет только одну комнату (to_room или from_room = None)
    from_room = door_info.get("from_room")
    to_room = door_info.get("to_room")
    if (from_room is None) != (to_room is None):
        # Одна сторона двери не имеет комнаты - вероятно входная
        return True
    
    return False


def get_room_separation_lines(link_doc, room, link_transform):
    """
    Находит Room Separation Lines, граничащие с комнатой.
    
    Returns:
        list of dicts with keys: line_start, line_end, line_center, line_direction
    """
    separation_lines = []
    
    try:
        # Получаем BoundingBox комнаты для фильтрации
        room_bb = room.get_BoundingBox(None)
        if not room_bb:
            return separation_lines
        
        # Собираем все Room Separation Lines
        collector = DB.FilteredElementCollector(link_doc) \
            .OfCategory(DB.BuiltInCategory.OST_RoomSeparationLines) \
            .WhereElementIsNotElementType()
        
        for elem in collector:
            try:
                # Получаем геометрию линии
                geom = elem.get_Geometry(DB.Options())
                if not geom:
                    continue
                    
                for geom_obj in geom:
                    if isinstance(geom_obj, DB.Line):
                        p0 = geom_obj.GetEndPoint(0)
                        p1 = geom_obj.GetEndPoint(1)
                        
                        # Проверяем, находится ли линия рядом с комнатой
                        # Расширяем BB комнаты на 100мм для поиска
                        tolerance = mm_to_ft(100)
                        
                        line_center = DB.XYZ(
                            (p0.X + p1.X) / 2,
                            (p0.Y + p1.Y) / 2,
                            (p0.Z + p1.Z) / 2
                        )
                        
                        # Проверяем, что центр линии в пределах BB комнаты (с допуском)
                        if (room_bb.Min.X - tolerance <= line_center.X <= room_bb.Max.X + tolerance and
                            room_bb.Min.Y - tolerance <= line_center.Y <= room_bb.Max.Y + tolerance):
                            
                            # Трансформируем точки
                            p0_t = link_transform.OfPoint(p0)
                            p1_t = link_transform.OfPoint(p1)
                            center_t = link_transform.OfPoint(line_center)
                            
                            dx = p1_t.X - p0_t.X
                            dy = p1_t.Y - p0_t.Y
                            length = math.sqrt(dx * dx + dy * dy)
                            
                            if length > mm_to_ft(300):  # Минимум 300мм
                                direction = DB.XYZ(dx / length, dy / length, 0)
                                
                                separation_lines.append({
                                    "line_start": p0_t,
                                    "line_end": p1_t,
                                    "line_center": center_t,
                                    "line_direction": direction,
                                    "line_length": length,
                                    "element": elem,
                                })
                    
                    elif isinstance(geom_obj, DB.GeometryInstance):
                        # Иногда геометрия обёрнута в GeometryInstance
                        inst_geom = geom_obj.GetInstanceGeometry()
                        for sub_obj in inst_geom:
                            if isinstance(sub_obj, DB.Line):
                                p0 = sub_obj.GetEndPoint(0)
                                p1 = sub_obj.GetEndPoint(1)
                                
                                tolerance = mm_to_ft(100)
                                line_center = DB.XYZ(
                                    (p0.X + p1.X) / 2,
                                    (p0.Y + p1.Y) / 2,
                                    (p0.Z + p1.Z) / 2
                                )
                                
                                if (room_bb.Min.X - tolerance <= line_center.X <= room_bb.Max.X + tolerance and
                                    room_bb.Min.Y - tolerance <= line_center.Y <= room_bb.Max.Y + tolerance):
                                    
                                    p0_t = link_transform.OfPoint(p0)
                                    p1_t = link_transform.OfPoint(p1)
                                    center_t = link_transform.OfPoint(line_center)
                                    
                                    dx = p1_t.X - p0_t.X
                                    dy = p1_t.Y - p0_t.Y
                                    length = math.sqrt(dx * dx + dy * dy)
                                    
                                    if length > mm_to_ft(300):
                                        direction = DB.XYZ(dx / length, dy / length, 0)
                                        
                                        separation_lines.append({
                                            "line_start": p0_t,
                                            "line_end": p1_t,
                                            "line_center": center_t,
                                            "line_direction": direction,
                                            "line_length": length,
                                            "element": elem,
                                        })
            except Exception:
                continue
                
    except Exception:
        pass
    
    return separation_lines


def find_wall_near_point(link_doc, link_transform, point, search_radius_mm=500):
    """
    Находит ближайшую стену к заданной точке.
    
    Returns:
        (wall, p0, p1, width) or (None, None, None, None)
    """
    try:
        search_radius = mm_to_ft(search_radius_mm)
        
        walls = DB.FilteredElementCollector(link_doc) \
            .OfCategory(DB.BuiltInCategory.OST_Walls) \
            .WhereElementIsNotElementType() \
            .ToElements()
        
        closest_wall = None
        closest_dist = float('inf')
        closest_p0 = None
        closest_p1 = None
        closest_width = None
        
        for wall in walls:
            p0, p1, width = get_wall_curve_and_width(wall)
            if not p0 or not p1:
                continue
            
            p0_t = link_transform.OfPoint(p0)
            p1_t = link_transform.OfPoint(p1)
            
            # Расстояние от точки до линии стены
            dx = p1_t.X - p0_t.X
            dy = p1_t.Y - p0_t.Y
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1e-9:
                continue
            
            # Проекция точки на линию стены
            t = ((point.X - p0_t.X) * dx + (point.Y - p0_t.Y) * dy) / (length * length)
            t = max(0, min(1, t))  # Clamp to line segment
            
            proj_x = p0_t.X + t * dx
            proj_y = p0_t.Y + t * dy
            
            dist = math.sqrt((point.X - proj_x) ** 2 + (point.Y - proj_y) ** 2)
            
            if dist < closest_dist and dist < search_radius:
                closest_dist = dist
                closest_wall = wall
                closest_p0 = p0_t
                closest_p1 = p1_t
                closest_width = width
        
        return closest_wall, closest_p0, closest_p1, closest_width
        
    except Exception:
        return None, None, None, None


def calc_switch_position_from_separation_line(sep_line_info, room, link_transform, link_doc):
    """
    Вычисляет позицию выключателя для комнаты без двери,
    используя Room Separation Line как виртуальный вход.
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
    
    # Определяем сторону стены (внутри комнаты)
    room_center = get_room_center(room)
    surface_sign = 1
    
    if room_center:
        room_center_t = link_transform.OfPoint(room_center)
        to_room_x = room_center_t.X - axis_x
        to_room_y = room_center_t.Y - axis_y
        room_dot = to_room_x * wall_normal.X + to_room_y * wall_normal.Y
        surface_sign = 1 if room_dot >= 0 else -1
    
    surface_x = axis_x + wall_normal.X * half_width * surface_sign
    surface_y = axis_y + wall_normal.Y * half_width * surface_sign
    surface_z = line_center.Z + mm_to_ft(SWITCH_HEIGHT_MM)
    
    point = DB.XYZ(surface_x, surface_y, surface_z)
    rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2
    
    return point, rotation


def get_outlet_symbol(doc):
    """Получает символ розетки по ID."""
    try:
        elem = doc.GetElement(DB.ElementId(OUTLET_TYPE_ID))
        if elem and isinstance(elem, DB.FamilySymbol):
            if not elem.IsActive:
                elem.Activate()
            return elem
    except Exception:
        pass
    return None


def calc_outlet_position(door_info, reference_room, link_transform):
    """Вычисляет позицию розетки около двери (внутри комнаты).
    
    Розетка размещается на высоте OUTLET_HEIGHT_MM, со стороны ручки двери.
    """
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

        # Определяем сторону ручки (аналогично calc_switch_position)
        type_name = door_info.get("type_name", "") or ""
        type_name_lower = type_name.lower()
        
        door_hand_from_name = None
        if re.search(r'[_\s\-]лв(?:[_\s\-]|$)|лв$', type_name_lower):
            door_hand_from_name = "left"
        elif re.search(r'[_\s\-]пр(?:[_\s\-]|$)|пр$', type_name_lower):
            door_hand_from_name = "right"
        elif re.search(r'[_\s\-]л(?:[_\s\-]|$)|(?<![а-я])л$', type_name_lower):
            door_hand_from_name = "left"
        elif re.search(r'[_\s\-]п(?:[_\s\-]|$)|(?<![а-я])п$', type_name_lower):
            door_hand_from_name = "right"
        
        if door_hand_from_name:
            if facing:
                facing_host = link_transform.OfVector(facing)
                if door_hand_from_name == "left":
                    handle_dir = DB.XYZ(-facing_host.Y, facing_host.X, 0)
                else:
                    handle_dir = DB.XYZ(facing_host.Y, -facing_host.X, 0)
            else:
                handle_dir = wall_dir if door_hand_from_name == "right" else DB.XYZ(-wall_dir.X, -wall_dir.Y, 0)
            handle_dot = handle_dir.X * wall_dir.X + handle_dir.Y * wall_dir.Y
            side_along_wall = 1 if handle_dot >= 0 else -1
        elif hand:
            hand_host = link_transform.OfVector(hand)
            handle_dir = DB.XYZ(-hand_host.X, -hand_host.Y, 0)
            handle_dot = handle_dir.X * wall_dir.X + handle_dir.Y * wall_dir.Y
            side_along_wall = 1 if handle_dot >= 0 else -1
        else:
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
        if door_width < mm_to_ft(600):
            door_width = mm_to_ft(900)

        half_door = door_width / 2.0
        jamb_offset = mm_to_ft(JAMB_OFFSET_MM)
        offset_from_center = half_door + jamb_offset

        t_outlet = t_door_center + side_along_wall * offset_from_center
        # Ограничиваем только если выходим за пределы стены
        min_edge_offset = mm_to_ft(50)
        t_outlet = max(min_edge_offset, min(length - min_edge_offset, t_outlet))

        axis_x = wall_p0.X + wall_dir.X * t_outlet
        axis_y = wall_p0.Y + wall_dir.Y * t_outlet

        half_width = wall_width / 2.0

        # Размещаем розетку внутри прихожей (со стороны reference_room)
        surface_sign = 1
        if reference_room:
            ref_center = get_room_center(reference_room)
            if ref_center:
                ref_center_host = link_transform.OfPoint(ref_center)
                to_ref_x = ref_center_host.X - axis_x
                to_ref_y = ref_center_host.Y - axis_y
                ref_dot = to_ref_x * wall_normal.X + to_ref_y * wall_normal.Y
                surface_sign = 1 if ref_dot >= 0 else -1

        surface_x = axis_x + wall_normal.X * half_width * surface_sign
        surface_y = axis_y + wall_normal.Y * half_width * surface_sign
        surface_z = center_host.Z + mm_to_ft(OUTLET_HEIGHT_MM)

        point = DB.XYZ(surface_x, surface_y, surface_z)
        rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2

        return point, rotation

    return None, None


def place_outlet(doc, symbol, point, rotation, level):
    """Размещает розетку."""
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
                p.Set(COMMENT_TAG_OUTLET)
        except Exception:
            pass
        return inst
    except Exception:
        return None
