# -*- coding: utf-8 -*-
import math
import re

from pyrevit import DB

from constants import COMMENT_TAG_OUTLET, JAMB_OFFSET_MM, OUTLET_HEIGHT_MM, OUTLET_TYPE_ID
from domain import mm_to_ft
from adapters_geometry import get_room_center


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
