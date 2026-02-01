# -*- coding: utf-8 -*-

import math
import re

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, ensure_symbol_active, log_exception, set_comments, set_mark, tx
from time_savings import report_time_saved
from utils_units import mm_to_ft
try:
    import socket_utils as su
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


def _get_user_config():
    try:
        return script.get_config()
    except Exception:
        return None


def _save_user_config():
    try:
        script.save_config()
        return True
    except Exception:
        return False


def _load_symbol_from_saved_id(doc, cfg, key):
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
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, int(symbol.Id.IntegerValue))
    except Exception:
        pass


def _store_symbol_unique_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


def _pick_symbol_from_existing_instance(category_bic):
    """Pick an existing instance in host doc and use its type (avoids scanning all types)."""
    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    bic_int = int(category_bic)

    class InstFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                if elem is None:
                    return False
                if not isinstance(elem, DB.FamilyInstance):
                    return False
                cat = getattr(elem, 'Category', None)
                return bool(cat and cat.Id and int(cat.Id.IntegerValue) == bic_int)
            except Exception:
                return False

        def AllowReference(self, reference, position):
            return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.Element, InstFilter(), 'Выберите размещённый щит в модели ЭОМ, чтобы определить тип семейства')
    except Exception:
        return None

    try:
        inst = doc.GetElement(r.ElementId)
        return inst.Symbol if inst else None
    except Exception:
        return None


KEYWORDS = [u'кв', u'apartment', u'вход']
HALL_KEYWORD = u'прихож'
STEEL_FAMILY_KEYWORDS = [u'сталь', u'стал', u'стальное', u'steel']

# Apartment-side detection for "inside" placement
APARTMENT_ROOM_KEYWORDS = [u'прихож', u'квартир', u'квар', u'студия', u'кухня-столовая', u'studio']
OUTSIDE_ROOM_KEYWORDS = [u'внекварт', u'корид', u'моп', u'лестн', u'тамбур', u'улиц', u'наруж', u'холл', u'шахт', u'подъезд']

# Panel auto-pick heuristics (when config type is missing in project)
PANEL_STRONG_KEYWORDS = [u'щк', u'shk', u'шк']
PANEL_APT_KEYWORDS = [u'квартир', u'apartment', u'apt']
PANEL_GENERIC_KEYWORDS = [u'щит', u'panel']
PANEL_WEAK_KEYWORDS = [u'щр', u'board']
PANEL_NEGATIVE_KEYWORDS = [u'вру', u'грщ', u'main', u'уго', u'аннотац']


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _norm_type_key(s):
    """Normalize strings to reduce Cyrillic/Latin look-alike mismatches."""
    t = _norm(s)
    if not t:
        return t

    # Normalize dash variants to '-'
    try:
        for ch in (u'–', u'—', u'‑', u'−'):
            t = t.replace(ch, u'-')
    except Exception:
        pass

    try:
        repl = {
            u'а': u'a',
            u'в': u'b',
            u'е': u'e',
            u'к': u'k',
            u'м': u'm',
            u'н': u'h',
            u'о': u'o',
            u'р': u'p',
            u'с': u'c',
            u'т': u't',
            u'у': u'y',
            u'х': u'x',
        }
        for k, v in repl.items():
            t = t.replace(k, v)
    except Exception:
        pass
    try:
        t = u' '.join(t.split())
    except Exception:
        pass
    try:
        t = t.replace(u' : ', u':').replace(u' :', u':').replace(u': ', u':')
    except Exception:
        pass
    return t


def _get_param_as_double(elem, bip=None, name=None):
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


def _door_text(door):
    # Combine Mark + Comments
    mark = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name='Mark')
    comm = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name='Comments')
    return _norm(u'{0} {1}'.format(mark, comm))


def _door_family_type_text(door):
    """Return normalized door Family/Type info (link-side)."""
    if door is None:
        return u''
    try:
        # CPython/pythonnet can sometimes return None or a proxy for door.Symbol; use GetTypeId as a robust fallback.
        sym = None

        # 1) Direct Symbol
        try:
            sym = getattr(door, 'Symbol', None)
        except Exception:
            sym = None

        if sym is not None:
            try:
                fam = getattr(sym, 'Family', None)
                fam_name = getattr(fam, 'Name', u'') if fam else u''
                typ_name = getattr(sym, 'Name', u'') or u''
                if fam_name or typ_name:
                    return _norm(u'{0} {1}'.format(fam_name, typ_name))
            except Exception:
                pass

        # 2) Fallback via type id
        try:
            ddoc = getattr(door, 'Document', None)
            tid = door.GetTypeId() if hasattr(door, 'GetTypeId') else None
            if ddoc is not None and tid is not None and tid != DB.ElementId.InvalidElementId:
                sym = ddoc.GetElement(tid)
        except Exception:
            sym = None

        if sym is not None:
            try:
                fam = getattr(sym, 'Family', None)
                fam_name = getattr(fam, 'Name', u'') if fam else u''
                typ_name = getattr(sym, 'Name', u'') or u''
                if fam_name or typ_name:
                    return _norm(u'{0} {1}'.format(fam_name, typ_name))
            except Exception:
                pass

        return u''
    except Exception:
        return u''


def _has_any_keyword(text, keywords):
    t = _norm(text)
    for k in keywords or []:
        if _norm(k) and _norm(k) in t:
            return True
    return False


def _score_text(text, plus=None, minus=None):
    t = _norm(text)
    score = 0

    for k in plus or []:
        kk = _norm(k)
        if kk and kk in t:
            score += 1

    for k in minus or []:
        kk = _norm(k)
        if kk and kk in t:
            score -= 1

    return score


def _score_panel_symbol(symbol):
    try:
        label = placement_engine.format_family_type(symbol)
    except Exception:
        label = ''

    t = _norm(label)
    score = 0
    if not t:
        return -999

    # Strong preference for ShK/ЩК names
    if _has_any_keyword(t, PANEL_STRONG_KEYWORDS):
        score += 100

    # Apartment hints
    if _has_any_keyword(t, PANEL_APT_KEYWORDS):
        score += 60

    # Generic panel hints
    if _has_any_keyword(t, PANEL_GENERIC_KEYWORDS):
        score += 30

    # Weak hints (distribution board etc.)
    if _has_any_keyword(t, PANEL_WEAK_KEYWORDS):
        score += 15

    # Mild preference for EOM naming
    if 'eom' in t:
        score += 10

    # Penalize obvious non-targets
    if _has_any_keyword(t, PANEL_NEGATIVE_KEYWORDS):
        score -= 80

    return score


def _iter_panel_symbols(doc, limit=2000):
    """Iterate candidate panel symbols from the host doc.

    We intentionally restrict to Electrical Equipment symbols to keep collectors fast and stable.
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
    """Iterate FamilySymbol across categories.

    Used for *configured* lookup to avoid missing the target if the family category differs.
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


def _find_panel_symbol_by_label(doc, fam_fullname):
    target = _norm_type_key(fam_fullname)
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
                if _norm_type_key(placement_engine.format_family_type(s)) == target:
                    return s
            else:
                # If no family specified, allow matching by type name or family name.
                try:
                    if _norm_type_key(getattr(s, 'Name', u'')) == target:
                        return s
                except Exception:
                    pass
                try:
                    fam = getattr(s, 'Family', None)
                    fam_name = getattr(fam, 'Name', u'') if fam else u''
                    if _norm_type_key(fam_name) == target:
                        return s
                except Exception:
                    pass
        except Exception:
            continue

    # 2) Fallback: scan all FamilySymbol (capped)
    for s in _iter_panel_symbols_any(doc, limit=50000):
        try:
            if has_colon:
                if _norm_type_key(placement_engine.format_family_type(s)) == target:
                    return s
            else:
                try:
                    if _norm_type_key(getattr(s, 'Name', u'')) == target:
                        return s
                except Exception:
                    pass
                try:
                    fam = getattr(s, 'Family', None)
                    fam_name = getattr(fam, 'Name', u'') if fam else u''
                    if _norm_type_key(fam_name) == target:
                        return s
                except Exception:
                    pass
        except Exception:
            continue
    return None


def _find_param_by_norm(elem, pname):
    """Find parameter on element by exact name, then by normalized name."""
    if elem is None or not pname:
        return None

    try:
        p = elem.LookupParameter(pname)
        if p is not None:
            return p
    except Exception:
        p = None

    key = _norm_type_key(pname)
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
            if _norm_type_key(n) == key:
                return p2
    except Exception:
        return None

    return None


def _symbol_matches_label(symbol, fam_fullname):
    if symbol is None:
        return False
    target = _norm_type_key(fam_fullname)
    if not target:
        return False
    try:
        has_colon = (u':' in (fam_fullname or u''))
    except Exception:
        has_colon = False

    try:
        if has_colon and _norm_type_key(placement_engine.format_family_type(symbol)) == target:
            return True
    except Exception:
        pass

    try:
        if _norm_type_key(getattr(symbol, 'Name', u'')) == target:
            return True
    except Exception:
        pass

    try:
        fam = getattr(symbol, 'Family', None)
        fam_name = getattr(fam, 'Name', u'') if fam else u''
        if _norm_type_key(fam_name) == target:
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


def _param_checked(elem, pname):
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


def _variant_prefix_key(variant_param_name):
    # IMPORTANT: parameter names often contain non-ascii hyphens (– — ‑ −),
    # so we normalize first using the same routine as everywhere else.
    n = _norm_type_key(variant_param_name)
    if not n:
        return None

    try:
        m = re.match(u'^(.*?)-\s*\d+\b', n)
    except Exception:
        m = None
    if not m:
        return None
    try:
        base = (m.group(1) or u'').strip()
    except Exception:
        base = u''
    if not base:
        return None
    return _norm_type_key(base + u'-')


def _is_panel_module_variant_param_name(pname):
    """Heuristic: detect Yes/No params that represent panel box module variants.

    Some families expose multiple series (e.g. ЩРВ-П-* and ЩРВ-П-П-*) as separate Yes/No params,
    and several of them can be ON simultaneously. We treat any param that mentions modules and
    contains a number as a variant switch.
    """
    n = _norm(pname)
    if not n:
        return False
    try:
        has_modul = re.search(u'(модул|module|modul)', n, flags=re.IGNORECASE) is not None
    except Exception:
        has_modul = (u'модул' in n) or ('module' in n) or ('modul' in n)

    if not has_modul:
        return False

    try:
        has_num = re.search(u'\d+', n) is not None
    except Exception:
        has_num = any(ch.isdigit() for ch in n)

    return bool(has_modul and has_num)


def _apply_panel_variant_params(elem, desired_param_name):
    """Enable desired module variant and disable other module variants.

    Works for both FamilySymbol (type params) and FamilyInstance (instance params).
    """
    if elem is None or not desired_param_name:
        return False

    desired_key = _norm_type_key(desired_param_name)
    if not desired_key:
        return False

    p_des = _find_param_by_norm(elem, desired_param_name)
    if p_des is None:
        return False

    prefix_key = _variant_prefix_key(desired_param_name)
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

                nkey = _norm_type_key(pname)
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
            if not _is_panel_module_variant_param_name(pname):
                continue

            nkey = _norm_type_key(pname)
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


def _enabled_panel_module_variant_param_names(elem):
    """Return list of enabled module-variant parameter names (value==1)."""
    if elem is None:
        return []
    try:
        params = getattr(elem, 'Parameters', None)
    except Exception:
        params = None
    if params is None:
        return []

    enabled = []
    for p in params:
        try:
            d = getattr(p, 'Definition', None)
            pname = getattr(d, 'Name', None) if d is not None else None
        except Exception:
            pname = None
        if not pname:
            continue
        if not _is_panel_module_variant_param_name(pname):
            continue
        try:
            if p.StorageType != DB.StorageType.Integer:
                continue
        except Exception:
            continue
        try:
            if int(p.AsInteger() or 0) == 1:
                enabled.append(pname)
        except Exception:
            continue
    return enabled


def _log_shk_variant_state(label, symbol, desired_param_name=None):
    """Log enabled module variants for a symbol (only logs when state looks suspicious)."""
    if symbol is None:
        return
    try:
        enabled = _enabled_panel_module_variant_param_names(symbol)
        if not enabled:
            return
        desired_key = _norm_type_key(desired_param_name) if desired_param_name else ''
        ok = False
        if desired_key and len(enabled) == 1 and _norm_type_key(enabled[0]) == desired_key:
            ok = True
        if ok:
            return

        try:
            sid = symbol.Id.IntegerValue
        except Exception:
            sid = None
        try:
            sname = getattr(symbol, 'Name', u'')
        except Exception:
            sname = u''
        logger.warning(u"[ShK] %s | Type='%s' (Id:%s) | enabled=%s", label, sname, sid, enabled)
    except Exception:
        pass


def _iter_family_symbols(doc_, family):
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


def _make_unique_type_name(doc_, family, base_name):
    if doc_ is None or family is None:
        return base_name
    try:
        existing = set([_norm_type_key(getattr(s, 'Name', u'')) for s in _iter_family_symbols(doc_, family)])
    except Exception:
        existing = set()

    bn = _norm_type_key(base_name)
    if bn and bn not in existing:
        return base_name

    i = 2
    while i < 100:
        cand = u'{0} ({1})'.format(base_name, i)
        if _norm_type_key(cand) not in existing:
            return cand
        i += 1
    return base_name


def _make_variant_type_name(doc_, base_symbol, desired_param_name):
    try:
        base_type = getattr(base_symbol, 'Name', u'') or u''
    except Exception:
        base_type = u''
    if not base_type:
        base_type = u'Panel'

    num = None
    try:
        m = re.search(u'-(\d+)\b', (desired_param_name or u''))
        if m:
            num = m.group(1)
    except Exception:
        num = None

    if num:
        name = u'{0}-{1}'.format(base_type, num)
    else:
        name = u'{0} (VAR)'.format(base_type)

    try:
        fam = getattr(base_symbol, 'Family', None)
    except Exception:
        fam = None
    return _make_unique_type_name(doc_, fam, name)


def _ensure_panel_variant_symbol(doc_, base_symbol, desired_param_name):
    """Return a FamilySymbol with desired_param_name checked (creates a duplicate type if needed)."""
    if doc_ is None or base_symbol is None or not desired_param_name:
        return base_symbol

    # If base doesn't even have this parameter, nothing to do
    if _find_param_by_norm(base_symbol, desired_param_name) is None:
        return base_symbol

    def _has_other_variant_checked(sym):
        """Detect if any other module variant is enabled (across all series/prefixes)."""
        if sym is None:
            return False
        desired_key = _norm_type_key(desired_param_name)
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
            if not _is_panel_module_variant_param_name(pname):
                continue
            nkey = _norm_type_key(pname)
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
    new_sym = None
    new_name = _make_variant_type_name(doc_, base_symbol, desired_param_name)
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


def _post_fix_panel_variant(doc_, symbol, desired_param_name):
    """Best-effort post-fix: ensure only desired module variant is enabled on the TYPE.

    This runs after placement to counter cases when Revit/other logic re-enables a module option.
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
        desired_key = _norm_type_key(desired_param_name)
    except Exception:
        desired_key = ''

    desired_is_four = False
    try:
        desired_is_four = re.search(u'(^|[^0-9])4([^0-9]|$)', desired_key or u'') is not None
    except Exception:
        desired_is_four = False

    four_re = None
    try:
        four_re = re.compile(u'(?:^|[^0-9])4\s*(?:модул|modul|module)', re.IGNORECASE)
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
            is_variant = _is_panel_module_variant_param_name(pname)
            try:
                norm_name = _norm_type_key(pname)
            except Exception:
                norm_name = u''
            is_four = False
            try:
                is_four = bool(four_re and four_re.search(_norm(pname)))
            except Exception:
                is_four = (u'4' in norm_name and u'модул' in norm_name)

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


def _guess_panel_symbol_for_variant(doc_, desired_param_name, candidate_labels=None):
    """Try to pick a base panel symbol that contains the desired_param_name as a Yes/No parameter."""
    if doc_ is None or not desired_param_name:
        return None

    # 1) Prefer candidates suggested by auto-pick
    for lbl in candidate_labels or []:
        try:
            sym = _find_panel_symbol_by_label(doc_, lbl)
        except Exception:
            sym = None
        if sym is None:
            continue
        if _find_param_by_norm(sym, desired_param_name) is not None:
            return sym

    # 2) Try derive base name (prefix before -<digits>) and match family/type
    base_guess = None
    try:
        m = re.match(u'^(.*?)-\s*\d+\b', (desired_param_name or u'').strip())
        if m:
            base_guess = (m.group(1) or u'').strip()
    except Exception:
        base_guess = None

    if base_guess:
        bkey = _norm_type_key(base_guess)
        if bkey:
            for sym in _iter_panel_symbols(doc_, limit=20000):
                try:
                    if sym is None:
                        continue
                    try:
                        fam = getattr(sym, 'Family', None)
                        fam_name = getattr(fam, 'Name', u'') if fam else u''
                    except Exception:
                        fam_name = u''

                    if (bkey == _norm_type_key(getattr(sym, 'Name', u''))) or (bkey == _norm_type_key(fam_name)):
                        if _find_param_by_norm(sym, desired_param_name) is not None:
                            return sym
                except Exception:
                    continue

    # 3) Last resort: any electrical equipment symbol that has this parameter
    for sym in _iter_panel_symbols(doc_, limit=20000):
        try:
            if _find_param_by_norm(sym, desired_param_name) is not None:
                return sym
        except Exception:
            continue

    return None


def _is_hosted_symbol(symbol):
    if symbol is None:
        return False
    try:
        _, pt_name = placement_engine.get_symbol_placement_type(symbol)
        n = _norm(str(pt_name))
        return ('host' in n) or ('hosted' in n) or ('wall' in n) or ('face' in n)
    except Exception:
        return False


def _is_supported_panel_placement(symbol):
    if symbol is None:
        return False
    try:
        if placement_engine.is_supported_point_placement(symbol):
            return True
    except Exception:
        pass
    return _is_hosted_symbol(symbol)


def _auto_pick_panel_symbol(doc, prefer_fullname=None):
    """Auto-pick best available electrical equipment symbol for ShK.

    Returns (symbol, picked_label, candidates_labels)
    """
    prefer = _norm(prefer_fullname)

    ranked = []
    for s in _iter_panel_symbols(doc, limit=5000):
        try:
            if not _is_supported_panel_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue

            sc = _score_panel_symbol(s)
            if prefer and _norm(lbl) == prefer:
                # Config match wins if present
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None, None, []

    ranked.sort(key=lambda x: (x[0], _norm(x[1])), reverse=True)
    best = ranked[0]
    return best[2], best[1], [r[1] for r in ranked[:10]]


def _pick_panel_symbol(doc_, cfg, fullname):
    """Pick panel symbol from configured name -> cache -> auto.

    If `fullname` is provided but not found, returns (None, None, top10_candidates).
    """
    prefer_fullname = fullname

    def _try_pick_from_cache():
        sym = None
        try:
            sym = _load_symbol_from_saved_unique_id(doc_, cfg, 'last_panel_shk_symbol_uid')
        except Exception:
            sym = None
        if sym is None:
            try:
                sym = _load_symbol_from_saved_id(doc_, cfg, 'last_panel_shk_symbol_id')
            except Exception:
                sym = None
        if sym is not None:
            try:
                if _is_supported_panel_placement(sym):
                    return sym
            except Exception:
                return sym
        return None

    # 1) Configured fullname/name takes precedence
    if prefer_fullname:
        sym_cfg = _find_panel_symbol_by_label(doc_, prefer_fullname)
        if sym_cfg is not None:
            try:
                if _is_supported_panel_placement(sym_cfg):
                    return sym_cfg, placement_engine.format_family_type(sym_cfg), []
            except Exception:
                return sym_cfg, None, []

        # If config doesn't match what's loaded, only allow using cache if it matches config.
        sym_cache = _try_pick_from_cache()
        if sym_cache is not None and _symbol_matches_label(sym_cache, prefer_fullname):
            return sym_cache, placement_engine.format_family_type(sym_cache), []

        # Not found: show candidates but do NOT auto-place a random panel.
        _sym_auto, _lbl_auto, top10 = _auto_pick_panel_symbol(doc_, prefer_fullname=None)
        return None, None, top10

    # 2) Cache
    sym = _try_pick_from_cache()
    if sym is not None:
        return sym, placement_engine.format_family_type(sym), []

    # 3) Auto
    return _auto_pick_panel_symbol(doc_, prefer_fullname=None)


def _select_panel_symbol_ui(doc_, prefer_fullname=None, scan_limit=20000, limit=300):
    """Ask user to pick a panel FamilySymbol from loaded types (best-effort, capped)."""
    if doc_ is None:
        return None

    prefer_key = _norm_type_key(prefer_fullname) if prefer_fullname else u''
    ranked = []

    for s in _iter_panel_symbols_any(doc_, limit=scan_limit):
        try:
            if s is None:
                continue
            if not _is_supported_panel_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue
            sc = _score_panel_symbol(s)
            if prefer_key and _norm_type_key(lbl) == prefer_key:
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None

    ranked.sort(key=lambda x: (x[0], _norm(x[1])), reverse=True)

    items = []
    for sc, lbl, s in ranked[:max(int(limit or 300), 50)]:
        try:
            cat = u''
            try:
                cat = s.Category.Name if getattr(s, 'Category', None) else u''
            except Exception:
                cat = u''
            _, pt_name = placement_engine.get_symbol_placement_type(s)
            try:
                sid = s.Id.IntegerValue
            except Exception:
                sid = None
            disp = u'{0}   [{1}]   [{2}]'.format(lbl, cat or u'категория?', pt_name)
            if sid is not None:
                disp = disp + u'   (Id:{0})'.format(sid)
            items.append((disp, s))
        except Exception:
            continue

    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title='Выберите тип щита ШК',
        multiselect=False,
        button_name='Выбрать',
        allow_none=True
    )
    if not picked:
        return None
    for lbl, sym in items:
        if lbl == picked:
            return sym
    return None


def _iter_from_to_rooms(door, phases):
    """Yield adjacent rooms (best-effort) across phases."""
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


def _is_apartment_entrance_by_rooms(door, link_doc):
    # Using all phases can be very slow. Prefer last phase.
    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []

    for r in _iter_from_to_rooms(door, phases):
        try:
            name = _norm(getattr(r, 'Name', u''))
            if HALL_KEYWORD in name:
                return True
        except Exception:
            continue
    return False


def _try_get_apartment_number(door, link_doc):
    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []

    for r in _iter_from_to_rooms(door, phases):
        try:
            name = _norm(getattr(r, 'Name', u''))
            if HALL_KEYWORD in name:
                num = getattr(r, 'Number', None)
                if num:
                    return str(num)
        except Exception:
            continue
    return None


def _door_head_point_link(door):
    """Return placement point in LINK coordinates: above door head center."""
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
    """Return door center point in LINK coordinates (XY at door insertion), best-effort."""
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
    """Return door head Z in LINK coordinates, best-effort."""
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


def _pick_apartment_room(door, link_doc):
    """Pick adjacent room that represents apartment interior (prefer "прихож")."""
    if door is None or link_doc is None:
        return None

    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []

    best = None
    for r in _iter_from_to_rooms(door, phases):
        try:
            name = _norm(getattr(r, 'Name', u''))
        except Exception:
            name = u''

        if not name:
            continue

        # strong match
        if HALL_KEYWORD in name:
            return r

        # weaker apartment hints
        for kw in APARTMENT_ROOM_KEYWORDS:
            if _norm(kw) and _norm(kw) in name:
                best = best or r
                break

    return best


def _get_last_phase(doc):
    try:
        phases = list(doc.Phases)
        return phases[-1] if phases else None
    except Exception:
        return None


def _try_get_room_at_point(doc, pt, phase=None):
    if doc is None or pt is None:
        return None
    # Try overloads (phase-aware first)
    try:
        if phase is not None:
            return doc.GetRoomAtPoint(pt, phase)
    except Exception:
        pass
    try:
        return doc.GetRoomAtPoint(pt)
    except Exception:
        return None


def _score_room_apartment(room):
    if room is None:
        return 0
    try:
        name = _norm(getattr(room, 'Name', u''))
    except Exception:
        name = u''

    if not name:
        return 0

    score = 0
    # Strong preference for Hallway inside apartment
    if HALL_KEYWORD in name:
        score += 100
    for kw in APARTMENT_ROOM_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in name):
            score += 30
    for kw in OUTSIDE_ROOM_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in name):
            score -= 200 # Heavy penalty for public/corridor rooms

    return score


def _is_confirmed_apartment_door(door, link_doc):
    """Check if door leads TO or FROM a confirmed apartment room (avoids MOP-MOP doors)."""
    # 1. Try specific created phase (most accurate)
    phases_to_try = []
    try:
        ph_id = getattr(door, 'CreatedPhaseId', DB.ElementId.InvalidElementId)
        if ph_id != DB.ElementId.InvalidElementId:
            ph = link_doc.GetElement(ph_id)
            if ph: phases_to_try.append(ph)
    except: pass
    
    # 2. Add Last phase (common fallback)
    try:
        last_ph = list(link_doc.Phases)[-1]
        if last_ph not in phases_to_try:
            phases_to_try.append(last_ph)
    except Exception:
        pass

    # 3. Add ALL phases (last resort)
    try:
        all_phases = list(link_doc.Phases)
        for p in all_phases:
            if p not in phases_to_try:
                phases_to_try.append(p)
    except Exception:
        pass

    has_apt = False
    has_outside = False

    # Check phases in order of likelihood
    # If we find a valid room configuration in ANY phase, we accept it.
    for phase_set in [phases_to_try]: 
        # actually iterate individual phases, but we want to break early if we find a match?
        # A door exists in one phase timeline. Usually FromRoom/ToRoom methods take a single phase.
        pass

    # Different strategy: check 'FromRoom'/'ToRoom' for the *specific* list of phases 
    # and accumulate evidence.
    
    for ph in phases_to_try:
        # Check this specific phase
        # Note: _iter_from_to_rooms yields rooms for the given list of phases
        found_rooms = list(_iter_from_to_rooms(door, [ph]))
        if not found_rooms:
            continue
            
        this_phase_apt = False
        this_phase_out = False
        
        for r in found_rooms:
            sc = _score_room_apartment(r)
            if sc > 0: this_phase_apt = True
            if sc < -50: this_phase_out = True
        
        # Accumulate global flags (if it's an apartment door in ANY valid phase, count it)
        if this_phase_apt: has_apt = True
        if this_phase_out: has_outside = True
        
        # Optimization: if we found both, we are sure.
        if has_apt and has_outside:
             return True

    # If we noticed it's an apartment entrance in at least one phase
    if has_apt and has_outside:
        return True
    
    # Weak check: if we see apartment side but can't resolve outside (e.g. unplaced room), accept
    if has_apt and (not has_outside):
        return True 

    # 4. Final Fallback: Spatial Check (Geometric) with Offset
    # If API properties failed, try to spatially find a room near the door center.
    try:
        if not (has_apt or has_outside): # only if completely failed
            p_door = None
            facing = None
            try:
                loc = door.Location
                if loc and hasattr(loc, 'Point'):
                    p_door = loc.Point
                if hasattr(door, 'FacingOrientation'):
                    facing = door.FacingOrientation
            except: pass
            
            check_points = []
            if p_door:
                # Lift point by 1 ft (~300mm) to avoid being below room volume (e.g. floor finishes)
                p_check = DB.XYZ(p_door.X, p_door.Y, p_door.Z + 1.0)
                
                # 1. Center point (might be in wall)
                check_points.append(p_check)
                
                # 2. Offset points (front/back) to get out of the wall
                if facing:
                    try:
                        # Offset by ~400mm (1.3 ft)
                        off_vec = facing * 1.3
                        check_points.append(p_check + off_vec)
                        check_points.append(p_check - off_vec)
                    except: pass
            
            found_apt_spatial = False
            found_out_spatial = False
            
            for pt in check_points:
                # Check IsPointInRoom for the phases we collected
                for ph in phases_to_try:
                    try:
                        # GetRoomAtPoint returns the room enclosing the point
                        r_at_point = link_doc.GetRoomAtPoint(pt, ph)
                        if r_at_point and r_at_point.Location:
                            sc = _score_room_apartment(r_at_point)
                            if sc > 0: found_apt_spatial = True
                            if sc < -50: found_out_spatial = True
                    except: 
                        continue
            
            if found_apt_spatial:
                return True
    except:
        pass
        
    return False


def _get_from_to_rooms(door, link_doc):
    """Return (from_room, to_room) for last phase, best-effort."""
    if door is None or link_doc is None:
        return None, None
    ph = _get_last_phase(link_doc)
    if ph is None:
        return None, None

    fr = None
    tr = None
    try:
        m = getattr(door, 'get_FromRoom', None)
        if m is not None:
            fr = m(ph)
    except Exception:
        fr = None
    try:
        m = getattr(door, 'get_ToRoom', None)
        if m is not None:
            tr = m(ph)
    except Exception:
        tr = None

    return fr, tr


def _choose_inside_dir_by_rooms_or_probe(door, link_doc, center_pt, normal_xy):
    """Return unit XY normal pointing INSIDE (apartment side) using rooms/probe. Returns None if unknown."""
    n = _xy_unit(normal_xy)
    if center_pt is None or n is None or link_doc is None:
        return None

    # 1) Prefer adjacent apartment room (does NOT assume From/To vs Facing mapping)
    try:
        apt_room = _pick_apartment_room(door, link_doc)
        if apt_room is not None:
            rc = _room_center_fast(apt_room)
            if rc is not None:
                v_to_room = _xy_unit(DB.XYZ(float(rc.X) - float(center_pt.X), float(rc.Y) - float(center_pt.Y), 0.0))
                if v_to_room is not None:
                    try:
                        dp = float(v_to_room.DotProduct(n))
                    except Exception:
                        dp = 0.0
                    # If room center is clearly in front/back of FacingOrientation, pick that side.
                    if dp > 0.2:
                        return n
                    if dp < -0.2:
                        return DB.XYZ(-n.X, -n.Y, 0.0)
    except Exception:
        pass

    # 2) Probe by sampling points on both sides of door
    ph = _get_last_phase(link_doc)
    th = _try_get_wall_thickness_ft(door)

    base_eps = mm_to_ft(500) or 0.0
    try:
        if th is not None:
            extra = (float(th) * 0.5) + (mm_to_ft(200) or 0.0)
            if extra > base_eps:
                base_eps = extra
    except Exception:
        pass

    try:
        zprobe = float(center_pt.Z) + (mm_to_ft(1000) or 0.0)
        base = DB.XYZ(float(center_pt.X), float(center_pt.Y), zprobe)
        for eps in (base_eps, base_eps * 1.5, base_eps * 2.0):
            if eps <= 1e-9:
                continue
            p_plus = base + (n * float(eps))
            p_minus = base + (n * float(-eps))
            r_plus = _try_get_room_at_point(link_doc, p_plus, phase=ph)
            r_minus = _try_get_room_at_point(link_doc, p_minus, phase=ph)
            sp = _score_room_apartment(r_plus)
            sm = _score_room_apartment(r_minus)
            if sp != sm:
                if sm > sp:
                    return DB.XYZ(-n.X, -n.Y, 0.0)
                return n
    except Exception:
        pass

    return None


def _xy_unit(vec):
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
    v = _xy_unit(v)
    if v is None:
        return None
    try:
        return DB.XYZ(-float(v.Y), float(v.X), 0.0)
    except Exception:
        return None


def _try_get_wall_thickness_ft(door):
    if door is None:
        return None
    try:
        host = getattr(door, 'Host', None)
        if host is None:
            return None
        # Wall.Width exists in many API versions; fall back to WallType.Width
        try:
            w = float(getattr(host, 'Width', None))
            if w > 0:
                return w
        except Exception:
            pass
        try:
            wt = getattr(host, 'WallType', None)
            w = float(getattr(wt, 'Width', None)) if wt is not None else None
            if w and w > 0:
                return w
        except Exception:
            pass
    except Exception:
        return None
    return None


def _try_get_door_facing_xy(door):
    """Return door facing normal as unit XY vector in LINK coords."""
    if door is None:
        return None
    # Prefer door facing
    try:
        fo = getattr(door, 'FacingOrientation', None)
        v = _xy_unit(fo)
        if v is not None:
            return v
    except Exception:
        pass

    # Fallback: host wall orientation
    try:
        host = getattr(door, 'Host', None)
        o = getattr(host, 'Orientation', None) if host is not None else None
        v = _xy_unit(o)
        if v is not None:
            return v
    except Exception:
        pass

    return None


def _calc_panel_point_and_dir_link(door, link_doc, above_offset_ft):
    """Return (point_link, dir_link_xy) where point is on apartment side and above door."""
    c = _door_center_point_link(door)
    if c is None:
        return None, None

    z_head = _door_head_z_link(door)
    if z_head is None:
        z_head = float(c.Z)

    # Start directly above door center
    p = DB.XYZ(float(c.X), float(c.Y), float(z_head) + float(above_offset_ft or 0.0))

    # Decide apartment side direction
    normal = _try_get_door_facing_xy(door)
    inside = _choose_inside_dir_by_rooms_or_probe(door, link_doc, c, normal)
    if inside is not None:
        normal = inside
    else:
        # As a last resort for entrance doors: assume FacingOrientation points outside and flip it.
        if normal is not None:
            try:
                normal = DB.XYZ(-float(normal.X), -float(normal.Y), 0.0)
            except Exception:
                pass

    # Move point to wall face (same plane as door/wall), towards apartment side
    th = _try_get_wall_thickness_ft(door)
    if th is not None and normal is not None:
        try:
            p = p + (normal * (float(th) * 0.5))
        except Exception:
            pass

    return p, normal


def _try_orient_instance_to_dir(doc, inst, origin_pt, desired_dir_xy):
    """Rotate instance around Z so that its facing matches desired_dir_xy (best-effort)."""
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
    """Best-effort: ensure instance faces towards desired_dir_host (XY).

    Fixes common case when wall-mounted devices are created with their front pointing into the wall.
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


def _collect_existing_tagged_points(host_doc, tag):
    """Collect points for already tagged panels using parameter filters (faster than scanning all instances)."""
    pts = []
    t = _norm(tag)
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
    """Collect already tagged panel instances (category Electrical Equipment)."""
    insts = []
    t = _norm(tag)
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
    """Return list of instances within radius from point."""
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


def _instance_has_variant(inst, desired_param_name):
    if inst is None or not desired_param_name:
        return False
    try:
        if _param_checked(inst, desired_param_name):
            return True
    except Exception:
        pass
    try:
        d = getattr(inst, 'Document', None)
        tid = inst.GetTypeId() if hasattr(inst, 'GetTypeId') else None
        sym = d.GetElement(tid) if (d is not None and tid is not None) else None
        if sym is not None and _param_checked(sym, desired_param_name):
            return True
    except Exception:
        pass
    return False


def _get_linked_wall_face_ref_and_point(link_wall, link_inst, point_link, preferred_normal_xy=None):
    """Return (link_face_ref, projected_point_link, face_normal_xy) or (None, None, None).

    If preferred_normal_xy is provided, prefers the wall side face whose normal aligns with it.
    This avoids picking the wrong wall face when point_link is near the wall centerline.
    """
    if link_wall is None or link_inst is None or point_link is None:
        return None, None, None

    prefer = _xy_unit(preferred_normal_xy)

    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Interior))
        except Exception:
            refs += []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Exterior))
        except Exception:
            refs += []

        if not refs:
            return None, None, None

        # Always keep nearest-by-distance fallback
        fb_ref = None
        fb_d = None
        fb_pt = None
        fb_n = None

        # Preferred-by-normal candidate
        best_ref = None
        best_d = None
        best_pt = None
        best_n = None
        best_dot = None

        for r in refs:
            try:
                face = link_wall.GetGeometryObjectFromReference(r)
            except Exception:
                face = None
            if face is None:
                continue

            try:
                ir = face.Project(point_link)
            except Exception:
                ir = None
            if ir is None:
                continue

            try:
                d = float(ir.Distance)
            except Exception:
                d = None
            if d is None:
                continue

            try:
                pt = getattr(ir, 'XYZPoint', None)
                if pt is None:
                    pt = getattr(ir, 'Point', None)
            except Exception:
                pt = None
            if pt is None:
                continue

            nxy = None
            try:
                n = getattr(face, 'FaceNormal', None)
                if n is None:
                    uv = getattr(ir, 'UVPoint', None)
                    if uv is not None and hasattr(face, 'ComputeNormal'):
                        n = face.ComputeNormal(uv)
                nxy = _xy_unit(n)
            except Exception:
                nxy = None

            # Distance fallback
            if fb_d is None or d < fb_d:
                fb_ref, fb_d, fb_pt, fb_n = r, d, pt, nxy

            # Normal preference
            if prefer is not None and nxy is not None:
                try:
                    dot = float(nxy.DotProduct(prefer))
                except Exception:
                    dot = None
                if dot is None:
                    continue
                # Prefer faces that point generally to prefer side
                if dot <= 0.0:
                    continue
                if best_dot is None or dot > best_dot or (abs(dot - best_dot) < 1e-6 and (best_d is None or d < best_d)):
                    best_ref, best_d, best_pt, best_n, best_dot = r, d, pt, nxy, dot

        # Pick by normal when possible, otherwise by distance
        pick_ref = best_ref or fb_ref
        pick_pt = best_pt or fb_pt
        pick_n = best_n or fb_n

        if pick_ref is None or pick_pt is None:
            return None, None, None

        try:
            link_ref = DB.Reference.CreateLinkReference(link_inst, pick_ref)
        except Exception:
            try:
                link_ref = pick_ref.CreateLinkReference(link_inst)
            except Exception:
                link_ref = None

        return link_ref, pick_pt, pick_n
    except Exception:
        return None, None, None


def _try_get_depth_ft(symbol, inst=None):
    """Try to get device depth (corpus) in feet from instance/type parameters."""
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


def _bbox_extents_along_dir(inst, origin_pt, dir_unit):
    """Return (min_rel, max_rel) of instance bbox projected onto dir_unit, relative to origin_pt."""
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
    """Try to adjust a hosted instance offset from its host by delta_ft."""
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


def _apply_half_protrusion(doc_, inst, outward_dir_xy, depth_ft, origin_pt=None, recess_ft=0.0):
    """Best-effort: keep the instance from being placed "inside" the wall.

    Historically this tool tried to set protrusion by half of device depth. In practice, for many
    panel families that results in the panel being sunk into the wall. Instead, we align the
    back-most point of the instance (along outward_dir_xy) to the wall plane point (origin_pt).

    `origin_pt` should be a point on the wall face plane (host coords). If not provided, falls back
    to the current instance location point.
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


def _collect_existing_type_points(host_doc, symbol):
    """Collect points for already placed instances of the target type (fast enough, avoids duplicates across runs)."""
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


def _as_net_id_list(ids):
    """Convert python list[ElementId] to .NET List[ElementId] for Revit API calls."""
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


def _get_or_create_debug_3d_view(doc, name, aliases=None):
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


def _is_near_existing(pt, existing_pts, radius_ft):
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


def _pick_linked_doors(link_inst):
    """Fallback: user picks doors in the selected link."""
    sel = uidoc.Selection

    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class DoorFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return elem and elem.Id == link_inst.Id
            except Exception:
                return False

        def AllowReference(self, reference, position):
            try:
                if reference is None:
                    return False
                if reference.ElementId != link_inst.Id:
                    return False
                if reference.LinkedElementId is None or reference.LinkedElementId == DB.ElementId.InvalidElementId:
                    return False
                ldoc = link_inst.GetLinkDocument()
                if ldoc is None:
                    return False
                le = ldoc.GetElement(reference.LinkedElementId)
                if le is None:
                    return False
                cat = le.Category
                return cat and cat.Id.IntegerValue == int(DB.BuiltInCategory.OST_Doors)
            except Exception:
                return False

    try:
        refs = sel.PickObjects(ObjectType.LinkedElement, DoorFilter(), 'Выберите двери в связанном файле АР')
    except Exception:
        return []

    picked = []
    ldoc = link_inst.GetLinkDocument()
    for r in refs or []:
        try:
            if r.ElementId != link_inst.Id:
                continue
            de = ldoc.GetElement(r.LinkedElementId)
            if de:
                picked.append(de)
        except Exception:
            continue
    return picked


def main():
    output.print_md('# Размещение щитов ШК над входной дверью квартиры')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    link_inst = link_reader.select_link_instance(doc, title='Выберите связь АР')
    if link_inst is None:
        output.print_md('**Отменено.**')
        return
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её в «Управление связями» и повторите.')
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи. Убедитесь, что связь загружена.')
        return

    output.print_md('Выбранная связь: `{0}`'.format(link_inst.Name))
    
    # Pre-check: does the link have rooms?
    try:
        all_rooms = link_reader.get_rooms(link_doc)
        room_count = len(all_rooms)
    except Exception:
        room_count = 0
    
    if room_count == 0:
        alert('В выбранной связи АР не найдено ни одного помещения (Rooms).\n\n'
              'Скрипт использует помещения для определения входных дверей квартир.\n'
              'Убедитесь, что в связи размещены помещения, или выберите другой файл.')
        return
        
    output.print_md('Найдено помещений в связи: **{0}**'.format(room_count))

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    offset_mm = rules.get('panel_above_door_offset_mm', 300)
    recess_mm = rules.get('panel_recess_mm', 40)
    dedupe_mm = rules.get('dedupe_radius_mm', 500)
    batch_size = int(rules.get('batch_size', 25) or 25)
    scan_limit_doors = int(rules.get('scan_limit_doors', 500) or 500)
    max_place = int(rules.get('max_place_count', 200) or 200)
    offset_ft = mm_to_ft(offset_mm) or 0.0
    recess_ft = mm_to_ft(recess_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0

    fam_fullname = (rules.get('family_type_names', {}) or {}).get('panel_shk') or ''
    variant_param_name = (rules.get('panel_shk_variant_param', '') or '').strip()

    cfg = _get_user_config()
    symbol, picked_label, top10 = _pick_panel_symbol(doc, cfg, fam_fullname)
    if symbol is None:
        # Some panel families keep module variants as Yes/No type parameters (not separate types).
        # In that case `fam_fullname` can be a *parameter name* like "...-18 модулей...".
        variant_candidate = variant_param_name or fam_fullname
        if variant_candidate:
            try:
                base_sym = _guess_panel_symbol_for_variant(doc, variant_candidate, candidate_labels=top10)
            except Exception:
                base_sym = None
            if base_sym is not None:
                symbol = _ensure_panel_variant_symbol(doc, base_sym, variant_candidate)
                try:
                    picked_label = placement_engine.format_family_type(symbol)
                except Exception:
                    picked_label = None
                top10 = []

    if symbol is None:
        msg = 'В проекте не найден тип семейства щита из правил:\n\n  {0}\n\n'.format(fam_fullname or '<пусто>')
        if top10:
            msg += 'Похожие варианты (первые 10):\n- ' + '\n- '.join([x for x in top10 if x])
        msg += '\n\nВыбрать тип вручную?' 

        try:
            pick_manual = forms.alert(msg, title='Размещение щитов ШК', warn_icon=True, yes=True, no=True)
        except Exception:
            pick_manual = False

        if not pick_manual:
            return

        symbol = _select_panel_symbol_ui(doc, prefer_fullname=fam_fullname)
        if symbol is None:
            output.print_md('**Отменено.**')
            return
        try:
            picked_label = placement_engine.format_family_type(symbol)
        except Exception:
            picked_label = None
        top10 = []

    # Apply variant selection if configured (or if config string is actually a param name)
    variant_candidate = variant_param_name
    if not variant_candidate:
        try:
            if symbol is not None and fam_fullname and _find_param_by_norm(symbol, fam_fullname) is not None:
                variant_candidate = fam_fullname
        except Exception:
            variant_candidate = ''

    if variant_candidate and symbol is not None:
        try:
            symbol2 = _ensure_panel_variant_symbol(doc, symbol, variant_candidate)
            if symbol2 is not None:
                symbol = symbol2
                try:
                    picked_label = placement_engine.format_family_type(symbol)
                except Exception:
                    picked_label = picked_label
        except Exception:
            pass

    # Finalize selected type state (disable other module options like "-4")
    if variant_candidate and symbol is not None:
        try:
            with tx('ЭОМ: Пост-фикс типа щита ШК (модули)', doc=doc, swallow_warnings=True):
                _post_fix_panel_variant(doc, symbol, variant_candidate)
        except Exception:
            pass
    if top10:
        output.print_md('Лучшие варианты (автовыбор):')
        for x in top10:
            output.print_md('- `{0}`'.format(x))

    # Cache for next run
    try:
        _store_symbol_id(cfg, 'last_panel_shk_symbol_id', symbol)
        _store_symbol_unique_id(cfg, 'last_panel_shk_symbol_uid', symbol)
        _save_user_config()
    except Exception:
        pass

    pt_enum, pt_name = placement_engine.get_symbol_placement_type(symbol)
    is_point = False
    try:
        is_point = bool(placement_engine.is_supported_point_placement(symbol))
    except Exception:
        is_point = False
    if not (is_point or _is_hosted_symbol(symbol)):
        alert('Выбранный тип щита не поддерживается этим инструментом (тип размещения: {0}).'.format(pt_name))
        return

    # Scan ALL doors (avoids user mis-picking a level and missing entrance doors)
    lvl = None
    level_id = None

    # Identify candidate doors (per-door priority)
    # All entrance doors are steel (project convention)
    # PLUS check rooms to ensure it's an apartment entrance
    target_doors = []
    di = 0
    
    # Log rejection reasons for debugging the first few failures
    debug_log = []
    
    pb_max = scan_limit_doors if scan_limit_doors > 0 else 500
    with forms.ProgressBar(title='ЭОМ: Поиск дверей (связь АР)', cancellable=True, step=1) as pbscan:
        pbscan.max_value = pb_max
        for d in link_reader.iter_doors(link_doc, limit=scan_limit_doors, level_id=level_id):
            di += 1
            pbscan.update_progress(min(di, pb_max), pb_max)
            if pbscan.cancelled:
                break

            try:
                tname = _door_family_type_text(d)
                if not _has_any_keyword(tname, STEEL_FAMILY_KEYWORDS):
                    # if len(debug_log) < 10: debug_log.append(u"Skip '{0}': not steel".format(tname))
                    continue
                
                # Strict apartment check
                is_apt = _is_confirmed_apartment_door(d, link_doc)
                if not is_apt:
                    # VERBOSE DIAGNOSTIC FOR FIRST 3 FAILURES
                    if len(debug_log) < 3:
                        output.print_md('---')
                        output.print_md('**DEBUG DIAGNOSTIC for: {0} (Id: {1})**'.format(tname, d.Id))
                        
                        # 1. Phases
                        all_phases = list(link_doc.Phases)
                        output.print_md('Link Phases: ' + ', '.join(['{0} (Id: {1})'.format(p.Name, p.Id) for p in all_phases]))
                        
                        # 2. Geometry
                        try:
                            loc = d.Location
                            if loc and hasattr(loc, 'Point'):
                                pt = loc.Point
                                output.print_md('Door Point: X={0:.2f}, Y={1:.2f}, Z={2:.2f}'.format(pt.X, pt.Y, pt.Z))
                                
                                # Probe points
                                probes = []
                                # Center + 1ft up
                                probes.append(('Center+1ft', DB.XYZ(pt.X, pt.Y, pt.Z + 1.0)))
                                # Offsets
                                if hasattr(d, 'FacingOrientation'):
                                    f = d.FacingOrientation
                                    off = f * 1.3
                                    probes.append(('Front+1ft', DB.XYZ(pt.X + off.X, pt.Y + off.Y, pt.Z + 1.0)))
                                    probes.append(('Back+1ft', DB.XYZ(pt.X - off.X, pt.Y - off.Y, pt.Z + 1.0)))
                                
                                # Check each probe against ALL phases
                                for pname, ppt in probes:
                                    output.print_md('  Probe **{0}** ({1:.2f}, {2:.2f}, {3:.2f}):'.format(pname, ppt.X, ppt.Y, ppt.Z))
                                    found_any = False
                                    for ph in all_phases:
                                        r = link_doc.GetRoomAtPoint(ppt, ph)
                                        if r:
                                            found_any = True
                                            sc = _score_room_apartment(r)
                                            output.print_md('    - Phase "{0}": Room "{1}" (Id: {2}, Score: {3})'.format(ph.Name, r.Name, r.Id, sc))
                                    if not found_any:
                                        output.print_md('    - No rooms found in any phase.')
                            else:
                                output.print_md('Door has no Location Point.')
                        except Exception as ex:
                            output.print_md('Diagnostic Error: {0}'.format(ex))
                        output.print_md('---')

                    if len(debug_log) < 15: 
                        # Get room names for debug
                        try:
                            # Try to reproduce logic from _is_confirmed_apartment_door for logging
                            ph = list(link_doc.Phases)[-1]
                            try:
                                ph_id = getattr(d, 'CreatedPhaseId', DB.ElementId.InvalidElementId)
                                if ph_id != DB.ElementId.InvalidElementId:
                                    p_obj = link_doc.GetElement(ph_id)
                                    if p_obj: ph = p_obj
                            except: pass
                            
                            r1 = d.get_FromRoom(ph)
                            r2 = d.get_ToRoom(ph)
                            
                            # Fallback if get_FromRoom(ph) fails
                            if not r1 and not r2:
                                r1 = getattr(d, 'FromRoom', None)
                                if r1 and hasattr(r1, 'getitem'): r1 = r1[ph]
                                r2 = getattr(d, 'ToRoom', None)
                                if r2 and hasattr(r2, 'getitem'): r2 = r2[ph]
                                
                            n1 = getattr(r1, 'Name', 'None')
                            n2 = getattr(r2, 'Name', 'None')
                            debug_log.append(u"Warn '{0}': rooms {1}/{2} not Apt+Out (Phase: {3}) -> ACCEPTING by name property".format(tname, n1, n2, ph.Name if ph else '?'))
                        except:
                            debug_log.append(u"Warn '{0}': rooms check failed -> ACCEPTING by name property".format(tname))
                    # Fallback: Accept valid steel doors even if room topology is unclear (User request)
                    pass
                
                target_doors.append(d)
            except Exception:
                continue

    reason = 'Авто: только стальные двери (в названии семейства/типа есть "сталь"/"стал"/"steel")'

    if not target_doors:
        # Help user understand why detection failed
        sample = []
        try:
            i = 0
            for d in link_reader.iter_doors(link_doc, limit=min(scan_limit_doors, 30) if scan_limit_doors else 30, level_id=None):
                i += 1
                try:
                    sample.append(_door_family_type_text(d))
                except Exception:
                    sample.append('')
                if i >= 10:
                    break
        except Exception:
            sample = []

        msg = 'Автоматически не найдено ни одной стальной двери в выбранной связи АР.\n'
        msg += 'Сканируемая связь: {0}\n\n'.format(link_inst.Name)
        msg += 'Ожидается, что в названии семейства/типа двери есть одно из: {0}\n\n'.format(', '.join([str(x) for x in STEEL_FAMILY_KEYWORDS]))
        
        if debug_log:
            msg += 'Причины пропуска (первые 15):\n' + '\n'.join(debug_log) + '\n\n'
            
        if sample:
            msg += 'Примеры названий семейства/типа дверей (первые 10):\n- ' + '\n- '.join([s for s in sample if s])

        forms.alert(msg, title='Размещение щитов ШК', warn_icon=True)
        return

    output.print_md('Режим выбора дверей: **{0}**'.format(reason))
    try:
        output.print_md('Тип щита (автовыбор): `{0}`'.format(placement_engine.format_family_type(symbol)))
    except Exception:
        pass
    output.print_md('Дверей найдено: **{0}** (просканировано={1})'.format(len(target_doors), di))

    comment_value = '{0}:PANEL_SHK'.format(comment_tag)
    existing_insts = _collect_existing_tagged_instances(doc, comment_value)
    existing_pts = []
    for e in existing_insts or []:
        try:
            loc = getattr(e, 'Location', None)
            p = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            p = None
        if p is not None:
            existing_pts.append(p)

    t = link_reader.get_total_transform(link_inst)

    created = 0
    updated = 0
    retyped = 0
    created_ids = []
    touched_type_ids = set()
    first_created_id = None
    skipped_no_point = 0
    skipped_dedupe = 0

    # Cap placement per run
    if max_place > 0 and len(target_doors) > max_place:
        target_doors = target_doors[:max_place]

    # Batch placement + progress bar
    batch_size = max(batch_size, 1)
    batches = []
    cur = []
    for d in target_doors:
        cur.append(d)
        if len(cur) >= batch_size:
            batches.append(cur)
            cur = []
    if cur:
        batches.append(cur)

    with forms.ProgressBar(title='ЭОМ: Размещение щитов ШК', cancellable=True, step=1) as pb:
        pb.max_value = len(batches)
        bi = 0
        for batch in batches:
            bi += 1
            pb.update_progress(bi, pb.max_value)
            if pb.cancelled:
                break

            with tx('ЭОМ: Разместить щиты ШК над входными дверями', doc=doc, swallow_warnings=True):
                # Ensure TYPE module toggles are applied inside the same transaction as placement.
                # This avoids cases where a separate transaction for type editing fails silently.
                if variant_candidate and symbol is not None:
                    try:
                        _apply_panel_variant_params(symbol, variant_candidate)
                        doc.Regenerate()
                    except Exception:
                        pass

                for d in batch:
                    p_link, dir_link = _calc_panel_point_and_dir_link(d, link_doc, offset_ft)
                    if p_link is None:
                        skipped_no_point += 1
                        continue

                    # Desired facing / outward direction in HOST coords
                    if dir_link is not None:
                        try:
                            dir_host = t.OfVector(dir_link)
                        except Exception:
                            dir_host = None
                    else:
                        dir_host = None

                    # Compute target wall face point (HOST coords) and linked face ref if possible
                    p_host_guess = t.OfPoint(p_link)
                    p_host_target = p_host_guess
                    face_ref = None
                    p_on_face_link = None
                    _face_n = None
                    try:
                        link_wall = getattr(d, 'Host', None)
                    except Exception:
                        link_wall = None
                    if link_wall is not None:
                        try:
                            face_ref, p_on_face_link, _face_n = _get_linked_wall_face_ref_and_point(link_wall, link_inst, p_link, preferred_normal_xy=dir_link)
                        except Exception:
                            face_ref, p_on_face_link, _face_n = None, None, None
                        if p_on_face_link is not None:
                            try:
                                p_host_target = t.OfPoint(p_on_face_link)
                            except Exception:
                                p_host_target = p_host_guess

                    # If we failed to compute dir_host from door facing, fall back to chosen face normal
                    if dir_host is None and _face_n is not None:
                        try:
                            dir_host = _xy_unit(t.OfVector(_face_n))
                        except Exception:
                            dir_host = None

                    # Use selected face normal for wall-offset calculations (recess/protrusion).
                    # This is critical for hosted families where "Offset from Host" follows face normal,
                    # which can be opposite to door facing.
                    offset_dir_host = dir_host
                    if _face_n is not None:
                        try:
                            offset_dir_host = _xy_unit(t.OfVector(_face_n))
                        except Exception:
                            offset_dir_host = dir_host

                    # Cleanup duplicates at the same location (keep the 18-module variant if possible)
                    try:
                        cleanup_ft = float(mm_to_ft(50) or 0.0)
                    except Exception:
                        cleanup_ft = 0.0
                    if cleanup_ft > 1e-9:
                        near_dupes = _find_near_instances(p_host_target, existing_insts, cleanup_ft)
                        if len(near_dupes) > 1:
                            keep = None
                            if variant_candidate:
                                for e in near_dupes:
                                    try:
                                        if _instance_has_variant(e, variant_candidate):
                                            keep = e
                                            break
                                    except Exception:
                                        continue
                            keep = keep or near_dupes[0]

                            try:
                                rr = float(mm_to_ft(10) or 0.0)
                            except Exception:
                                rr = 0.0

                            for e in list(near_dupes):
                                try:
                                    if keep is not None and e.Id == keep.Id:
                                        continue
                                except Exception:
                                    pass

                                try:
                                    loc = getattr(e, 'Location', None)
                                    p_old = loc.Point if loc and hasattr(loc, 'Point') else None
                                except Exception:
                                    p_old = None

                                if p_old is not None and rr > 1e-9:
                                    for i in range(len(existing_pts) - 1, -1, -1):
                                        try:
                                            pp = existing_pts[i]
                                            if pp is not None and float(pp.DistanceTo(p_old)) <= rr:
                                                existing_pts.pop(i)
                                                break
                                        except Exception:
                                            continue

                                try:
                                    doc.Delete(e.Id)
                                except Exception:
                                    pass
                                try:
                                    existing_insts.remove(e)
                                except Exception:
                                    pass

                    # If we already placed a panel at this door on a previous run, update it.
                    existing = _find_near_instance(p_host_target, existing_insts, dedupe_ft) if dedupe_ft > 0 else None
                    if existing is not None:
                        # For hosted families we must recreate to change the hosting face reliably
                        if not is_point:
                            try:
                                pid = existing.Id
                            except Exception:
                                pid = None
                            # remove old point from dedupe list
                            try:
                                loc = getattr(existing, 'Location', None)
                                p_old = loc.Point if loc and hasattr(loc, 'Point') else None
                            except Exception:
                                p_old = None
                            if p_old is not None:
                                try:
                                    rr = float(mm_to_ft(10) or 0.0)
                                    if rr > 1e-9:
                                        for i in range(len(existing_pts) - 1, -1, -1):
                                            try:
                                                pp = existing_pts[i]
                                                if pp is not None and float(pp.DistanceTo(p_old)) <= rr:
                                                    existing_pts.pop(i)
                                                    break
                                            except Exception:
                                                continue
                                except Exception:
                                    pass
                            try:
                                if pid is not None:
                                    doc.Delete(pid)
                            except Exception:
                                pass
                            try:
                                existing_insts.remove(existing)
                            except Exception:
                                pass
                            existing = None

                    if existing is not None:
                        try:
                            if existing.GetTypeId() != symbol.Id:
                                ensure_symbol_active(doc, symbol)
                                existing.ChangeTypeId(symbol.Id)
                                retyped += 1
                        except Exception:
                            pass

                        try:
                            if variant_candidate:
                                touched_type_ids.add(int(existing.GetTypeId().IntegerValue))
                        except Exception:
                            pass

                        # Enforce module variant on instance (some families use instance parameters)
                        if variant_candidate:
                            try:
                                _apply_panel_variant_params(existing, variant_candidate)
                            except Exception:
                                pass

                        # Best-effort facing + protrusion fix
                        final_dir = dir_host
                        try:
                            if dir_host is not None:
                                if is_point:
                                    try:
                                        _try_orient_instance_to_dir(doc, existing, p_host_target, dir_host)
                                    except Exception:
                                        pass
                                # Invert dir_host so panel faces INTO apartment (outward from wall)
                                flip_dir = DB.XYZ(-dir_host.X, -dir_host.Y, 0.0) if dir_host is not None else None
                                _try_flip_facing_to_dir(existing, flip_dir, origin_pt=p_host_target)
                                try:
                                    fo = getattr(existing, 'FacingOrientation', None)
                                    final_dir = _xy_unit(fo) or dir_host
                                except Exception:
                                    final_dir = dir_host
                        except Exception:
                            final_dir = dir_host

                        try:
                            depth_ft = _try_get_depth_ft(symbol, existing)
                            use_dir = offset_dir_host or dir_host or final_dir
                            if use_dir is not None:
                                _apply_half_protrusion(doc, existing, use_dir, depth_ft, origin_pt=p_host_target, recess_ft=recess_ft)
                        except Exception:
                            pass

                        set_comments(existing, comment_value)
                        aptnum = _try_get_apartment_number(d, link_doc)
                        if aptnum:
                            set_mark(existing, 'APT-{0}-SHK'.format(aptnum))

                        updated += 1
                        continue

                    if dedupe_ft > 0 and _is_near_existing(p_host_target, existing_pts, dedupe_ft):
                        skipped_dedupe += 1
                        continue

                    inst = None
                    p_host = None
                    ensure_symbol_active(doc, symbol)
                    if is_point:
                        p_host = p_host_target
                        inst = placement_engine.place_point_family_instance(doc, symbol, p_host, view=doc.ActiveView)
                    else:
                        # Face-hosted placement on linked wall face
                        if face_ref is not None and p_host_target is not None:
                            p_host = p_host_target
                            try:
                                ref_dir = _xy_perp(dir_host) if dir_host is not None else None
                                if ref_dir is None:
                                    ref_dir = DB.XYZ.BasisX
                                inst = doc.Create.NewFamilyInstance(face_ref, p_host, ref_dir, symbol)
                            except Exception:
                                inst = None

                    if inst is None:
                        continue

                    try:
                        if variant_candidate:
                            touched_type_ids.add(int(inst.GetTypeId().IntegerValue))
                    except Exception:
                        pass

                    # Enforce module variant on instance (some families use instance parameters)
                    if variant_candidate:
                        try:
                            _apply_panel_variant_params(inst, variant_candidate)
                        except Exception:
                            pass

                    # Align + facing (point-based rotation + hosted FlipFacing)
                    final_dir = dir_host
                    if dir_host is not None and p_host is not None:
                        try:
                            if is_point:
                                _try_orient_instance_to_dir(doc, inst, p_host, dir_host)
                        except Exception:
                            pass
                        try:
                            # Invert dir_host so panel faces INTO apartment (outward from wall)
                            flip_dir = DB.XYZ(-dir_host.X, -dir_host.Y, 0.0) if dir_host is not None else None
                            _try_flip_facing_to_dir(inst, flip_dir, origin_pt=p_host)
                        except Exception:
                            pass
                        try:
                            fo = getattr(inst, 'FacingOrientation', None)
                            final_dir = _xy_unit(fo) or dir_host
                        except Exception:
                            final_dir = dir_host

                    # Protrusion fix: keep panel from ending up inside the wall
                    try:
                        depth_ft = _try_get_depth_ft(symbol, inst)
                        use_dir = offset_dir_host or dir_host or final_dir
                        if use_dir is not None and p_host is not None:
                            _apply_half_protrusion(doc, inst, use_dir, depth_ft, origin_pt=p_host, recess_ft=recess_ft)
                    except Exception:
                        pass

                    try:
                        if first_created_id is None:
                            first_created_id = inst.Id
                    except Exception:
                        pass
                    try:
                        if len(created_ids) < 500:
                            created_ids.append(inst.Id)
                    except Exception:
                        pass

                    set_comments(inst, comment_value)

                    aptnum = _try_get_apartment_number(d, link_doc)
                    if aptnum:
                        set_mark(inst, 'APT-{0}-SHK'.format(aptnum))

                    if p_host is not None:
                        existing_pts.append(p_host)
                    try:
                        existing_insts.append(inst)
                    except Exception:
                        pass
                    created += 1

    output.print_md('---')
    output.print_md('Создано щитов: **{0}**'.format(created))
    if updated:
        output.print_md('Обновлено существующих щитов (повторный запуск): **{0}**'.format(updated))
    if retyped:
        output.print_md('Переназначено типов: **{0}**'.format(retyped))
    if skipped_dedupe:
        output.print_md('Пропущено (радиус дублирования {0}мм): **{1}**'.format(dedupe_mm, skipped_dedupe))
    if skipped_no_point:
        output.print_md('Пропущено (не удалось получить точку двери): **{0}**'.format(skipped_no_point))
    output.print_md('Комментарий установлен: `{0}`'.format(comment_value))

    report_time_saved(output, 'panels_shk_apartment')

    # Debug: open a 3D view zoomed to placed panels
    if created_ids:
        try:
            go3d = forms.alert(
                'Открыть отладочный 3D-вид и приблизить к размещённым щитам ШК?',
                title='ЭОМ: Показать размещённые щиты',
                warn_icon=False,
                yes=True,
                no=True
            )
        except Exception:
            go3d = True

        if go3d:
            v3d = None
            try:
                bb = _bbox_from_element_ids(doc, created_ids, pad_ft=60.0, limit=500)
                with tx('ЭОМ: Создать/открыть 3D-вид (ШК)', doc=doc, swallow_warnings=True):
                    v3d = _get_or_create_debug_3d_view(doc, 'ЭОМ_ОТЛАДКА_Размещенные_ШК', aliases=['EOM_DEBUG_Placed_ShK'])
                    if v3d and bb:
                        try:
                            v3d.ViewTemplateId = DB.ElementId.InvalidElementId
                        except Exception:
                            pass
                        try:
                            v3d.DetailLevel = DB.ViewDetailLevel.Fine
                        except Exception:
                            pass
                        try:
                            v3d.DisplayStyle = DB.DisplayStyle.Shading
                        except Exception:
                            pass

                        # Show links and electrical equipment
                        try:
                            cat_links = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_RvtLinks)
                            if cat_links:
                                v3d.SetCategoryHidden(cat_links.Id, False)
                        except Exception:
                            pass
                        try:
                            cat_eq = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_ElectricalEquipment)
                            if cat_eq:
                                v3d.SetCategoryHidden(cat_eq.Id, False)
                        except Exception:
                            pass

                        try:
                            v3d.IsSectionBoxActive = True
                        except Exception:
                            pass
                        try:
                            v3d.SetSectionBox(bb)
                        except Exception:
                            pass

                if v3d:
                    try:
                        uidoc.RequestViewChange(v3d)
                    except Exception:
                        pass

                    # Select + zoom to first placed element
                    try:
                        av = uidoc.ActiveView
                        if av:
                            try:
                                if av.IsTemporaryHideIsolateActive():
                                    av.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
                            except Exception:
                                pass

                        try:
                            sel_ids = _as_net_id_list(created_ids[:50])
                            if sel_ids is not None:
                                uidoc.Selection.SetElementIds(sel_ids)
                        except Exception:
                            pass
                        try:
                            if first_created_id is not None:
                                uidoc.ShowElements(first_created_id)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass

    logger.info('ШК создано=%s пропущено_дубли=%s пропущено_без_точки=%s', created, skipped_dedupe, skipped_no_point)
    report_time_saved(output, 'panel_door', created)
    try:
        from time_savings import calculate_time_saved, calculate_time_saved_range
        minutes = calculate_time_saved('panel_door', created)
        minutes_min, minutes_max = calculate_time_saved_range('panel_door', created)
        global EOM_HUB_RESULT
        cnt_skip = (skipped_dedupe or 0) + (skipped_no_point or 0)
        stats = {'total': created, 'processed': created, 'skipped': cnt_skip, 'errors': 0}
        EOM_HUB_RESULT = {
            'stats': stats,
            'time_saved_minutes': minutes,
            'time_saved_minutes_min': minutes_min,
            'time_saved_minutes_max': minutes_max,
            'placed': created,
        }
    except: pass

    # Post-fix again after placement batches (some families re-evaluate visibility during placement)
    if variant_candidate:
        try:
            type_ids = set(touched_type_ids or [])
        except Exception:
            type_ids = set()
        try:
            if symbol is not None:
                type_ids.add(int(symbol.Id.IntegerValue))
        except Exception:
            pass

        if type_ids:
            try:
                with tx('ЭОМ: Пост-фикс типа щита ШК (после размещения)', doc=doc, swallow_warnings=True):
                    for tid in sorted(list(type_ids)):
                        try:
                            sym = doc.GetElement(DB.ElementId(int(tid)))
                        except Exception:
                            sym = None
                        if sym is None:
                            continue
                        try:
                            _post_fix_panel_variant(doc, sym, variant_candidate)
                        except Exception:
                            continue
                        try:
                            _log_shk_variant_state('post-fix verify', sym, variant_candidate)
                        except Exception:
                            pass
            except Exception:
                pass


try:
    main()
except Exception:
    log_exception('Ошибка инструмента размещения щитов ШК')
    alert('Ошибка. Подробности смотрите в выводе pyRevit.')
