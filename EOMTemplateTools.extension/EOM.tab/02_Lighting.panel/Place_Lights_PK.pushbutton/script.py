# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved
from utils_revit import alert, log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    orchestrator.run_placement(doc, output, script)
    report_time_saved(output, 'lights_pk')

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('PK indicators failed')
        alert('Ошибка при размещении указателей ПК. См. лог pyRevit.')
