# -*- coding: utf-8 -*-


def _to_xyz_tuple(p):
    """Return (x, y, z) tuple from a sequence or object with X/Y/Z."""
    if hasattr(p, 'X') and hasattr(p, 'Y') and hasattr(p, 'Z'):
        return (float(p.X), float(p.Y), float(p.Z))
    try:
        return (float(p[0]), float(p[1]), float(p[2]))
    except Exception:
        raise ValueError('Unsupported point type: {0}'.format(type(p)))


def midpoint(p1, p2):
    """Return midpoint of two 3D points as (x, y, z) tuple."""
    x1, y1, z1 = _to_xyz_tuple(p1)
    x2, y2, z2 = _to_xyz_tuple(p2)
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0, (z1 + z2) / 2.0)
