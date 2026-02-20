# -*- coding: utf-8 -*-

import sys
import os

# Add lib path to sys.path
try:
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
except Exception:
    pass

from pyrevit import revit, script
from utils_revit import log_exception
from time_savings import report_time_saved
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
        default_all_levels=False,
        loaded_only=True
    )
    if not pairs:
        output.print_md('**Отменено (связи/уровни не выбраны).**')
        return

    combined_created = {}
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

            created = orchestrator.run(doc, output) or {}
            if isinstance(created, dict):
                combined_created.update(created)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    if combined_created:
        total_elements = 0
        for room_data in combined_created.values():
            if room_data.get('created'):
                total_elements += 1
        report_time_saved(output, 'storage_equipment', total_elements)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 08_Кладовые')
