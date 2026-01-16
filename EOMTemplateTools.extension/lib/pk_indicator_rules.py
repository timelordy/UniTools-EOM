# -*- coding: utf-8 -*-


import re


def _norm(text):
    try:
        return (text or u"").strip().lower()
    except Exception:
        return u""


def match_any(text, keywords):
    """Return True if any keyword is found in text (case-insensitive)."""
    t = _norm(text)
    if not t:
        return False
    for kw in (keywords or []):
        k = _norm(kw)
        if k and (k in t):
            return True
    return False


def _tokenize(text):
    try:
        return re.findall(u"[0-9a-zа-яё]+", _norm(text))
    except Exception:
        return []


def _match_short_keyword(tokens, kw):
    for tok in tokens or []:
        if tok == kw:
            return True
        if tok.startswith(kw) and tok[len(kw):].isdigit():
            return True
    return False


def match_any_keyword(text, keywords):
    """Match keywords with special handling for short tokens like 'PK'/'ПК'."""
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


def is_hydrant_candidate(text, include_keywords, exclude_keywords=None):
    """Match include keywords and ensure exclude keywords are not present."""
    if not match_any_keyword(text, include_keywords):
        return False
    if exclude_keywords and match_any_keyword(text, exclude_keywords):
        return False
    return True
