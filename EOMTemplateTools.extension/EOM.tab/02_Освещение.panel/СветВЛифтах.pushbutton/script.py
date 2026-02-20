# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved, calculate_time_saved, calculate_time_saved_range
from utils_revit import alert, log_exception
import link_reader
import magic_context
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    pairs = link_reader.select_link_level_pairs(
        doc,
        link_title=u'Выберите связь(и) АР',
        level_title=u'Выберите уровни для обработки',
        default_all_links=True,
        default_all_levels=True,
        loaded_only=True
    )
    if not pairs:
        output.print_md('**Отменено (связи/уровни не выбраны).**')
        return

    created_lights = 0
    shafts = 0
    skipped = 0
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

            res = orchestrator.run_placement(doc, output, script)
            if isinstance(res, dict):
                created_lights += int(res.get('placed', 0) or 0)
                shafts += int(res.get('shafts', 0) or 0)
                skipped += int(res.get('skipped', 0) or 0)
            elif isinstance(res, int):
                created_lights += int(res)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    # Time is estimated per shaft; fall back to placed lights if shaft count is not available.
    time_count = shafts or created_lights
    report_time_saved(output, 'lights_elevator', time_count)
    try:
        minutes = calculate_time_saved('lights_elevator', time_count)
        minutes_min, minutes_max = calculate_time_saved_range('lights_elevator', time_count)
        global EOM_HUB_RESULT
        stats = {'total': created_lights, 'processed': created_lights, 'skipped': skipped, 'errors': 0}
        EOM_HUB_RESULT = {'stats': stats, 'placed': created_lights, 'shafts': shafts}
        if minutes > 0:
            EOM_HUB_RESULT['time_saved_minutes'] = minutes
            EOM_HUB_RESULT['time_saved_minutes_min'] = minutes_min
            EOM_HUB_RESULT['time_saved_minutes_max'] = minutes_max
    except: pass

try:
    main()
except Exception:
    log_exception('Place lift shaft lights failed')
    alert('Инструмент завершился с ошибкой. Проверьте pyRevit Output.')
