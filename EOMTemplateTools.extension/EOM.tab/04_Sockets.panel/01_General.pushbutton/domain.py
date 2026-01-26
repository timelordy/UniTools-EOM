# -*- coding: utf-8 -*-

import math
from utils_units import mm_to_ft
try:
    import socket_utils as su
except ImportError:
    import sys, os
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su

def compile_patterns(patterns):
    return su._compile_patterns(patterns)

def match_any(regex_list, text):
    return su._match_any(regex_list, text)

def is_hallway(text, patterns_rx):
    return match_any(patterns_rx, text)

def filter_rooms(raw_rooms, rules, apt_rx, public_rx, wet_rx, kitchen_rx, exclude_rx=None):
    filtered = []
    for r in raw_rooms:
        txt = su._room_text(r)
        if public_rx and match_any(public_rx, txt):
            continue
        if apt_rx and (not match_any(apt_rx, txt)):
            continue
        if match_any(wet_rx, txt):
            continue
        if su._room_is_wc(r, rules):
            continue
        if match_any(kitchen_rx, txt):
            continue
        if exclude_rx and match_any(exclude_rx, txt):
            continue
        filtered.append(r)
    return filtered

def calculate_allowed_path(link_doc, room, boundary_opts, avoid_door_ft, openings_cache):
    segs = su._get_room_outer_boundary_segments(room, boundary_opts)
    if not segs:
        return [], 0.0
    allowed_path = []
    effective_len_ft = 0.0
    for seg in segs:
        c = seg.GetCurve()
        if not c:
            continue
        seg_len = c.Length
        if seg_len < 1e-9:
            continue
        wall = link_doc.GetElement(seg.ElementId)
        if not wall:
            continue
        if su._is_curtain_wall(wall):
            continue
        ops = su._get_wall_openings_cached(link_doc, wall, openings_cache)
        if ops.get('windows'):
            continue
        blocked = []
        for pt, w in ops.get('doors', []):
            half = (float(w) * 0.5) if w else 1.5
            d0 = su._project_dist_on_curve_xy_ft(c, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                blocked.append((d0 - half - avoid_door_ft, d0 + half + avoid_door_ft))
        merged = su._merge_intervals(blocked, 0.0, seg_len)
        allowed = su._invert_intervals(merged, 0.0, seg_len)
        for a, b in allowed:
            if (b - a) > 1e-6:
                allowed_path.append((wall, c, seg_len, a, b))
                effective_len_ft += (b - a)
    return allowed_path, effective_len_ft

def generate_candidates_hallway(allowed_path, room_area_sqm):
    candidates = []
    target_count = 1 if room_area_sqm <= 10.0 else 2
    fine_candidates = []
    for w, c, sl, a, b in allowed_path:
        mid = (a + b) * 0.5
        pt = c.Evaluate(mid / sl, True)
        d = c.ComputeDerivatives(mid / sl, True)
        v = d.BasisX.Normalize()
        fine_candidates.append((w, pt, v, (b - a)))
    if not fine_candidates:
        return []
    if target_count == 1:
        fine_candidates.sort(key=lambda x: x[3], reverse=True)
        candidates.append(fine_candidates[0][:3])
    else:
        best_pair = None
        max_d = -1.0
        for i1 in range(len(fine_candidates)):
            for i2 in range(i1 + 1, len(fine_candidates)):
                d = su._dist_xy(fine_candidates[i1][1], fine_candidates[i2][1])
                if d > max_d:
                    max_d = d
                    best_pair = (fine_candidates[i1][:3], fine_candidates[i2][:3])
        if best_pair:
            candidates.extend(best_pair)
        else:
            candidates.append(fine_candidates[0][:3])
            if len(fine_candidates) > 1:
                candidates.append(fine_candidates[1][:3])
    return candidates

def generate_candidates_general(allowed_path, effective_len_ft, spacing_ft):
    candidates = []
    try:
        num = int(math.floor(effective_len_ft / spacing_ft))
    except:
        num = 0
    if num < 1:
        return []
    acc = 0.0
    path_idx = 0
    for k in range(1, num + 1):
        target_d = k * spacing_ft
        while path_idx < len(allowed_path):
            w, c, sl, a, b = allowed_path[path_idx]
            seg_len_eff = b - a
            if target_d <= (acc + seg_len_eff):
                local_d = a + (target_d - acc)
                pt = c.Evaluate(local_d / sl, True)
                d = c.ComputeDerivatives(local_d / sl, True)
                v = d.BasisX.Normalize()
                candidates.append((w, pt, v))
                break
            else:
                acc += seg_len_eff
                path_idx += 1
    return candidates
