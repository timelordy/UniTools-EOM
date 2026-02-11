# -*- coding: utf-8 -*-
import math

from pyrevit import DB

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


def _xy_distance(p1, p2):
    try:
        return math.sqrt((p1.X - p2.X) ** 2 + (p1.Y - p2.Y) ** 2)
    except Exception:
        return float('inf')


def _get_wall_host_geometry(wall, link_transform):
    """Возвращает геометрию стены в координатах host-документа."""
    try:
        p0, p1, width = get_wall_curve_and_width(wall)
        if not p0 or not p1:
            return None, None, None, None, None

        p0_t = link_transform.OfPoint(p0)
        p1_t = link_transform.OfPoint(p1)

        dx = p1_t.X - p0_t.X
        dy = p1_t.Y - p0_t.Y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-9:
            return None, None, None, None, None

        direction = DB.XYZ(dx / length, dy / length, 0)
        return p0_t, p1_t, width, length, direction
    except Exception:
        return None, None, None, None, None


def _project_point_to_segment(point, seg_p0, seg_p1):
    """Проекция точки на отрезок в XY. Возвращает (proj_point, t_clamped, dist)."""
    try:
        dx = seg_p1.X - seg_p0.X
        dy = seg_p1.Y - seg_p0.Y
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-9:
            return seg_p0, 0.0, _xy_distance(point, seg_p0)

        t = ((point.X - seg_p0.X) * dx + (point.Y - seg_p0.Y) * dy) / seg_len_sq
        t_clamped = max(0.0, min(1.0, t))

        proj_point = DB.XYZ(
            seg_p0.X + dx * t_clamped,
            seg_p0.Y + dy * t_clamped,
            seg_p0.Z,
        )
        dist = _xy_distance(point, proj_point)
        return proj_point, t_clamped, dist
    except Exception:
        return None, 0.0, float('inf')


def _is_point_in_room_host(room, point_host, link_transform):
    """Проверяет принадлежность точки (host coords) комнате (link coords). Возвращает True/False/None."""
    if not room or not point_host or not link_transform:
        return None
    try:
        inv = link_transform.Inverse
        point_link = inv.OfPoint(point_host)
        return bool(room.IsPointInRoom(point_link))
    except Exception:
        return None


def _get_connected_wall_candidates(current_wall, joint_point, link_doc, link_transform, preferred_dir, visited_ids, allow_backward=False):
    """Ищет стены, примыкающие к узлу (joint_point), и ориентирует их от узла наружу.

    Поддерживает 2 типа соединений:
    - endpoint: узел совпадает с концом стены;
    - segment: узел попадает в середину длинной стены (T-узел).
    """
    candidates = []
    if not link_doc or not joint_point:
        return candidates

    try:
        endpoint_tolerance = mm_to_ft(120)
        segment_tolerance = mm_to_ft(120)
        min_length = mm_to_ft(100)

        walls = DB.FilteredElementCollector(link_doc) \
            .OfCategory(DB.BuiltInCategory.OST_Walls) \
            .WhereElementIsNotElementType() \
            .ToElements()

        for wall in walls:
            try:
                wall_id = wall.Id.IntegerValue
            except Exception:
                continue

            if current_wall and wall.Id == current_wall.Id:
                continue
            if wall_id in visited_ids:
                continue

            wp0_t, wp1_t, wwidth, wlength, _ = _get_wall_host_geometry(wall, link_transform)
            if not wp0_t or not wp1_t:
                continue
            if wlength < min_length:
                continue

            dist_to_p0 = _xy_distance(wp0_t, joint_point)
            dist_to_p1 = _xy_distance(wp1_t, joint_point)
            proj_point, _, dist_to_segment = _project_point_to_segment(joint_point, wp0_t, wp1_t)

            connected_by_endpoint = (dist_to_p0 <= endpoint_tolerance) or (dist_to_p1 <= endpoint_tolerance)
            connected_by_segment = dist_to_segment <= segment_tolerance

            if not connected_by_endpoint and not connected_by_segment:
                continue

            local_candidates = []

            if connected_by_endpoint:
                # Классический случай: продолжаем от ближайшего конца стены
                if dist_to_p0 <= dist_to_p1:
                    start = wp0_t
                    end = wp1_t
                else:
                    start = wp1_t
                    end = wp0_t

                seg_len = _xy_distance(start, end)
                if seg_len >= min_length:
                    dir_from_joint = DB.XYZ(
                        (end.X - start.X) / seg_len,
                        (end.Y - start.Y) / seg_len,
                        0,
                    )
                    local_candidates.append((start, end, dir_from_joint, seg_len, "endpoint"))

            elif connected_by_segment and proj_point:
                # T-узел: узел лежит в середине стены, можно идти в обе стороны
                len_to_p0 = _xy_distance(proj_point, wp0_t)
                len_to_p1 = _xy_distance(proj_point, wp1_t)

                if len_to_p0 >= min_length:
                    dir_to_p0 = DB.XYZ(
                        (wp0_t.X - proj_point.X) / len_to_p0,
                        (wp0_t.Y - proj_point.Y) / len_to_p0,
                        0,
                    )
                    local_candidates.append((proj_point, wp0_t, dir_to_p0, len_to_p0, "segment_to_p0"))

                if len_to_p1 >= min_length:
                    dir_to_p1 = DB.XYZ(
                        (wp1_t.X - proj_point.X) / len_to_p1,
                        (wp1_t.Y - proj_point.Y) / len_to_p1,
                        0,
                    )
                    local_candidates.append((proj_point, wp1_t, dir_to_p1, len_to_p1, "segment_to_p1"))

            for start, end, dir_from_joint, seg_len, connection_kind in local_candidates:
                score = 0.0
                if preferred_dir:
                    score = preferred_dir.X * dir_from_joint.X + preferred_dir.Y * dir_from_joint.Y
                    # Не ходим явно назад (разворот почти на 180°), если не включён relaxed fallback
                    if (not allow_backward) and score < -0.5:
                        continue

                candidates.append({
                    "wall": wall,
                    "wall_id": wall_id,
                    "start": start,
                    "end": end,
                    "width": wwidth,
                    "length": seg_len,
                    "dir": dir_from_joint,
                    "score": score,
                    "connection": connection_kind,
                })

        candidates.sort(key=lambda x: (x["score"], x["length"]), reverse=True)
    except Exception:
        return []

    return candidates


def _walk_along_connected_walls(start_wall, start_joint, remaining_distance, link_doc, link_transform, travel_dir):
    """Проходит по смежным стенам и возвращает стену/параметр, где нужно разместить выключатель."""
    if remaining_distance < 0:
        remaining_distance = 0

    visited_ids = set()
    try:
        if start_wall:
            visited_ids.add(start_wall.Id.IntegerValue)
    except Exception:
        pass

    current_wall = start_wall
    current_joint = start_joint
    preferred_dir = travel_dir

    hops = 0
    max_hops = 10

    while hops < max_hops:
        candidates = _get_connected_wall_candidates(
            current_wall,
            current_joint,
            link_doc,
            link_transform,
            preferred_dir,
            visited_ids,
            allow_backward=False,
        )

        # Relaxed fallback: если строгий фильтр по направлению ничего не дал,
        # разрешаем отклониться сильнее (нужно для неидеальных узлов/геометрии)
        if not candidates:
            candidates = _get_connected_wall_candidates(
                current_wall,
                current_joint,
                link_doc,
                link_transform,
                preferred_dir,
                visited_ids,
                allow_backward=True,
            )

        if not candidates:
            return None

        selected = None
        for cand in candidates:
            if cand["length"] >= remaining_distance:
                selected = cand
                break

        if not selected:
            selected = candidates[0]

        if remaining_distance <= selected["length"]:
            return {
                "wall": selected["wall"],
                "wall_id": selected["wall_id"],
                "wall_p0": selected["start"],
                "wall_p1": selected["end"],
                "wall_width": selected["width"],
                "wall_length": selected["length"],
                "wall_dir": selected["dir"],
                "t_on_wall": remaining_distance,
                "hops": hops + 1,
            }

        remaining_distance -= selected["length"]
        visited_ids.add(selected["wall_id"])
        current_wall = selected["wall"]
        current_joint = selected["end"]
        preferred_dir = selected["dir"]
        hops += 1

    return None


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
