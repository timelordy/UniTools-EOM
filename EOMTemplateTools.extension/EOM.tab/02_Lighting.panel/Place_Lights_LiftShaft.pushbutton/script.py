# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved
from utils_revit import alert, log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    orchestrator.run_placement(doc, output, script)
    report_time_saved(output, 'lights_lift_shaft')

try:
    main()
except Exception:
    log_exception('Place lift shaft lights failed')
    alert('Инструмент завершился с ошибкой. Проверьте pyRevit Output.')
