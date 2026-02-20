# -*- coding: utf-8 -*-

import config_loader
import link_reader
import placement_engine
import socket_utils as su
from pyrevit import DB, forms, revit
import constants
import domain
from utils_units import mm_to_ft, ft_to_mm


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


def get_all_linked_rooms(link_doc, limit=None, level_ids=None):
    return su._get_all_linked_rooms(link_doc, limit=limit, level_ids=level_ids)


def pick_socket_symbol(doc, cfg, prefer):
    return su._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_wet')


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


def collect_fixture_candidates(link_doc, keywords, categories, fixture_kind='wm'):
    fixtures = []
    if not link_doc:
        return fixtures
    key_norms = [su._norm(k) for k in (keywords or []) if k]
    for bic in categories:
        try:
            collector = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for elem in collector:
            try:
                label = su._elem_text(elem)
                norm_label = su._norm(label)
                if key_norms and not any(k in norm_label for k in key_norms):
                    continue
                center = su._inst_center_point(elem)
                if not center:
                    continue
                bbox = domain.get_2d_bbox(elem)
                if not bbox:
                    buf = mm_to_ft(350)
                    bbox = (
                        DB.XYZ(center.X - buf, center.Y - buf, 0.0),
                        DB.XYZ(center.X + buf, center.Y + buf, 0.0)
                    )
                fixtures.append(domain.Fixture2D(elem, center, bbox[0], bbox[1], kind=fixture_kind))
            except Exception:
                continue
    return fixtures


def collect_door_points(link_doc):
    pts = []
    if not link_doc:
        return pts
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
    except Exception:
        col = None
    if not col:
        return pts
    for e in col:
        try:
            pt = su._inst_center_point(e)
        except Exception:
            pt = None
        if pt:
            pts.append(pt)
    return pts
