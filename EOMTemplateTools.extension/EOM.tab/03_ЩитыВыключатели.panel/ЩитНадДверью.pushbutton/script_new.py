# -*- coding: utf-8 -*-
"""Размещение щитов ШК над входной дверью квартиры.

Entry point - тонкая обёртка для запуска orchestrator.

**Архитектура (Clean Architecture):**
- script.py (entry point) → вызывает orchestrator
- orchestrator.py (workflow coordination) → использует domain + adapters
- adapters.py (Revit API layer) → работает с Revit
- domain.py (business logic) → чистая логика без Revit API
"""

from pyrevit import revit, script
from utils_revit import alert, log_exception

# Импорт orchestrator
import orchestrator

# pyRevit context
doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# Global variable для интеграции с Hub
EOM_HUB_RESULT = None


def main():
    """Entry point для pyRevit."""
    try:
        global EOM_HUB_RESULT
        EOM_HUB_RESULT = orchestrator.run(doc, uidoc, output)
    except Exception:
        log_exception('Ошибка инструмента размещения щитов ШК')
        alert('Ошибка. Подробности смотрите в выводе pyRevit.')


if __name__ == '__main__':
    main()
