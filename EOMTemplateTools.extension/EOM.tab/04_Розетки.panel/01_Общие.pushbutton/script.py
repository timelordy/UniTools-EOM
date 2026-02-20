# -*- coding: utf-8 -*-

import sys
import os

# Add lib path to sys.path
try:
    # .../01_General.pushbutton/script.py -> .../01_General.pushbutton -> .../04_Sockets.panel -> .../EOM.tab -> .../EOMTemplateTools.extension -> lib
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
except Exception:
    pass

try:
    tool_dir = os.path.dirname(os.path.abspath(__file__))
    if tool_dir in sys.path:
        sys.path.remove(tool_dir)
    sys.path.insert(0, tool_dir)
except Exception:
    pass

# Reset local modules cached from other socket commands in shared IronPython engine.
def _clear_local_modules():
    local_module_names = (
        'orchestrator',
        'adapters',
        'constants',
        'domain',
        'logic',
        'placement_engine',
        'config_loader',
        'validator',
    )
    for module_name in local_module_names:
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]
        except Exception:
            pass

_clear_local_modules()

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

    created = 0
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

            created += int(orchestrator.run(doc, output) or 0)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels

    try:
        from time_savings import set_room_count_override
        set_room_count_override('sockets_general', getattr(orchestrator, 'LAST_ROOM_COUNT', None))
    except Exception:
        pass
    if created:
        report_time_saved(output, 'sockets_general', created)
        try:
            from time_savings import calculate_time_saved, calculate_time_saved_range
            minutes = calculate_time_saved('sockets_general', created)
            minutes_min, minutes_max = calculate_time_saved_range('sockets_general', created)
            global EOM_HUB_RESULT
            EOM_HUB_RESULT = {
                'stats': {'total': created, 'processed': created, 'skipped': 0, 'errors': 0},
                'time_saved_minutes': minutes,
                'time_saved_minutes_min': minutes_min,
                'time_saved_minutes_max': minutes_max,
                'placed': created
            }
        except Exception:
            pass

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 01_General')
