# -*- coding: utf-8 -*-
"""Fire hydrant (PK/ПК) indicator detection rules.

This module provides functions for detecting fire hydrant indicators
in Revit element names and descriptions, with special handling for
short Cyrillic/Latin keywords like 'ПК' (fire hydrant in Russian).

Example:
    >>> from pk_indicator_rules import is_hydrant_candidate
    >>> is_hydrant_candidate("Пожарный кран ПК-01", ["пк", "пожарн"])
    True
    >>> is_hydrant_candidate("ПКС переключатель", ["пк"], ["пкс"])
    False
"""
import re
from typing import List, Optional


def _norm(text: Optional[str]) -> str:
    """Normalize text to lowercase with stripped whitespace."""
    try:
        return (text or u"").strip().lower()
    except Exception:
        return u""


def match_any(text: Optional[str], keywords: Optional[List[str]]) -> bool:
    """Check if any keyword is found in text (case-insensitive substring match).

    Args:
        text: Text to search in.
        keywords: List of keywords to search for.

    Returns:
        True if any keyword is found as a substring in the text.

    Examples:
        >>> match_any("Fire hose cabinet", ["fire", "hydrant"])
        True
        >>> match_any("Radiator", ["fire", "hydrant"])
        False
    """
    t = _norm(text)
    if not t:
        return False
    for kw in (keywords or []):
        k = _norm(kw)
        if k and (k in t):
            return True
    return False


def _tokenize(text: str) -> List[str]:
    """Split text into alphanumeric tokens (Cyrillic and Latin)."""
    try:
        return re.findall(u"[0-9a-zа-яё]+", _norm(text))
    except Exception:
        return []


def _match_short_keyword(tokens: Optional[List[str]], kw: str) -> bool:
    """Match short keyword as exact token or token with numeric suffix."""
    for tok in tokens or []:
        if tok == kw:
            return True
        if tok.startswith(kw) and tok[len(kw):].isdigit():
            return True
    return False


def match_any_keyword(text: Optional[str], keywords: Optional[List[str]]) -> bool:
    """Match keywords with special handling for short tokens like 'PK'/'ПК'.

    Short keywords (<=2 chars) are matched as exact tokens or with numeric
    suffixes (e.g., 'ПК1', 'ПК-01') to avoid false positives.

    Args:
        text: Text to search in.
        keywords: List of keywords to search for.

    Returns:
        True if any keyword matches according to the rules.

    Examples:
        >>> match_any_keyword("ПК-01", ["пк"])
        True
        >>> match_any_keyword("ПКС", ["пк"])
        False
    """
    t = _norm(text)
    if not t:
        return False
    tokens = None
    for kw in (keywords or []):
        k = _norm(kw)
        if not k:
            continue
        if len(k) <= 2:
            if tokens is None:
                tokens = _tokenize(t)
            if _match_short_keyword(tokens, k):
                return True
        else:
            if k in t:
                return True
    return False


def is_hydrant_candidate(
    text: Optional[str],
    include_keywords: Optional[List[str]],
    exclude_keywords: Optional[List[str]] = None,
) -> bool:
    """Determine if text indicates a fire hydrant element.

    Matches include keywords and ensures exclude keywords are not present.
    Useful for filtering Revit elements by name/description.

    Args:
        text: Text to analyze (element name, description, etc.).
        include_keywords: Keywords that must be present.
        exclude_keywords: Keywords that must NOT be present.

    Returns:
        True if text matches include keywords and doesn't match exclude keywords.

    Examples:
        >>> is_hydrant_candidate("Пожарный кран ПК", ["пк", "пожарн"])
        True
        >>> is_hydrant_candidate("ПКС переключатель", ["пк"], ["пкс"])
        False
    """
    if not match_any_keyword(text, include_keywords):
        return False
    if exclude_keywords and match_any_keyword(text, exclude_keywords):
        return False
    return True
