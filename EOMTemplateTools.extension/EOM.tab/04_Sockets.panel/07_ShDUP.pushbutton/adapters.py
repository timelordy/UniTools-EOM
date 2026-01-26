# -*- coding: utf-8 -*-

import config_loader
import link_reader
import placement_engine
import socket_utils as su
from pyrevit import DB, forms, revit
import constants
import domain


def get_rules():
    return config_loader.load_rules()


def get_config():
    from pyrevit import script
    return script.get_config()


def save_config():
    from pyrevit import script
    script.save_config()


def select_link_instance(doc, title):
    return su._select_link_instance_ru(doc, title)


def get_link_doc(link_inst):
    return link_reader.get_link_doc(link_inst)


def get_total_transform(link_inst):
    return link_reader.get_total_transform(link_inst)


def get_all_linked_rooms(link_doc, limit):
    return su._get_all_linked_rooms(link_doc, limit=limit)


def pick_shdup_symbol(host_doc, cfg, rules):
    if host_doc is None:
        return None, None

    try:
        sym = su._load_symbol_from_saved_unique_id(host_doc, cfg, 'last_shdup_symbol_uid')
        if not sym:
            sym = su._load_symbol_from_saved_id(host_doc, cfg, 'last_shdup_symbol_id')
        if sym:
            return sym, placement_engine.format_family_type(sym)
    except Exception:
        pass

    fams = rules.get('family_type_names', {}) if rules else {}
    prefer = fams.get('shdup')
    prefer_list = []
    try:
        if isinstance(prefer, (list, tuple)):
            prefer_list = [x for x in prefer if x]
        elif prefer:
            prefer_list = [prefer]
    except Exception:
        prefer_list = [prefer] if prefer else []

    for want in prefer_list:
        try:
            sym = su._find_symbol_by_fullname(host_doc, want)
            if sym:
                return sym, placement_engine.format_family_type(sym)
        except Exception:
            continue

    keys = constants.SHDUP_KEYWORDS
    best = None
    best_score = -999
    for bic in (
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_GenericModel,
    ):
        for s in placement_engine.iter_family_symbols(host_doc, category_bic=bic, limit=None):
            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''
            if not lbl:
                continue
            t = (lbl or u'').lower()
            if not any(k in t for k in keys):
                continue
            sc = 0
            if bic == DB.BuiltInCategory.OST_ElectricalEquipment:
                sc += 20
            if 'eom' in t:
                sc += 10
            if u'(нагрузка)' in t:
                sc += 30
            if u'230' in t or u'230в' in t:
                sc += 10
            if sc > best_score:
                best = s
                best_score = sc

    if best:
        return best, placement_engine.format_family_type(best)

    items = []
    by_label = {}
    for bic in (
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_GenericModel,
    ):
        for s in placement_engine.iter_family_symbols(host_doc, category_bic=bic, limit=None):
            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''
            if not lbl:
                continue
            t = (lbl or u'').lower()
            if t in by_label:
                continue
            by_label[t] = s
            items.append(lbl)

    items = sorted(items, key=lambda x: x.lower())
    picked = forms.SelectFromList.show(
        items,
        title='Выберите тип ШДУП (Family : Type)',
        multiselect=False,
        button_name='Выбрать',
        allow_none=True,
    )
    if not picked:
        return None, None

    sym = by_label.get(picked.lower())
    if not sym:
        return None, None
    return sym, placement_engine.format_family_type(sym)


def collect_tagged_instances(host_doc, tag_value, symbol_id=None):
    ids = set()
    elems = []
    pts = []
    if host_doc is None or not tag_value:
        return ids, elems, pts

    try:
        sym_id_int = int(symbol_id) if symbol_id is not None else None
    except Exception:
        sym_id_int = None

    tag_value_norm = (tag_value or u'').strip().lower()

    for bic in (
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_Furniture,
    ):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                c = su._get_comments_text(e)
            except Exception:
                c = u''
            if not c:
                continue
            if tag_value not in c:
                continue

            c_norm = (c or u'').lower()
            if tag_value_norm:
                try:
                    ok = False
                    for part in c_norm.split():
                        if part.startswith(tag_value_norm):
                            ok = True
                            break
                    if not ok:
                        continue
                except Exception:
                    pass

            if sym_id_int is not None:
                try:
                    es = getattr(e, 'Symbol', None)
                    if es is None:
                        continue
                    if int(es.Id.IntegerValue) != sym_id_int:
                        continue
                except Exception:
                    continue

            try:
                ids.add(int(e.Id.IntegerValue))
            except Exception:
                pass
            elems.append(e)
            try:
                pt = su._inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    return ids, elems, pts


def collect_sink_points(link_doc, rules):
    keys = rules.get('sink_family_keywords', []) or constants.SINK_KEYWORDS_DEFAULT
    bics = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericAnnotation,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    tag_bics = []
    for nm in (
        'OST_PlumbingFixtureTags',
        'OST_GenericModelTags',
        'OST_FurnitureTags',
        'OST_GenericAnnotation',
    ):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                tag_bics.append(bic)
        except Exception:
            continue
    return su._collect_points_by_keywords_multi(link_doc, keys, bics, tag_bics=(tag_bics if tag_bics else None))


def collect_tub_points(link_doc, rules):
    keys = rules.get('bath_keywords', None) or constants.TUB_KEYWORDS_DEFAULT
    bics = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericAnnotation,
        DB.BuiltInCategory.OST_DetailComponents,
    ]
    tag_bics = []
    for nm in (
        'OST_PlumbingFixtureTags',
        'OST_GenericModelTags',
        'OST_FurnitureTags',
        'OST_GenericAnnotation',
    ):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                tag_bics.append(bic)
        except Exception:
            continue
    return su._collect_points_by_keywords_multi(link_doc, keys, bics, tag_bics=(tag_bics if tag_bics else None))


def collect_toilet_points(link_doc, rules):
    """Collect toilet/WC points from linked document."""
    keys = rules.get('toilet_keywords', None) or constants.TOILET_KEYWORDS_DEFAULT
    bics = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
    ]
    pts = []
    for bic in bics:
        pts.extend(su._collect_points_by_keywords(link_doc, keys, bic))
    return pts
