# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved, set_element_count, calculate_time_saved, calculate_time_saved_range
import orchestrator

def main():
    doc = revit.doc
    uidoc = revit.uidoc
    output = script.get_output()
    result = orchestrator.run_placement(doc, uidoc, output, script)
    placed = 0
    skipped = 0
    if isinstance(result, dict):
        try:
            placed = int(result.get('placed', 0) or 0)
            skipped = int(result.get('skipped', 0) or 0)
        except Exception:
            placed = 0
            skipped = 0

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
