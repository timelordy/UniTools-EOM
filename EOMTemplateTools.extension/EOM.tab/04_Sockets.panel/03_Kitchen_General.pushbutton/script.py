# -*- coding: utf-8 -*-

import sys
import os

# Add lib path to sys.path
try:
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
except Exception:
    pass

from pyrevit import revit, script
from utils_revit import log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    orchestrator.run(doc, output)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 03_Kitchen_General')
