# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved
from utils_revit import alert, log_exception
from orchestrator import run_placement


doc = revit.doc
output = script.get_output()


def main():
    run_placement(doc, output, script)
    report_time_saved(output, 'lights_entrance_doors')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Place_Lights_EntranceDoors: error')
        alert('Ошибка. Подробности см. в журнале.')
