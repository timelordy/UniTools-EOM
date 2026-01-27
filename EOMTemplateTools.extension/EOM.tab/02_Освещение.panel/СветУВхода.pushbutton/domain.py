# -*- coding: utf-8 -*-

import math
from pyrevit import DB
from utils_units import mm_to_ft
from constants import (
    LIGHT_STRONG_KEYWORDS,
    LIGHT_EXTERIOR_KEYWORDS,
    LIGHT_NEGATIVE_KEYWORDS,
)
import placement_engine


def get_user_config(script_module):
    try:
        return script_module.get_config()
    except Exception:
        return None


def save_user_config(script_module):
    try:
        script_module.save_config()
        return True
    except Exception:
        return False


def norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def text_has_any(text, patterns):
    t = norm(text)
    if not t:
        return False
    for p in patterns or []:
        np = norm(p)
        if np and (np in t):
            return True
    return False


class PointGridIndex(object):
    def __init__(self, radius_ft):
        self.r = float(radius_ft or 0.0)
        self.r2 = self.r * self.r
        self.cell = self.r if self.r > 1e-9 else 1.0
        self._grid = {}

    def _key(self, p):
        try:
            return (
                int(math.floor(float(p.X) / self.cell)),
                int(math.floor(float(p.Y) / self.cell)),
                int(math.floor(float(p.Z) / self.cell)),
            )
        except Exception:
            return (0, 0, 0)

    def add(self, p):
        if p is None:
            return
        k = self._key(p)
        bucket = self._grid.get(k)
        if bucket is None:
            bucket = []
            self._grid[k] = bucket
        bucket.append(p)

    def add_many(self, pts):
        for p in pts or []:
            self.add(p)

    def is_near(self, p):
        if p is None or self.r <= 1e-9:
            return False
        k = self._key(p)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    kk = (k[0] + dx, k[1] + dy, k[2] + dz)
                    bucket = self._grid.get(kk)
                    if not bucket:
                        continue
                    for q in bucket:
                        try:
                            if float(p.DistanceTo(q)) <= self.r:
                                return True
                        except Exception:
                            continue
        return False


def score_light_symbol(symbol):
    try:
        label = placement_engine.format_family_type(symbol)
    except Exception:
        label = ''
    t = norm(label)
    if not t:
        return -999

    score = 0
    if 'eom' in t:
        score += 10

    for kw in LIGHT_STRONG_KEYWORDS:
        if norm(kw) in t:
            score += 20
    for kw in LIGHT_EXTERIOR_KEYWORDS:
        if norm(kw) in t:
            score += 15
    for kw in LIGHT_NEGATIVE_KEYWORDS:
        if norm(kw) in t:
            score -= 80

    return score


def score_room_outside(room, outside_patterns, inside_patterns, roof_patterns=None, room_matches_func=None):
    score = 0
    if room is None:
        score += 2
    if room_matches_func(room, outside_patterns):
        score += 2
    if roof_patterns and room_matches_func(room, roof_patterns):
        score += 3
    if room_matches_func(room, inside_patterns):
        score -= 1
    return score
