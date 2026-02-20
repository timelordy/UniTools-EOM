# -*- coding: utf-8 -*-

from pyrevit import DB
import placement_engine
from domain import as_list, is_wall_hosted, is_one_level_based
from utils_revit import alert


_LIFT_LIGHT_PREFERRED = [
    u'(LF)_RSC PROM настенный : RSC PROM 18-2100LM [OneLevelBased]',
    u'(LF)_RSC PROM настенный : RSC PROM 18-2100LM',
    u'(LF)_RSC PROM настенный',
]


def _strip_placement_suffix(name):
    try:
        t = (name or u'').strip()
    except Exception:
        return u''
    if not t:
        return u''
    try:
        rb = t.rfind(']')
        lb = t.rfind('[')
        if rb == len(t) - 1 and lb > 0 and lb < rb:
            t = t[:lb].strip()
    except Exception:
        pass
    return t


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
    # Prefer explicit rules first, so stale cached symbol does not override project settings.
    search_names = []
    for raw_name in list(_LIFT_LIGHT_PREFERRED) + as_list(type_names):
        clean_name = _strip_placement_suffix(raw_name)
        if not clean_name:
            continue
        if clean_name in search_names:
            continue
        search_names.append(clean_name)

    for name in search_names:
        try:
            found = placement_engine.find_family_symbol(doc, name, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
        except Exception:
            found = None
        if found is None:
            try:
                found = placement_engine.find_family_symbol(doc, name, category_bic=None)
            except Exception:
                found = None
        if found and (is_wall_hosted(found) or is_one_level_based(found)):
            return found

    sym = load_symbol_from_saved_id(doc, cfg, 'last_light_lift_shaft_symbol_id')
    if sym is None:
        sym = load_symbol_from_saved_unique_id(doc, cfg, 'last_light_lift_shaft_symbol_uid')
    if sym is not None and (is_wall_hosted(sym) or is_one_level_based(sym)):
        return sym

    picked = placement_engine.select_family_symbol(
        doc,
        title='Выберите тип светильника (шахта лифта)',
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=False,
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
        alert(
            'Для "Свет в лифтах" нужен настенный или уровневый (OneLevelBased) тип.\n'
            'Текущий тип не поддерживает ни один из этих режимов.\n\n'
            'Тип размещения: {0}\n\n'
            'Нужно поправить семейство (например, LF)_RSC PROM настенный.rfa):\n'
            '- для настенного варианта: опорная поверхность должна быть связана со стеной;\n'
            '- для уровневого варианта: используйте параметр "Настенный" в самом семействе;\n'
            '- после этого перезагрузите семейство в проект и повторите.'
            .format(pt_name)
        )
        return False
    return True
