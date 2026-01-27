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
    try:
        target_path = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                '01_Placement.pulldown',
                '02_Kitchen_Unit.pushbutton',
                'script.py',
            )
        )
    except Exception:
        target_path = None

    try:
        if target_path and os.path.exists(target_path):
            target_dir = os.path.dirname(target_path)
            if target_dir in sys.path:
                sys.path.remove(target_dir)
            sys.path.insert(0, target_dir)
            try:
                sys.modules.pop('domain', None)
            except Exception:
                pass
            import imp
            mod = imp.load_source('kitchen_unit_unified', target_path)
            if hasattr(mod, 'main'):
                mod.main()
                return
    except Exception:
        log_exception('Error in unified kitchen script')
        return

    output.print_md('Unified script not found: {0}'.format(target_path))
    return

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 02_Kitchen_Unit')
