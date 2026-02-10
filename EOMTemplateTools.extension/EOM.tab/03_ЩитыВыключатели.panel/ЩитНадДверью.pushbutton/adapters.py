# -*- coding: utf-8 -*-
"""Адаптеры для работы с Revit API (Infrastructure Layer).

Этот модуль содержит функции для взаимодействия с Revit API:
- Чтение/запись параметров элементов
- Работа с конфигурацией (config management)
- Коллекторы элементов (двери, щиты, помещения)
- Геометрические helper-функции
- Работа с семействами и типами
- Размещение и ориентация элементов
- Дедупликация элементов
- Создание 3D видов

Все функции начинаются с underscore (внутренние) и работают только
с Revit API, без бизнес-логики.
"""

import math
import re

from pyrevit import DB
from pyrevit import script

import placement_engine
from domain import norm_type_key, variant_prefix_key, is_panel_module_variant_param_name


logger = script.get_logger()


# ====================================================================
# CONFIG MANAGEMENT
# ====================================================================

def _get_user_config():
    """Получить пользовательскую конфигурацию скрипта."""
    try:
        return script.get_config()
    except Exception:
        return None


def _save_user_config():
    """Сохранить пользовательскую конфигурацию скрипта."""
    try:
        script.save_config()
        return True
    except Exception:
        return False


def _load_symbol_from_saved_id(doc, cfg, key):
    """Загрузить FamilySymbol из сохраненного ElementId."""
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


def _load_symbol_from_saved_unique_id(doc, cfg, key):
    """Загрузить FamilySymbol из сохраненного UniqueId."""
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


def _store_symbol_id(cfg, key, symbol):
    """Сохранить ElementId семейства в конфигурацию."""
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, int(symbol.Id.IntegerValue))
    except Exception:
        pass


def _store_symbol_unique_id(cfg, key, symbol):
    """Сохранить UniqueId семейства в конфигурацию."""
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


# ====================================================================
# РАБОТА С ПАРАМЕТРАМИ REVIT API
# ====================================================================

def _get_param_as_double(elem, bip=None, name=None):
    """Получить значение параметра как Double.

    Args:
        elem: Элемент Revit
        bip: BuiltInParameter (опционально)
        name: Имя параметра (опционально)

    Returns:
        float или None
    """
    if elem is None:
        return None
    p = None
    try:
        if bip is not None:
            p = elem.get_Parameter(bip)
    except Exception:
        p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return None
    try:
        if not p.HasValue:
            return None
    except Exception:
        pass
    try:
        return p.AsDouble()
    except Exception:
        return None


def _get_param_as_string(elem, bip=None, name=None):
    """Получить значение параметра как String.

    Args:
        elem: Элемент Revit
        bip: BuiltInParameter (опционально)
        name: Имя параметра (опционально)

    Returns:
        unicode строка (пустая строка если нет значения)
    """
    if elem is None:
        return u''
    p = None
    try:
        if bip is not None:
            p = elem.get_Parameter(bip)
    except Exception:
        p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return u''
    try:
        s = p.AsString()
        return s if s is not None else u''
    except Exception:
        return u''


def _param_to_string(p):
    """Преобразовать значение параметра в строку (универсальный метод).

    Работает с любым StorageType (String, Integer, Double, ElementId).
    """
    if p is None:
        return u''
    try:
        st = p.StorageType
    except Exception:
        st = None
    try:
        if st == DB.StorageType.String:
            s = p.AsString()
            return s if s is not None else u''
        if st == DB.StorageType.Integer:
            try:
                return unicode(p.AsInteger())
            except Exception:
                return u''
        if st == DB.StorageType.Double:
            try:
                return p.AsValueString() or u''
            except Exception:
                return u''
        if st == DB.StorageType.ElementId:
            try:
                eid = p.AsElementId()
                return unicode(eid.IntegerValue) if eid is not None else u''
            except Exception:
                return u''
    except Exception:
        pass
    try:
        return p.AsValueString() or u''
    except Exception:
        return u''


def _find_param_by_norm(elem, pname):
    """Найти параметр на элементе по точному имени, затем по нормализованному.

    Args:
        elem: Элемент Revit
        pname: Имя параметра

    Returns:
        Parameter или None
    """
    if elem is None or not pname:
        return None

    # Попытка точного совпадения
    try:
        p = elem.LookupParameter(pname)
        if p is not None:
            return p
    except Exception:
        p = None

    # Поиск по нормализованному имени
    key = norm_type_key(pname)
    if not key:
        return None

    try:
        params = getattr(elem, 'Parameters', None)
        if params is None:
            return None
        for p2 in params:
            try:
                d = getattr(p2, 'Definition', None)
                n = getattr(d, 'Name', None) if d is not None else None
            except Exception:
                n = None
            if not n:
                continue
            if norm_type_key(n) == key:
                return p2
    except Exception:
        return None

    return None


def _param_checked(elem, pname):
    """Проверить, что параметр Yes/No включен (значение == 1).

    Args:
        elem: Элемент Revit
        pname: Имя параметра

    Returns:
        bool: True если параметр найден и включен
    """
    p = _find_param_by_norm(elem, pname)
    if p is None:
        return False
    try:
        if p.StorageType != DB.StorageType.Integer:
            return False
    except Exception:
        return False
    try:
        return int(p.AsInteger() or 0) == 1
    except Exception:
        return False


# ====================================================================
# КОЛЛЕКТОРЫ ЭЛЕМЕНТОВ
# ====================================================================

def _iter_panel_symbols(doc, limit=2000):
    """Итератор по FamilySymbol электрооборудования (OST_ElectricalEquipment).

    Используется для быстрого поиска щитов. Ограничен категорией для стабильности.

    Args:
        doc: Document
        limit: Максимальное количество элементов (по умолчанию 2000)

    Yields:
        FamilySymbol
    """
    if doc is None:
        return

    lim = 2000
    try:
        lim = int(limit or 2000)
    except Exception:
        lim = 2000
    lim = max(lim, 1)

    try:
        col = (DB.FilteredElementCollector(doc)
               .OfClass(DB.FamilySymbol)
               .OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment))
        i = 0
        for s in col:
            yield s
            i += 1
            if lim and i >= lim:
                break
    except Exception:
        return


def _iter_panel_symbols_any(doc, limit=5000):
    """Итератор по всем FamilySymbol (любые категории).

    Используется для поиска по конфигурации, чтобы не пропустить семейство
    с неправильной категорией.

    Args:
        doc: Document
        limit: Максимальное количество элементов (по умолчанию 5000)

    Yields:
        FamilySymbol
    """
    if doc is None:
        return

    lim = 5000
    try:
        lim = int(limit or 5000)
    except Exception:
        lim = 5000
    lim = max(lim, 1)

    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
        i = 0
        for s in col:
            yield s
            i += 1
            if lim and i >= lim:
                break
    except Exception:
        return


def _iter_family_symbols(doc_, family):
    """Итератор по типам семейства (FamilySymbol).

    Args:
        doc_: Document
        family: Family

    Yields:
        FamilySymbol
    """
    if doc_ is None or family is None:
        return
    try:
        ids = list(family.GetFamilySymbolIds())
    except Exception:
        ids = []
    for sid in ids or []:
        try:
            s = doc_.GetElement(sid)
        except Exception:
            s = None
        if s is not None:
            yield s


def _iter_from_to_rooms(door, phases):
    """Итератор по смежным помещениям двери (FromRoom, ToRoom) для заданных фаз.

    Args:
        door: FamilyInstance (дверь)
        phases: Список Phase

    Yields:
        Room
    """
    if door is None:
        return

    # Try indexed properties first (IronPython)
    for ph in phases or []:
        for attr in ('FromRoom', 'ToRoom'):
            try:
                rr = getattr(door, attr, None)
                if rr is None:
                    continue
                # rr might be indexable by Phase
                r = rr[ph]
                if r:
                    yield r
            except Exception:
                pass

    # Try API methods
    for ph in phases or []:
        for mname in ('get_FromRoom', 'get_ToRoom'):
            try:
                m = getattr(door, mname, None)
                if m is None:
                    continue
                r = m(ph)
                if r:
                    yield r
            except Exception:
                pass


# ====================================================================
# GEOMETRY / LOCATION HELPERS
# ====================================================================

def _door_head_point_link(door):
    """Точка размещения над дверью (координаты в связи): центр двери, верх.

    Returns:
        XYZ в координатах связи
    """
    # Best: bounding box
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            cx = (bb.Min.X + bb.Max.X) * 0.5
            cy = (bb.Min.Y + bb.Max.Y) * 0.5
            z = bb.Max.Z
            return DB.XYZ(cx, cy, z)
    except Exception:
        pass

    # Fallback: location + head height
    try:
        loc = door.Location
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is None:
            return None
        head = None
        try:
            p = door.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM)
            if p:
                head = p.AsDouble()
        except Exception:
            head = None
        z = pt.Z + (float(head) if head else 0.0)
        return DB.XYZ(pt.X, pt.Y, z)
    except Exception:
        return None


def _door_center_point_link(door):
    """Центральная точка двери (координаты в связи): XY на вставке двери.

    Returns:
        XYZ в координатах связи
    """
    if door is None:
        return None

    try:
        loc = getattr(door, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is not None:
            return pt
    except Exception:
        pass

    # Fallback: bbox center
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return (bb.Min + bb.Max) * 0.5
    except Exception:
        pass

    return None


def _door_head_z_link(door):
    """Z-координата верха двери (координаты в связи).

    Returns:
        float или None
    """
    if door is None:
        return None

    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return float(bb.Max.Z)
    except Exception:
        pass

    try:
        loc = getattr(door, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is None:
            return None
        head = None
        try:
            p = door.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM)
            if p:
                head = p.AsDouble()
        except Exception:
            head = None
        if head is None:
            return float(pt.Z)
        return float(pt.Z) + float(head)
    except Exception:
        return None


def _room_center_fast(room):
    """Быстрое получение центра помещения (Location.Point или bbox center).

    Returns:
        XYZ или None
    """
    if room is None:
        return None

    try:
        loc = getattr(room, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is not None:
            return pt
    except Exception:
        pass

    try:
        bb = room.get_BoundingBox(None)
        if bb:
            return (bb.Min + bb.Max) * 0.5
    except Exception:
        pass

    return None


def _xy_unit(vec):
    """Нормализовать вектор в XY плоскости (Z=0).

    Returns:
        XYZ (unit vector) или None
    """
    if vec is None:
        return None
    try:
        v = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
        if v.GetLength() < 1e-9:
            return None
        return v.Normalize()
    except Exception:
        return None


def _xy_perp(v):
    """Перпендикулярный вектор в XY плоскости (поворот на 90°).

    Returns:
        XYZ или None
    """
    v = _xy_unit(v)
    if v is None:
        return None
    try:
        return DB.XYZ(-float(v.Y), float(v.X), 0.0)
    except Exception:
        return None


# ====================================================================
# SYMBOL / TYPE MANAGEMENT
# ====================================================================

def _find_panel_symbol_by_label(doc, fam_fullname):
    """Найти FamilySymbol щита по label (Family: Type или просто Type/Family).

    Args:
        doc: Document
        fam_fullname: Строка вида "Family: Type" или "Type"

    Returns:
        FamilySymbol или None
    """
    target = norm_type_key(fam_fullname)
    if not target:
        return None

    try:
        has_colon = (u':' in (fam_fullname or u''))
    except Exception:
        has_colon = False

    # 1) Fast path: Electrical Equipment (expected category for panels)
    for s in _iter_panel_symbols(doc, limit=20000):
        try:
            if has_colon:
                if norm_type_key(placement_engine.format_family_type(s)) == target:
                    return s
            else:
                # If no family specified, allow matching by type name or family name.
                try:
                    if norm_type_key(getattr(s, 'Name', u'')) == target:
                        return s
                except Exception:
                    pass
                try:
                    fam = getattr(s, 'Family', None)
                    fam_name = getattr(fam, 'Name', u'') if fam else u''
                    if norm_type_key(fam_name) == target:
                        return s
                except Exception:
                    pass
        except Exception:
            continue

    # 2) Fallback: scan all FamilySymbol (capped)
    for s in _iter_panel_symbols_any(doc, limit=50000):
        try:
            if has_colon:
                if norm_type_key(placement_engine.format_family_type(s)) == target:
                    return s
            else:
                try:
                    if norm_type_key(getattr(s, 'Name', u'')) == target:
                        return s
                except Exception:
                    pass
                try:
                    fam = getattr(s, 'Family', None)
                    fam_name = getattr(fam, 'Name', u'') if fam else u''
                    if norm_type_key(fam_name) == target:
                        return s
                except Exception:
                    pass
        except Exception:
            continue
    return None


def _symbol_matches_label(symbol, fam_fullname):
    """Проверить, соответствует ли символ заданному label.

    Также проверяет Yes/No параметры с именем label (для семейств с вариантами).
    """
    if symbol is None:
        return False
    target = norm_type_key(fam_fullname)
    if not target:
        return False
    try:
        has_colon = (u':' in (fam_fullname or u''))
    except Exception:
        has_colon = False

    try:
        if has_colon and norm_type_key(placement_engine.format_family_type(symbol)) == target:
            return True
    except Exception:
        pass

    try:
        if norm_type_key(getattr(symbol, 'Name', u'')) == target:
            return True
    except Exception:
        pass

    try:
        fam = getattr(symbol, 'Family', None)
        fam_name = getattr(fam, 'Name', u'') if fam else u''
        if norm_type_key(fam_name) == target:
            return True
    except Exception:
        pass

    # Also allow matching by a Yes/No type parameter name (used by some panel families)
    try:
        p = _find_param_by_norm(symbol, fam_fullname)
        if p is not None and p.StorageType == DB.StorageType.Integer:
            try:
                if int(p.AsInteger() or 0) == 1:
                    return True
            except Exception:
                pass
    except Exception:
        pass

    return False


def _make_unique_type_name(doc_, family, base_name):
    """Сгенерировать уникальное имя типа в семействе.

    Args:
        doc_: Document
        family: Family
        base_name: Базовое имя (например, "Щит ШК-18")

    Returns:
        str: Уникальное имя (добавляет (2), (3), ... если имя занято)
    """
    if doc_ is None or family is None:
        return base_name
    try:
        existing = set([norm_type_key(getattr(s, 'Name', u'')) for s in _iter_family_symbols(doc_, family)])
    except Exception:
        existing = set()

    bn = norm_type_key(base_name)
    if bn and bn not in existing:
        return base_name

    i = 2
    while i < 100:
        cand = u'{0} ({1})'.format(base_name, i)
        if norm_type_key(cand) not in existing:
            return cand
        i += 1
    return base_name


def _ensure_panel_variant_symbol(doc_, base_symbol, desired_param_name):
    """Получить или создать FamilySymbol с включенным вариантом модуля.

    Если нужного типа нет, создает дубликат базового типа и настраивает параметры.

    Args:
        doc_: Document
        base_symbol: FamilySymbol (базовый)
        desired_param_name: Имя параметра варианта (например, "ЩРВ-П-18 модулей")

    Returns:
        FamilySymbol с настроенным вариантом
    """
    if doc_ is None or base_symbol is None or not desired_param_name:
        return base_symbol

    # If base doesn't even have this parameter, nothing to do
    if _find_param_by_norm(base_symbol, desired_param_name) is None:
        return base_symbol

    def _has_other_variant_checked(sym):
        """Detect if any other module variant is enabled (across all series/prefixes)."""
        if sym is None:
            return False
        desired_key = norm_type_key(desired_param_name)
        try:
            params = getattr(sym, 'Parameters', None)
        except Exception:
            params = None
        if params is None:
            return False
        for p in params:
            try:
                d = getattr(p, 'Definition', None)
                pname = getattr(d, 'Name', None) if d is not None else None
            except Exception:
                pname = None
            if not pname:
                continue
            if not is_panel_module_variant_param_name(pname):
                continue
            nkey = norm_type_key(pname)
            if not nkey:
                continue
            if nkey == desired_key:
                continue
            try:
                if p.StorageType == DB.StorageType.Integer and int(p.AsInteger() or 0) == 1:
                    return True
            except Exception:
                continue
        return False

    try:
        fam = getattr(base_symbol, 'Family', None)
    except Exception:
        fam = None

    # Try find existing CLEAN type in the same family
    for s in _iter_family_symbols(doc_, fam):
        try:
            if _param_checked(s, desired_param_name) and (not _has_other_variant_checked(s)):
                return s
        except Exception:
            continue

    # If base already matches and is clean -> done
    if _param_checked(base_symbol, desired_param_name) and (not _has_other_variant_checked(base_symbol)):
        return base_symbol

    # Create a new type and configure it
    from domain import make_variant_type_name
    from utils_revit import tx

    new_sym = None
    try:
        base_type_name = getattr(base_symbol, 'Name', u'') or u''
    except Exception:
        base_type_name = u''
    new_name_base = make_variant_type_name(base_type_name, desired_param_name)
    new_name = _make_unique_type_name(doc_, fam, new_name_base)

    with tx('ЭОМ: Создать тип щита ШК (вариант)', doc=doc_, swallow_warnings=True):
        try:
            dup = base_symbol.Duplicate(new_name)
            try:
                # Revit API may return either ElementType (preferred) or ElementId depending on wrappers.
                if isinstance(dup, DB.ElementId):
                    new_sym = doc_.GetElement(dup)
                else:
                    new_sym = dup
            except Exception:
                new_sym = None
        except Exception:
            new_sym = None

        if new_sym is not None:
            _apply_panel_variant_params(new_sym, desired_param_name)
        else:
            # Fallback: adjust base type directly
            _apply_panel_variant_params(base_symbol, desired_param_name)
            new_sym = base_symbol

        try:
            doc_.Regenerate()
        except Exception:
            pass

    return new_sym or base_symbol


def _apply_panel_variant_params(elem, desired_param_name):
    """Включить желаемый вариант модуля и выключить остальные варианты.

    Работает как для FamilySymbol (тип), так и для FamilyInstance (экземпляр).

    Args:
        elem: FamilySymbol или FamilyInstance
        desired_param_name: Имя параметра варианта для включения

    Returns:
        bool: True если были изменения
    """
    if elem is None or not desired_param_name:
        return False

    desired_key = norm_type_key(desired_param_name)
    if not desired_key:
        return False

    p_des = _find_param_by_norm(elem, desired_param_name)
    if p_des is None:
        return False

    prefix_key = variant_prefix_key(desired_param_name)
    toggled = False
    variant_actions = []

    # Toggle sibling options (only if we can identify the group by prefix)
    if prefix_key:
        try:
            params = getattr(elem, 'Parameters', None)
        except Exception:
            params = None

        if params is not None:
            for p in params:
                try:
                    d = getattr(p, 'Definition', None)
                    pname = getattr(d, 'Name', None) if d is not None else None
                except Exception:
                    pname = None
                if not pname:
                    continue

                nkey = norm_type_key(pname)
                if not nkey or (not nkey.startswith(prefix_key)):
                    continue

                try:
                    if p.StorageType != DB.StorageType.Integer:
                        continue
                except Exception:
                    continue

                try:
                    if p.IsReadOnly:
                        continue
                except Exception:
                    pass

                val = 1 if nkey == desired_key else 0
                try:
                    cur = int(p.AsInteger() or 0)
                except Exception:
                    cur = None
                try:
                    if cur is None or cur != int(val):
                        p.Set(int(val))
                        toggled = True
                        variant_actions.append((pname, val, True, 'prefix'))
                    else:
                        variant_actions.append((pname, val, False, 'prefix'))
                except Exception:
                    continue

    # Strict toggle: disable any *other* module variants (can belong to a different prefix group).
    try:
        params = getattr(elem, 'Parameters', None)
    except Exception:
        params = None

    if params is not None:
        for p in params:
            try:
                d = getattr(p, 'Definition', None)
                pname = getattr(d, 'Name', None) if d is not None else None
            except Exception:
                pname = None
            if not pname:
                continue
            if not is_panel_module_variant_param_name(pname):
                continue

            nkey = norm_type_key(pname)
            if not nkey:
                continue

            try:
                if p.StorageType != DB.StorageType.Integer:
                    continue
            except Exception:
                continue

            try:
                if p.IsReadOnly:
                    continue
            except Exception:
                pass

            val = 1 if nkey == desired_key else 0
            try:
                cur = int(p.AsInteger() or 0)
            except Exception:
                cur = None
            try:
                if cur is None or cur != int(val):
                    p.Set(int(val))
                    toggled = True
                    variant_actions.append((pname, val, True, 'variant'))
                else:
                    variant_actions.append((pname, val, False, 'variant'))
            except Exception:
                continue

    # Ensure desired is ON
    try:
        if p_des.StorageType == DB.StorageType.Integer and (not p_des.IsReadOnly):
            try:
                cur = int(p_des.AsInteger() or 0)
            except Exception:
                cur = None
            if cur != 1:
                p_des.Set(1)
                toggled = True
                variant_actions.append((getattr(p_des.Definition, 'Name', desired_param_name), 1, True, 'desired'))
            else:
                toggled = True
                variant_actions.append((getattr(p_des.Definition, 'Name', desired_param_name), 1, False, 'desired'))
    except Exception:
        pass

    if variant_actions:
        try:
            msg_parts = []
            for name, val, changed, src in variant_actions:
                label = u'{0}->{1}'.format(name, val)
                if src:
                    label = u'{0} [{1}]'.format(label, src)
                if not changed:
                    label = label + u' (no change)'
                msg_parts.append(label)
            logger.info(u"[ShK] apply variant '%s': %s", desired_param_name, '; '.join(msg_parts))
        except Exception:
            pass

    return toggled


def _post_fix_panel_variant(doc_, symbol, desired_param_name):
    """Пост-фикс: убедиться, что только желаемый вариант модуля включен на ТИПЕ.

    Выполняется после размещения для противодействия случаям, когда Revit/другая логика
    повторно включает опцию модуля.

    Args:
        doc_: Document
        symbol: FamilySymbol
        desired_param_name: Имя параметра варианта

    Returns:
        bool: True если были изменения
    """
    if doc_ is None or symbol is None or not desired_param_name:
        return False

    try:
        changed = _apply_panel_variant_params(symbol, desired_param_name)
    except Exception:
        changed = False

    try:
        doc_.Regenerate()
    except Exception:
        pass

    try:
        desired_key = norm_type_key(desired_param_name)
    except Exception:
        desired_key = ''

    desired_is_four = False
    try:
        desired_is_four = re.search(u'(^|[^0-9])4([^0-9]|$)', desired_key or u'') is not None
    except Exception:
        desired_is_four = False

    four_re = None
    try:
        four_re = re.compile(u'(?:^|[^0-9])4\\s*(?:модул|modul|module)', re.IGNORECASE)
    except Exception:
        four_re = None

    try:
        params = getattr(symbol, 'Parameters', None)
    except Exception:
        params = None

    enforcement_actions = []

    if params is not None:
        for p in params:
            try:
                d = getattr(p, 'Definition', None)
                pname = getattr(d, 'Name', None) if d is not None else None
            except Exception:
                pname = None
            if not pname:
                continue

            # Treat any module-variant param OR explicit "4 modules" param.
            is_variant = is_panel_module_variant_param_name(pname)
            try:
                norm_name = norm_type_key(pname)
            except Exception:
                norm_name = u''
            is_four = False
            try:
                is_four = bool(four_re and four_re.search(pname))
            except Exception:
                from domain import norm
                is_four = (u'4' in norm_name and u'модул' in norm(pname))

            if (not is_variant) and (not is_four):
                continue

            try:
                if p.StorageType != DB.StorageType.Integer:
                    continue
            except Exception:
                continue
            try:
                if p.IsReadOnly:
                    continue
            except Exception:
                pass

            desired_match = bool(desired_key and norm_name == desired_key)
            target_val = 1 if desired_match else 0

            # Aggressively disable 4-module option unless it is explicitly desired.
            if is_four and (not desired_is_four):
                target_val = 0

            try:
                cur = int(p.AsInteger() or 0)
            except Exception:
                cur = None

            try:
                if cur is None or cur != int(target_val):
                    p.Set(int(target_val))
                    changed = True
                    enforcement_actions.append((pname, target_val, True))
                else:
                    enforcement_actions.append((pname, target_val, False))
            except Exception:
                continue

    try:
        doc_.Regenerate()
    except Exception:
        pass

    if enforcement_actions:
        try:
            msg = '; '.join([u"{0}->{1}{2}".format(n, v, '' if ch else ' (no change)') for n, v, ch in enforcement_actions])
        except Exception:
            try:
                msg = '; '.join([u"{0}->{1}".format(n, v) for n, v, _ in enforcement_actions])
            except Exception:
                msg = ''
        try:
            logger.info(u"[ShK] post-fix '%s': %s", desired_param_name, msg)
        except Exception:
            pass

    return bool(changed)


# ====================================================================
# PLACEMENT HELPERS
# ====================================================================

def _try_get_depth_ft(symbol, inst=None):
    """Попытка получить глубину устройства (корпус) в футах из параметров.

    Args:
        symbol: FamilySymbol
        inst: FamilyInstance (опционально)

    Returns:
        float или None
    """
    for obj in (inst, symbol):
        if obj is None:
            continue
        for pname in (u'Глубина', u'Depth', u'ADSK_Размер_Глубина'):
            try:
                v = _get_param_as_double(obj, name=pname)
                if v is not None and float(v) > 1e-9:
                    return float(v)
            except Exception:
                continue
    return None


def _try_orient_instance_to_dir(doc, inst, origin_pt, desired_dir_xy):
    """Повернуть экземпляр вокруг оси Z так, чтобы его facing совпадал с desired_dir_xy.

    Args:
        doc: Document
        inst: FamilyInstance
        origin_pt: XYZ (точка вращения)
        desired_dir_xy: XYZ (желаемое направление facing)
    """
    if doc is None or inst is None or origin_pt is None or desired_dir_xy is None:
        return

    des = _xy_unit(desired_dir_xy)
    if des is None:
        return

    cur = None
    try:
        cur = getattr(inst, 'FacingOrientation', None)
    except Exception:
        cur = None
    if cur is None:
        try:
            cur = getattr(inst, 'HandOrientation', None)
        except Exception:
            cur = None

    cur = _xy_unit(cur)
    if cur is None:
        return

    try:
        ang = float(cur.AngleTo(des))
        if ang < 1e-6:
            return

        cross = cur.CrossProduct(des)
        if cross and float(cross.Z) < 0.0:
            ang = -ang

        axis = DB.Line.CreateBound(origin_pt, origin_pt + DB.XYZ(0, 0, 10))
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, ang)
    except Exception:
        return


def _try_flip_facing_to_dir(inst, desired_dir_host, origin_pt=None):
    """Убедиться, что экземпляр смотрит в сторону desired_dir_host (XY).

    Исправляет случай, когда устройства на стене создаются лицом внутрь стены.

    Args:
        inst: FamilyInstance
        desired_dir_host: XYZ (желаемое направление facing)
        origin_pt: XYZ (точка вращения, опционально)

    Returns:
        bool: True если был flip
    """
    if inst is None or desired_dir_host is None:
        return False

    des = _xy_unit(desired_dir_host)
    if des is None:
        return False

    cur = None
    try:
        cur = getattr(inst, 'FacingOrientation', None)
    except Exception:
        cur = None
    cur = _xy_unit(cur)
    if cur is None:
        return False

    try:
        dp = float(cur.DotProduct(des))
    except Exception:
        dp = None
    if dp is None or dp >= 0.0:
        return False

    # 1) Preferred API
    try:
        inst.FlipFacing()
        return True
    except Exception:
        pass

    # 2) Fallback: toggle built-in facing flipped parameter if available
    try:
        for bip_name in ('INSTANCE_FACING_FLIPPED', 'FACING_FLIPPED'):
            try:
                bip = getattr(DB.BuiltInParameter, bip_name, None)
            except Exception:
                bip = None
            if bip is None:
                continue
            p = None
            try:
                p = inst.get_Parameter(bip)
            except Exception:
                p = None
            if p is None:
                continue
            try:
                if p.IsReadOnly:
                    continue
            except Exception:
                pass
            try:
                if p.StorageType != DB.StorageType.Integer:
                    continue
            except Exception:
                pass
            try:
                v = p.AsInteger()
                p.Set(0 if int(v or 0) else 1)
                return True
            except Exception:
                continue
    except Exception:
        pass

    # 3) Last resort: rotate 180° around vertical axis at insertion point
    try:
        lp = origin_pt
        if lp is None:
            try:
                loc = getattr(inst, 'Location', None)
                lp = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                lp = None
        if lp is None:
            try:
                bb = inst.get_BoundingBox(None)
                if bb:
                    lp = (bb.Min + bb.Max) * 0.5
            except Exception:
                lp = None
        if lp is None:
            return False

        axis = DB.Line.CreateBound(lp, lp + DB.XYZ.BasisZ)
        DB.ElementTransformUtils.RotateElement(inst.Document, inst.Id, axis, float(math.pi))
        return True
    except Exception:
        return False


def _apply_half_protrusion(doc_, inst, outward_dir_xy, depth_ft, origin_pt=None, recess_ft=0.0):
    """Выровнять заднюю часть экземпляра с плоскостью стены (избежать утопления в стену).

    Исторически этот инструмент пытался установить выступ на половину глубины устройства.
    На практике для многих семейств панелей это приводит к утоплению панели в стену.
    Вместо этого мы выравниваем заднюю точку экземпляра (вдоль outward_dir_xy)
    с точкой плоскости стены (origin_pt).

    Args:
        doc_: Document
        inst: FamilyInstance
        outward_dir_xy: XYZ (направление "наружу" от стены)
        depth_ft: float (глубина устройства в футах)
        origin_pt: XYZ (точка на плоскости стены, опционально)
        recess_ft: float (желаемое углубление в стену, по умолчанию 0.0)

    Returns:
        bool: True если удалось выровнять
    """
    if doc_ is None or inst is None or outward_dir_xy is None:
        return False

    des = _xy_unit(outward_dir_xy)
    if des is None:
        return False

    if origin_pt is None:
        try:
            loc = getattr(inst, 'Location', None)
            origin_pt = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            origin_pt = None
    if origin_pt is None:
        return False

    from utils_units import mm_to_ft
    tol = float(mm_to_ft(1) or 0.0)

    def _extents():
        return _bbox_extents_along_dir(inst, origin_pt, des)

    try:
        recess = float(recess_ft) if recess_ft is not None else 0.0
    except Exception:
        recess = 0.0
    if recess < 0.0:
        recess = 0.0
    target = -float(recess)  # negative => into wall (recess)

    min_rel, _max_rel = _extents()
    if min_rel is None:
        return False

    # Target: min_rel == target
    move_dist = float(min_rel) - float(target)
    if abs(move_dist) <= tol:
        return True

    delta = float(-move_dist)  # + => move outward, - => move inward

    # Safety clamp: avoid moving the panel by an unreasonable distance due to bad bbox/dir.
    try:
        max_shift = float(mm_to_ft(500) or 0.0)
        if max_shift > 1e-9 and abs(delta) > max_shift:
            return False
    except Exception:
        pass

    # 1) Try host offset (for face-hosted families). Verify direction; if wrong, try opposite.
    if _try_adjust_host_offset(inst, delta):
        m2, _ = _extents()
        if m2 is not None and abs(float(m2) - float(target)) <= tol:
            return True
        # If it got worse (more embedded), revert and try opposite sign
        if m2 is not None and abs(float(m2) - float(target)) > abs(float(min_rel) - float(target)):
            try:
                _try_adjust_host_offset(inst, -delta)  # revert
            except Exception:
                pass
            if _try_adjust_host_offset(inst, -delta):
                m3, _ = _extents()
                if m3 is not None and abs(float(m3) - float(target)) <= tol:
                    return True
                if m3 is not None and abs(float(m3) - float(target)) < abs(float(min_rel) - float(target)):
                    return True
                # still not improved -> revert back
                try:
                    _try_adjust_host_offset(inst, delta)
                except Exception:
                    pass
        else:
            # Some improvement even if not perfect
            if m2 is not None and abs(float(m2) - float(target)) < abs(float(min_rel) - float(target)):
                return True

    # 2) Fallback: move element (works for unhosted point-based families)
    try:
        v = DB.XYZ(float(des.X) * float(delta), float(des.Y) * float(delta), 0.0)
        DB.ElementTransformUtils.MoveElement(doc_, inst.Id, v)
        m2, _ = _extents()
        if m2 is not None and abs(float(m2) - float(target)) <= tol:
            return True
        if m2 is not None and abs(float(m2) - float(target)) > abs(float(min_rel) - float(target)):
            # revert and try opposite
            try:
                v_back = DB.XYZ(float(des.X) * float(-delta), float(des.Y) * float(-delta), 0.0)
                DB.ElementTransformUtils.MoveElement(doc_, inst.Id, v_back)
            except Exception:
                return False
            try:
                v2 = DB.XYZ(float(des.X) * float(-delta), float(des.Y) * float(-delta), 0.0)
                DB.ElementTransformUtils.MoveElement(doc_, inst.Id, v2)
                m3, _ = _extents()
                if m3 is not None and (abs(float(m3) - float(target)) <= tol or abs(float(m3) - float(target)) < abs(float(min_rel) - float(target))):
                    return True
                # revert back
                try:
                    v3 = DB.XYZ(float(des.X) * float(delta), float(des.Y) * float(delta), 0.0)
                    DB.ElementTransformUtils.MoveElement(doc_, inst.Id, v3)
                except Exception:
                    pass
            except Exception:
                return False
        if m2 is not None and abs(float(m2) - float(target)) < abs(float(min_rel) - float(target)):
            return True
        return True
    except Exception:
        return False


def _bbox_extents_along_dir(inst, origin_pt, dir_unit):
    """Вернуть (min_rel, max_rel) bbox экземпляра, спроецированные на dir_unit относительно origin_pt.

    Returns:
        tuple: (min_rel, max_rel) или (None, None)
    """
    if inst is None or origin_pt is None or dir_unit is None:
        return None, None
    try:
        bb = inst.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        # Newly created/modified elements may require regeneration for bbox
        try:
            d = getattr(inst, 'Document', None)
            if d is not None:
                d.Regenerate()
        except Exception:
            pass
        try:
            bb = inst.get_BoundingBox(None)
        except Exception:
            bb = None
    if bb is None:
        return None, None

    try:
        mn = bb.Min
        mx = bb.Max
        corners = []
        for xx in (mn.X, mx.X):
            for yy in (mn.Y, mx.Y):
                for zz in (mn.Z, mx.Z):
                    corners.append(DB.XYZ(float(xx), float(yy), float(zz)))
    except Exception:
        return None, None

    min_rel = None
    max_rel = None
    for c in corners:
        try:
            rel = DB.XYZ(float(c.X) - float(origin_pt.X), float(c.Y) - float(origin_pt.Y), float(c.Z) - float(origin_pt.Z))
            d = float(rel.DotProduct(dir_unit))
        except Exception:
            continue
        if min_rel is None or d < min_rel:
            min_rel = d
        if max_rel is None or d > max_rel:
            max_rel = d

    return min_rel, max_rel


def _try_adjust_host_offset(inst, delta_ft):
    """Попытка скорректировать смещение от хоста (hosted instance) на delta_ft.

    Returns:
        bool: True если удалось
    """
    if inst is None or delta_ft is None:
        return False
    try:
        delta = float(delta_ft)
    except Exception:
        return False

    # Built-in param works across languages if present
    try:
        bip = getattr(DB.BuiltInParameter, 'INSTANCE_FREE_HOST_OFFSET_PARAM', None)
        if bip is not None:
            p = inst.get_Parameter(bip)
            if p is not None and (not p.IsReadOnly):
                try:
                    cur = p.AsDouble()
                except Exception:
                    cur = 0.0
                try:
                    return bool(p.Set(float(cur) + float(delta)))
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback by common localized names
    for pname in (u'Смещение от основы', u'Смещение от хоста', u'Смещение', u'Offset from Host', u'Offset'):
        try:
            p = inst.LookupParameter(pname)
            if p is None or p.IsReadOnly:
                continue
            try:
                cur = p.AsDouble()
            except Exception:
                cur = 0.0
            try:
                return bool(p.Set(float(cur) + float(delta)))
            except Exception:
                continue
        except Exception:
            continue

    return False


# ====================================================================
# DEDUPLICATION
# ====================================================================

def _collect_existing_tagged_points(host_doc, tag):
    """Собрать точки уже размещенных элементов с заданным тегом в Comments.

    Использует parameter filter для быстрого поиска.

    Args:
        host_doc: Document
        tag: Строка тега (например, "AUTO_EOM")

    Returns:
        list of XYZ
    """
    pts = []
    from domain import norm
    t = norm(tag)
    if not t:
        return pts

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag)

        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter)
               .ToElements())

        for e in col:
            try:
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
                if p:
                    pts.append(p)
            except Exception:
                continue
    except Exception:
        return []

    return pts


def _collect_existing_tagged_instances(host_doc, tag):
    """Собрать экземпляры электрооборудования с заданным тегом в Comments.

    Args:
        host_doc: Document
        tag: Строка тега

    Returns:
        list of FamilyInstance
    """
    insts = []
    from domain import norm
    t = norm(tag)
    if not t:
        return insts

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag)

        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))

        for e in col:
            try:
                if e is None or (not isinstance(e, DB.FamilyInstance)):
                    continue
            except Exception:
                continue
            insts.append(e)
    except Exception:
        return []

    return insts


def _find_near_instance(pt, insts, r_ft):
    """Найти первый экземпляр в радиусе r_ft от точки pt.

    Returns:
        FamilyInstance или None
    """
    if pt is None or not insts or not r_ft or float(r_ft) <= 1e-9:
        return None
    rr = float(r_ft)
    for e in insts:
        try:
            loc = getattr(e, 'Location', None)
            p = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            p = None
        if p is None:
            continue
        try:
            if float(p.DistanceTo(pt)) <= rr:
                return e
        except Exception:
            continue
    return None


def _find_near_instances(pt, insts, r_ft):
    """Найти все экземпляры в радиусе r_ft от точки pt.

    Returns:
        list of FamilyInstance
    """
    if pt is None or not insts or not r_ft or float(r_ft) <= 1e-9:
        return []
    rr = float(r_ft)
    res = []
    for e in insts:
        try:
            loc = getattr(e, 'Location', None)
            p = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            p = None
        if p is None:
            continue
        try:
            if float(p.DistanceTo(pt)) <= rr:
                res.append(e)
        except Exception:
            continue
    return res


def _is_near_existing(pt, existing_pts, radius_ft):
    """Проверить, находится ли точка pt близко к какой-либо из existing_pts.

    Returns:
        bool
    """
    if pt is None or not existing_pts or radius_ft is None:
        return False
    r = float(radius_ft)
    for p in existing_pts:
        try:
            if pt.DistanceTo(p) <= r:
                return True
        except Exception:
            continue
    return False


def _collect_existing_type_points(host_doc, symbol):
    """Собрать точки уже размещенных экземпляров заданного типа.

    Избегает дублирования при множественных запусках.

    Args:
        host_doc: Document
        symbol: FamilySymbol

    Returns:
        list of XYZ
    """
    pts = []
    if host_doc is None or symbol is None:
        return pts

    sid = None
    try:
        sid = symbol.Id
    except Exception:
        sid = None

    if sid is None:
        return pts

    try:
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment))

        for e in col:
            try:
                if e is None:
                    continue
                if e.GetTypeId() != sid:
                    continue
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
                if p:
                    pts.append(p)
            except Exception:
                continue
    except Exception:
        return []

    return pts


# ====================================================================
# 3D VIEW HELPERS
# ====================================================================

def _get_or_create_debug_3d_view(doc, name, aliases=None):
    """Получить или создать 3D вид с заданным именем.

    Args:
        doc: Document
        name: Имя вида
        aliases: Список альтернативных имен (для поиска существующих)

    Returns:
        View3D или None
    """
    try:
        # Reuse if exists (by primary name or aliases)
        aliases = list(aliases or [])
        for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            try:
                if not v or v.IsTemplate:
                    continue
                if v.Name == name:
                    return v
            except Exception:
                continue

        for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            try:
                if not v or v.IsTemplate:
                    continue
                if aliases and v.Name in aliases:
                    # Try to rename to the primary Russian name
                    try:
                        v.Name = name
                    except Exception:
                        pass
                    return v
            except Exception:
                continue

        vft_id = None
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.ThreeDimensional:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
        if vft_id is None:
            return None

        v3d = DB.View3D.CreateIsometric(doc, vft_id)
        try:
            v3d.Name = name
        except Exception:
            pass
        return v3d
    except Exception:
        return None


def _bbox_from_element_ids(doc, ids, pad_ft=60.0, limit=500):
    """Создать BoundingBoxXYZ из точек элементов с заданными Id.

    Args:
        doc: Document
        ids: Список ElementId
        pad_ft: Отступ от границ (в футах)
        limit: Максимальное количество элементов для обработки

    Returns:
        BoundingBoxXYZ или None
    """
    if doc is None or not ids:
        return None
    try:
        pad = float(pad_ft or 0.0)
        minx = None
        miny = None
        minz = None
        maxx = None
        maxy = None
        maxz = None
        i = 0
        for eid in ids:
            i += 1
            if limit and i > int(limit):
                break
            e = None
            try:
                e = doc.GetElement(eid)
            except Exception:
                e = None
            if e is None:
                continue

            p = None
            try:
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                p = None

            if p is None:
                try:
                    bb = e.get_BoundingBox(None)
                    if bb:
                        p = (bb.Min + bb.Max) * 0.5
                except Exception:
                    p = None

            if p is None:
                continue

            if minx is None:
                minx = p.X
                miny = p.Y
                minz = p.Z
                maxx = p.X
                maxy = p.Y
                maxz = p.Z
            else:
                if p.X < minx:
                    minx = p.X
                if p.Y < miny:
                    miny = p.Y
                if p.Z < minz:
                    minz = p.Z
                if p.X > maxx:
                    maxx = p.X
                if p.Y > maxy:
                    maxy = p.Y
                if p.Z > maxz:
                    maxz = p.Z

        if minx is None:
            return None

        bb2 = DB.BoundingBoxXYZ()
        bb2.Min = DB.XYZ(minx - pad, miny - pad, minz - pad)
        bb2.Max = DB.XYZ(maxx + pad, maxy + pad, maxz + pad)
        return bb2
    except Exception:
        return None


def _as_net_id_list(ids):
    """Преобразовать python list[ElementId] в .NET List[ElementId] для Revit API.

    Returns:
        System.Collections.Generic.List[ElementId] или None
    """
    try:
        from System.Collections.Generic import List
        lst = List[DB.ElementId]()
        for i in ids or []:
            try:
                if i is not None:
                    lst.Add(i)
            except Exception:
                continue
        return lst
    except Exception:
        return None
