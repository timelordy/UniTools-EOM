# -*- coding: utf-8 -*-

import math


LINE_EPS = 0.00853018372702215


def _to_xyz_tuple(point):
    if point is None:
        return None
    if hasattr(point, "X"):
        return (point.X, point.Y, point.Z)
    return (point[0], point[1], point[2])


def _distance(p1, p2):
    a = _to_xyz_tuple(p1)
    b = _to_xyz_tuple(p2)
    if a is None or b is None:
        return None
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def should_create_segment(p1, p2, min_len=LINE_EPS):
    dist = _distance(p1, p2)
    if dist is None:
        return False
    return dist > min_len
