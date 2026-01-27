# -*- coding: utf-8 -*-


def mm_to_ft(mm):
    return mm / 304.8


def ft_to_mm(ft):
    return ft * 304.8


def contains_any(text, patterns):
    if not text:
        return False
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)
