# -*- coding: utf-8 -*-

# Импорт domain-логики (чистая бизнес-логика)
from domain import (
    norm,                                    # было: norm()
    norm_type_key,                          # было: norm_type_key()
    clean_apt_number,                       # было: clean_apt_number()
    is_valid_apt_value,                     # было: is_valid_apt_value()
    has_any_keyword,                        # было: has_any_keyword()
    score_text,                             # было: score_text()
    score_panel_symbol_label,               # было: score_panel_symbol_label()
    variant_prefix_key,                     # было: variant_prefix_key()
    is_panel_module_variant_param_name,     # было: is_panel_module_variant_param_name()
)

# Импорт adapters (Revit API слой)
from adapters import (
    _get_user_config,
    _save_user_config,
    _load_symbol_from_saved_id,
    _load_symbol_from_saved_unique_id,
    _store_symbol_id,
    _store_symbol_unique_id,
    _get_param_as_double,
    _get_param_as_string,
    _param_to_string,
    _find_param_by_norm,
    _param_checked,
    _iter_panel_symbols,
    _iter_panel_symbols_any,
    _iter_family_symbols,
    _find_panel_symbol_by_label,
    _symbol_matches_label,
    _make_unique_type_name,
    _ensure_panel_variant_symbol,
    _apply_panel_variant_params,
    _post_fix_panel_variant,
    _try_get_depth_ft,
    _try_orient_instance_to_dir,
    _try_flip_facing_to_dir,
    _apply_half_protrusion,
    _bbox_extents_along_dir,
    _try_adjust_host_offset,
    _collect_existing_tagged_points,
    _collect_existing_tagged_instances,
    _find_near_instance,
    _find_near_instances,
    _is_near_existing,
    _collect_existing_type_points,
    _get_or_create_debug_3d_view,
    _bbox_from_element_ids,
    _as_net_id_list,
    _iter_from_to_rooms,
    _door_head_point_link,
    _door_center_point_link,
    _door_head_z_link,
    _room_center_fast,
    _xy_unit,
    _xy_perp,
)

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
    import input_utils as iu
    import room_name_utils as rnu
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su
    import input_utils as iu
    import room_name_utils as rnu


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


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

# Apartment parameter detection (strict by default)
APT_PARAM_NAMES_DEFAULT = [u'Квартира', u'Номер квартиры', u'ADSK_Номер квартиры', u'ADSK_Номер_квартиры', u'Apartment', u'Flat']
APT_PARAM_NAMES = []
APT_REQUIRE_PARAM = True
APT_ALLOW_DEPARTMENT = False
APT_ALLOW_NUMBER = False


def _get_room_apartment_number_strict(room):
    if room is None:
        return None

    # 1) Explicit apartment params
    for pname in (APT_PARAM_NAMES or []):
        try:
            p = _find_param_bynorm(room, pname)
        except Exception:
            p = None
        if p is None:
            continue
        val = _param_to_string(p)
        clean_val = clean_apt_number(val)
        if is_valid_apt_value(clean_val):
            return clean_val

    # 2) Optional fallbacks (off by default)
    if APT_ALLOW_DEPARTMENT:
        try:
            dept = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT, name='Department')
            clean_dept = clean_apt_number(dept)
            if is_valid_apt_value(clean_dept):
                return clean_dept
        except Exception:
            pass

    if APT_ALLOW_NUMBER:
        try:
            num = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER, name='Number')
            if num:
                parts = num.split('.')
                if len(parts) > 1 and parts[0].isdigit():
                    return parts[0]
        except Exception:
            pass

    return None


def _door_text(door):
    # Combine Mark + Comments
    mark = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name='Mark')
    comm = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name='Comments')
    return norm(u'{0} {1}'.format(mark, comm))


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
                    return norm(u'{0} {1}'.format(fam_name, typ_name))
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
                    return norm(u'{0} {1}'.format(fam_name, typ_name))
            except Exception:
                pass

        return u''
    except Exception:
        return u''


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
        if not is_panel_module_variant_param_name(pname):
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
        desired_key = norm_type_key(desired_param_name) if desired_param_name else ''
        ok = False
        if desired_key and len(enabled) == 1 and norm_type_key(enabled[0]) == desired_key:
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
        if _find_param_bynorm(sym, desired_param_name) is not None:
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
        bkey = norm_type_key(base_guess)
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

                    if (bkey == norm_type_key(getattr(sym, 'Name', u''))) or (bkey == norm_type_key(fam_name)):
                        if _find_param_bynorm(sym, desired_param_name) is not None:
                            return sym
                except Exception:
                    continue

    # 3) Last resort: any electrical equipment symbol that has this parameter
    for sym in _iter_panel_symbols(doc_, limit=20000):
        try:
            if _find_param_bynorm(sym, desired_param_name) is not None:
                return sym
        except Exception:
            continue

    return None


def _is_hosted_symbol(symbol):
    if symbol is None:
        return False
    try:
        _, pt_name = placement_engine.get_symbol_placement_type(symbol)
        n = norm(str(pt_name))
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
    prefer = norm(prefer_fullname)

    ranked = []
    for s in _iter_panel_symbols(doc, limit=5000):
        try:
            if not _is_supported_panel_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue

            sc = score_panel_symbol_label(s)
            if prefer and norm(lbl) == prefer:
                # Config match wins if present
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None, None, []

    ranked.sort(key=lambda x: (x[0], norm(x[1])), reverse=True)
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

    prefer_key = norm_type_key(prefer_fullname) if prefer_fullname else u''
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
            sc = score_panel_symbol_label(s)
            if prefer_key and norm_type_key(lbl) == prefer_key:
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None

    ranked.sort(key=lambda x: (x[0], norm(x[1])), reverse=True)

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


def _is_apartment_entrance_by_rooms(door, link_doc):
    # Using all phases can be very slow. Prefer last phase.
    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []

    for r in _iter_from_to_rooms(door, phases):
        try:
            name = norm(getattr(r, 'Name', u''))
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

    # 1) Prefer explicit apartment number from room parameters (strict)
    for r in _iter_from_to_rooms(door, phases):
        try:
            apt = _get_room_apartment_number_strict(r)
            if apt:
                return str(apt)
        except Exception:
            continue

    # 2) Optional: non-strict fallback
    if not APT_REQUIRE_PARAM:
        for r in _iter_from_to_rooms(door, phases):
            try:
                apt = su.get_room_apartment_number(r)
                if apt:
                    return str(apt)
            except Exception:
                continue

    # 3) Fallback: hallway room number
    for r in _iter_from_to_rooms(door, phases):
        try:
            name = norm(getattr(r, 'Name', u''))
            if HALL_KEYWORD in name:
                num = getattr(r, 'Number', None)
                if num:
                    return str(num)
        except Exception:
            continue
    return None


def _pick_apartment_room(door, link_doc):
    """Pick adjacent room that represents apartment interior (prefer "прихож")."""
    if door is None or link_doc is None:
        return None

    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []

    best_apt = None
    best_kw = None
    for r in _iter_from_to_rooms(door, phases):
        try:
            name = norm(getattr(r, 'Name', u''))
        except Exception:
            name = u''

        # Prefer explicit apartment rooms (parameter-based)
        try:
            if _room_has_apartment(r):
                if name and HALL_KEYWORD in name:
                    return r
                best_apt = best_apt or r
        except Exception:
            pass

        if not name:
            continue

        # strong match (name-based fallback)
        if HALL_KEYWORD in name:
            return r

        # weaker apartment hints (name-based fallback)
        for kw in APARTMENT_ROOM_KEYWORDS:
            if norm(kw) and norm(kw) in name:
                best_kw = best_kw or r
                break

    return best_apt or best_kw


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


def _room_has_apartment(room):
    if room is None:
        return False
    try:
        if _get_room_apartment_number_strict(room):
            return True
        if APT_REQUIRE_PARAM:
            return False
        return bool(su.get_room_apartment_number(room))
    except Exception:
        return False


def _score_room_apartment(room):
    if room is None:
        return 0
    try:
        name = norm(getattr(room, 'Name', u''))
    except Exception:
        name = u''

    if not name:
        name = u''

    score = 0
    # Strong positive signal when room has explicit apartment number
    try:
        if _room_has_apartment(room):
            score += 120
    except Exception:
        pass
    # Strong preference for Hallway inside apartment
    if HALL_KEYWORD in name:
        score += 100
    for kw in APARTMENT_ROOM_KEYWORDS:
        nkw = norm(kw)
        if nkw and (nkw in name):
            score += 30
    for kw in OUTSIDE_ROOM_KEYWORDS:
        nkw = norm(kw)
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
    has_apt_param = False

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
            try:
                if _room_has_apartment(r):
                    has_apt_param = True
            except Exception:
                pass
            sc = _score_room_apartment(r)
            if sc > 0: this_phase_apt = True
            if sc < -50: this_phase_out = True
        
        # Accumulate global flags (if it's an apartment door in ANY valid phase, count it)
        if this_phase_apt: has_apt = True
        if this_phase_out: has_outside = True
        
        # Optimization: if we found both, we are sure.
        if has_apt and has_outside:
             return True

    # Require explicit apartment room assignment
    if not has_apt_param:
        return False

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


def _room_is_tbo(room):
    if room is None:
        return False
    try:
        name = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME, name='Name')
    except Exception:
        name = u''
    if not name:
        try:
            name = getattr(room, 'Name', u'') or u''
        except Exception:
            name = u''
    return bool(rnu.is_tbo_room_name(name))


def _door_has_tbo_room(door, link_doc):
    if door is None or link_doc is None:
        return False
    try:
        phases = [list(link_doc.Phases)[-1]]
    except Exception:
        phases = []
    try:
        for r in _iter_from_to_rooms(door, phases):
            if _room_is_tbo(r):
                return True
    except Exception:
        return False
    return False


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
    # Apartment param rules (strict by default)
    global APT_PARAM_NAMES, APT_REQUIRE_PARAM, APT_ALLOW_DEPARTMENT, APT_ALLOW_NUMBER
    try:
        APT_PARAM_NAMES = list((rules.get('apartment_param_names', []) or []))
    except Exception:
        APT_PARAM_NAMES = []
    if not APT_PARAM_NAMES:
        APT_PARAM_NAMES = list(APT_PARAM_NAMES_DEFAULT)
    try:
        APT_REQUIRE_PARAM = bool(rules.get('apartment_require_param', True))
    except Exception:
        APT_REQUIRE_PARAM = True
    try:
        APT_ALLOW_DEPARTMENT = bool(rules.get('apartment_allow_department_fallback', False))
    except Exception:
        APT_ALLOW_DEPARTMENT = False
    try:
        APT_ALLOW_NUMBER = bool(rules.get('apartment_allow_room_number_fallback', False))
    except Exception:
        APT_ALLOW_NUMBER = False
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    offset_mm = rules.get('panel_above_door_offset_mm', 300)
    user_offset_mm = iu.ask_for_mm_value(
        prompt=u'Высота размещения над дверью (мм)',
        title=u'Щит над дверью',
        default_mm=offset_mm,
    )
    if user_offset_mm is None:
        return
    offset_mm = user_offset_mm
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
            if symbol is not None and fam_fullname and _find_param_bynorm(symbol, fam_fullname) is not None:
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
                if not has_any_keyword(tname, STEEL_FAMILY_KEYWORDS):
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
                            debug_log.append(u"Skip '{0}': rooms {1}/{2} not Apt+Out (Phase: {3}) -> REJECTED (no apartment)".format(tname, n1, n2, ph.Name if ph else '?'))
                        except:
                            debug_log.append(u"Skip '{0}': rooms check failed -> REJECTED (no apartment)".format(tname))
                    # Skip doors without confirmed apartment rooms
                    continue
                if _door_has_tbo_room(d, link_doc):
                    # Skip doors adjacent to TBO rooms
                    continue
                
                target_doors.append(d)
            except Exception:
                continue

    reason = 'Авто: только стальные двери и только при наличии квартиры у помещения (параметр/номер квартиры)'

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
