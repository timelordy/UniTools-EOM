# -*- coding: utf-8 -*-

from pyrevit import DB
import placement_engine
from domain import as_list, is_wall_hosted, is_one_level_based
from utils_revit import alert


def load_symbol_from_saved_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        try:
            eid = DB.ElementId(int(val))
        except Exception:
            return None
        e = doc.GetElement(eid)
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def load_symbol_from_saved_unique_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc.GetElement(str(uid))
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def store_symbol_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, int(symbol.Id.IntegerValue))
    except Exception:
        pass


def store_symbol_unique_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


def pick_light_symbol(doc, cfg, type_names):
    sym = load_symbol_from_saved_id(doc, cfg, 'last_light_lift_shaft_symbol_id')
    if sym is None:
        sym = load_symbol_from_saved_unique_id(doc, cfg, 'last_light_lift_shaft_symbol_uid')
    if sym is not None:
        return sym

    for name in as_list(type_names):
        try:
            found = placement_engine.find_family_symbol(doc, name, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
        except Exception:
            found = None
        if found and placement_engine.is_supported_point_placement(found):
            return found

    picked = placement_engine.select_family_symbol(
        doc,
        title='Выберите тип светильника (шахта лифта)',
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=True,
        allow_none=True,
        button_name='Выбрать',
        search_text=None,
        limit=200,
        scan_cap=5000
    )
    return picked


def check_symbol_compatibility(symbol):
    is_wall = is_wall_hosted(symbol)
    is_one_level = is_one_level_based(symbol)
    if not is_wall and not is_one_level:
        _, pt_name = placement_engine.get_symbol_placement_type(symbol)
        alert('Выбранный тип не поддерживает настенное размещение и не является уровневым (OneLevelBased).\n\nТип: {0}'.format(pt_name))
        return False
    return True
