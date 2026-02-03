# -*- coding: utf-8 -*-

import os
import sys

# Add lib path to sys.path
try:
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
except Exception:
    pass

from pyrevit import revit, script
from utils_revit import log_exception
from time_savings import report_time_saved, calculate_time_saved, calculate_time_saved_range
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    try:
        created = orchestrator.run(doc, output)
    except Exception:
        log_exception('Error in 02_Kitchen_Unit')
        created = 0

    try:
        created = int(created or 0)
    except Exception:
        created = 0

    try:
        from time_savings import set_room_count_override
        set_room_count_override('kitchen_block', getattr(orchestrator, 'LAST_ROOM_COUNT', None))
    except Exception:
        pass

    report_time_saved(output, 'kitchen_block', created)

    try:
        minutes = calculate_time_saved('kitchen_block', created)
        minutes_min, minutes_max = calculate_time_saved_range('kitchen_block', created)
        global EOM_HUB_RESULT
        EOM_HUB_RESULT = {
            'stats': {'total': created, 'processed': created, 'skipped': 0, 'errors': 0},
            'time_saved_minutes': minutes,
            'time_saved_minutes_min': minutes_min,
            'time_saved_minutes_max': minutes_max,
            'placed': created,
        }
    except Exception:
        pass

if __name__ == '__main__':
    main()

