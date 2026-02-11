# -*- coding: utf-8 -*-
import os
import re
import sys

from pyrevit import DB

from constants import SWITCH_1G_TYPE_ID, SWITCH_2G_TYPE_ID


try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)


SWITCH_STRONG_KEYWORDS = [u'выключ', u'switch']
SWITCH_NEGATIVE_KEYWORDS = [
    u'розет', u'socket', u'панел', u'щит', u'шк', u'panel', u'shk',
    u'свет', u'light', u'lum', u'светиль',
    u'датчик', u'sensor', u'detector', u'motion', u'pir', u'presence',
    u'проход', u'прк', u'перекрест', u'пкс', u'димер', u'dimmer'
]
SWITCH_1G_KEYWORDS = [u'1к', u'1-к', u'1 клав', u'одноклав', u'1gang', u'1-gang', u'1g', u'single', u'1кл']
SWITCH_2G_KEYWORDS = [u'2к', u'2-к', u'2 клав', u'двухклав', u'2gang', u'2-gang', u'2g', u'double', u'2кл']


def _ensure_lib_path():
    try:
        ext_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        lib_path = os.path.join(ext_dir, 'lib')
        if lib_path not in sys.path:
            sys.path.append(lib_path)
    except Exception:
        pass


def _load_rules():
    try:
        _ensure_lib_path()
        import config_loader
        return config_loader.load_rules()
    except Exception:
        return {}


def _norm(text):
    try:
        return re.sub(r'\s+', '', text).lower()
    except Exception:
        return u''


def _get_symbol_label(symbol):
    try:
        return u"{} : {}".format(symbol.Family.Name, symbol.Name)
    except Exception:
        try:
            return u"{}".format(symbol.Name)
        except Exception:
            return u''


def _iter_switch_symbols(doc):
    seen = set()
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        try:
            collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
            if bic:
                collector = collector.OfCategory(bic)
            for sym in collector:
                try:
                    sid = int(sym.Id.IntegerValue)
                except Exception:
                    sid = None
                if sid is not None and sid in seen:
                    continue
                if sid is not None:
                    seen.add(sid)
                yield sym
        except Exception:
            continue


def _find_symbol_by_name(doc, name_with_type):
    if not name_with_type:
        return None
    try:
        if ':' in name_with_type:
            parts = name_with_type.split(':')
            family_name = parts[0].strip()
            type_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            family_name = name_with_type.strip()
            type_name = ''
    except Exception:
        family_name = name_with_type
        type_name = ''

    for sym in _iter_switch_symbols(doc):
        try:
            fam = sym.Family.Name
            typ = sym.Name
            full_name = u"{} : {}".format(fam, typ)
            if full_name == name_with_type.strip():
                return sym
            if family_name and family_name.lower() in fam.lower():
                if (not type_name) or (type_name.lower() in typ.lower()):
                    return sym
        except Exception:
            continue
    return None


def _score_switch_symbol(symbol, want_two_gang=False):
    if symbol is None:
        return None
    label = _get_symbol_label(symbol)
    nlabel = _norm(label)
    if not nlabel:
        return None

    s = 0
    strong_hit = False
    for kw in SWITCH_STRONG_KEYWORDS:
        if _norm(kw) in nlabel:
            s += 80
            strong_hit = True
            break

    hit1 = any(_norm(kw) in nlabel for kw in SWITCH_1G_KEYWORDS)
    hit2 = any(_norm(kw) in nlabel for kw in SWITCH_2G_KEYWORDS)

    # Safety: require explicit switch/gang hints to avoid random devices
    if (not strong_hit) and (not hit1) and (not hit2):
        return None

    for kw in SWITCH_NEGATIVE_KEYWORDS:
        if _norm(kw) in nlabel:
            s -= 120

    if want_two_gang:
        if hit2:
            s += 60
        if hit1:
            s -= 30
    else:
        if hit1:
            s += 60
        if hit2:
            s -= 30

    return s


def _auto_pick_switch_symbol(doc, want_two_gang=False):
    best = None
    best_score = None
    for sym in _iter_switch_symbols(doc):
        sc = _score_switch_symbol(sym, want_two_gang=want_two_gang)
        if sc is None:
            continue
        if best is None or sc > best_score:
            best = sym
            best_score = sc
    return best


def get_switch_symbol(doc, two_gang=False):
    type_id = SWITCH_2G_TYPE_ID if two_gang else SWITCH_1G_TYPE_ID
    try:
        elem = doc.GetElement(DB.ElementId(type_id))
        if elem and isinstance(elem, DB.FamilySymbol):
            if not elem.IsActive:
                elem.Activate()
            return elem
    except Exception:
        pass
    # Fallback 1: try rules.default.json preferred names
    try:
        rules = _load_rules() or {}
        family_names = rules.get('family_type_names', {})
        key = 'switch_2g' if two_gang else 'switch_1g'
        names = family_names.get(key) or family_names.get('switch') or []
        if isinstance(names, _STRING_TYPES):
            names = [names]
        if isinstance(names, list):
            for name in names:
                sym = _find_symbol_by_name(doc, name)
                if sym:
                    if not sym.IsActive:
                        sym.Activate()
                    return sym
    except Exception:
        pass
    # Fallback 2: heuristic auto-pick by keywords
    try:
        sym = _auto_pick_switch_symbol(doc, want_two_gang=two_gang)
        if sym:
            if not sym.IsActive:
                sym.Activate()
            return sym
    except Exception:
        pass
    return None
