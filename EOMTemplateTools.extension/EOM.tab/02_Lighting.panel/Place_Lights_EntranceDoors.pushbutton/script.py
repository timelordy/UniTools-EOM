# -*- coding: utf-8 -*-

from pyrevit import revit, script
from utils_revit import alert, log_exception
from orchestrator import run_placement


doc = revit.doc
output = script.get_output()


def main():
    run_placement(doc, output, script)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Place_Lights_EntranceDoors: error')
        alert('Ошибка. Подробности см. в журнале.')
