# -*- coding: utf-8 -*-
from pyrevit import DB


def count_tagged_instances(host_doc, tag):
    t = (tag or '').strip()
    if not t:
        return 0
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, t, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, t)
        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfCategory(DB.BuiltInCategory.OST_LightingFixtures)
               .WherePasses(pfilter))
        c = 0
        for _ in col:
            c += 1
        return c
    except Exception:
        return 0


def count_tagged_family_instances_any_category(host_doc, tag):
    t = (tag or '').strip()
    if not t:
        return 0
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, t, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, t)
        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfClass(DB.FamilyInstance)
               .WherePasses(pfilter))
        c = 0
        for _ in col:
            c += 1
        return c
    except Exception:
        return 0


def bbox_from_element_ids(doc, ids, pad_ft=30.0, limit=500):
    if doc is None or not ids:
        return None
    try:
        pad = float(pad_ft or 0.0)
        minx = None
        miny = None
        minz = None
        maxx = None
        maxy = None
        maxz = None
        i = 0
        for eid in ids:
            i += 1
            if limit and i > int(limit):
                break
            e = None
            try:
                e = doc.GetElement(eid)
            except Exception:
                e = None
            if e is None:
                continue

            p = None
            try:
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                p = None

            if p is None:
                try:
                    bb = e.get_BoundingBox(None)
                    if bb:
                        p = (bb.Min + bb.Max) * 0.5
                except Exception:
                    p = None

            if p is None:
                continue

            if minx is None:
                minx = p.X
                miny = p.Y
                minz = p.Z
                maxx = p.X
                maxy = p.Y
                maxz = p.Z
            else:
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

        if minx is None:
            return None

        bb2 = DB.BoundingBoxXYZ()
        bb2.Min = DB.XYZ(minx - pad, miny - pad, minz - pad)
        bb2.Max = DB.XYZ(maxx + pad, maxy + pad, maxz + pad)
        return bb2
    except Exception:
        return None
