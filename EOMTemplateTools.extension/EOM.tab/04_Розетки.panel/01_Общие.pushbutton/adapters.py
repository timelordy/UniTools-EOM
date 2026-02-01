# -*- coding: utf-8 -*-

import io
import json
from pyrevit import DB, forms
import config_loader
import link_reader
import placement_engine
try:
    import socket_utils as su
except ImportError:
    # Should be in path by now via script.py, but for robustness
    import sys, os
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su


def get_rules():
    return config_loader.load_rules()


def get_config():
    from pyrevit import script
    return script.get_config()


def save_config():
    from pyrevit import script
    script.save_config()


def pick_socket_symbol(doc, cfg, fam_names):
    return su._pick_socket_symbol(doc, cfg, fam_names, cache_prefix='socket_general')


def auto_pick_socket_symbol(doc):
    return su._auto_pick_socket_symbol(doc, prefer_fullname=None)


def save_default_rule(key, value):
    try:
        rules_path = config_loader.get_default_rules_path()
        with io.open(rules_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        fams2 = data.get('family_type_names', {}) or {}
        arr = fams2.get(key, [])
        if not isinstance(arr, list):
            arr = [arr] if arr else []
        if value and value not in arr:
            arr.insert(0, value)
        fams2[key] = arr
        data['family_type_names'] = fams2
        with io.open(rules_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except Exception:
        pass


def select_link_instance(doc, title):
    return su._select_link_instance_ru(doc, title)


def get_link_doc(link_inst):
    return link_reader.get_link_doc(link_inst)


def get_all_linked_rooms(link_doc, level_ids=None):
    return su._get_all_linked_rooms(link_doc, level_ids=level_ids)


def collect_radiator_points(link_doc):
    return su._collect_radiator_points(link_doc)


def get_total_transform(link_inst):
    return link_reader.get_total_transform(link_inst)


def place_socket_batch(doc, link_inst, transform, pending, sym_flags, sp_cache, comment_value, strict_hosting):
    return su._place_socket_batch(doc, link_inst, transform, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting)


def create_progress_bar(title, max_value):
    pb = forms.ProgressBar(title=title, cancellable=True)
    pb.max_value = max_value
    return pb
