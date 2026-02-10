# -*- coding: utf-8 -*-
"""Загрузчик конфигурации для EOM Template Tools.

Загружает правила из JSON конфигурационных файлов с разумными дефолтами.
Совместим с IronPython 2.7 (pyRevit).
"""
import io
import json
import os


def _extension_root_from_lib():
    """Получить корневую директорию расширения из расположения lib."""
    return os.path.dirname(os.path.dirname(__file__))


def get_default_rules_path():
    """Получить путь к файлу конфигурации по умолчанию."""
    return os.path.join(_extension_root_from_lib(), 'config', 'rules.default.json')


def load_rules(path=None):
    """Загрузить правила из JSON конфигурационного файла.

    Args:
        path: Путь к JSON конфиг-файлу. Если None, используется дефолтный файл правил.

    Returns:
        Словарь со всеми ключами конфигурации, с применёнными дефолтами.
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

    # Дефолтные значения
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
        'floor_panel_type_rules': [],
        'floor_panel_niche_patterns': [u'ниша', u'niche', u'эом', u'шахт'],
        'floor_panel_niche_patterns_single': [],
        'floor_panel_height_mm': 1700,
        'floor_panel_opening_type_names': [],
        'floor_panel_opening_room_patterns': [u'эом'],
        'floor_panel_min_wall_clearance_mm': 0,
        'floor_panel_dedupe_radius_mm': 300,
        'dedupe_radius_mm': 500,
        'max_place_count': 200,
        'batch_size': 25,
        'scan_limit_rooms': 500,
        'scan_limit_doors': 500,
        'apartment_param_names': [u'Квартира', u'Номер квартиры', u'ADSK_Номер квартиры', u'ADSK_Номер_квартиры', u'Apartment', u'Flat'],
        'apartment_require_param': True,
        'apartment_allow_department_fallback': False,
        'apartment_allow_room_number_fallback': False,
        'apartment_infer_from_rooms': True,
        'apartment_department_patterns': [u'кварт', u'apartment', u'flat'],
        'apartment_room_name_patterns': [u'кварт', u'кух', u'спаль', u'гост', u'прих', u'living', u'bed'],
        'apartment_exclude_department_patterns': [u'моп', u'tech', u'тех', u'офис', u'office'],

        # Специфичные переопределения для этажных щитов (ЩЭ).
        # Дефолтное поведение: определять количество квартир из помещений (даже если параметр квартиры отсутствует).
        'floor_panel_apartment_require_param': False,
        'floor_panel_apartment_infer_from_rooms': True,
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
