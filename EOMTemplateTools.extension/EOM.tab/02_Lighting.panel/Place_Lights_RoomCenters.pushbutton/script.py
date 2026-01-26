# -*- coding: utf-8 -*-

from pyrevit import revit, script
from time_savings import report_time_saved
import orchestrator

def main():
    doc = revit.doc
    uidoc = revit.uidoc
    output = script.get_output()
    orchestrator.run_placement(doc, uidoc, output, script)
    report_time_saved(output, 'lights_room')

if __name__ == '__main__':
    main()
