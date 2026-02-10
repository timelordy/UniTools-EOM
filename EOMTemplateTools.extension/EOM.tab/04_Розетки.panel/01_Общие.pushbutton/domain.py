# -*- coding: utf-8 -*-

import math
from utils_units import mm_to_ft, ft_to_mm
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


def is_wardrobe(text, patterns_rx):
    return match_any(patterns_rx, text)


def is_sliding_door_text(text, patterns_rx):
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

def calculate_allowed_path(link_doc, room, boundary_opts, avoid_door_ft, openings_cache, window_offset_ft=0.0, corner_offset_ft=0.0):
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
        blocked = []
        try:
            window_offset = float(window_offset_ft or 0.0)
        except Exception:
            window_offset = 0.0
        try:
            corner_offset = float(corner_offset_ft or 0.0)
        except Exception:
            corner_offset = 0.0
        for pt, w in ops.get('doors', []):
            half = (float(w) * 0.5) if w else 1.5
            d0 = su._project_dist_on_curve_xy_ft(c, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                blocked.append((d0 - half - avoid_door_ft, d0 + half + avoid_door_ft))
        for pt, w in ops.get('windows', []):
            half = (float(w) * 0.5) if w else 2.0
            d0 = su._project_dist_on_curve_xy_ft(c, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                blocked.append((d0 - half - window_offset, d0 + half + window_offset))
        if corner_offset > 1e-6:
            blocked.append((0.0, corner_offset))
            blocked.append((seg_len - corner_offset, seg_len))
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


def should_skip_wardrobe(room_area_sqm, room_text, wardrobe_rx, min_area_sqm=10.0):
    try:
        area = float(room_area_sqm or 0.0)
    except Exception:
        area = 0.0
    try:
        min_area = float(min_area_sqm or 0.0)
    except Exception:
        min_area = 0.0

    if area >= min_area:
        return False
    return bool(is_wardrobe(room_text, wardrobe_rx))


def is_point_near_sliding_doors(pt, doors, extra_ft=0.0):
    if not pt or not doors:
        return False
    try:
        extra = float(extra_ft or 0.0)
    except Exception:
        extra = 0.0
    for dpt, half_w in doors:
        if dpt is None:
            continue
        try:
            half = float(half_w or 0.0)
        except Exception:
            half = 0.0
        if su._dist_xy(pt, dpt) <= (half + extra):
            return True
    return False

def calc_general_socket_count_and_step(effective_len_ft, spacing_ft):
    try:
        eff = float(effective_len_ft)
    except Exception:
        eff = 0.0
    try:
        spacing = float(spacing_ft)
    except Exception:
        spacing = 0.0

    if eff <= 1e-9 or spacing <= 1e-9:
        return 0, 0.0

    try:
        num = int(math.ceil(eff / spacing))
    except Exception:
        return 0, 0.0

    if num < 1:
        return 0, 0.0

    step = eff / float(num)
    return num, step


def calc_general_socket_count_and_step_for_lengths(count_len_ft, allowed_len_ft, spacing_ft):
    """Count sockets using count_len_ft; compute placement step using allowed_len_ft."""
    num, _ = calc_general_socket_count_and_step(count_len_ft, spacing_ft)
    if num < 1:
        return 0, 0.0
    try:
        allowed = float(allowed_len_ft)
    except Exception:
        allowed = 0.0
    if allowed <= 1e-9:
        return 0, 0.0
    return num, allowed / float(num)


def format_room_socket_summary(room_label, effective_len_ft, count, step_ft, is_hallway=False, room_area_sqm=None):
    try:
        label = (room_label or u'').strip()
    except Exception:
        label = u''

    try:
        perim_m = ft_to_mm(effective_len_ft) / 1000.0
    except Exception:
        perim_m = None

    perim_txt = '{0:.2f}'.format(perim_m) if perim_m is not None else '?'
    cnt = int(count or 0)

    if is_hallway:
        try:
            area_txt = '{0:.1f}'.format(float(room_area_sqm))
        except Exception:
            area_txt = '?'
        return u'Комната: {0}; периметр: {1} м; розеток: {2} (по площади {3} м²); шаг: не применяется'.format(
            label, perim_txt, cnt, area_txt
        )

    try:
        step_m = ft_to_mm(step_ft) / 1000.0
    except Exception:
        step_m = None
    step_txt = '{0:.2f}'.format(step_m) if step_m is not None else '?'
    return u'Комната: {0}; периметр: {1} м; розеток: {2}; шаг: {3} м'.format(
        label, perim_txt, cnt, step_txt
    )

def generate_candidates_general(allowed_path, effective_len_ft, spacing_ft):
    candidates = []
    num, step = calc_general_socket_count_and_step(effective_len_ft, spacing_ft)
    if num < 1 or step <= 1e-9:
        return []
    try:
        eff = float(effective_len_ft)
    except Exception:
        eff = 0.0
    if eff <= 1e-9:
        return []

    acc = 0.0
    path_idx = 0
    for k in range(1, num + 1):
        target_d = k * step
        if target_d > eff:
            target_d = eff
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


def generate_candidates_general_with_count(allowed_path, allowed_len_ft, count):
    candidates = []
    try:
        num = int(count or 0)
    except Exception:
        num = 0
    if num < 1:
        return []
    try:
        eff = float(allowed_len_ft)
    except Exception:
        eff = 0.0
    if eff <= 1e-9:
        return []
    step = eff / float(num)
    if step <= 1e-9:
        return []

    acc = 0.0
    path_idx = 0
    for k in range(1, num + 1):
        target_d = k * step
        if target_d > eff:
            target_d = eff
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
