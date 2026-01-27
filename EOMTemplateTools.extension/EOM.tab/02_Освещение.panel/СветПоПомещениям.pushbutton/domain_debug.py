# -*- coding: utf-8 -*-


def points_debug_stats(points_xyz):
    pts = points_xyz or []
    if not pts:
        return None
    try:
        minx = pts[0].X
        miny = pts[0].Y
        minz = pts[0].Z
        maxx = pts[0].X
        maxy = pts[0].Y
        maxz = pts[0].Z
        for p in pts[1:]:
            if p.X < minx:
                minx = p.X
            if p.Y < miny:
                miny = p.Y
            if p.Z < minz:
                minz = p.Z
            if p.X > maxx:
                maxx = p.X
            if p.Y > maxy:
                maxy = p.Y
            if p.Z > maxz:
                maxz = p.Z

        return {
            'count': len(pts),
            'min': (minx, miny, minz),
            'max': (maxx, maxy, maxz),
        }
    except Exception:
        return None
