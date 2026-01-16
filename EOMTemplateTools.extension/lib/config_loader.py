# -*- coding: utf-8 -*-

import io
import json
import os


def _extension_root_from_lib():
    # lib/<thisfile> -> extension_root
    return os.path.dirname(os.path.dirname(__file__))


def get_default_rules_path():
    return os.path.join(_extension_root_from_lib(), 'config', 'rules.default.json')


def load_rules(path=None):
    """Load rules JSON.

    If `path` is None uses extension `config/rules.default.json`.
    """
    rules_path = path or get_default_rules_path()
    try:
        with io.open(rules_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
    except Exception:
        # Common failure in pyRevit on Windows: relative working dir / encoding issues.
        # Try a raw open fallback and ensure BOM/encoding is handled.
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

    # Minimal normalization / defaults
    if 'comment_tag' not in data:
        data['comment_tag'] = 'AUTO_EOM'
    if 'family_type_names' not in data:
        data['family_type_names'] = {}
    if 'light_center_room_height_mm' not in data:
        data['light_center_room_height_mm'] = 2700
    if 'min_light_spacing_mm' not in data:
        data['min_light_spacing_mm'] = 800
    if 'allow_two_lights_per_room' not in data:
        data['allow_two_lights_per_room'] = False
    if 'max_lights_per_room' not in data:
        data['max_lights_per_room'] = 1
    if 'light_room_elongation_ratio' not in data:
        data['light_room_elongation_ratio'] = 2.2
    if 'light_two_centers_min_long_mm' not in data:
        data['light_two_centers_min_long_mm'] = 4500
    if 'exclude_room_name_keywords' not in data:
        data['exclude_room_name_keywords'] = [
            u'ниша',
            u'балкон',
            u'лодж',
            u'loggia',
            u'balcony',
            u'niche',
        ]
    if 'panel_above_door_offset_mm' not in data:
        data['panel_above_door_offset_mm'] = 300
    if 'dedupe_radius_mm' not in data:
        data['dedupe_radius_mm'] = 500
    if 'max_place_count' not in data:
        data['max_place_count'] = 200
    if 'batch_size' not in data:
        data['batch_size'] = 25
    if 'scan_limit_rooms' not in data:
        data['scan_limit_rooms'] = 500
    if 'scan_limit_doors' not in data:
        data['scan_limit_doors'] = 500
    if 'enable_existing_dedupe' not in data:
        data['enable_existing_dedupe'] = False
    if 'socket_spacing_mm' not in data:
        data['socket_spacing_mm'] = 3000
    if 'socket_height_mm' not in data:
        data['socket_height_mm'] = 300
    if 'avoid_door_mm' not in data:
        data['avoid_door_mm'] = 300
    if 'avoid_radiator_mm' not in data:
        data['avoid_radiator_mm'] = 500
    if 'socket_dedupe_radius_mm' not in data:
        data['socket_dedupe_radius_mm'] = 300
    if 'host_wall_search_mm' not in data:
        data['host_wall_search_mm'] = 300

    if 'debug_section_half_height_mm' not in data:
        # for debug 3D view section box Z slice around placement height
        data['debug_section_half_height_mm'] = 1500

    if 'lift_shaft_room_name_patterns' not in data:
        data['lift_shaft_room_name_patterns'] = [
            u'лифт',
            u'лифтов',
            u'шахт',
            u'elevator',
            u'lift',
            u'shaft',
        ]
    if 'lift_shaft_generic_model_keywords' not in data:
        data['lift_shaft_generic_model_keywords'] = list(data.get('lift_shaft_room_name_patterns') or [])
    if 'lift_shaft_family_names' not in data:
        data['lift_shaft_family_names'] = []
    if 'lift_shaft_room_exclude_patterns' not in data:
        data['lift_shaft_room_exclude_patterns'] = [
            u'машин',
            u'machine',
        ]
    if 'lift_shaft_generic_model_exclude_patterns' not in data:
        data['lift_shaft_generic_model_exclude_patterns'] = list(data.get('lift_shaft_room_exclude_patterns') or [])
    if 'lift_shaft_light_height_mm' not in data:
        data['lift_shaft_light_height_mm'] = 2500
    if 'lift_shaft_edge_offset_mm' not in data:
        data['lift_shaft_edge_offset_mm'] = 500
    if 'lift_shaft_min_wall_clearance_mm' not in data:
        data['lift_shaft_min_wall_clearance_mm'] = 300
    if 'lift_shaft_min_height_mm' not in data:
        data['lift_shaft_min_height_mm'] = 2000
    if 'lift_shaft_wall_search_mm' not in data:
        data['lift_shaft_wall_search_mm'] = 1000
    if 'lift_shaft_dedupe_radius_mm' not in data:
        data['lift_shaft_dedupe_radius_mm'] = 500

    return data
