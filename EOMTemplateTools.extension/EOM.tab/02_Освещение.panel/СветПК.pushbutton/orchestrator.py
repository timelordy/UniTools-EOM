# -*- coding: utf-8 -*-

from pyrevit import DB
import link_reader
import placement_engine
from utils_revit import alert, log_exception, set_comments, tx
from utils_units import mm_to_ft
import adapters
from domain import (
    dedupe_points_xy,
    filter_points_by_view_level,
    is_view_based,
    is_point_based,
    points_near_xy
)


def place_view_based(doc, symbol, pt, view, comment):
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
    inst = doc.Create.NewFamilyInstance(p, symbol, view)
    if inst and comment:
        set_comments(inst, comment)
    return inst


def run_placement(doc, output, script_module):
    try:
        rules = adapters.get_rules()
        cfg = script_module.get_config()
    except Exception:
        rules = adapters.get_rules()
        cfg = None

    include_keys, exclude_keys = adapters.get_keywords(rules)
    scan_limit = int(adapters.get_number(rules, 'pk_scan_limit', 3000))
    dedupe_ft = mm_to_ft(adapters.get_number(rules, 'pk_dedupe_radius_mm', 300.0)) or 0.0
    level_tol_ft = mm_to_ft(adapters.get_number(rules, 'pk_level_z_tol_mm', 4000.0)) or 0.0
    height_ft = mm_to_ft(adapters.get_number(rules, 'pk_sign_height_mm', 2300.0)) or 0.0

    symbol = adapters.pick_pk_symbol(doc, cfg, rules)
    if symbol is None:
        alert('Не выбран тип указателя ПК. Загрузите семейство и повторите.')
        return

    is_view_based_sym = is_view_based(symbol)
    if (not is_view_based_sym) and (not is_point_based(symbol)):
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

    link_inst, link_doc = adapters.pick_link_doc(doc, include_keys, exclude_keys, scan_limit)
    if link_doc is None:
        alert('Не найден документ связи с пожарными кранами.')
        return

    # Collect candidate points in link coordinates
    pts = adapters.collect_hydrant_points(link_doc, include_keys, exclude_keys, scan_limit)
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
    pts = filter_points_by_view_level(pts, doc.ActiveView, level_tol_ft)
    pts = dedupe_points_xy(pts, dedupe_ft)

    comment_tag = (rules or {}).get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:PK_SIGN'.format(comment_tag)

    existing = adapters.collect_existing_points(doc, comment_value, view_based=is_view_based_sym)
    if existing:
        pts = [p for p in pts if not any(points_near_xy(p, ex, dedupe_ft) for ex in existing)]

    created = []
    skipped = 0
    with tx('ЭОМ: Указатели ПК'):
        for p in pts:
            try:
                use_pt = p
                if (not is_view_based_sym) and height_ft:
                    use_pt = DB.XYZ(float(p.X), float(p.Y), float(p.Z) + float(height_ft))
                if is_view_based_sym:
                    inst = place_view_based(doc, symbol, use_pt, doc.ActiveView, comment_value)
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
        adapters.store_symbol_id(cfg, 'last_pk_symbol_id', symbol)
        adapters.store_symbol_unique_id(cfg, 'last_pk_symbol_uid', symbol)
        try:
            script_module.save_config()
        except Exception:
            pass

    output.print_md('**Указатели ПК**')
    output.print_md('Найдено кандидатов: **{0}**'.format(len(pts)))
    output.print_md('Создано: **{0}**'.format(len(created)))
    if skipped:
        output.print_md('Пропущено: **{0}**'.format(skipped))
