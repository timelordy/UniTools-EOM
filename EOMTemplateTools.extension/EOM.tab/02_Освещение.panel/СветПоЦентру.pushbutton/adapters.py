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


def get_or_create_debug_view(doc, level_id):
    """Create or return a FloorPlan view named 'DEBUG_LIGHTS_<LevelName>'."""
    if doc is None or not level_id:
        return None

    level = doc.GetElement(level_id)
    if not level:
        return None

    view_name = 'DEBUG_LIGHTS_{0}'.format(level.Name)

    # Check existing
    col = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan).WhereElementIsNotElementType()
    for v in col:
        if v.Name == view_name and not v.IsTemplate:
            return v

    # Create new
    vft_id = None
    for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
        if vft.ViewFamily == DB.ViewFamily.FloorPlan:
            vft_id = vft.Id
            break

    if not vft_id:
        return None

    view = DB.ViewPlan.Create(doc, vft_id, level.Id)
    try:
        view.Name = view_name
        # Try to set view range to show lights (cut plane at 1500mm, top at 4000mm)
        vr = view.GetViewRange()
        vr.SetOffset(DB.PlanViewPlane.CutPlane, 5.0) # ~1500mm
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, 15.0) # ~4500mm
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, 0.0)
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, 0.0)
        view.SetViewRange(vr)
    except Exception:
        pass

    return view


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
    return placement_engine.find_family_symbol(doc, family_name, category_bic=category_bic)


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
