# -*- coding: utf-8 -*-

import config_loader
import link_reader
import placement_engine
import socket_utils as su
from pyrevit import DB, forms, revit
from pyrevit.framework import List


def get_rules():
    return config_loader.load_rules()


def get_config():
    from pyrevit import script
    return script.get_config()


def save_config():
    from pyrevit import script
    script.save_config()


def select_link_instance(doc, title):
    return su._select_link_instance_ru(doc, title)


def get_link_doc(link_inst):
    return link_reader.get_link_doc(link_inst)


def get_total_transform(link_inst):
    return link_reader.get_total_transform(link_inst)


def get_all_linked_rooms(link_doc, limit):
    return su._get_all_linked_rooms(link_doc, limit=limit)


def collect_sinks_points(link_doc, rules):
    return su._collect_sinks_points(link_doc, rules)


def collect_stoves_points(link_doc, rules):
    return su._collect_stoves_points(link_doc, rules)


def pick_socket_symbol(doc, cfg, prefer):
    return su._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_kitchen_unit')


def find_symbol_by_fullname(doc, name):
    return su._find_symbol_by_fullname(doc, name)


def format_family_type(sym):
    return placement_engine.format_family_type(sym)


def collect_host_socket_instances(host_doc):
    items = []
    if host_doc is None:
        return items
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            if not su._is_socket_instance(e):
                continue
            pt = su._inst_center_point(e)
            if pt:
                items.append((e, pt))
    return items


def pick_linked_element_any(link_inst, prompt):
    if link_inst is None:
        return None

    uidoc = revit.uidoc
    if uidoc is None:
        return None

    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class _AnyLinkedFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return elem and elem.Id == link_inst.Id
            except Exception:
                return False

        def AllowReference(self, reference, position):
            try:
                if reference is None:
                    return False
                if reference.ElementId != link_inst.Id:
                    return False
                if reference.LinkedElementId is None or reference.LinkedElementId == DB.ElementId.InvalidElementId:
                    return False
                return True
            except Exception:
                return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.LinkedElement, _AnyLinkedFilter(), prompt)
    except Exception:
        return None

    try:
        if r is None or r.ElementId != link_inst.Id:
            return None
    except Exception:
        return None

    ldoc = link_inst.GetLinkDocument()
    if ldoc is None:
        return None
    try:
        return ldoc.GetElement(r.LinkedElementId)
    except Exception:
        return None


def collect_family_instance_points_by_symbol_id(link_doc, symbol_id_int):
    pts = []
    if link_doc is None or symbol_id_int is None:
        return pts
    try:
        want = int(symbol_id_int)
    except Exception:
        return pts
    try:
        col = (
            DB.FilteredElementCollector(link_doc)
            .OfClass(DB.FamilyInstance)
            .WhereElementIsNotElementType()
        )
    except Exception:
        col = None
    if not col:
        return pts
    for inst in col:
        try:
            sid = int(inst.Symbol.Id.IntegerValue)
        except Exception:
            continue
        if sid != want:
            continue
        try:
            pt = su._inst_center_point(inst)
        except Exception:
            pt = None
        if pt:
            pts.append(pt)
    return pts
