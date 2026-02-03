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
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    created = orchestrator.run(doc, output)
    try:
        from time_savings import set_room_count_override
        set_room_count_override('low_voltage', getattr(orchestrator, 'LAST_ROOM_COUNT', None))
    except Exception:
        pass
    report_time_saved(output, 'low_voltage', created)
    try:
        from time_savings import calculate_time_saved, calculate_time_saved_range
        minutes = calculate_time_saved('low_voltage', created)
        minutes_min, minutes_max = calculate_time_saved_range('low_voltage', created)
        global EOM_HUB_RESULT
        EOM_HUB_RESULT = {
            'stats': {'total': created, 'processed': created, 'skipped': 0, 'errors': 0},
            'time_saved_minutes': minutes,
            'time_saved_minutes_min': minutes_min,
            'time_saved_minutes_max': minutes_max,
            'placed': created,
        }
    except: pass

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 06_Low_Voltage')

