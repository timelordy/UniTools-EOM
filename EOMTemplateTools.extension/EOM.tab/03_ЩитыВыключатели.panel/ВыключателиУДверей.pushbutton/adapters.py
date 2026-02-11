# -*- coding: utf-8 -*-
import math
import re
import os
import sys

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


try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)


SWITCH_STRONG_KEYWORDS = [u'выключ', u'switch']
SWITCH_NEGATIVE_KEYWORDS = [
    u'розет', u'socket', u'панел', u'щит', u'шк', u'panel', u'shk',
    u'свет', u'light', u'lum', u'светиль',
    u'датчик', u'sensor', u'detector', u'motion', u'pir', u'presence',
    u'проход', u'прк', u'перекрест', u'пкс', u'димер', u'dimmer'
]
SWITCH_1G_KEYWORDS = [u'1к', u'1-к', u'1 клав', u'одноклав', u'1gang', u'1-gang', u'1g', u'single', u'1кл']
SWITCH_2G_KEYWORDS = [u'2к', u'2-к', u'2 клав', u'двухклав', u'2gang', u'2-gang', u'2g', u'double', u'2кл']


def _ensure_lib_path():
    try:
        ext_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        lib_path = os.path.join(ext_dir, 'lib')
        if lib_path not in sys.path:
            sys.path.append(lib_path)
    except Exception:
        pass


def _load_rules():
    try:
        _ensure_lib_path()
        import config_loader
        return config_loader.load_rules()
    except Exception:
        return {}


def _norm(text):
    try:
        return re.sub(r'\s+', '', text).lower()
    except Exception:
        return u''


def _get_symbol_label(symbol):
    try:
        return u"{} : {}".format(symbol.Family.Name, symbol.Name)
    except Exception:
        try:
            return u"{}".format(symbol.Name)
        except Exception:
            return u''


def _iter_switch_symbols(doc):
    seen = set()
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        try:
            collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
            if bic:
                collector = collector.OfCategory(bic)
            for sym in collector:
                try:
                    sid = int(sym.Id.IntegerValue)
                except Exception:
                    sid = None
                if sid is not None and sid in seen:
                    continue
                if sid is not None:
                    seen.add(sid)
                yield sym
        except Exception:
            continue


def _find_symbol_by_name(doc, name_with_type):
    if not name_with_type:
        return None
    try:
        if ':' in name_with_type:
            parts = name_with_type.split(':')
            family_name = parts[0].strip()
            type_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            family_name = name_with_type.strip()
            type_name = ''
    except Exception:
        family_name = name_with_type
        type_name = ''

    for sym in _iter_switch_symbols(doc):
        try:
            fam = sym.Family.Name
            typ = sym.Name
            full_name = u"{} : {}".format(fam, typ)
            if full_name == name_with_type.strip():
                return sym
            if family_name and family_name.lower() in fam.lower():
                if (not type_name) or (type_name.lower() in typ.lower()):
                    return sym
        except Exception:
            continue
    return None


def _score_switch_symbol(symbol, want_two_gang=False):
    if symbol is None:
        return None
    label = _get_symbol_label(symbol)
    nlabel = _norm(label)
    if not nlabel:
        return None

    s = 0
    strong_hit = False
    for kw in SWITCH_STRONG_KEYWORDS:
        if _norm(kw) in nlabel:
            s += 80
            strong_hit = True
            break

    hit1 = any(_norm(kw) in nlabel for kw in SWITCH_1G_KEYWORDS)
    hit2 = any(_norm(kw) in nlabel for kw in SWITCH_2G_KEYWORDS)

    # Safety: require explicit switch/gang hints to avoid random devices
    if (not strong_hit) and (not hit1) and (not hit2):
        return None

    for kw in SWITCH_NEGATIVE_KEYWORDS:
        if _norm(kw) in nlabel:
            s -= 120

    if want_two_gang:
        if hit2:
            s += 60
        if hit1:
            s -= 30
    else:
        if hit1:
            s += 60
        if hit2:
            s -= 30

    return s


def _auto_pick_switch_symbol(doc, want_two_gang=False):
    best = None
    best_score = None
    for sym in _iter_switch_symbols(doc):
        sc = _score_switch_symbol(sym, want_two_gang=want_two_gang)
        if sc is None:
            continue
        if best is None or sc > best_score:
            best = sym
            best_score = sc
    return best


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
        rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2

        # DEBUG: side-choice diagnostics
        door_info["_debug_surface_sign"] = surface_sign
        door_info["_debug_surface_source"] = surface_source
        door_info["_debug_ref_probe_plus"] = ref_plus
        door_info["_debug_ref_probe_minus"] = ref_minus
        door_info["_debug_target_probe_plus"] = target_plus
        door_info["_debug_target_probe_minus"] = target_minus
        door_info["_debug_has_target_room"] = bool(target_room)

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
    # Fallback 1: try rules.default.json preferred names
    try:
        rules = _load_rules() or {}
        family_names = rules.get('family_type_names', {})
        key = 'switch_2g' if two_gang else 'switch_1g'
        names = family_names.get(key) or family_names.get('switch') or []
        if isinstance(names, _STRING_TYPES):
            names = [names]
        if isinstance(names, list):
            for name in names:
                sym = _find_symbol_by_name(doc, name)
                if sym:
                    if not sym.IsActive:
                        sym.Activate()
                    return sym
    except Exception:
        pass
    # Fallback 2: heuristic auto-pick by keywords
    try:
        sym = _auto_pick_switch_symbol(doc, want_two_gang=two_gang)
        if sym:
            if not sym.IsActive:
                sym.Activate()
            return sym
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
