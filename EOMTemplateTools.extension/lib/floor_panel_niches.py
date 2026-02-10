# -*- coding: utf-8 -*-
"""Вспомогательные функции для размещения этажных щитов (ЩЭ).

Этот модуль используется несколькими инструментами (placement engine, link reader и др.).

Примечание: Некоторые деплойменты могут поставлять только байткод (`__pycache__`).
Предоставление исходной версии здесь позволяет делать hotfix без изменения скомпилированных артефактов.
"""

import re

from pyrevit import DB


# Номера квартир, которые являются известными плейсхолдерами / не-квартирами в наших проектах.
# Можно переопределить через env переменную `EOM_APT_INVALID_NUMBERS` (разделитель: запятая/пробел).
DEFAULT_INVALID_APARTMENT_NUMBERS = {u"0", u"777"}


def _load_invalid_apartment_numbers_from_env():
    try:
        import os

        raw = os.environ.get('EOM_APT_INVALID_NUMBERS')
    except Exception:
        raw = None
    if not raw:
        return None
    vals = set()
    try:
        parts = re.split(r'[\s,;]+', str(raw))
    except Exception:
        parts = []
    for p in parts:
        try:
            s = str(p).strip()
        except Exception:
            continue
        if not s:
            continue
        vals.add(s)
    return vals or None


INVALID_APARTMENT_NUMBERS = set(DEFAULT_INVALID_APARTMENT_NUMBERS)
_env_invalid = _load_invalid_apartment_numbers_from_env()
if _env_invalid:
    INVALID_APARTMENT_NUMBERS = set(_env_invalid)


def _norm(value):
    try:
        return (value or u"").strip().lower()
    except Exception:
        return u""


def _get_param_as_string(elem, bip=None, name=None):
    if elem is None:
        return u""
    param = None
    try:
        if bip is not None:
            param = elem.get_Parameter(bip)
    except Exception:
        param = None
    if param is None and name:
        try:
            param = elem.LookupParameter(name)
        except Exception:
            param = None
    if param is None:
        return u""
    try:
        return param.AsString() or u""
    except Exception:
        return u""


def room_text(room):
    if room is None:
        return u""
    parts = []
    try:
        if getattr(room, 'Name', None):
            parts.append(room.Name)
    except Exception:
        pass
    try:
        val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME, name="Name")
        if val:
            parts.append(val)
    except Exception:
        pass
    try:
        val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER, name="Number")
        if not val and getattr(room, "Number", None):
            val = str(room.Number)
        if val:
            parts.append(val)
    except Exception:
        pass
    try:
        val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT, name="Department")
        if val:
            parts.append(val)
    except Exception:
        pass
    return u" ".join([p for p in parts if p])


def compile_patterns(patterns):
    rx = []
    for p in (patterns or []):
        try:
            txt = (p or u"").strip()
            if not txt:
                continue
            rx.append(re.compile(txt, re.IGNORECASE))
        except Exception:
            try:
                txt = (p or u"").strip()
                if txt:
                    rx.append(re.compile(re.escape(txt), re.IGNORECASE))
            except Exception:
                continue
    return rx


def match_any(rx_list, text):
    if not rx_list:
        return False
    t = text or u""
    for rx in rx_list:
        try:
            if rx.search(t):
                return True
        except Exception:
            continue
    return False


def is_niche_room(room, patterns):
    rx = compile_patterns(patterns or [])
    return match_any(rx, room_text(room))


def select_niche_patterns(rules, apartment_count):
    if rules is None:
        rules = {}
    if int(apartment_count or 0) == 1:
        special = rules.get("floor_panel_niche_patterns_single") or []
        if special:
            return list(special)
    return list(rules.get("floor_panel_niche_patterns") or [])


def normalize_type_names(value):
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v]
    return [value]


def normalize_type_key(value):
    try:
        t = (value or u"").strip()
    except Exception:
        return u""
    if not t:
        return t

    try:
        t = t.casefold()
    except Exception:
        try:
            t = t.lower()
        except Exception:
            pass

    try:
        t = t.replace(u"\u00a0", u" ").replace(u"\u202f", u" ")
    except Exception:
        pass

    # Нормализация тире.
    try:
        for ch in (u"–", u"—", u"‑", u"−"):
            t = t.replace(ch, u"-")
    except Exception:
        pass

    # Базовая транслитерация ru->latin (достаточно для сопоставления имён типов инструментов).
    try:
        repl = {
            u"а": u"a",
            u"б": u"b",
            u"в": u"v",
            u"г": u"g",
            u"д": u"d",
            u"е": u"e",
            u"ё": u"yo",
            u"ж": u"zh",
            u"з": u"z",
            u"и": u"i",
            u"й": u"y",
            u"к": u"k",
            u"л": u"l",
            u"м": u"m",
            u"н": u"n",
            u"о": u"o",
            u"п": u"p",
            u"р": u"r",
            u"с": u"s",
            u"т": u"t",
            u"у": u"u",
            u"ф": u"f",
            u"х": u"h",
            u"ц": u"ts",
            u"ч": u"ch",
            u"ш": u"sh",
            u"щ": u"shh",
            u"ъ": u"",
            u"ы": u"y",
            u"ь": u"",
            u"э": u"e",
            u"ю": u"yu",
            u"я": u"ya",
        }
        for k, v in repl.items():
            t = t.replace(k, v)
    except Exception:
        pass

    try:
        t = u" ".join(t.split())
    except Exception:
        pass

    try:
        t = t.replace(u" : ", u":").replace(u" :", u":").replace(u": ", u":")
    except Exception:
        pass
    return t


def extract_panel_number_from_type_name(name):
    t = normalize_type_key(name)
    if not t:
        return None
    try:
        m = re.search(r"(?:shhe|sh?e)\s*[-_ ]*\s*([0-9]{1,2})", t)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def select_opening_type_names(rules):
    if rules is None:
        rules = {}
    names = rules.get("floor_panel_opening_type_names")
    if not names:
        names = rules.get("floor_panel_opening_type_name")
    return normalize_type_names(names)


def clean_apartment_number(value):
    if value is None:
        return u""
    try:
        v = str(value).strip()
    except Exception:
        return u""
    try:
        v = re.sub(r'^(кв\.?|apt\.?|квартира)\s*', '', v, flags=re.IGNORECASE)
    except Exception:
        pass
    return v.upper()


def is_valid_apartment_number(value):
    if not value:
        return False
    v = _norm(value)
    if not v:
        return False
    if v in [u"квартира", u"apartment", u"flat", u"room", u"моп"]:
        return False

    # Drop known placeholders.
    try:
        if clean_apartment_number(value) in INVALID_APARTMENT_NUMBERS:
            return False
    except Exception:
        pass
    try:
        if v in INVALID_APARTMENT_NUMBERS:
            return False
    except Exception:
        pass

    # Должен содержать цифры.
    return any(ch.isdigit() for ch in v)


def get_room_apartment_number(room,
                              param_names=None,
                              allow_department=False,
                              allow_number=False):
    if room is None:
        return None
    names = list(param_names or [])

    for name in names:
        try:
            val = _get_param_as_string(room, name=name)
            if val:
                clean = clean_apartment_number(val)
                if is_valid_apartment_number(clean):
                    return clean
        except Exception:
            continue

    if allow_department:
        try:
            val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT)
            clean = clean_apartment_number(val)
            if is_valid_apartment_number(clean):
                return clean
        except Exception:
            pass

    if allow_number:
        try:
            val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER)
            if not val and getattr(room, "Number", None):
                val = str(room.Number)
            if val:
                parts = str(val).split(".")
                if parts and parts[0].isdigit():
                    clean = clean_apartment_number(parts[0])
                    if is_valid_apartment_number(clean):
                        return clean
        except Exception:
            pass

    return None


def _contains_any(text_value, patterns):
    t = _norm(text_value)
    if not t:
        return False
    for p in (patterns or []):
        pp = _norm(p)
        if pp and pp in t:
            return True
    return False


def _room_department(room):
    if room is None:
        return u""
    try:
        v = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT)
        if v:
            return v
    except Exception:
        pass
    try:
        v = _get_param_as_string(room, name="Department")
        if v:
            return v
    except Exception:
        pass
    return u""


def _room_name(room):
    if room is None:
        return u""
    try:
        v = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME)
        if v:
            return v
    except Exception:
        pass
    try:
        if getattr(room, "Name", None):
            return str(room.Name)
    except Exception:
        pass
    return u""


def _room_number(room):
    if room is None:
        return u""
    try:
        v = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER)
        if v:
            return v
    except Exception:
        pass
    try:
        if getattr(room, "Number", None):
            return str(room.Number)
    except Exception:
        pass
    return u""


def _extract_number_prefix(value):
    if not value:
        return None
    try:
        vv = str(value).strip()
    except Exception:
        return None
    if not vv:
        return None
    try:
        m = re.match(r'^\s*([0-9]+)', vv)
        if m:
            return m.group(1)
    except Exception:
        pass
    try:
        parts = re.split(r'[\.\-_\s]+', vv)
        if parts:
            p0 = (parts[0] or u"").strip()
            if p0 and any(ch.isdigit() for ch in p0):
                return p0
    except Exception:
        pass
    return None


def infer_apartment_number_from_room(room,
                                     apartment_department_patterns=None,
                                     apartment_room_name_patterns=None,
                                     apartment_exclude_department_patterns=None):
    if room is None:
        return None

    dep_patterns = list(apartment_department_patterns or [u"кварт", u"apartment", u"flat"])
    name_patterns = list(apartment_room_name_patterns or [u"кварт", u"кух", u"спаль", u"гост", u"прих", u"living", u"bed"])
    dep_exclude = list(apartment_exclude_department_patterns or [u"моп", u"tech", u"тех", u"офис", u"office"])

    dep = _room_department(room)
    name = _room_name(room)
    if _contains_any(dep, dep_exclude):
        return None

    is_apartment_room = _contains_any(dep, dep_patterns)
    if not is_apartment_room:
        is_apartment_room = _contains_any(name, name_patterns)
    if not is_apartment_room:
        return None

    num = _room_number(room)
    pref = _extract_number_prefix(num)
    if pref:
        clean = clean_apartment_number(pref)
        if is_valid_apartment_number(clean):
            return clean

    try:
        m = re.search(r'([0-9]{1,4})', room_text(room))
        if m:
            clean = clean_apartment_number(m.group(1))
            if is_valid_apartment_number(clean):
                return clean
    except Exception:
        pass

    return None


def count_apartments_by_level(rooms,
                              param_names=None,
                              allow_department=False,
                              allow_number=False,
                              require_param=False,
                              infer_from_rooms=False,
                              apartment_department_patterns=None,
                              apartment_room_name_patterns=None,
                              apartment_exclude_department_patterns=None,
                              return_details=False):
    by_level_param = {}
    by_level_inferred = {}
    details = {}

    for room in rooms or []:
        try:
            level_id = getattr(room, "LevelId", None)
            lvl = int(level_id.IntegerValue) if level_id is not None else None
        except Exception:
            lvl = None
        if lvl is None:
            continue

        apt = get_room_apartment_number(
            room,
            param_names=param_names,
            allow_department=allow_department,
            allow_number=allow_number,
        )

        if apt:
            by_level_param.setdefault(lvl, set()).add(str(apt))
            continue

        if infer_from_rooms and (not require_param):
            apt2 = infer_apartment_number_from_room(
                room,
                apartment_department_patterns=apartment_department_patterns,
                apartment_room_name_patterns=apartment_room_name_patterns,
                apartment_exclude_department_patterns=apartment_exclude_department_patterns,
            )
            if apt2:
                by_level_inferred.setdefault(lvl, set()).add(str(apt2))

    counts = {}
    for lvl in set(list(by_level_param.keys()) + list(by_level_inferred.keys())):
        param_vals = by_level_param.get(lvl, set()) or set()
        inferred_vals = by_level_inferred.get(lvl, set()) or set()

        use_mode = 'param' if param_vals else 'inferred'
        used = param_vals if param_vals else inferred_vals

        counts[int(lvl)] = len(used)
        details[int(lvl)] = {
            'mode': use_mode,
            'param': sorted(list(param_vals)),
            'inferred': sorted(list(inferred_vals)),
            'used': sorted(list(used)),
        }

    if return_details:
        return counts, details
    return counts


def select_panel_rule(apartment_count, type_rules):
    if not type_rules:
        return None
    try:
        count = int(apartment_count or 0)
    except Exception:
        count = 0

    exact_any = False
    for rule in type_rules:
        if not isinstance(rule, dict):
            continue
        if "exact_apartments" not in rule:
            continue
        exact_any = True
        exact_vals = rule.get("exact_apartments")
        values = []
        if isinstance(exact_vals, (list, tuple, set)):
            values = list(exact_vals)
        else:
            values = [exact_vals]
        for v in values:
            try:
                if int(v) == count:
                    return rule
            except Exception:
                continue

    if exact_any:
        return None

    normalized = []
    for rule in type_rules:
        if not isinstance(rule, dict):
            continue
        max_apartments = rule.get("max_apartments", None)
        if max_apartments is None or max_apartments == "":
            normalized.append((None, rule))
            continue
        try:
            normalized.append((int(max_apartments), rule))
        except Exception:
            continue

    if not normalized:
        return None

    normalized.sort(key=lambda item: float("inf") if item[0] is None else item[0])
    for max_apts, rule in normalized:
        if max_apts is None or count <= max_apts:
            return rule
    return None

