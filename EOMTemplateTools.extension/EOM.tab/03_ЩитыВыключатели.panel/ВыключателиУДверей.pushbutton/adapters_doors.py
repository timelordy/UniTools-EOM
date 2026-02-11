# -*- coding: utf-8 -*-

from pyrevit import DB

from constants import ENTRANCE_DOOR_PATTERNS
from domain import mm_to_ft
from adapters_geometry import get_door_host_wall, get_wall_curve_and_width


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
