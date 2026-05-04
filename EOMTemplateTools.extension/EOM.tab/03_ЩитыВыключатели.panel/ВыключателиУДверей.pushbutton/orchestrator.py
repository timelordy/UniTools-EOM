# -*- coding: utf-8 -*-
"""Слой оркестрации для расстановки выключателей у дверей квартир."""

from pyrevit import DB, forms, revit, script
from time_savings import report_time_saved

from adapters import (
    calc_switch_position_with_debug,
    calc_switch_position_from_separation_line,
    get_closest_level,
    get_door_info,
    get_room_name,
    get_room_separation_lines,
    get_switch_symbol,
    is_entrance_door,
    place_switch,
    prefer_farther_candidate,
)
from domain import ft_to_mm
from room_policy import (
    is_non_apartment_room,
    is_skip_room,
    is_two_gang_room,
    is_wet_room,
    should_place_inside_room,
)
from room_selection import select_best_candidate_for_room
from switch_reporting import print_selection_debug, publish_single_link_summary


class AdapterPorts(object):
    """Application-level dependency port for geometry/symbol adapters."""

    def __init__(
        self,
        calc_switch_position_with_debug_fn,
        calc_switch_position_from_separation_line_fn,
        get_closest_level_fn,
        get_door_info_fn,
        get_room_name_fn,
        get_room_separation_lines_fn,
        get_switch_symbol_fn,
        is_entrance_door_fn,
        place_switch_fn,
        prefer_farther_candidate_fn,
    ):
        self.calc_switch_position_with_debug = calc_switch_position_with_debug_fn
        self.calc_switch_position_from_separation_line = calc_switch_position_from_separation_line_fn
        self.get_closest_level = get_closest_level_fn
        self.get_door_info = get_door_info_fn
        self.get_room_name = get_room_name_fn
        self.get_room_separation_lines = get_room_separation_lines_fn
        self.get_switch_symbol = get_switch_symbol_fn
        self.is_entrance_door = is_entrance_door_fn
        self.place_switch = place_switch_fn
        self.prefer_farther_candidate = prefer_farther_candidate_fn


class RuntimePorts(object):
    """Runtime dependency port for Revit/pyRevit integration APIs."""

    def __init__(self, db_module, forms_api, revit_api, script_api, report_time_saved_fn):
        self.DB = db_module
        self.forms = forms_api
        self.revit = revit_api
        self.script = script_api
        self.report_time_saved = report_time_saved_fn


def _default_adapter_ports():
    return AdapterPorts(
        calc_switch_position_with_debug_fn=calc_switch_position_with_debug,
        calc_switch_position_from_separation_line_fn=calc_switch_position_from_separation_line,
        get_closest_level_fn=get_closest_level,
        get_door_info_fn=get_door_info,
        get_room_name_fn=get_room_name,
        get_room_separation_lines_fn=get_room_separation_lines,
        get_switch_symbol_fn=get_switch_symbol,
        is_entrance_door_fn=is_entrance_door,
        place_switch_fn=place_switch,
        prefer_farther_candidate_fn=prefer_farther_candidate,
    )


def _default_runtime_ports():
    return RuntimePorts(
        db_module=DB,
        forms_api=forms,
        revit_api=revit,
        script_api=script,
        report_time_saved_fn=report_time_saved,
    )


def _mark_processed(processed_room_keys, room_key):
    if room_key:
        processed_room_keys.add(room_key)


def _get_room_key(link_inst, room_id):
    try:
        return u"{}::{}".format(link_inst.Id.IntegerValue, room_id)
    except Exception:
        return None


def _build_room_to_doors(doors, link_doc, link_transform, adapter_ports):
    room_to_doors = {}
    for door in doors:
        info = adapter_ports.get_door_info(door, link_doc, link_transform)
        for room in [info["from_room"], info["to_room"]]:
            if room and room.Id.IntegerValue not in room_to_doors:
                room_to_doors[room.Id.IntegerValue] = []
            if room:
                room_to_doors[room.Id.IntegerValue].append((door, info))
    return room_to_doors


def _place_switch_for_point(doc, symbol, point, rotation, adapter_ports):
    level = adapter_ports.get_closest_level(doc, point.Z)
    if not level:
        return False

    inst = adapter_ports.place_switch(doc, symbol, point, rotation, level)
    return bool(inst)


def _try_place_from_separation_line(
    doc,
    output,
    room,
    room_name,
    sep_line_info,
    link_transform,
    link_doc,
    sym_1g,
    sym_2g,
    created,
    adapter_ports,
):
    is_wet = is_wet_room(room_name)
    is_two_gang = is_two_gang_room(room_name)
    symbol = sym_2g if is_two_gang else sym_1g

    point, rotation = adapter_ports.calc_switch_position_from_separation_line(
        sep_line_info,
        room,
        link_transform,
        link_doc,
        place_inside_room=should_place_inside_room(room_name),
    )

    if created < 3 or "кухн" in room_name.lower():
        output.print_md(u"")
        output.print_md(u"**{}** (via Room Separation Line)".format(room_name))
        output.print_md(u"  line length: {:.0f}mm".format(ft_to_mm(sep_line_info["line_length"])))
        if point:
            output.print_md(u"  switch: ({:.0f}, {:.0f}, {:.0f}) mm".format(
                ft_to_mm(point.X), ft_to_mm(point.Y), ft_to_mm(point.Z)
            ))
        else:
            output.print_md(u"  switch: NONE (no wall found?)")

    if not point:
        return 0, 1, "SEPARATION_LINE_NO_POINT"

    if _place_switch_for_point(doc, symbol, point, rotation, adapter_ports):
        return 1, 0, None

    return 0, 1, "SEPARATION_LINE_PLACE_FAILED"


def _select_best_candidate_for_room(
    room,
    room_name,
    door_list,
    link_transform,
    link_doc,
    sym_1g,
    sym_2g,
    adapter_ports=None,
    diagnostics=None,
):
    if adapter_ports is None:
        adapter_ports = _default_adapter_ports()

    return select_best_candidate_for_room(
        room=room,
        room_name=room_name,
        door_list=door_list,
        link_transform=link_transform,
        link_doc=link_doc,
        sym_1g=sym_1g,
        sym_2g=sym_2g,
        adapter_ports=adapter_ports,
        diagnostics=diagnostics,
    )


def _print_selection_debug(
    output,
    created,
    room_name,
    is_wet,
    is_two_gang,
    best_info,
    debug_info,
    point,
    selected_candidate_index,
    link_transform,
):
    return print_selection_debug(
        output=output,
        created=created,
        room_name=room_name,
        is_wet=is_wet,
        is_two_gang=is_two_gang,
        best_info=best_info,
        debug_info=debug_info,
        point=point,
        selected_candidate_index=selected_candidate_index,
        link_transform=link_transform,
    )


_SKIP_REASON_LABELS = {
    "NO_DOORS_AND_NO_SEPARATION_LINES": u"нет дверей и Room Separation Line",
    "SEPARATION_LINE_NO_POINT": u"по Room Separation Line не найдена точка",
    "SEPARATION_LINE_PLACE_FAILED": u"точка найдена, но размещение по Room Separation Line не удалось",
    "NO_ENTRANCE_DOOR_IN_CORRIDOR": u"для коридора не найдена входная дверь",
    "NO_VALID_POINT_FOR_ENTRANCE_DOOR": u"для входной двери не удалось вычислить точку",
    "WET_ROOM_HAS_NO_CORRIDOR_ADJACENT_DOOR": u"у мокрой комнаты нет двери в коридор/прихожую",
    "NO_VALID_SWITCH_POINT_FOR_ANY_CANDIDATE": u"ни для одной двери не удалось вычислить точку",
    "ROOM_HAS_NO_DOORS": u"у комнаты нет дверей",
    "NO_CANDIDATE_SELECTED": u"подходящий кандидат не выбран",
    "SELECTION_WITHOUT_POINT": u"кандидат выбран, но точка выключателя отсутствует",
    "PLACE_SWITCH_FAILED": u"точка рассчитана, но экземпляр выключателя не создан",
}


def _skip_reason_label(reason_code):
    if not reason_code:
        return u"неизвестная причина"
    return _SKIP_REASON_LABELS.get(reason_code, reason_code)


def _print_room_skip_debug(output, room_name, room_id, reason_code, details=None):
    details = details or {}
    output.print_md(u"")
    output.print_md(
        u"⚠️ Пропуск: **{}** (id={}) — {}".format(
            room_name,
            room_id,
            _skip_reason_label(reason_code),
        )
    )

    detail_parts = []
    door_count = details.get("door_count")
    if door_count is not None:
        detail_parts.append(u"doors={}".format(door_count))

    wet_rejected = details.get("wet_rejected")
    if wet_rejected is not None:
        detail_parts.append(u"wet_rejected={}".format(wet_rejected))

    no_point_rejected = details.get("no_point_rejected")
    if no_point_rejected is not None:
        detail_parts.append(u"no_point_rejected={}".format(no_point_rejected))

    entrance_rejected = details.get("entrance_rejected")
    if entrance_rejected is not None:
        detail_parts.append(u"entrance_rejected={}".format(entrance_rejected))

    adjacent_rooms = details.get("adjacent_rooms") or []
    if adjacent_rooms:
        joined = u", ".join(adjacent_rooms)
        detail_parts.append(u"adjacent=[{}]".format(joined))

    if detail_parts:
        output.print_md(u"  details: {}".format(u"; ".join(detail_parts)))


def _run_multi_link_mode(doc, output, pairs, magic_context, rerun_fn):
    total_created = 0
    old_force = bool(getattr(magic_context, 'FORCE_SELECTION', False))
    old_link = getattr(magic_context, 'SELECTED_LINK', None)
    old_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
    old_levels = list(getattr(magic_context, 'SELECTED_LEVELS', []) or [])

    try:
        for pair in pairs:
            link_inst = pair.get('link_instance')
            levels = list(pair.get('levels') or [])
            if link_inst is None or not levels:
                continue

            try:
                link_name = link_inst.Name
            except Exception:
                link_name = u'<Связь>'
            output.print_md(u'## Обработка связи: `{0}`'.format(link_name))

            magic_context.FORCE_SELECTION = True
            magic_context.SELECTED_LINK = link_inst
            magic_context.SELECTED_LINKS = [link_inst]
            magic_context.SELECTED_LEVELS = levels

            total_created += int(rerun_fn() or 0)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    output.print_md(u'---')
    output.print_md(u'Итог по выбранным связям: **{}** выключателей'.format(total_created))
    return total_created


def _resolve_link_context(doc, link_reader, forms_api):
    link_inst = link_reader.select_link_instance_auto(doc)
    if not link_inst:
        forms_api.alert(u"Связь АР не найдена", exitscript=True)
        return None, None, None

    link_doc = link_inst.GetLinkDocument()
    if not link_doc:
        forms_api.alert(u"Связь не загружена", exitscript=True)
        return None, None, None

    link_transform = link_inst.GetTotalTransform()
    return link_inst, link_doc, link_transform


def _resolve_selected_level_ids(link_doc, link_reader):
    selected_levels = link_reader.select_levels_multi(link_doc, title=u"Выберите этажи")
    if not selected_levels:
        return None
    return {lvl.Id.IntegerValue for lvl in selected_levels}


def _safe_symbol_name(symbol, db):
    try:
        return symbol.get_Parameter(db.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except Exception:
        try:
            return str(symbol.Id.IntegerValue)
        except Exception:
            return u"<N/A>"


def _resolve_switch_symbols(doc, adapter_ports, forms_api, db):
    sym_1g = adapter_ports.get_switch_symbol(doc, two_gang=False)
    sym_2g = adapter_ports.get_switch_symbol(doc, two_gang=True)

    if not sym_1g:
        forms_api.alert(
            u"Не найден тип 1-кл выключателя.\n"
            u"Загрузите подходящее семейство или укажите тип в config/rules.default.json "
            u"(family_type_names.switch_1g).",
            exitscript=True,
        )
        return None, None, None, None
    if not sym_2g:
        sym_2g = sym_1g

    return sym_1g, sym_2g, _safe_symbol_name(sym_1g, db), _safe_symbol_name(sym_2g, db)


def _collect_rooms_and_doors(db, link_doc, selected_level_ids):
    rooms = [
        room for room in db.FilteredElementCollector(link_doc)
        .OfCategory(db.BuiltInCategory.OST_Rooms)
        if room.Area > 0 and room.LevelId.IntegerValue in selected_level_ids
    ]

    doors = list(
        db.FilteredElementCollector(link_doc)
        .OfCategory(db.BuiltInCategory.OST_Doors)
        .WhereElementIsNotElementType()
    )
    return rooms, doors


def _process_room(
    room,
    created,
    doc,
    output,
    link_inst,
    link_doc,
    link_transform,
    room_to_doors,
    processed_room_keys,
    sym_1g,
    sym_2g,
    adapter_ports,
):
    room_name = adapter_ports.get_room_name(room)
    room_id = room.Id.IntegerValue

    room_key = _get_room_key(link_inst, room_id)
    if room_key and room_key in processed_room_keys:
        return 0, 0

    if is_skip_room(room_name):
        _mark_processed(processed_room_keys, room_key)
        return 0, 0

    if is_non_apartment_room(room_name):
        _mark_processed(processed_room_keys, room_key)
        return 0, 0

    has_doors = room_id in room_to_doors and room_to_doors[room_id]
    use_separation_line = False
    sep_line_info = None

    if not has_doors:
        sep_lines = adapter_ports.get_room_separation_lines(link_doc, room, link_transform)
        if sep_lines:
            sep_line_info = max(sep_lines, key=lambda x: x["line_length"])
            use_separation_line = True
        else:
            _print_room_skip_debug(
                output,
                room_name,
                room_id,
                "NO_DOORS_AND_NO_SEPARATION_LINES",
                {"door_count": 0},
            )
            _mark_processed(processed_room_keys, room_key)
            return 0, 1

    door_list = room_to_doors.get(room_id, [])

    if use_separation_line:
        created_delta, skipped_delta, skip_reason = _try_place_from_separation_line(
            doc,
            output,
            room,
            room_name,
            sep_line_info,
            link_transform,
            link_doc,
            sym_1g,
            sym_2g,
            created,
            adapter_ports,
        )
        if skipped_delta > 0:
            _print_room_skip_debug(output, room_name, room_id, skip_reason)
        _mark_processed(processed_room_keys, room_key)
        return created_delta, skipped_delta

    selection_diagnostics = {}
    selection = _select_best_candidate_for_room(
        room,
        room_name,
        door_list,
        link_transform,
        link_doc,
        sym_1g,
        sym_2g,
        adapter_ports=adapter_ports,
        diagnostics=selection_diagnostics,
    )
    if not selection:
        _print_room_skip_debug(
            output,
            room_name,
            room_id,
            selection_diagnostics.get("skip_reason"),
            selection_diagnostics,
        )
        _mark_processed(processed_room_keys, room_key)
        return 0, 1

    point = selection["point"]
    _print_selection_debug(
        output,
        created,
        room_name,
        selection["is_wet"],
        selection["is_two_gang"],
        selection["best_info"],
        selection.get("debug_info"),
        point,
        selection["selected_candidate_index"],
        link_transform,
    )

    if not point:
        _print_room_skip_debug(output, room_name, room_id, "SELECTION_WITHOUT_POINT")
        _mark_processed(processed_room_keys, room_key)
        return 0, 1

    created_delta = 0
    skipped_delta = 0
    if _place_switch_for_point(doc, selection["symbol"], point, selection["rotation"], adapter_ports):
        created_delta = 1
    else:
        _print_room_skip_debug(output, room_name, room_id, "PLACE_SWITCH_FAILED")
        skipped_delta = 1

    _mark_processed(processed_room_keys, room_key)
    return created_delta, skipped_delta


def _publish_single_link_summary(output, created, skipped, runtime_ports):
    hub_result = publish_single_link_summary(
        output=output,
        created=created,
        skipped=skipped,
        report_time_saved_fn=runtime_ports.report_time_saved,
    )
    if hub_result is not None:
        global EOM_HUB_RESULT
        EOM_HUB_RESULT = hub_result


def _run_single_link_mode(doc, output, link_reader, magic_context, adapter_ports, runtime_ports):
    db = runtime_ports.DB
    forms_api = runtime_ports.forms
    output.print_md(u"# Размещение выключателей")

    link_inst, link_doc, link_transform = _resolve_link_context(doc, link_reader, forms_api)
    if not link_inst:
        return 0

    selected_level_ids = _resolve_selected_level_ids(link_doc, link_reader)
    if not selected_level_ids:
        return 0

    sym_1g, sym_2g, name_1g, name_2g = _resolve_switch_symbols(doc, adapter_ports, forms_api, db)
    if not sym_1g:
        return 0

    output.print_md(u"- 1-кл: `{}`".format(name_1g))
    output.print_md(u"- 2-кл: `{}`".format(name_2g))

    rooms, doors = _collect_rooms_and_doors(db, link_doc, selected_level_ids)

    output.print_md(u"- Комнат: **{}**, дверей: **{}**".format(len(rooms), len(doors)))

    room_to_doors = _build_room_to_doors(doors, link_doc, link_transform, adapter_ports)

    created = 0
    skipped = 0

    processed_room_keys = set()

    with db.Transaction(doc, u"ЭОМ: Выключатели") as t:
        t.Start()

        for room in rooms:
            created_delta, skipped_delta = _process_room(
                room,
                created,
                doc,
                output,
                link_inst,
                link_doc,
                link_transform,
                room_to_doors,
                processed_room_keys,
                sym_1g,
                sym_2g,
                adapter_ports,
            )
            created += created_delta
            skipped += skipped_delta

        t.Commit()

    _publish_single_link_summary(output, created, skipped, runtime_ports)

    if created > 0 and not bool(getattr(magic_context, 'FORCE_SELECTION', False)):
        forms_api.alert(u"Создано {} выключателей".format(created))

    return created


def run(adapter_ports=None, runtime_ports=None, link_reader_module=None, magic_context_module=None):
    if adapter_ports is None:
        adapter_ports = _default_adapter_ports()
    if runtime_ports is None:
        runtime_ports = _default_runtime_ports()
    if link_reader_module is None:
        import link_reader as link_reader_module
    if magic_context_module is None:
        import magic_context as magic_context_module

    doc = runtime_ports.revit.doc
    output = runtime_ports.script.get_output()

    if (
        not bool(getattr(magic_context_module, 'FORCE_SELECTION', False))
        and not bool(getattr(magic_context_module, 'IS_RUNNING', False))
    ):
        pairs = link_reader_module.select_link_level_pairs(
            doc,
            link_title=u'Выберите связь(и) АР',
            level_title=u'Выберите этажи',
            default_all_links=True,
            default_all_levels=False,
            loaded_only=True,
        )
        if not pairs:
            output.print_md('**Отменено (связи/уровни не выбраны).**')
            return 0

        def _rerun_single_mode():
            return run(
                adapter_ports=adapter_ports,
                runtime_ports=runtime_ports,
                link_reader_module=link_reader_module,
                magic_context_module=magic_context_module,
            )

        return _run_multi_link_mode(doc, output, pairs, magic_context_module, _rerun_single_mode)

    return _run_single_link_mode(
        doc,
        output,
        link_reader_module,
        magic_context_module,
        adapter_ports,
        runtime_ports,
    )


def main():
    return run()


if __name__ == "__main__":
    run()
