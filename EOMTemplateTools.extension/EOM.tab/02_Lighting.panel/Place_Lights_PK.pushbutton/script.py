# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
import link_reader
import placement_engine
import socket_utils
import pk_indicator_rules
from utils_revit import alert, log_exception, set_comments, tx
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


DEFAULT_PK_KEYS = [
    u'пожарный кран', u'пож. кран', u'пожарн кран', u'пожарный шкаф', u'кран пожарный',
    u'пк', u'п/к',
    u'fire hose', u'fire hydrant', u'hydrant', u'hose reel', u'fire hose cabinet',
]

DEFAULT_PK_EXCLUDE = [
    u'пкс', u'перекрест', u'перекл', u'переключатель',
]


def _as_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [v for v in val if v]
    return [val]


def _get_rules():
    try:
        return config_loader.load_rules()
    except Exception:
        log_exception('Failed to load rules')
        return {}


def _get_keywords(rules):
    include = _as_list((rules or {}).get('pk_hydrant_keywords')) or list(DEFAULT_PK_KEYS)
    exclude = _as_list((rules or {}).get('pk_hydrant_exclude_keywords')) or list(DEFAULT_PK_EXCLUDE)
    return include, exclude


def _get_number(rules, key, default):
    try:
        v = (rules or {}).get(key, default)
        return float(v)
    except Exception:
        return float(default)


def _load_symbol_from_saved_id(doc_, cfg, key):
    if doc_ is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        eid = DB.ElementId(int(val))
        e = doc_.GetElement(eid)
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def _load_symbol_from_saved_unique_id(doc_, cfg, key):
    if doc_ is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc_.GetElement(str(uid))
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


def _safe_bic(name):
    try:
        return getattr(DB.BuiltInCategory, name)
    except Exception:
        return None


def _is_view_based(symbol):
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.ViewBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and 'viewbased' in pt_name.lower():
            return True
    except Exception:
        pass
    return False


def _is_point_based(symbol):
    return placement_engine.is_supported_point_placement(symbol)


def _select_family_symbol_any(doc_, title, categories, search_text=None, limit=200, scan_cap=5000):
    items = []
    scanned = 0
    for bic in categories or []:
        if bic is None:
            continue
        for s in placement_engine.iter_family_symbols(doc_, category_bic=bic, limit=None):
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
            pt, pt_name = placement_engine.get_symbol_placement_type(s)
            # Accept view-based or point-based types only
            if (not _is_view_based(s)) and (not _is_point_based(s)):
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


def _pick_pk_symbol(doc_, cfg, rules):
    sym = _load_symbol_from_saved_id(doc_, cfg, 'last_pk_symbol_id')
    if sym is None:
        sym = _load_symbol_from_saved_unique_id(doc_, cfg, 'last_pk_symbol_uid')
    if sym is not None:
        return sym

    type_names = None
    try:
        type_names = (rules or {}).get('family_type_names', {}).get('pk_indicator', None)
    except Exception:
        type_names = None
    for name in _as_list(type_names):
        # Try annotation category first
        for bic in (
            _safe_bic('OST_GenericAnnotation'),
            _safe_bic('OST_DetailComponents'),
            _safe_bic('OST_LightingFixtures'),
            _safe_bic('OST_SpecialityEquipment'),
            _safe_bic('OST_GenericModel'),
        ):
            if bic is None:
                continue
            try:
                found = placement_engine.find_family_symbol(doc_, name, category_bic=bic)
            except Exception:
                found = None
            if found:
                return found

    cats = [
        _safe_bic('OST_GenericAnnotation'),
        _safe_bic('OST_DetailComponents'),
        _safe_bic('OST_LightingFixtures'),
        _safe_bic('OST_SpecialityEquipment'),
        _safe_bic('OST_GenericModel'),
    ]
    return _select_family_symbol_any(
        doc_,
        title='Выберите тип указателя ПК',
        categories=cats,
        search_text=None,
        limit=200,
        scan_cap=5000
    )


def _elem_text(e):
    try:
        return socket_utils._elem_text(e)
    except Exception:
        return u''


def _inst_center_point(inst):
    try:
        return socket_utils._inst_center_point(inst)
    except Exception:
        return None


def _collect_textnote_points(doc_, include_keys, exclude_keys):
    pts = []
    if doc_ is None:
        return pts
    try:
        col = DB.FilteredElementCollector(doc_).OfClass(DB.TextNote)
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


def _collect_tag_points(doc_, include_keys, exclude_keys):
    pts = []
    if doc_ is None:
        return pts
    try:
        col = DB.FilteredElementCollector(doc_).OfClass(DB.IndependentTag)
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


def _collect_hydrant_points(doc_, include_keys, exclude_keys, scan_limit=None):
    pts = []
    if doc_ is None:
        return pts

    bics_model = [
        _safe_bic('OST_PlumbingFixtures'),
        _safe_bic('OST_SpecialityEquipment'),
        _safe_bic('OST_MechanicalEquipment'),
        _safe_bic('OST_PipeAccessory'),
        _safe_bic('OST_GenericModel'),
        _safe_bic('OST_Furniture'),
        _safe_bic('OST_FireProtection'),
    ]
    bics_annot = [
        _safe_bic('OST_GenericAnnotation'),
        _safe_bic('OST_DetailComponents'),
    ]

    for bic in bics_model + bics_annot:
        if bic is None:
            continue
        for e in link_reader.iter_elements_by_category(doc_, bic, limit=scan_limit, level_id=None):
            t = _elem_text(e)
            if not pk_indicator_rules.is_hydrant_candidate(t, include_keys, exclude_keys):
                continue
            pt = _inst_center_point(e)
            if pt:
                pts.append(pt)

    pts.extend(_collect_textnote_points(doc_, include_keys, exclude_keys))
    pts.extend(_collect_tag_points(doc_, include_keys, exclude_keys))

    return pts


def _points_near_xy(a, b, r_ft):
    try:
        dx = float(a.X) - float(b.X)
        dy = float(a.Y) - float(b.Y)
        return ((dx * dx + dy * dy) ** 0.5) <= float(r_ft)
    except Exception:
        return False


def _dedupe_points_xy(points, radius_ft):
    out = []
    r = float(radius_ft or 0.0)
    if r <= 1e-9:
        return list(points or [])
    for p in points or []:
        if p is None:
            continue
        dup = False
        for q in out:
            if _points_near_xy(p, q, r):
                dup = True
                break
        if not dup:
            out.append(p)
    return out


def _filter_points_by_view_level(points, view, tol_ft):
    if view is None:
        return list(points or [])
    try:
        lvl = getattr(view, 'GenLevel', None)
        if lvl is None:
            return list(points or [])
        z = float(lvl.Elevation)
    except Exception:
        return list(points or [])
    out = []
    for p in points or []:
        try:
            if abs(float(p.Z) - z) <= float(tol_ft):
                out.append(p)
        except Exception:
            out.append(p)
    return out


def _collect_existing_points(doc_, tag, view_based=False):
    pts = []
    if doc_ is None or not tag:
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
        _safe_bic('OST_LightingFixtures'),
        _safe_bic('OST_LightingDevices'),
        _safe_bic('OST_ElectricalFixtures'),
        _safe_bic('OST_SpecialityEquipment'),
        _safe_bic('OST_GenericModel'),
    ]
    if view_based:
        bics.extend([_safe_bic('OST_GenericAnnotation'), _safe_bic('OST_DetailComponents')])

    for bic in bics:
        if bic is None:
            continue
        try:
            col = (DB.FilteredElementCollector(doc_)
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


def _pick_link_doc(host_doc, include_keys, exclude_keys, scan_limit):
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
        if _collect_hydrant_points(ld, include_keys, exclude_keys, scan_limit):
            return ln, ld

    # Fallback: host model
    if _collect_hydrant_points(host_doc, include_keys, exclude_keys, scan_limit):
        return None, host_doc

    # Manual pick
    ln = socket_utils._select_link_instance_ru(host_doc, 'Выберите связь АР (пожарные краны)')
    if ln is None:
        return None, None
    if not link_reader.is_link_loaded(ln):
        alert('Связь не загружена. Загрузите её в Manage Links и повторите.')
        return None, None
    return ln, link_reader.get_link_doc(ln)


def _place_view_based(doc_, symbol, pt, view, comment):
    if view is None or symbol is None or pt is None:
        return None
    try:
        if view.IsTemplate:
            raise Exception('Active view is a template.')
    except Exception:
        pass
    try:
        lvl = getattr(view, 'GenLevel', None)
        z = float(lvl.Elevation) if lvl else float(pt.Z)
    except Exception:
        z = float(pt.Z)
    p = DB.XYZ(float(pt.X), float(pt.Y), z)
    inst = doc_.Create.NewFamilyInstance(p, symbol, view)
    if inst and comment:
        set_comments(inst, comment)
    return inst


def main():
    try:
        rules = _get_rules()
        cfg = script.get_config()
    except Exception:
        rules = _get_rules()
        cfg = None

    include_keys, exclude_keys = _get_keywords(rules)
    scan_limit = int(_get_number(rules, 'pk_scan_limit', 3000))
    dedupe_ft = mm_to_ft(_get_number(rules, 'pk_dedupe_radius_mm', 300.0)) or 0.0
    level_tol_ft = mm_to_ft(_get_number(rules, 'pk_level_z_tol_mm', 4000.0)) or 0.0
    height_ft = mm_to_ft(_get_number(rules, 'pk_sign_height_mm', 2300.0)) or 0.0

    symbol = _pick_pk_symbol(doc, cfg, rules)
    if symbol is None:
        alert('Не выбран тип указателя ПК. Загрузите семейство и повторите.')
        return

    is_view_based = _is_view_based(symbol)
    if (not is_view_based) and (not _is_point_based(symbol)):
        alert('Выбранный тип не поддерживает ViewBased или точечное размещение. Выберите другой тип.')
        return

    if doc.ActiveView is None:
        alert('Нет активного вида. Перейдите на план и повторите.')
        return
    try:
        if doc.ActiveView.ViewType not in (
            DB.ViewType.FloorPlan,
            DB.ViewType.CeilingPlan,
            DB.ViewType.EngineeringPlan,
            DB.ViewType.AreaPlan,
            DB.ViewType.Detail,
        ):
            alert('Активный вид не является планом/деталью. Перейдите на план и повторите.')
            return
    except Exception:
        pass

    link_inst, link_doc = _pick_link_doc(doc, include_keys, exclude_keys, scan_limit)
    if link_doc is None:
        alert('Не найден документ связи с пожарными кранами.')
        return

    # Collect candidate points in link coordinates
    pts = _collect_hydrant_points(link_doc, include_keys, exclude_keys, scan_limit)
    if not pts:
        alert('Пожарные краны не найдены по ключевым словам. Проверьте правила pk_hydrant_keywords.')
        return

    # Transform to host coordinates
    if link_inst is not None:
        try:
            tr = link_reader.get_total_transform(link_inst)
            pts = [tr.OfPoint(p) for p in pts if p is not None]
        except Exception:
            pass

    # Level filter for active view
    pts = _filter_points_by_view_level(pts, doc.ActiveView, level_tol_ft)
    pts = _dedupe_points_xy(pts, dedupe_ft)

    comment_tag = (rules or {}).get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:PK_SIGN'.format(comment_tag)

    existing = _collect_existing_points(doc, comment_value, view_based=is_view_based)
    if existing:
        pts = [p for p in pts if not any(_points_near_xy(p, ex, dedupe_ft) for ex in existing)]

    created = []
    skipped = 0
    with tx('ЭОМ: Указатели ПК'):
        for p in pts:
            try:
                use_pt = p
                if (not is_view_based) and height_ft:
                    use_pt = DB.XYZ(float(p.X), float(p.Y), float(p.Z) + float(height_ft))
                if is_view_based:
                    inst = _place_view_based(doc, symbol, use_pt, doc.ActiveView, comment_value)
                else:
                    inst = placement_engine.place_point_family_instance(doc, symbol, use_pt, view=doc.ActiveView)
                    if inst and comment_value:
                        set_comments(inst, comment_value)
                if inst:
                    created.append(inst)
                else:
                    skipped += 1
            except Exception:
                skipped += 1
                continue

    if cfg is not None:
        _store_symbol_id(cfg, 'last_pk_symbol_id', symbol)
        _store_symbol_unique_id(cfg, 'last_pk_symbol_uid', symbol)
        try:
            script.save_config()
        except Exception:
            pass

    output.print_md('**Указатели ПК**')
    output.print_md('Найдено кандидатов: **{0}**'.format(len(pts)))
    output.print_md('Создано: **{0}**'.format(len(created)))
    if skipped:
        output.print_md('Пропущено: **{0}**'.format(skipped))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('PK indicators failed')
        alert('Ошибка при размещении указателей ПК. См. лог pyRevit.')
