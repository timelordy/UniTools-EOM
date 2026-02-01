# -*- coding: utf-8 -*-
from pyrevit import DB


def load_symbol_from_saved_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        try:
            eid = DB.ElementId(int(val))
        except Exception:
            return None
        e = doc.GetElement(eid)
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def load_symbol_from_saved_unique_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc.GetElement(str(uid))
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def store_symbol_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, int(symbol.Id.IntegerValue))
    except Exception:
        pass


def store_symbol_unique_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


def as_net_id_list(ids):
    """Convert python list[ElementId] to .NET List[ElementId] for Revit API calls."""
    try:
        from System.Collections.Generic import List
        lst = List[DB.ElementId]()
        for i in ids or []:
            try:
                if i is not None:
                    lst.Add(i)
            except Exception:
                pass
        return lst
    except Exception:
        return None


def get_or_create_debug_3d_view(doc, name, aliases=None):
    try:
        aliases = list(aliases or [])

        # Reuse if exists (primary)
        for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    return v
            except Exception:
                continue

        # Reuse by alias and rename to primary
        if aliases:
            for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
                try:
                    if not v or v.IsTemplate:
                        continue
                    if v.Name in aliases:
                        try:
                            v.Name = name
                        except Exception:
                            pass
                        return v
                except Exception:
                    continue

        vft_id = None
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.ThreeDimensional:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
        if vft_id is None:
            return None

        v3d = DB.View3D.CreateIsometric(doc, vft_id)
        try:
            v3d.Name = name
        except Exception:
            pass
        return v3d
    except Exception:
        return None


def bbox_from_points(points_xyz, pad_ft=20.0):
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

        pad = float(pad_ft or 0.0)
        bb = DB.BoundingBoxXYZ()
        bb.Min = DB.XYZ(minx - pad, miny - pad, minz - pad)
        bb.Max = DB.XYZ(maxx + pad, maxy + pad, maxz + pad)
        return bb
    except Exception:
        return None
