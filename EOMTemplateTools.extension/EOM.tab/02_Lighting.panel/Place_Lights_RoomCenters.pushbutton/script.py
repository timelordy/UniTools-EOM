# -*- coding: utf-8 -*-

from pyrevit import revit, script
import orchestrator

def main():
    doc = revit.doc
    uidoc = revit.uidoc
    output = script.get_output()
    orchestrator.run_placement(doc, uidoc, output, script)

if __name__ == '__main__':
    main()
