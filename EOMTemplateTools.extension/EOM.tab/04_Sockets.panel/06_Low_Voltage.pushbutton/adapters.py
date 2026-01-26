# -*- coding: utf-8 -*-

import config_loader
import link_reader
import placement_engine
import socket_utils as su
from pyrevit import DB, forms, revit
import constants
import domain


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


def get_all_linked_rooms(link_doc):
    return su._get_all_linked_rooms(link_doc)


def pick_socket_symbol(doc, cfg, prefer, cache_prefix):
    return su._pick_socket_symbol(doc, cfg, prefer, cache_prefix=cache_prefix)


def collect_textnote_points(link_doc, keywords):
    return su._collect_textnote_points(link_doc, keywords)


def collect_independent_tag_points(link_doc, keywords):
    return su._collect_independent_tag_points(link_doc, keywords)


def collect_points_by_keywords(link_doc, keywords, bic):
    return su._collect_points_by_keywords(link_doc, keywords, bic)
