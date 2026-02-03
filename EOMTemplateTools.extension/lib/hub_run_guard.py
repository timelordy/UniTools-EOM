# -*- coding: utf-8 -*-
"""Revit run guard helpers (pure Python)."""


def should_defer_run(has_doc, is_quiescent):
    """Return True when it is safer to defer tool execution."""
    if not has_doc:
        return True
    if is_quiescent is False:
        return True
    return False
