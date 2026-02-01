# -*- coding: utf-8 -*-
"""Configuration loader for EOM Template Tools.

Loads rules from JSON configuration files with sensible defaults.
Compatible with IronPython 2.7 (pyRevit).
"""
import io
import json
import os


def _extension_root_from_lib():
    """Get extension root directory from lib location."""
    return os.path.dirname(os.path.dirname(__file__))


def get_default_rules_path():
    """Get the path to the default rules configuration file."""
    return os.path.join(_extension_root_from_lib(), 'config', 'rules.default.json')


def load_rules(path=None):
    """Load rules from JSON configuration file.
    
    Args:
        path: Path to JSON config file. If None, uses default rules file.
    
    Returns:
        Dictionary with all configuration keys, defaults applied.
    """
    rules_path = path or get_default_rules_path()
    try:
        with io.open(rules_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
    except Exception:
        try:
            with open(rules_path, 'rb') as fb:
                raw = fb.read()
            try:
                txt = raw.decode('utf-8-sig')
            except Exception:
                txt = raw.decode('utf-8')
            data = json.loads(txt)
        except Exception:
            raise

    # Defaults
    defaults = {
        'comment_tag': 'AUTO_EOM',
        'family_type_names': {},
        'light_center_room_height_mm': 2700,
        'min_light_spacing_mm': 800,
        'allow_two_lights_per_room': False,
        'max_lights_per_room': 1,
        'light_room_elongation_ratio': 2.2,
        'light_two_centers_min_long_mm': 4500,
        'exclude_room_name_keywords': [u'ниша', u'балкон', u'лодж', u'loggia', u'balcony', u'niche'],
        'panel_above_door_offset_mm': 300,
        'dedupe_radius_mm': 500,
        'max_place_count': 200,
        'batch_size': 25,
        'scan_limit_rooms': 500,
        'scan_limit_doors': 500,
        'enable_existing_dedupe': False,
        'socket_spacing_mm': 3000,
        'socket_height_mm': 300,
        'kitchen_fridge_height_mm': 300,
        'avoid_door_mm': 300,
        'avoid_radiator_mm': 500,
        'socket_dedupe_radius_mm': 300,
        'host_wall_search_mm': 300,
        'debug_section_half_height_mm': 1500,
        'lift_shaft_room_name_patterns': [u'лифт', u'лифтов', u'шахт', u'elevator', u'lift', u'shaft'],
        'lift_shaft_generic_model_keywords': [u'лифт', u'лифтов', u'шахт', u'elevator', u'lift', u'shaft'],
        'lift_shaft_family_names': [],
        'lift_shaft_room_exclude_patterns': [u'машин', u'machine'],
        'lift_shaft_generic_model_exclude_patterns': [u'машин', u'machine'],
        'lift_shaft_light_height_mm': 2500,
        'lift_shaft_edge_offset_mm': 500,
        'lift_shaft_min_wall_clearance_mm': 300,
        'lift_shaft_min_height_mm': 2000,
        'lift_shaft_wall_search_mm': 1000,
        'lift_shaft_dedupe_radius_mm': 500,
    }
    
    for key, val in defaults.items():
        if key not in data:
            data[key] = val
    
    return data
