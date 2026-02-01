# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved, calculate_time_saved, calculate_time_saved_range
from utils_revit import alert, log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    res = orchestrator.run_placement(doc, output, script)
    created_lights = 0
    shafts = 0
    skipped = 0
    if isinstance(res, dict):
        created_lights = int(res.get('placed', 0) or 0)
        shafts = int(res.get('shafts', 0) or 0)
        skipped = int(res.get('skipped', 0) or 0)
    elif isinstance(res, int):
        created_lights = int(res)

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
