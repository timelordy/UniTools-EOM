# -*- coding: utf-8 -*-

from __future__ import print_function

from pyrevit import DB, forms, revit, script

import link_reader
from utils_revit import tx


doc = revit.doc
output = script.get_output()


def _safe_text(value):
    try:
        return (value or u'').strip()
    except Exception:
        return u''


def _level_name(level):
    return _safe_text(getattr(level, 'Name', u'')) or u'<Уровень>'


def _elev_ft(level):
    try:
        return float(getattr(level, 'Elevation', 0.0) or 0.0)
    except Exception:
        return 0.0


def _find_level_by_name(levels, name):
    if not name:
        return None
    for lvl in levels:
        try:
            if _safe_text(getattr(lvl, 'Name', u'')) == name:
                return lvl
        except Exception:
            continue
    return None


def _find_level_by_elevation(levels, elev_ft, tol_ft):
    for lvl in levels:
        try:
            if abs(float(getattr(lvl, 'Elevation', 0.0) or 0.0) - float(elev_ft)) <= float(tol_ft):
                return lvl
        except Exception:
            continue
    return None


def _try_copy_building_story(src_level, dst_level):
    try:
        bip = DB.BuiltInParameter.LEVEL_IS_BUILDING_STORY
        p_src = src_level.get_Parameter(bip)
        p_dst = dst_level.get_Parameter(bip)
        if p_src is None or p_dst is None:
            return
        if p_dst.IsReadOnly:
            return
        p_dst.Set(int(p_src.AsInteger()))
    except Exception:
        return


def _iter_viewplans(doc, view_type=None):
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)
    except Exception:
        return []

    result = []
    for view in col:
        try:
            if view is None:
                continue
            if view.IsTemplate:
                continue
            if view_type is not None and view.ViewType != view_type:
                continue
            result.append(view)
        except Exception:
            continue
    return result


def _pick_source_plan(doc, view_type):
    for view in _iter_viewplans(doc, view_type=view_type):
        try:
            if getattr(view, 'GenLevel', None) is not None:
                return view
        except Exception:
            continue
    return None


def _find_view_family_type_id(doc, view_family):
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType)
    except Exception:
        return None

    for vft in col:
        try:
            if vft.ViewFamily == view_family:
                return vft.Id
        except Exception:
            continue
    return None


def _get_level_of_view(view):
    try:
        return getattr(view, 'GenLevel', None)
    except Exception:
        return None


def _find_plan_for_level(doc, level_id, view_type):
    for view in _iter_viewplans(doc, view_type=view_type):
        try:
            lvl = _get_level_of_view(view)
            if lvl is not None and lvl.Id.IntegerValue == level_id.IntegerValue:
                return view
        except Exception:
            continue
    return None


def _copy_plan_settings(src_view, dst_view):
    if src_view is None or dst_view is None:
        return

    try:
        tid = src_view.ViewTemplateId
        if tid is not None and tid.IntegerValue > 0:
            dst_view.ViewTemplateId = tid
    except Exception:
        pass

    try:
        dst_view.Scale = src_view.Scale
    except Exception:
        pass

    try:
        dst_view.DetailLevel = src_view.DetailLevel
    except Exception:
        pass

    try:
        dst_view.CropBoxActive = src_view.CropBoxActive
        dst_view.CropBoxVisible = src_view.CropBoxVisible
    except Exception:
        pass

    for bip in (
        DB.BuiltInParameter.VIEW_DISCIPLINE,
        DB.BuiltInParameter.VIEW_SUB_DISCIPLINE,
    ):
        try:
            p_src = src_view.get_Parameter(bip)
            p_dst = dst_view.get_Parameter(bip)
            if p_src is None or p_dst is None:
                continue
            if p_dst.IsReadOnly:
                continue
            p_dst.Set(p_src.AsInteger())
        except Exception:
            continue


def _build_plan_name(src_view, target_level):
    level_name = _level_name(target_level)
    if src_view is None:
        return level_name

    src_name = _safe_text(getattr(src_view, 'Name', u''))
    src_level = _get_level_of_view(src_view)
    src_level_name = _level_name(src_level) if src_level is not None else u''

    if src_name and src_level_name and (src_level_name in src_name):
        return src_name.replace(src_level_name, level_name)

    if src_name:
        return u'{} {}'.format(src_name, level_name)

    return level_name


def _make_unique_view_name(base_name, names_set):
    if base_name not in names_set:
        return base_name

    i = 2
    while True:
        candidate = u'{} ({})'.format(base_name, i)
        if candidate not in names_set:
            return candidate
        i += 1


def _collect_view_names(doc):
    names = set()
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.View)
        for v in col:
            try:
                n = _safe_text(getattr(v, 'Name', u''))
                if n:
                    names.add(n)
            except Exception:
                continue
    except Exception:
        pass
    return names


def _create_plan_for_level(doc, target_level, source_plan, view_type, view_family, names_set, debug_lines):
    if target_level is None:
        return None, u'level-none'

    if _find_plan_for_level(doc, target_level.Id, view_type) is not None:
        return None, u'exists'

    vft_id = None
    if source_plan is not None:
        try:
            vft_id = source_plan.GetTypeId()
        except Exception:
            vft_id = None

    if vft_id is None or vft_id.IntegerValue <= 0:
        vft_id = _find_view_family_type_id(doc, view_family)

    if vft_id is None or vft_id.IntegerValue <= 0:
        debug_lines.append(u'no ViewFamilyType for {}'.format(view_family))
        return None, u'no-type'

    try:
        new_view = DB.ViewPlan.Create(doc, vft_id, target_level.Id)
    except Exception as ex:
        debug_lines.append(u'ViewPlan.Create failed: {}'.format(ex))
        return None, u'create-failed'

    _copy_plan_settings(source_plan, new_view)

    try:
        base_name = _build_plan_name(source_plan, target_level)
        unique_name = _make_unique_view_name(base_name, names_set)
        new_view.Name = unique_name
        names_set.add(unique_name)
    except Exception as ex:
        debug_lines.append(u'view naming failed: {}'.format(ex))

    return new_view, u'created'


def main():
    output.print_md(u'# Копировать уровни из AR')

    if doc is None:
        forms.alert(u'Нет активного документа.', exitscript=True)
        return

    if getattr(doc, 'IsFamilyDocument', False):
        forms.alert(u'Это семейство. В семействах уровни не создаются.', exitscript=True)
        return

    link_inst = link_reader.select_link_instance(doc, title=u'Выберите AR-связь')
    if not link_inst:
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        forms.alert(u'Связь не загружена.', exitscript=True)
        return

    link_levels = link_reader.select_levels_multi(
        link_doc,
        title=u'Выберите уровни из AR (будут созданы в текущем файле)',
        default_all=False
    )

    if not link_levels:
        return

    host_levels = link_reader.list_levels(doc)

    tol_ft = 1.0 / 304.8  # 1 мм
    created = 0
    skipped_name = 0
    skipped_elev = 0
    renamed = 0

    source_floor_plan = _pick_source_plan(doc, DB.ViewType.FloorPlan)
    source_ceiling_plan = _pick_source_plan(doc, DB.ViewType.CeilingPlan)

    created_floor = 0
    skipped_floor_exists = 0
    failed_floor = 0

    created_ceiling = 0
    skipped_ceiling_exists = 0
    failed_ceiling = 0

    view_names = _collect_view_names(doc)
    debug_lines = []

    with tx(u'ЭОМ: Копировать уровни из AR', doc=doc, swallow_warnings=True):
        for src in link_levels:
            src_name = _level_name(src)
            src_elev = _elev_ft(src)

            if _find_level_by_name(host_levels, src_name) is not None:
                skipped_name += 1
                continue

            if _find_level_by_elevation(host_levels, src_elev, tol_ft) is not None:
                skipped_elev += 1
                continue

            new_level = DB.Level.Create(doc, float(src_elev))
            if new_level is None:
                continue

            try:
                new_level.Name = src_name
            except Exception:
                try:
                    new_level.Name = src_name + u'_AR'
                    renamed += 1
                except Exception:
                    pass

            _try_copy_building_story(src, new_level)

            host_levels.append(new_level)
            created += 1

            _, floor_status = _create_plan_for_level(
                doc,
                new_level,
                source_floor_plan,
                DB.ViewType.FloorPlan,
                DB.ViewFamily.FloorPlan,
                view_names,
                debug_lines
            )
            if floor_status == u'created':
                created_floor += 1
            elif floor_status == u'exists':
                skipped_floor_exists += 1
            else:
                failed_floor += 1

            if source_ceiling_plan is not None:
                _, ceil_status = _create_plan_for_level(
                    doc,
                    new_level,
                    source_ceiling_plan,
                    DB.ViewType.CeilingPlan,
                    DB.ViewFamily.CeilingPlan,
                    view_names,
                    debug_lines
                )
                if ceil_status == u'created':
                    created_ceiling += 1
                elif ceil_status == u'exists':
                    skipped_ceiling_exists += 1
                else:
                    failed_ceiling += 1

    output.print_md(u'---')
    output.print_md(u'Создано уровней: **{}**'.format(created))
    output.print_md(u'Пропущено (дубликат имени): **{}**'.format(skipped_name))
    output.print_md(u'Пропущено (дубликат отметки ±1мм): **{}**'.format(skipped_elev))
    output.print_md(u'Переименовано (суффикс _AR): **{}**'.format(renamed))
    output.print_md(u'Создано планов этажа: **{}**'.format(created_floor))
    output.print_md(u'Пропущено планов этажа (уже есть): **{}**'.format(skipped_floor_exists))
    output.print_md(u'Не удалось создать планов этажа: **{}**'.format(failed_floor))
    output.print_md(u'Создано потолочных планов: **{}**'.format(created_ceiling))
    output.print_md(u'Не удалось создать потолочных планов: **{}**'.format(failed_ceiling))

    if debug_lines:
        output.print_md(u'---')
        output.print_md(u'## DEBUG (создание планов)')
        for ln in debug_lines[:20]:
            try:
                output.print_md(u'- {}'.format(ln))
            except Exception:
                pass

    forms.alert(
        u'Готово.\n'
        u'Создано уровней: {}\n'
        u'Создано планов этажа: {}\n'
        u'Создано потолочных планов: {}'.format(
            created, created_floor, created_ceiling
        ),
        title=u'Копировать уровни из AR',
        warn_icon=False
    )


if __name__ == '__main__':
    main()

