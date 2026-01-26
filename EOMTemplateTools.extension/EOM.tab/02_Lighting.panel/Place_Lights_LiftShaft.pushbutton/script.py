# -*- coding: utf-8 -*-

from pyrevit import revit, script
from utils_revit import alert, log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    orchestrator.run_placement(doc, output, script)

try:
    main()
except Exception:
    log_exception('Place lift shaft lights failed')
    alert('Инструмент завершился с ошибкой. Проверьте pyRevit Output.')
