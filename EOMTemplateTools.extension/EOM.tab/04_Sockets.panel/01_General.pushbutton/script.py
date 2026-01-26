# -*- coding: utf-8 -*-

import sys
import os

# Add lib path to sys.path
try:
    # .../01_General.pushbutton/script.py -> .../01_General.pushbutton -> .../04_Sockets.panel -> .../EOM.tab -> .../EOMTemplateTools.extension -> lib
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
    if created:
        report_time_saved(output, 'sockets_general', created)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 01_General')
