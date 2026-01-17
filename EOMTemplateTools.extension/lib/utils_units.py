# -*- coding: utf-8 -*-

"""Units conversion helpers for Revit.

Revit internal units are feet.
This module provides conversion between millimeters and feet.

Example:
    >>> from utils_units import mm_to_ft, ft_to_mm
    >>> mm_to_ft(304.8)
    1.0
    >>> ft_to_mm(1.0)
    304.8
"""
from typing import Optional, Union


MM_PER_FOOT: float = 304.8


def mm_to_ft(mm: Optional[Union[float, int, str]]) -> Optional[float]:
    """Convert millimeters to feet.

    Args:
        mm: Value in millimeters. Can be float, int, or numeric string.
            If None, returns None.

    Returns:
        Value converted to feet, or None if input is None.

    Examples:
        >>> mm_to_ft(304.8)
        1.0
        >>> mm_to_ft(None)
        None
    """
    if mm is None:
        return None
    return float(mm) / MM_PER_FOOT


def ft_to_mm(ft: Optional[Union[float, int, str]]) -> Optional[float]:
    """Convert feet to millimeters.

    Args:
        ft: Value in feet. Can be float, int, or numeric string.
            If None, returns None.

    Returns:
        Value converted to millimeters, or None if input is None.

    Examples:
        >>> ft_to_mm(1.0)
        304.8
        >>> ft_to_mm(None)
        None
    """
    if ft is None:
        return None
    return float(ft) * MM_PER_FOOT
