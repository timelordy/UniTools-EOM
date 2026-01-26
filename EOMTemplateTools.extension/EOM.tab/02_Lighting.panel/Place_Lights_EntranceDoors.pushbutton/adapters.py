# -*- coding: utf-8 -*-

from pyrevit import DB
import placement_engine
from domain import norm, score_light_symbol
from utils_revit import alert


def load_symbol_from_saved_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        eid = DB.ElementId(int(val))
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


def auto_pick_light_symbol(doc, prefer_fullname=None):
    prefer = norm(prefer_fullname)
    ranked = []
    scan_cap = 2000
    for s in placement_engine.iter_family_symbols(doc, category_bic=DB.BuiltInCategory.OST_LightingFixtures, limit=scan_cap):
        try:
            if not placement_engine.is_supported_point_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue
            sc = score_light_symbol(s)
            if prefer and norm(lbl) == prefer:
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None, None, []

    ranked.sort(key=lambda x: (x[0], norm(x[1])), reverse=True)
    best = ranked[0]
    return best[2], best[1], [r[1] for r in ranked[:10]]


def pick_light_symbol(doc, cfg, fullname=None):
    sym = None
    try:
        sym = load_symbol_from_saved_unique_id(doc, cfg, 'last_light_entrance_symbol_uid')
    except Exception:
        sym = None
    if sym is None:
        try:
            sym = load_symbol_from_saved_id(doc, cfg, 'last_light_entrance_symbol_id')
        except Exception:
            sym = None

    if sym is not None:
        try:
            if placement_engine.is_supported_point_placement(sym):
                return sym, placement_engine.format_family_type(sym), []
        except Exception:
            sym = None

    if fullname:
        try:
            sym = placement_engine.find_family_symbol(doc, fullname, category_bic=DB.BuiltInCategory.OST_LightingFixtures, limit=5000)
        except Exception:
            sym = None
        if sym is not None:
            try:
                if placement_engine.is_supported_point_placement(sym):
                    return sym, placement_engine.format_family_type(sym), []
            except Exception:
                sym = None

    sym, picked_label, top10 = auto_pick_light_symbol(doc, prefer_fullname=fullname)
    if sym is not None:
        return sym, picked_label, top10

    sym = placement_engine.select_family_symbol(
        doc,
        title='Выберите тип светильника (входы/кровля)',
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=True,
        allow_none=True,
        button_name='Выбрать',
        limit=200,
        scan_cap=5000
    )
    if sym is None:
        return None, None, []
    return sym, placement_engine.format_family_type(sym), []
