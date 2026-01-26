# -*- coding: utf-8 -*-

import config_loader
from pyrevit import DB, forms, revit
from utils_revit import alert, log_exception
import link_reader
import placement_engine
import socket_utils
import pk_indicator_rules
from constants import DEFAULT_PK_KEYS, DEFAULT_PK_EXCLUDE
from domain import (
    get_safe_bic,
    as_list,
    is_view_based,
    is_point_based,
    points_near_xy
)


def get_rules():
    try:
        return config_loader.load_rules()
    except Exception:
        log_exception('Failed to load rules')
        return {}


def get_keywords(rules):
    include = as_list((rules or {}).get('pk_hydrant_keywords')) or list(DEFAULT_PK_KEYS)
    exclude = as_list((rules or {}).get('pk_hydrant_exclude_keywords')) or list(DEFAULT_PK_EXCLUDE)
    return include, exclude


def get_number(rules, key, default):
    try:
        v = (rules or {}).get(key, default)
        return float(v)
    except Exception:
        return float(default)


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


def select_family_symbol_any(doc, title, categories, search_text=None, limit=200, scan_cap=5000):
    items = []
    scanned = 0
    for bic in categories or []:
        if bic is None:
            continue
        for s in placement_engine.iter_family_symbols(doc, category_bic=bic, limit=None):
            scanned += 1
            if scanned > scan_cap:
                break
            try:
                label = placement_engine.format_family_type(s)
            except Exception:
                label = ''
            if not label:
                continue
            if search_text:
                try:
                    if search_text.lower() not in label.lower():
                        continue
                except Exception:
                    pass
            _, pt_name = placement_engine.get_symbol_placement_type(s)
            # Accept view-based or point-based types only
            if (not is_view_based(s)) and (not is_point_based(s)):
                continue
            items.append((u'{0}   [{1}]'.format(label, pt_name), s))
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break

    if not items:
        return None

    items = sorted(items, key=lambda x: x[0].lower())
    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
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


def pick_pk_symbol(doc, cfg, rules):
    sym = load_symbol_from_saved_id(doc, cfg, 'last_pk_symbol_id')
    if sym is None:
        sym = load_symbol_from_saved_unique_id(doc, cfg, 'last_pk_symbol_uid')
    if sym is not None:
        return sym

    type_names = None
    try:
        type_names = (rules or {}).get('family_type_names', {}).get('pk_indicator', None)
    except Exception:
        type_names = None
    for name in as_list(type_names):
        # Try annotation category first
        for bic in (
            get_safe_bic('OST_GenericAnnotation'),
            get_safe_bic('OST_DetailComponents'),
            get_safe_bic('OST_LightingFixtures'),
            get_safe_bic('OST_SpecialityEquipment'),
            get_safe_bic('OST_GenericModel'),
        ):
            if bic is None:
                continue
            try:
                found = placement_engine.find_family_symbol(doc, name, category_bic=bic)
            except Exception:
                found = None
            if found:
                return found

    cats = [
        get_safe_bic('OST_GenericAnnotation'),
        get_safe_bic('OST_DetailComponents'),
        get_safe_bic('OST_LightingFixtures'),
        get_safe_bic('OST_SpecialityEquipment'),
        get_safe_bic('OST_GenericModel'),
    ]
    return select_family_symbol_any(
        doc,
        title='Выберите тип указателя ПК',
        categories=cats,
        search_text=None,
        limit=200,
        scan_cap=5000
    )


def elem_text(e):
    try:
        return socket_utils._elem_text(e)
    except Exception:
        return u''


def inst_center_point(inst):
    try:
        return socket_utils._inst_center_point(inst)
    except Exception:
        return None


def collect_textnote_points(doc, include_keys, exclude_keys):
    pts = []
    if doc is None:
        return pts
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.TextNote)
        for tn in col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not pk_indicator_rules.is_hydrant_candidate(txt, include_keys, exclude_keys):
                continue
            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass
    return pts


def collect_tag_points(doc, include_keys, exclude_keys):
    pts = []
    if doc is None:
        return pts
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.IndependentTag)
        for tag in col:
            try:
                txt = tag.TagText
            except Exception:
                txt = u''
            if not pk_indicator_rules.is_hydrant_candidate(txt, include_keys, exclude_keys):
                continue
            try:
                pt = tag.TagHeadPosition
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass
    return pts


def collect_hydrant_points(doc, include_keys, exclude_keys, scan_limit=None):
    pts = []
    if doc is None:
        return pts

    bics_model = [
        get_safe_bic('OST_PlumbingFixtures'),
        get_safe_bic('OST_SpecialityEquipment'),
        get_safe_bic('OST_MechanicalEquipment'),
        get_safe_bic('OST_PipeAccessory'),
        get_safe_bic('OST_GenericModel'),
        get_safe_bic('OST_Furniture'),
        get_safe_bic('OST_FireProtection'),
    ]
    bics_annot = [
        get_safe_bic('OST_GenericAnnotation'),
        get_safe_bic('OST_DetailComponents'),
    ]

    for bic in bics_model + bics_annot:
        if bic is None:
            continue
        for e in link_reader.iter_elements_by_category(doc, bic, limit=scan_limit, level_id=None):
            t = elem_text(e)
            if not pk_indicator_rules.is_hydrant_candidate(t, include_keys, exclude_keys):
                continue
            pt = inst_center_point(e)
            if pt:
                pts.append(pt)

    pts.extend(collect_textnote_points(doc, include_keys, exclude_keys))
    pts.extend(collect_tag_points(doc, include_keys, exclude_keys))

    return pts


def collect_existing_points(doc, tag, view_based=False):
    pts = []
    if doc is None or not tag:
        return pts
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag)
        pfilter = DB.ElementParameterFilter(rule)
    except Exception:
        return pts

    bics = [
        get_safe_bic('OST_LightingFixtures'),
        get_safe_bic('OST_LightingDevices'),
        get_safe_bic('OST_ElectricalFixtures'),
        get_safe_bic('OST_SpecialityEquipment'),
        get_safe_bic('OST_GenericModel'),
    ]
    if view_based:
        bics.extend([get_safe_bic('OST_GenericAnnotation'), get_safe_bic('OST_DetailComponents')])

    for bic in bics:
        if bic is None:
            continue
        try:
            col = (DB.FilteredElementCollector(doc)
                   .WhereElementIsNotElementType()
                   .OfCategory(bic)
                   .WherePasses(pfilter))
            for e in col:
                try:
                    loc = getattr(e, 'Location', None)
                    p = loc.Point if loc and hasattr(loc, 'Point') else None
                except Exception:
                    p = None
                if p:
                    pts.append(p)
        except Exception:
            continue
    return pts


def pick_link_doc(host_doc, include_keys, exclude_keys, scan_limit):
    # Prefer a loaded link that already contains hydrant candidates
    try:
        links = link_reader.list_link_instances(host_doc)
    except Exception:
        links = []
    for ln in links:
        if not link_reader.is_link_loaded(ln):
            continue
        ld = link_reader.get_link_doc(ln)
        if ld is None:
            continue
        if collect_hydrant_points(ld, include_keys, exclude_keys, scan_limit):
            return ln, ld

    # Fallback: host model
    if collect_hydrant_points(host_doc, include_keys, exclude_keys, scan_limit):
        return None, host_doc

    # Manual pick
    ln = socket_utils._select_link_instance_ru(host_doc, 'Выберите связь АР (пожарные краны)')
    if ln is None:
        return None, None
    if not link_reader.is_link_loaded(ln):
        alert('Связь не загружена. Загрузите её в Manage Links и повторите.')
        return None, None
    return ln, link_reader.get_link_doc(ln)
