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

from pyrevit import revit, forms
from utils_revit import log_exception
import orchestrator
import adapters
import domain
import constants

def main():
    doc = revit.doc
    target_comment = constants.TARGET_COMMENT

    found = adapters.collect_sockets(doc, target_comment)
    if not found:
        forms.alert('Розетки с меткой {} не найдены.'.format(target_comment))
        return

    items = [domain.SocketItem(e, doc) for e in found]
    items.sort(key=lambda x: x.Name)

    win = orchestrator.MainWindow(items, doc)
    win.Show()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 98_ShowACSockets')
