# -*- coding: utf-8 -*-

import math
from pyrevit import DB
import socket_utils
import placement_engine


def as_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [v for v in val if v]
    return [val]


def is_wall_hosted(symbol):
    if symbol is None:
        return False
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.OneLevelBasedHosted:
            return True
    except Exception:
        pass
    try:
        if pt == DB.FamilyPlacementType.FaceBased:
            return True
    except Exception:
        pass
    try:
        if pt == DB.FamilyPlacementType.TwoLevelsBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and (u'host' in pt_name.lower() or u'face' in pt_name.lower() or u'wall' in pt_name.lower()):
            return True
    except Exception:
        pass
    return False


def is_one_level_based(symbol):
    if symbol is None:
        return False
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.OneLevelBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and u'onelevelbased' in pt_name.lower():
            return True
    except Exception:
        pass
    return False


def iter_solids(geom):
    if geom is None:
        return
    try:
        for go in geom:
            if isinstance(go, DB.Solid):
                try:
                    if float(go.Volume) > 1e-9:
                        yield go
                except Exception:
                    continue
            elif isinstance(go, DB.GeometryInstance):
                try:
                    inst_geom = go.GetInstanceGeometry()
                except Exception:
                    inst_geom = None
                if inst_geom is None:
                    continue
                for ig in inst_geom:
                    if isinstance(ig, DB.Solid):
                        try:
                            if float(ig.Volume) > 1e-9:
                                yield ig
                        except Exception:
                            continue
    except Exception:
        return


def solid_centroid(elem):
    if elem is None:
        return None
    try:
        opt = DB.Options()
        try:
            opt.DetailLevel = DB.ViewDetailLevel.Fine
        except Exception:
            pass
        try:
            opt.IncludeNonVisibleObjects = True
        except Exception:
            pass
        geom = elem.get_Geometry(opt)
    except Exception:
        geom = None

    if geom is None:
        return None

    total_vol = 0.0
    sx = sy = sz = 0.0
    for solid in iter_solids(geom):
        try:
            c = solid.ComputeCentroid()
            v = float(solid.Volume)
        except Exception:
            continue
        if c is None or v <= 1e-9:
            continue
        total_vol += v
        sx += float(c.X) * v
        sy += float(c.Y) * v
        sz += float(c.Z) * v
    if total_vol <= 1e-9:
        return None
    return DB.XYZ(sx / total_vol, sy / total_vol, sz / total_vol)


def geom_center_and_z(elem):
    if elem is None:
        return None, None, None, None, None
    center = solid_centroid(elem)
    try:
        bb = elem.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        return center, None, None, None, None
    try:
        minx = float(min(bb.Min.X, bb.Max.X))
        miny = float(min(bb.Min.Y, bb.Max.Y))
        minz = float(min(bb.Min.Z, bb.Max.Z))
        maxx = float(max(bb.Min.X, bb.Max.X))
        maxy = float(max(bb.Min.Y, bb.Max.Y))
        maxz = float(max(bb.Min.Z, bb.Max.Z))
        if center is None:
            center = DB.XYZ((minx + maxx) * 0.5, (miny + maxy) * 0.5, (minz + maxz) * 0.5)
        bmin = DB.XYZ(minx, miny, minz)
        bmax = DB.XYZ(maxx, maxy, maxz)
        return center, minz, maxz, bmin, bmax
    except Exception:
        return center, None, None, None, None


def bbox_contains_point(bmin, bmax, pt, eps=1e-6):
    if bmin is None or bmax is None or pt is None:
        return False
    try:
        return (float(bmin.X) - eps <= float(pt.X) <= float(bmax.X) + eps and
                float(bmin.Y) - eps <= float(pt.Y) <= float(bmax.Y) + eps and
                float(bmin.Z) - eps <= float(pt.Z) <= float(bmax.Z) + eps)
    except Exception:
        return False


def bbox_intersects(bmin, bmax, omin, omax, eps=1e-6):
    if bmin is None or bmax is None or omin is None or omax is None:
        return False
    try:
        return (float(bmin.X) - eps <= float(omax.X) and float(bmax.X) + eps >= float(omin.X) and
                float(bmin.Y) - eps <= float(omax.Y) and float(bmax.Y) + eps >= float(omin.Y) and
                float(bmin.Z) - eps <= float(omax.Z) and float(bmax.Z) + eps >= float(omin.Z))
    except Exception:
        return False


def expand_bbox_xy(bmin, bmax, delta):
    if bmin is None or bmax is None or delta is None:
        return bmin, bmax
    try:
        d = float(delta)
        return (DB.XYZ(float(bmin.X) - d, float(bmin.Y) - d, float(bmin.Z)),
                DB.XYZ(float(bmax.X) + d, float(bmax.Y) + d, float(bmax.Z)))
    except Exception:
        return bmin, bmax


def transform_bbox(t, bmin, bmax):
    if bmin is None or bmax is None:
        return None, None
    if t is None:
        return bmin, bmax
    try:
        xs = [float(bmin.X), float(bmax.X)]
        ys = [float(bmin.Y), float(bmax.Y)]
        zs = [float(bmin.Z), float(bmax.Z)]
        pts = []
        for x in xs:
            for y in ys:
                for z in zs:
                    pts.append(t.OfPoint(DB.XYZ(x, y, z)))
        minx = min([p.X for p in pts])
        miny = min([p.Y for p in pts])
        minz = min([p.Z for p in pts])
        maxx = max([p.X for p in pts])
        maxy = max([p.Y for p in pts])
        maxz = max([p.Z for p in pts])
        return DB.XYZ(minx, miny, minz), DB.XYZ(maxx, maxy, maxz)
    except Exception:
        return None, None


def norm_lift_name(s):
    try:
        t = socket_utils._norm(s)
    except Exception:
        t = (s or u'').strip().lower()
    try:
        t = t.replace(u'\u0425', u'x').replace(u'\u0445', u'x')
    except Exception:
        pass
    return t


def match_exact_names(txt, names):
    if not txt or not names:
        return False
    t = norm_lift_name(txt)
    for nm in names:
        nn = norm_lift_name(nm)
        if nn and (nn in t):
            return True
    return False


def segment_ranges(levels, shaft_min_z, shaft_max_z):
    if shaft_min_z is None or shaft_max_z is None:
        return []
    if not levels:
        return [(shaft_min_z, shaft_max_z)]

    out = []
    for i, lvl in enumerate(levels):
        try:
            bottom = float(lvl.Elevation)
        except Exception:
            continue

        if i + 1 < len(levels):
            try:
                top = float(levels[i + 1].Elevation)
            except Exception:
                top = None
        else:
            top = None

        seg_min = max(bottom, shaft_min_z)
        seg_max = shaft_max_z if top is None else min(top, shaft_max_z)
        if seg_max <= seg_min:
            continue
        out.append((seg_min, seg_max))
    return out


def chunks(seq, n):
    if not seq:
        return
    n = max(int(n or 1), 1)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]
