# -*- coding: utf-8 -*-


def norm(s):
    try:
        return (s or '').strip().lower()
    except Exception:
        return ''


def score_light_label(label):
    t = norm(label)
    if not t:
        return -999

    score = 0
    if 'eom' in t:
        score += 40

    return score


def score_light_keywords(text, strong, ceiling, point, negative):
    t = norm(text)
    if not t:
        return 0

    score = 0
    for kw in strong:
        if kw and (kw in t):
            score += 20
    for kw in ceiling:
        if kw and (kw in t):
            score += 30
    for kw in point:
        if kw and (kw in t):
            score += 25
    for kw in negative:
        if kw and (kw in t):
            score -= 80
    return score
