# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved
from utils_revit import alert, log_exception
import link_reader
import magic_context
from orchestrator import run_placement


doc = revit.doc
output = script.get_output()


def main():
    pairs = link_reader.select_link_level_pairs(
        doc,
        link_title=u'Выберите связь(и) АР',
        level_title=u'Выберите уровни для обработки',
        default_all_links=True,
        default_all_levels=False,
        loaded_only=True
    )
    if not pairs:
        output.print_md('**Отменено (связи/уровни не выбраны).**')
        return

    total_placed = 0
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

            res = run_placement(doc, output, script)
            if isinstance(res, dict):
                total_placed += int(res.get('placed', 0) or 0)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    report_time_saved(output, 'lights_entrance_doors', total_placed)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Place_Lights_EntranceDoors: error')
        alert('Ошибка. Подробности см. в журнале.')
