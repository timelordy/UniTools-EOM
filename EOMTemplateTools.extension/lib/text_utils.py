 # -*- coding: utf-8 -*-
 """Pure text processing utilities (no Revit dependencies).
 
 These functions are extracted for testability and reuse.
 """
 import re
 
 
 def norm(text):
     """Normalize text: strip whitespace and lowercase."""
     try:
         return (text or u'').strip().lower()
     except Exception:
         return u''
 
 
 def norm_type_key(s):
     """Normalize family type name for comparison.
     
     Handles Cyrillic/Latin lookalikes, various dash types, whitespace normalization.
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
 
 
 def merge_intervals(intervals, lo, hi):
     """Merge overlapping intervals within [lo, hi] range.
     
     Args:
         intervals: List of (start, end) tuples
         lo: Lower bound
         hi: Upper bound
         
     Returns:
         List of merged (start, end) tuples within bounds
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
 
 
 def invert_intervals(blocked, lo, hi):
     """Get free intervals by inverting blocked intervals within [lo, hi].
     
     Args:
         blocked: List of (start, end) blocked intervals (must be sorted and merged)
         lo: Lower bound
         hi: Upper bound
         
     Returns:
         List of free (start, end) intervals
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
 
 
 def text_has_any_keyword(norm_text, keys):
     """Check if normalized text contains any keyword.
     
     Short keywords (<=2 chars) are matched as tokens, not substrings,
     to avoid false positives like 'пк' in 'пкс'.
     
     Args:
         norm_text: Text to search in (will be normalized)
         keys: List of keywords to search for
         
     Returns:
         True if any keyword is found
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
