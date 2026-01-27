# -*- coding: utf-8 -*-

from pyrevit import DB
import math


def points_in_room(points, room, link_doc=None):
    """Фильтрует точки, находящиеся внутри помещения"""
    if not points:
        return []

    result = []
    try:
        # Получаем границы помещения
        room_boundaries = get_room_boundaries(room, link_doc)
        if not room_boundaries:
            return []

        for pt in points:
            if is_point_in_boundary(pt, room_boundaries):
                result.append(pt)

    except Exception:
        pass

    return result


def get_room_boundaries(room, link_doc=None):
    """Получает границы помещения как список сегментов стен"""
    try:
        # Используем Room boundary
        options = DB.SpatialElementBoundaryOptions()
        segments = room.GetBoundarySegments(options)

        if not segments:
            return []

        boundaries = []
        for seg_list in segments:
            for seg in seg_list:
                boundaries.append((seg.GetCurve().GetEndPoint(0), seg.GetCurve().GetEndPoint(1)))

        return boundaries
    except Exception:
        return []


def is_point_in_boundary(point, boundaries):
    """Проверяет, находится ли точка внутри границы"""
    try:
        x, y = point.X, point.Y
        inside = False

        for p0, p1 in boundaries:
            x1, y1 = p0.X, p0.Y
            x2, y2 = p1.X, p1.Y

            # Проверка пересечения луча
            if ((y1 > y) != (y2 > y)):
                x_intersect = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < x_intersect:
                    inside = not inside

        return inside
    except Exception:
        return False


def get_wall_segments(room, link_doc=None):
    """Получает сегменты стен помещения"""
    boundaries = get_room_boundaries(room, link_doc)
    if not boundaries:
        return []

    return [(p0, p1, None) for p0, p1 in boundaries]


def nearest_segment(point, segments):
    """Находит ближайший сегмент к точке"""
    if not segments:
        return None, None, None

    best_seg = None
    best_proj = None
    best_dist = float('inf')

    for p0, p1, wall in segments:
        proj = closest_point_on_segment_xy(point, p0, p1)
        dist = point.DistanceTo(proj)

        if dist < best_dist:
            best_dist = dist
            best_proj = proj
            best_seg = (p0, p1, wall)

    return best_seg if best_seg else (None, None, None), best_proj, best_dist


def closest_point_on_segment_xy(point, p0, p1):
    """Находит ближайшую точку на отрезке в XY плоскости"""
    try:
        v = DB.XYZ(p1.X - p0.X, p1.Y - p0.Y, 0)
        w = DB.XYZ(point.X - p0.X, point.Y - p0.Y, 0)

        c1 = v.X * w.X + v.Y * w.Y
        if c1 <= 0:
            return DB.XYZ(p0.X, p0.Y, point.Z)

        c2 = v.X * v.X + v.Y * v.Y
        if c2 <= c1:
            return DB.XYZ(p1.X, p1.Y, point.Z)

        b = c1 / c2
        pb = DB.XYZ(p0.X + b * v.X, p0.Y + b * v.Y, point.Z)
        return pb
    except Exception:
        return point


def dist_xy(p1, p2):
    """Расстояние между точками в XY плоскости"""
    try:
        dx = p1.X - p2.X
        dy = p1.Y - p2.Y
        return math.sqrt(dx * dx + dy * dy)
    except Exception:
        return float('inf')


def get_room_center(room):
    """Получает центр помещения"""
    try:
        # Проверяем LocationPoint
        loc = room.Location
        if loc and hasattr(loc, 'Point'):
            return loc.Point

        # Проверяем BoundingBox
        bbox = room.get_BoundingBox(None)
        if bbox:
            cx = (bbox.Min.X + bbox.Max.X) / 2
            cy = (bbox.Min.Y + bbox.Max.Y) / 2
            cz = (bbox.Min.Z + bbox.Max.Z) / 2
            return DB.XYZ(cx, cy, cz)

    except Exception:
        pass

    return None


def get_doors_in_room(room, link_doc):
    """Получает двери, принадлежащие помещению"""
    try:
        # Получаем все двери из линк-документа
        door_col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors)
        doors = door_col.ToElements()

        room_doors = []
        room_center = get_room_center(room)

        for door in doors:
            try:
                door_pt = get_element_location_point(door)
                if door_pt and room_center:
                    if dist_xy(door_pt, room_center) < 5000:  # 5м от центра
                        room_doors.append(door)
            except Exception:
                continue

        return room_doors
    except Exception:
        return []


def get_element_location_point(element):
    """Получает точку расположения элемента"""
    try:
        loc = element.Location
        if hasattr(loc, 'Point'):
            return loc.Point
        elif hasattr(loc, 'Curve'):
            curve = loc.Curve
            return curve.Evaluate(0.5, True)
    except Exception:
        pass
    return None
