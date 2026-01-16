# -*- coding: utf-8 -*-

"""Units helpers.

Revit internal units are feet.
"""


MM_PER_FOOT = 304.8


def mm_to_ft(mm):
    if mm is None:
        return None
    return float(mm) / MM_PER_FOOT


def ft_to_mm(ft):
    if ft is None:
        return None
    return float(ft) * MM_PER_FOOT
