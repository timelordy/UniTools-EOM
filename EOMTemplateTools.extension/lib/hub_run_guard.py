# -*- coding: utf-8 -*-
"""Revit run guard хелперы (чистый Python)."""


def should_defer_run(has_doc, is_quiescent):
    """Вернуть True когда безопаснее отложить выполнение инструмента."""
    if not has_doc:
        return True
    if is_quiescent is False:
        return True
    return False
