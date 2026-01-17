 # -*- coding: utf-8 -*-
"""Pure text processing utilities (no Revit dependencies).

These functions are extracted for testability and reuse.
They handle text normalization, interval operations, and keyword matching.

Example:
    >>> from text_utils import norm, text_has_any_keyword
    >>> norm("  Hello World  ")
    'hello world'
    >>> text_has_any_keyword("Пожарный кран ПК", ["пк"])
    True
"""
import re
from typing import List, Optional, Tuple
 
 
def norm(text: Optional[str]) -> str:
    """Normalize text: strip whitespace and lowercase.

    Args:
        text: Input text to normalize. If None, returns empty string.

    Returns:
        Normalized lowercase string with stripped whitespace.

    Examples:
        >>> norm("  Hello World  ")
        'hello world'
        >>> norm(None)
        ''
    """
     try:
         return (text or u'').strip().lower()
     except Exception:
         return u''
 
 
def norm_type_key(s: Optional[str]) -> str:
    """Normalize family type name for comparison.

    Handles Cyrillic/Latin lookalikes, various dash types, whitespace normalization.
    Used for fuzzy matching of Revit family type names across different encodings.

    Args:
        s: Family type name string to normalize.

    Returns:
        Normalized string with underscores instead of spaces,
        Cyrillic chars replaced with Latin equivalents.

    Examples:
        >>> norm_type_key("TSL_EF Socket : Type 01")
        'tsl_ef_socket:type_01'
    """
     t = norm(s)
     if not t:
         return t
     
     # Replace various dash types with standard hyphen
     try:
         for ch in (u'–', u'—', u'‑', u'−'):
             t = t.replace(ch, u'-')
     except Exception:
         pass
     
     # Replace Cyrillic lookalikes with Latin equivalents
     try:
         repl = {
             u'а': u'a', u'в': u'b', u'е': u'e', u'з': u'3',
             u'к': u'k', u'м': u'm', u'н': u'h', u'о': u'o',
             u'р': u'p', u'с': u'c', u'т': u't', u'у': u'y',
             u'х': u'x', u'п': u'n'
         }
         for k, v in repl.items():
             t = t.replace(k, v)
     except Exception:
         pass
     
     # Common mixed variants in vendor naming
     try:
         t = t.replace(u'р3т', u'p3t')
         t = t.replace(u'рзт', u'p3t')
         t = t.replace(u'розет', u'p3t')
     except Exception:
         pass
     
     # Normalize whitespace and colons
     try:
         t = u' '.join(t.split())
         t = t.replace(u' : ', u':').replace(u' :', u':').replace(u': ', u':')
     except Exception:
         pass
     
     # Replace spaces and special chars with underscores
     try:
         for ch in (u' ', u'\t', u'\r', u'\n', u'-'):
             t = t.replace(ch, u'_')
         while u'__' in t:
             t = t.replace(u'__', u'_')
     except Exception:
         pass
     
     return t
 
 
def merge_intervals(
    intervals: List[Tuple[float, float]], lo: float, hi: float
) -> List[Tuple[float, float]]:
    """Merge overlapping intervals within [lo, hi] range.

    Args:
        intervals: List of (start, end) tuples representing intervals.
        lo: Lower bound of the range to consider.
        hi: Upper bound of the range to consider.

    Returns:
        List of merged (start, end) tuples within bounds, sorted by start.

    Examples:
        >>> merge_intervals([(1, 3), (2, 4)], 0, 10)
        [(1, 4)]
        >>> merge_intervals([(1, 2), (3, 4)], 0, 10)
        [(1, 2), (3, 4)]
    """
     out = []
     if hi <= lo:
         return out
     
     cleaned = []
     for a, b in intervals:
         if b < a:
             a, b = b, a
         if b <= lo or a >= hi:
             continue
         cleaned.append((max(lo, a), min(hi, b)))
     
     if not cleaned:
         return out
     
     cleaned.sort(key=lambda x: x[0])
     cur_a, cur_b = cleaned[0]
     
     for a, b in cleaned[1:]:
         if a <= cur_b + 1e-6:
             cur_b = max(cur_b, b)
         else:
             out.append((cur_a, cur_b))
             cur_a, cur_b = a, b
     
     out.append((cur_a, cur_b))
     return out
 
 
def invert_intervals(
    blocked: List[Tuple[float, float]], lo: float, hi: float
) -> List[Tuple[float, float]]:
    """Get free intervals by inverting blocked intervals within [lo, hi].

    Args:
        blocked: List of (start, end) blocked intervals.
            Should be sorted and non-overlapping for correct results.
        lo: Lower bound of the range.
        hi: Upper bound of the range.

    Returns:
        List of free (start, end) intervals not covered by blocked.

    Examples:
        >>> invert_intervals([(2, 4), (6, 8)], 0, 10)
        [(0, 2), (4, 6), (8, 10)]
    """
     out = []
     cur = lo
     
     for a, b in blocked:
         if a > cur + 1e-6:
             out.append((cur, a))
         cur = max(cur, b)
         if cur >= hi - 1e-6:
             break
     
     if cur < hi - 1e-6:
         out.append((cur, hi))
     
     return out
 
 
def text_has_any_keyword(norm_text: Optional[str], keys: Optional[List[str]]) -> bool:
    """Check if normalized text contains any keyword.

    Short keywords (<=2 chars) are matched as tokens, not substrings,
    to avoid false positives like 'пк' matching 'пкс'.

    Args:
        norm_text: Text to search in (will be normalized).
        keys: List of keywords to search for.

    Returns:
        True if any keyword is found in the text.

    Examples:
        >>> text_has_any_keyword("Пожарный кран ПК", ["пк"])
        True
        >>> text_has_any_keyword("ПКСМ", ["пк"])
        False
    """
     try:
         t = norm(norm_text)
     except Exception:
         t = u''
     
     if not t:
         return False
     
     key_norms = []
     for k in (keys or []):
         nk = norm(k)
         if nk:
             key_norms.append(nk)
     
     if not key_norms:
         return False
 
     tokens = None
     
     for nk in key_norms:
         # Short keys should match as a token
         if len(nk) <= 2:
             if tokens is None:
                 try:
                     tokens = re.findall(u'[a-zа-я0-9]+', t)
                 except Exception:
                     tokens = []
             if nk in tokens:
                 return True
             # Also allow BK1, BK2... patterns
             try:
                 for tok in tokens:
                     if tok.startswith(nk) and tok[len(nk):].isdigit():
                         return True
             except Exception:
                 pass
         else:
             if nk in t:
                 return True
     
     return False
