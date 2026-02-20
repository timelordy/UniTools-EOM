# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved, set_element_count, calculate_time_saved, calculate_time_saved_range
import link_reader
import magic_context
import orchestrator

def main():
    doc = revit.doc
    uidoc = revit.uidoc
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

    placed = 0
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

            result = orchestrator.run_placement(doc, uidoc, output, script)
            if isinstance(result, dict):
                try:
                    placed += int(result.get('placed', 0) or 0)
                except Exception:
                    pass
                try:
                    skipped += int(result.get('skipped', 0) or 0)
                except Exception:
                    pass
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    set_element_count('lights_center', placed)
    report_time_saved(output, 'lights_center')

    # Report result to Hub (if running in Hub mode).
    try:
        time_saved_minutes = calculate_time_saved('lights_center', placed)
        time_saved_minutes_min, time_saved_minutes_max = calculate_time_saved_range('lights_center', placed)
        global EOM_HUB_RESULT
        EOM_HUB_RESULT = {
            'stats': {
                'total': placed,
                'processed': placed,
                'skipped': skipped,
                'errors': 0,
            },
            'time_saved_minutes': time_saved_minutes,
            'time_saved_minutes_min': time_saved_minutes_min,
            'time_saved_minutes_max': time_saved_minutes_max,
            'placed': placed,
            'skipped': skipped,
        }
    except Exception:
        pass

if __name__ == '__main__':
    main()
