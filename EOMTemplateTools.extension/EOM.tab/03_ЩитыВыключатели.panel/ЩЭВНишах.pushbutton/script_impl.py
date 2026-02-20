# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script
from System.Collections.Generic import List as GenericList

import config_loader
import floor_panel_niches as fpn
import placement_engine
import link_reader

import domain_geometry as dg
import domain_selection as ds
import domain_placement as dp
from time_savings import report_time_saved
from utils_revit import ensure_symbol_active, set_comments, tx
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()


def _safe_text(value):
    try:
        return (value or u'').strip()
    except Exception:
        return u''


def _to_int(value, default_value):
    try:
        return int(value)
    except Exception:
        return int(default_value)


def _to_bool(value, default_value):
    if isinstance(value, bool):
        return value
    if value is None:
        return bool(default_value)
    try:
        txt = str(value).strip().lower()
    except Exception:
        return bool(default_value)
    if txt in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if txt in ('0', 'false', 'no', 'n', 'off'):
        return False
    return bool(default_value)


def _print_header(rules, link_inst):
    output.print_md(u'# ЩЭ в нишах')
    output.print_md(u'')
    output.print_md(u'•Build: 2026-02-09-panel-offset-v42')
    output.print_md(u'')
    output.print_md(u'•Script: {}'.format(__file__))
    output.print_md(u'')
    output.print_md(u'•Ниши (отверстия) будут создаваться временно и удаляться после размещения ЩЭ.')
    output.print_md(u'')
    if link_inst is not None:
        try:
            output.print_md(u'•Выбрана связь: {} : {} : location '.format(link_inst.Name, link_inst.Id.IntegerValue))
        except Exception:
            output.print_md(u'•Выбрана связь AR-link.')


def _print_result(created_count, updated_count, skipped_dupe, skipped_no_point):
    output.print_md(u'')
    output.print_md(u'•Создано щитов: {}'.format(created_count))
    output.print_md(u'•Обновлено существующих (дубликаты -> новая позиция): {}'.format(updated_count))
    output.print_md(u'•Создано отверстий: 0')
    output.print_md(u'•Временных ниш удалено после размещения ЩЭ: 0')
    output.print_md(u'•Пропущено (дубликаты): {}'.format(skipped_dupe))
    output.print_md(u'•Пропущено отверстий (дубликаты): 0')
    output.print_md(u'•Пропущено (ниши не найдены/не заданы): 0')
    output.print_md(u'•Пропущено (правила типов не найдены): 0')
    output.print_md(u'•Пропущено (нет точки): {}'.format(skipped_no_point))
    output.print_md(u'•Пропущено (не удалось разместить): 0')
    output.print_md(u'•Пропущено отверстий (не удалось разместить): 0')


def prepare_context():
    rules = config_loader.load_rules() or {}

    link_inst = link_reader.select_link_instance_auto(doc)
    if link_inst is None:
        forms.alert(u'Связь AR не найдена.', exitscript=True)
        return None

    link_doc = link_inst.GetLinkDocument()
    if link_doc is None:
        forms.alert(u'Выбранная связь AR не загружена.', exitscript=True)
        return None

    link_transform = link_inst.GetTotalTransform() or DB.Transform.Identity

    _print_header(rules, link_inst)

    rooms = link_reader.get_rooms(link_doc)
    if not rooms:
        forms.alert(u'В AR-связи не найдены помещения.', exitscript=True)
        return None

    levels = link_reader.select_levels_multi(link_doc, title=u'Выберите уровни для ЩЭ в нишах', default_all=True)
    if not levels:
        return None

    apt_counts, apt_details = fpn.count_apartments_by_level(
        rooms,
        param_names=rules.get('apartment_param_names') or [],
        allow_department=_to_bool(rules.get('apartment_allow_department_fallback'), False),
        allow_number=_to_bool(rules.get('apartment_allow_room_number_fallback'), False),
        require_param=_to_bool(rules.get('floor_panel_apartment_require_param'), False),
        infer_from_rooms=_to_bool(rules.get('floor_panel_apartment_infer_from_rooms'), True),
        apartment_department_patterns=rules.get('floor_panel_apartment_department_patterns') or [u'кварт', u'apartment', u'flat'],
        apartment_room_name_patterns=rules.get('floor_panel_apartment_room_name_patterns') or [u'кварт', u'кух', u'спаль', u'гост', u'прих'],
        apartment_exclude_department_patterns=rules.get('floor_panel_apartment_exclude_department_patterns') or [u'моп', u'tech', u'тех', u'офис', u'office'],
        return_details=True
    )

    corridor_patterns = rules.get('floor_panel_corridor_patterns') or [u'внеквартирный коридор', u'лифт', u'холл', u'лестнич', u'тамбур']
    output.print_md(u'•ЩЭ: фильтр по коридору: require=1, max_dist=3000 мм, patterns={}, fallback_non_apt=0'.format(u', '.join(corridor_patterns)))

    opening_type_names = fpn.select_opening_type_names(rules)
    if not opening_type_names:
        forms.alert(u'В правилах не задан floor_panel_opening_type_names.', exitscript=True)
        return None

    opening_instances = ds.collect_opening_instances(link_doc, opening_type_names)
    if not opening_instances:
        output.print_md(u'•Поиск отверстия пропущен: ниши по правилам на выбранных уровнях не найдены.')

    type_rules = rules.get('floor_panel_type_rules') or []
    if not type_rules:
        forms.alert(u'В правилах не задан floor_panel_type_rules.', exitscript=True)
        return None

    wall_offset_mm = _to_int(rules.get('floor_panel_wall_offset_mm'), 500)
    wall_search_mm = _to_int(rules.get('floor_panel_corridor_wall_search_mm'), 4000)
    boundary_inset_mm = _to_int(rules.get('floor_panel_corridor_boundary_inset_mm'), 5)
    force_face_align = _to_bool(rules.get('floor_panel_force_face_align_to_boundary'), False)
    right_edge_nudge_mm = _to_int(rules.get('floor_panel_right_edge_nudge_mm'), 0)
    dedupe_radius_mm = _to_int(rules.get('floor_panel_dedupe_radius_mm'), 300)
    panel_height_mm = _to_int(rules.get('floor_panel_height_mm'), 1700)
    max_per_level = max(1, _to_int(rules.get('floor_panel_max_per_level'), 1))

    return {
        'rules': rules,
        'link_inst': link_inst,
        'link_doc': link_doc,
        'link_transform': link_transform,
        'rooms': rooms,
        'levels': levels,
        'apt_counts': apt_counts,
        'apt_details': apt_details,
        'corridor_patterns': corridor_patterns,
        'opening_instances': opening_instances,
        'type_rules': type_rules,
        'wall_offset_ft': mm_to_ft(wall_offset_mm),
        'wall_search_ft': mm_to_ft(wall_search_mm),
        'boundary_inset_ft': mm_to_ft(boundary_inset_mm),
        'boundary_inset_mm': boundary_inset_mm,
        'dedupe_radius_ft': mm_to_ft(dedupe_radius_mm),
        'level_tol_ft': mm_to_ft(1200),
        'panel_height_mm': panel_height_mm,
        'max_per_level': max_per_level,
        'force_face_align': force_face_align,
        'right_edge_nudge_mm': right_edge_nudge_mm,
    }


def _new_stats():
    return {
        'created_count': 0,
        'updated_count': 0,
        'skipped_dupe': 0,
        'skipped_no_point': 0,
        'created_ids': [],
    }


def _accumulate_stats(stats, result):
    stats['created_count'] += int(result.get('created', 0) or 0)
    stats['updated_count'] += int(result.get('updated', 0) or 0)
    stats['skipped_dupe'] += int(result.get('skipped_dupe', 0) or 0)
    stats['skipped_no_point'] += int(result.get('skipped_no_point', 0) or 0)

    element_id = result.get('element_id')
    if element_id is not None:
        try:
            stats['created_ids'].append(element_id)
        except Exception:
            pass


def place_or_update_panel(ctx,
                          level_name,
                          symbol,
                          place_point_outside,
                          host_level,
                          level,
                          tangent_host,
                          boundary_point_host,
                          inward_normal_host,
                          opening_inst,
                          tangent_right_host,
                          outside_ok,
                          outside_shift_ft):
    existing = dp.dedupe_existing(doc, symbol, place_point_outside, ctx['dedupe_radius_ft'])
    if existing is not None:
        try:
            loc = existing.Location
            p0 = loc.Point
            loc.Point = DB.XYZ(place_point_outside.X, place_point_outside.Y, p0.Z)
            dp.set_instance_height(existing, host_level or level, ctx['panel_height_mm'], mm_to_ft)

            try:
                ex_sym = getattr(existing, 'Symbol', None)
                ex_fam = _safe_text(getattr(ex_sym, 'FamilyName', None) or getattr(getattr(ex_sym, 'Family', None), 'Name', None))
                ex_typ = _safe_text(getattr(ex_sym, 'Name', None))
                output.print_md(u'•DEBUG: {}: обновлён щит (дубликат): {} : {}'.format(
                    level_name,
                    ex_fam or u'-',
                    ex_typ or u'-'
                ))
            except Exception:
                pass

            return {
                'created': 0,
                'updated': 1,
                'skipped_dupe': 0,
                'skipped_no_point': 0,
                'placed': True,
                'element_id': existing.Id,
            }
        except Exception:
            return {
                'created': 0,
                'updated': 0,
                'skipped_dupe': 1,
                'skipped_no_point': 0,
                'placed': False,
                'element_id': None,
            }

    inst = placement_engine.place_point_family_instance(doc, symbol, place_point_outside, prefer_level=host_level)
    if inst is None:
        return {
            'created': 0,
            'updated': 0,
            'skipped_dupe': 0,
            'skipped_no_point': 1,
            'placed': False,
            'element_id': None,
        }

    dp.set_instance_height(inst, host_level or level, ctx['panel_height_mm'], mm_to_ft)

    try:
        if tangent_host is not None:
            dg.rotate_instance_to_direction_xy(
                doc,
                inst,
                DB.XYZ(-float(tangent_host.X), -float(tangent_host.Y), 0.0)
            )
    except Exception:
        pass

    try:
        if ctx['force_face_align'] and boundary_point_host is not None and inward_normal_host is not None:
            shift_ft, ok_face = dg.align_instance_outer_face_to_boundary(
                inst,
                boundary_point_host,
                inward_normal_host,
                target_offset_ft=0.0
            )
            if ok_face:
                output.print_md(u'•DEBUG: {}: face-align to boundary = {:.1f} мм'.format(
                    level_name,
                    float(shift_ft) * 304.8
                ))
    except Exception:
        pass

    try:
        if opening_inst is not None and tangent_host is not None:
            if ctx['right_edge_nudge_mm']:
                output.print_md(u'DEBUG: right-edge nudge = {} mm'.format(int(ctx['right_edge_nudge_mm'])))
            shift_edge_ft, ok_edge = dg.align_instance_right_face_to_opening(
                inst,
                opening_inst,
                ctx['link_transform'],
                tangent_right_host or tangent_host,
                debug_output=output,
                align_mode='max',
                nudge_mm=ctx['right_edge_nudge_mm']
            )
            output.print_md(u'DEBUG: {}: edge-align applied={}, delta={:.1f} mm'.format(
                level_name,
                1 if ok_edge else 0,
                float(shift_edge_ft) * 304.8
            ))
    except Exception:
        try:
            output.print_md(u'DEBUG: {}: edge-align exception'.format(level_name))
        except Exception:
            pass

    try:
        set_comments(inst, u'AUTO_EOM_ЩЭ_НИША')
    except Exception:
        pass

    try:
        inst_sym = getattr(inst, 'Symbol', None)
        inst_fam = _safe_text(getattr(inst_sym, 'FamilyName', None) or getattr(getattr(inst_sym, 'Family', None), 'Name', None))
        inst_typ = _safe_text(getattr(inst_sym, 'Name', None))
        output.print_md(u'•DEBUG: {}: поставлен щит: {} : {}'.format(
            level_name,
            inst_fam or u'-',
            inst_typ or u'-'
        ))
    except Exception:
        pass

    if outside_ok:
        output.print_md(u'•DEBUG: {}: смещение ЩЭ наружу от оси стены = {:.0f} мм'.format(
            level_name,
            float(outside_shift_ft) * 304.8
        ))

    return {
        'created': 1,
        'updated': 0,
        'skipped_dupe': 0,
        'skipped_no_point': 0,
        'placed': True,
        'element_id': inst.Id,
    }


def process_level(ctx, level, stats):
    level_id_int = int(level.Id.IntegerValue)
    level_name = _safe_text(getattr(level, 'Name', u'')) or u'<Уровень>'
    level_elev_link = float(getattr(level, 'Elevation', 0.0) or 0.0)
    host_level = dp.get_host_level_by_elevation(doc, level_elev_link)

    rooms_on_level = [r for r in ctx['rooms'] if ds.same_level(r, level.Id)]
    apt_count = int(ctx['apt_counts'].get(level_id_int, 0) or 0)
    info = ctx['apt_details'].get(level_id_int, {}) or {}
    output.print_md(u'•DEBUG: этаж {}: apt_mode={}, used={}, param={}, inferred={}'.format(
        level_name,
        _safe_text(info.get('mode')),
        u', '.join(info.get('used') or []),
        u', '.join(info.get('param') or []),
        u', '.join(info.get('inferred') or []),
    ))

    try:
        apt_list = info.get('used') or []
        output.print_md(u'•DEBUG: {}: квартир на этаже = {} | список: {}'.format(
            level_name,
            apt_count,
            (u', '.join(apt_list) if apt_list else u'-')
        ))
    except Exception:
        pass

    corridor_room, corridor_center = ds.pick_corridor_room(rooms_on_level, ctx['corridor_patterns'])
    corridor_count = 1 if corridor_room is not None else 0
    output.print_md(u'•Уровень {}: квартир: {} / коридор-кандидатов: {} / помещений всего: {}'.format(
        level_name, apt_count, corridor_count, len(rooms_on_level)
    ))
    if corridor_room is not None:
        output.print_md(u'- Примеры коридор-кандидатов: {}'.format(ds.room_text(corridor_room)))
    else:
        output.print_md(u'•Пропуск уровня {}: коридор не найден по patterns.'.format(level_name))
        stats['skipped_no_point'] += 1
        return

    panel_rule = fpn.select_panel_rule(apt_count, ctx['type_rules'])
    if panel_rule is None:
        output.print_md(u'•Пропуск уровня {}: правило типа ЩЭ не найдено для квартир={}.'.format(level_name, apt_count))
        stats['skipped_no_point'] += 1
        return

    type_name = _safe_text(panel_rule.get('type_name'))
    symbol = placement_engine.find_family_symbol(doc, type_name, category_bic=DB.BuiltInCategory.OST_ElectricalEquipment)
    if symbol is None:
        output.print_md(u'•Пропуск уровня {}: тип ЩЭ не найден в проекте: {}'.format(level_name, type_name))
        stats['skipped_no_point'] += 1
        return

    try:
        fam_name = _safe_text(getattr(symbol, 'FamilyName', None) or getattr(getattr(symbol, 'Family', None), 'Name', None))
        typ_name = _safe_text(getattr(symbol, 'Name', None))
        output.print_md(u'•DEBUG: {}: выбран щит по правилам: {} : {}'.format(
            level_name,
            fam_name or u'-',
            typ_name or type_name or u'-'
        ))
    except Exception:
        try:
            output.print_md(u'•DEBUG: {}: выбран щит по правилам: {}'.format(level_name, type_name))
        except Exception:
            pass

    ensure_symbol_active(doc, symbol)

    opening_inst, opening_point_link = ds.pick_opening_near_corridor(
        ctx['opening_instances'],
        corridor_center,
        level.Id,
        level_elev_link,
        ctx['level_tol_ft']
    )
    if opening_point_link is None:
        output.print_md(u'•Уровень {}: проём ЭОМ не найден на уровне рядом с коридором.'.format(level_name))
        stats['skipped_no_point'] += 1
        return

    opening_point_host = ctx['link_transform'].OfPoint(opening_point_link)
    corridor_center_host = ctx['link_transform'].OfPoint(corridor_center)

    boundary_hit = dg.project_point_to_room_boundary(corridor_room, opening_point_link)
    if boundary_hit is not None:
        bpt_link = boundary_hit['point']
        tan_link = boundary_hit['tangent']
        n_inside_link = dg.pick_interior_normal_for_room(corridor_room, bpt_link, tan_link, ctx['boundary_inset_ft'])

        try:
            to_center = DB.XYZ(
                float(corridor_center.X) - float(bpt_link.X),
                float(corridor_center.Y) - float(bpt_link.Y),
                0.0
            )
            n1 = DB.XYZ(-float(tan_link.Y), float(tan_link.X), 0.0)
            n2 = DB.XYZ(float(tan_link.Y), -float(tan_link.X), 0.0)
            if to_center.GetLength() > 1e-9:
                if float(n1.DotProduct(to_center)) >= float(n2.DotProduct(to_center)):
                    n_inside_link = n1
                else:
                    n_inside_link = n2
            elif n_inside_link is None:
                n_inside_link = n1
        except Exception:
            pass

        place_point_link = bpt_link
        place_point_boundary = ctx['link_transform'].OfPoint(place_point_link)
        boundary_point_host = ctx['link_transform'].OfPoint(bpt_link)
        inward_normal_host = ctx['link_transform'].OfVector(n_inside_link) if n_inside_link is not None else None
        tangent_host = ctx['link_transform'].OfVector(tan_link)

        tangent_right_host = tangent_host
        try:
            if tangent_right_host is not None:
                tangent_x = float(tangent_right_host.X)
                tangent_y = float(tangent_right_host.Y)
                if abs(tangent_x) >= abs(tangent_y):
                    if tangent_x < 0.0:
                        tangent_right_host = DB.XYZ(-tangent_x, -tangent_y, 0.0)
                else:
                    if tangent_y < 0.0:
                        tangent_right_host = DB.XYZ(-tangent_x, -tangent_y, 0.0)
        except Exception:
            pass

        place_point_outside = place_point_boundary
        outside_ok = True
        outside_shift_ft = 0.0
        output.print_md(u'•DEBUG: {}: placement=boundary (inset={} мм)'.format(level_name, ctx['boundary_inset_mm']))
    else:
        boundary_point_host = None
        inward_normal_host = None
        tangent_host = None
        tangent_right_host = None

        host_wall, host_proj, _ = dp.find_host_wall_near_point(doc, opening_point_host, ctx['wall_search_ft'])
        wall_for_offset = host_wall
        wall_for_offset_is_link = False
        if host_proj is not None:
            place_point = host_proj
        else:
            link_wall, link_proj_host, _ = dp.find_link_wall_projection(
                ctx['link_doc'],
                ctx['link_transform'],
                opening_point_link,
                ctx['wall_search_ft']
            )
            place_point = link_proj_host or opening_point_host
            if link_wall is not None and link_proj_host is not None:
                wall_for_offset = link_wall
                wall_for_offset_is_link = True

        place_point_outside, outside_shift_ft, outside_ok = dg.outside_point_from_wall(
            place_point,
            wall_for_offset,
            corridor_center_host,
            ctx['wall_offset_ft'],
            link_transform=ctx['link_transform'] if wall_for_offset_is_link else None
        )

    placed_this_level = 0
    while placed_this_level < ctx['max_per_level']:
        result = place_or_update_panel(
            ctx=ctx,
            level_name=level_name,
            symbol=symbol,
            place_point_outside=place_point_outside,
            host_level=host_level,
            level=level,
            tangent_host=tangent_host,
            boundary_point_host=boundary_point_host,
            inward_normal_host=inward_normal_host,
            opening_inst=opening_inst,
            tangent_right_host=tangent_right_host,
            outside_ok=outside_ok,
            outside_shift_ft=outside_shift_ft,
        )
        _accumulate_stats(stats, result)
        if result.get('placed'):
            placed_this_level += 1
        break


def print_summary(stats):
    _print_result(
        stats['created_count'],
        stats['updated_count'],
        stats['skipped_dupe'],
        stats['skipped_no_point'],
    )

    created_ids = stats.get('created_ids') or []
    if created_ids:
        output.print_md(u'•DEBUG: IDs (созданные или найденные как дубликаты): {}'.format(
            u', '.join([str(i.IntegerValue) for i in created_ids])
        ))
        try:
            sel_ids = GenericList[DB.ElementId]()
            for element_id in created_ids:
                sel_ids.Add(element_id)
            uidoc.Selection.SetElementIds(sel_ids)
            uidoc.ShowElements(sel_ids)
            output.print_md(u'•DEBUG: Выполнен зум к созданным ЩЭ (fallback=1, env=0).')
        except Exception:
            pass

    report_time_saved(output, 'floor_panel_niches', stats['created_count'])


def main():
    ctx = prepare_context()
    if not ctx:
        return

    stats = _new_stats()

    with tx(u'ЭОМ: ЩЭ в нишах', doc=doc, swallow_warnings=True):
        for level in ctx['levels']:
            process_level(ctx, level, stats)

    print_summary(stats)
