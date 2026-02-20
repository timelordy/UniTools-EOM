# -*- coding: utf-8 -*-

import config_loader
from pyrevit import DB, forms, revit
from utils_revit import alert, log_exception
import link_reader
import placement_engine
import socket_utils
from domain import norm


def get_rules():
    try:
        return config_loader.load_rules()
    except Exception:
        log_exception('Failed to load rules')
        return {}


def select_link_instance_ru(host_doc, title):
    return link_reader.select_link_instance_auto(host_doc)


def collect_existing_lights_centers(doc, tolerance_ft=1.5):
    """Return list of (X, Y, Z) for ALL existing lights in project."""
    centers = []
    # Collect ALL lighting fixtures, regardless of type
    col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsNotElementType()
    for e in col:
        try:
            loc = e.Location
            if loc and hasattr(loc, 'Point'):
                centers.append(loc.Point)
        except Exception:
            continue
    return centers


def find_family_symbol(doc, family_name, category_bic):
    """Find symbol by exact/flexible matching.

    Supports values like:
    - "Family : Type"
    - "TypeName"
    - full file paths from task docs (e.g. "...\\(FL)_НПБ_1101.rfa")
    """
    if not doc or not family_name:
        return None

    def _aliases(value):
        raw = value or u''
        out = [raw]

        # Extract basename from path-like inputs.
        base = raw.replace('\\', '/').split('/')[-1].strip()
        if base and base not in out:
            out.append(base)

        # Trim common file suffixes used in task docs.
        trims = []
        for item in list(out):
            t = item
            low = t.lower()
            if low.endswith('.rfa'):
                t = t[:-4]
                trims.append(t)
            low = t.lower()
            if low.endswith('.zip'):
                t = t[:-4]
                trims.append(t)
        for t in trims:
            if t and t not in out:
                out.append(t)

        return [x for x in out if x]

    def _norm_key(value):
        t = norm(value)
        if not t:
            return u''
        try:
            t = t.replace('\\', '/').split('/')[-1]
        except Exception:
            pass
        try:
            if t.endswith('.rfa'):
                t = t[:-4]
            if t.endswith('.zip'):
                t = t[:-4]
        except Exception:
            pass
        try:
            t = u' '.join(t.split())
        except Exception:
            pass
        return t

    # 1) Native lookup attempts.
    for alias in _aliases(family_name):
        try:
            sym = placement_engine.find_family_symbol(doc, alias, category_bic=category_bic)
        except Exception:
            sym = None
        if sym is not None:
            return sym

    # 2) Fallback: fuzzy contains match by family/type label.
    keys = [_norm_key(a) for a in _aliases(family_name)]
    keys = [k for k in keys if k]
    if not keys:
        return None

    collector = placement_engine.iter_family_symbols(doc, category_bic=category_bic, limit=None)
    for s in collector:
        try:
            fam = getattr(getattr(s, 'Family', None), 'Name', u'') or getattr(s, 'FamilyName', u'') or u''
        except Exception:
            fam = u''
        try:
            typ = s.Name or u''
        except Exception:
            typ = u''
        try:
            lbl = placement_engine.format_family_type(s) or u''
        except Exception:
            lbl = u''

        hay = [
            _norm_key(fam),
            _norm_key(typ),
            _norm_key(lbl),
        ]
        for key in keys:
            if any(key and h and (key in h) for h in hay):
                return s

    return None


def iter_rooms(link_doc, level_id=None):
    return link_reader.iter_rooms(link_doc, level_id=level_id)


def iter_plumbing_fixtures(link_doc):
    if not link_doc:
        return []
    fixtures = []
    try:
        plumbing = (
            DB.FilteredElementCollector(link_doc)
            .OfCategory(DB.BuiltInCategory.OST_PlumbingFixtures)
            .WhereElementIsNotElementType()
        )
        fixtures.extend(list(plumbing))
    except Exception:
        pass
    try:
        # Some sink families are modeled as Furniture (e.g. 130_Сантехнические приборы_2D).
        furniture = (
            DB.FilteredElementCollector(link_doc)
            .OfCategory(DB.BuiltInCategory.OST_Furniture)
            .WhereElementIsNotElementType()
        )
        sink_tokens = (u'раковина', u'мойка', u'умывальник', u'сантех')
        for item in furniture:
            try:
                name = (item.Name or u'').lower()
            except Exception:
                name = u''
            if name and any(token in name for token in sink_tokens):
                fixtures.append(item)
    except Exception:
        pass
    return fixtures
        
def iter_doors(link_doc):
    return link_reader.iter_doors(link_doc)


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
                continue
        return lst
    except Exception:
        return None
