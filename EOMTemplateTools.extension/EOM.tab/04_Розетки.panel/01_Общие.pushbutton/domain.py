# -*- coding: utf-8 -*-

import math
from utils_units import mm_to_ft, ft_to_mm
import constants
try:
    import socket_utils as su
except ImportError:
    import sys, os
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su

def _as_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    try:
        txt = (value or '').strip().lower()
    except Exception:
        return bool(default)
    if txt in ('1', 'true', 'yes', 'y', 'on', u'да'):
        return True
    if txt in ('0', 'false', 'no', 'n', 'off', u'нет'):
        return False
    return bool(default)


def _merge_patterns(default_patterns, custom_patterns):
    out = []
    try:
        for p in (default_patterns or []):
            if p and (p not in out):
                out.append(p)
    except Exception:
        pass

    if custom_patterns is None:
        return out

    try:
        if isinstance(custom_patterns, (list, tuple)):
            src = custom_patterns
        else:
            src = [custom_patterns]
    except Exception:
        src = []

    for p in src:
        try:
            if p and (p not in out):
                out.append(p)
        except Exception:
            continue
    return out


def build_wall_filter(rules):
    rules = rules or {}
    exterior_patterns = _merge_patterns(
        constants.DEFAULT_EXTERIOR_WALL_PATTERNS,
        rules.get('socket_general_exterior_wall_name_patterns'),
    )
    facade_patterns = _merge_patterns(
        constants.DEFAULT_FACADE_WALL_PATTERNS,
        rules.get('socket_general_facade_wall_name_patterns', rules.get('socket_general_exterior_wall_name_patterns')),
    )
    monolith_patterns = _merge_patterns(
        constants.DEFAULT_MONOLITH_WALL_PATTERNS,
        rules.get('socket_general_monolith_wall_name_patterns'),
    )
    skip_exterior = _as_bool(
        rules.get('socket_general_skip_exterior_walls', constants.DEFAULT_SKIP_EXTERIOR_WALLS),
        constants.DEFAULT_SKIP_EXTERIOR_WALLS,
    )
    skip_facade = _as_bool(
        rules.get('socket_general_skip_facade_walls', constants.DEFAULT_SKIP_FACADE_WALLS),
        constants.DEFAULT_SKIP_FACADE_WALLS,
    )
    exterior_by_geom = _as_bool(
        rules.get('socket_general_exterior_by_boundary_geometry', constants.DEFAULT_EXTERIOR_BY_BOUNDARY_GEOMETRY),
        constants.DEFAULT_EXTERIOR_BY_BOUNDARY_GEOMETRY,
    )
    exterior_requires_openings = _as_bool(
        rules.get('socket_general_exterior_requires_openings', constants.DEFAULT_EXTERIOR_REQUIRES_OPENINGS),
        constants.DEFAULT_EXTERIOR_REQUIRES_OPENINGS,
    )
    try:
        exterior_min_seg_ft = float(mm_to_ft(float(rules.get('socket_general_exterior_min_segment_mm', constants.DEFAULT_EXTERIOR_MIN_SEGMENT_MM)) or 0.0) or 0.0)
    except Exception:
        exterior_min_seg_ft = float(mm_to_ft(constants.DEFAULT_EXTERIOR_MIN_SEGMENT_MM) or 0.0)
    return {
        'skip_exterior': skip_exterior,
        'skip_facade': skip_facade,
        'exterior_by_geom': exterior_by_geom,
        'exterior_requires_openings': exterior_requires_openings,
        'exterior_min_seg_ft': exterior_min_seg_ft,
        'skip_monolith': _as_bool(rules.get('socket_general_skip_monolith_walls', constants.DEFAULT_SKIP_MONOLITH_WALLS), constants.DEFAULT_SKIP_MONOLITH_WALLS),
        'skip_structural': _as_bool(rules.get('socket_general_skip_structural_walls', constants.DEFAULT_SKIP_STRUCTURAL_WALLS), constants.DEFAULT_SKIP_STRUCTURAL_WALLS),
        'exterior_rx': compile_patterns(exterior_patterns),
        'facade_rx': compile_patterns(facade_patterns),
        'monolith_rx': compile_patterns(monolith_patterns),
    }


def new_general_breakdown():
    return {
        'wall_perimeter_ft': 0.0,
        'minus_kzh_ft': 0.0,
        'minus_exterior_ft': 0.0,
        'minus_openings_ft': 0.0,
        'allowed_ft': 0.0,
    }


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

def calculate_allowed_path(
    link_doc,
    room,
    boundary_opts,
    avoid_door_ft,
    openings_cache,
    window_offset_ft=0.0,
    corner_offset_ft=0.0,
    wall_filter=None,
    breakdown=None,
):
    segs = su._get_room_outer_boundary_segments(room, boundary_opts)
    if not segs:
        return [], 0.0
    if wall_filter is None:
        wall_filter = build_wall_filter(None)
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
        if not su._is_wall_element(wall):
            continue
        try:
            if breakdown is not None:
                breakdown['wall_perimeter_ft'] = float(breakdown.get('wall_perimeter_ft', 0.0) or 0.0) + float(seg_len or 0.0)
        except Exception:
            pass
        is_outer_boundary = False
        try:
            if wall_filter.get('exterior_by_geom', True):
                is_outer_boundary = bool(su._is_room_outer_boundary_segment(link_doc, room, c))
        except Exception:
            is_outer_boundary = False
        if su._is_curtain_wall(wall):
            try:
                if breakdown is not None:
                    key = 'minus_exterior_ft' if is_outer_boundary else 'minus_kzh_ft'
                    breakdown[key] = float(breakdown.get(key, 0.0) or 0.0) + float(seg_len or 0.0)
            except Exception:
                pass
            continue
        try:
            if wall_filter.get('skip_facade') and su._is_facade_wall(
                wall,
                patterns_rx=wall_filter.get('facade_rx') or wall_filter.get('exterior_rx'),
            ):
                try:
                    if breakdown is not None:
                        breakdown['minus_exterior_ft'] = float(breakdown.get('minus_exterior_ft', 0.0) or 0.0) + float(seg_len or 0.0)
                except Exception:
                    pass
                continue
        except Exception:
            pass
        try:
            if wall_filter.get('skip_structural') and su._is_structural_wall(wall):
                try:
                    if breakdown is not None:
                        breakdown['minus_kzh_ft'] = float(breakdown.get('minus_kzh_ft', 0.0) or 0.0) + float(seg_len or 0.0)
                except Exception:
                    pass
                continue
        except Exception:
            pass
        try:
            if wall_filter.get('skip_monolith') and su._is_monolith_wall(wall, patterns_rx=wall_filter.get('monolith_rx')):
                try:
                    if breakdown is not None:
                        breakdown['minus_kzh_ft'] = float(breakdown.get('minus_kzh_ft', 0.0) or 0.0) + float(seg_len or 0.0)
                except Exception:
                    pass
                continue
        except Exception:
            pass
        ops = su._get_wall_openings_cached(link_doc, wall, openings_cache)
        exterior_filtered = bool(is_outer_boundary)
        try:
            if exterior_filtered and wall_filter.get('exterior_requires_openings', False):
                has_openings = bool((ops.get('doors') or []) or (ops.get('windows') or []))
                if not has_openings:
                    exterior_filtered = False
        except Exception:
            pass
        try:
            min_seg_ft = float(wall_filter.get('exterior_min_seg_ft', 0.0) or 0.0)
        except Exception:
            min_seg_ft = 0.0
        if exterior_filtered and (seg_len < min_seg_ft):
            exterior_filtered = False
        try:
            if wall_filter.get('skip_exterior') and exterior_filtered:
                try:
                    if breakdown is not None:
                        breakdown['minus_exterior_ft'] = float(breakdown.get('minus_exterior_ft', 0.0) or 0.0) + float(seg_len or 0.0)
                except Exception:
                    pass
                continue
        except Exception:
            pass
        blocked = []
        blocked_openings = []
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
                a = d0 - half - avoid_door_ft
                b = d0 + half + avoid_door_ft
                blocked.append((a, b))
                blocked_openings.append((a, b))
        for pt, w in ops.get('windows', []):
            half = (float(w) * 0.5) if w else 2.0
            d0 = su._project_dist_on_curve_xy_ft(c, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                a = d0 - half - window_offset
                b = d0 + half + window_offset
                blocked.append((a, b))
                blocked_openings.append((a, b))
        try:
            if breakdown is not None:
                merged_openings = su._merge_intervals(blocked_openings, 0.0, seg_len)
                minus_ops = 0.0
                for aa, bb in merged_openings:
                    minus_ops += (bb - aa)
                breakdown['minus_openings_ft'] = float(breakdown.get('minus_openings_ft', 0.0) or 0.0) + float(minus_ops)
        except Exception:
            pass
        if corner_offset > 1e-6:
            blocked.append((0.0, corner_offset))
            blocked.append((seg_len - corner_offset, seg_len))
        merged = su._merge_intervals(blocked, 0.0, seg_len)
        allowed = su._invert_intervals(merged, 0.0, seg_len)
        for a, b in allowed:
            if (b - a) > 1e-6:
                allowed_path.append((wall, c, seg_len, a, b))
                effective_len_ft += (b - a)
    try:
        if breakdown is not None:
            breakdown['allowed_ft'] = float(effective_len_ft or 0.0)
    except Exception:
        pass
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
        # Avoid extra socket on exact multiples caused by tiny geometry floating errors.
        eps = float(mm_to_ft(1.0) or 0.0)
        ratio = (eff - eps) / spacing if eff > eps else (eff / spacing)
        num = int(math.ceil(ratio))
    except Exception:
        return 0, 0.0

    if num < 1 and eff > 1e-9:
        num = 1
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


def format_room_socket_breakdown(room_label, breakdown, spacing_ft, count):
    try:
        label = (room_label or u'').strip()
    except Exception:
        label = u''

    b = breakdown or {}
    try:
        perim_ft = float(b.get('wall_perimeter_ft', 0.0) or 0.0)
    except Exception:
        perim_ft = 0.0
    try:
        minus_kzh_ft = float(b.get('minus_kzh_ft', 0.0) or 0.0)
    except Exception:
        minus_kzh_ft = 0.0
    try:
        minus_ext_ft = float(b.get('minus_exterior_ft', 0.0) or 0.0)
    except Exception:
        minus_ext_ft = 0.0
    try:
        minus_ops_ft = float(b.get('minus_openings_ft', 0.0) or 0.0)
    except Exception:
        minus_ops_ft = 0.0
    try:
        base_ft = float(b.get('allowed_ft', 0.0) or 0.0)
    except Exception:
        base_ft = 0.0

    try:
        spacing = float(spacing_ft or 0.0)
    except Exception:
        spacing = 0.0
    raw = (base_ft / spacing) if spacing > 1e-9 else 0.0

    perim_m = ft_to_mm(perim_ft) / 1000.0
    minus_kzh_m = ft_to_mm(minus_kzh_ft) / 1000.0
    minus_ext_m = ft_to_mm(minus_ext_ft) / 1000.0
    minus_ops_m = ft_to_mm(minus_ops_ft) / 1000.0
    base_m = ft_to_mm(base_ft) / 1000.0
    spacing_m = ft_to_mm(spacing) / 1000.0 if spacing > 1e-9 else 0.0

    try:
        if abs(spacing_m - round(spacing_m)) < 1e-6:
            divisor_txt = str(int(round(spacing_m)))
        else:
            divisor_txt = '{0:.2f}'.format(spacing_m)
    except Exception:
        divisor_txt = '?'

    return u'Комната: {0}; периметр: {1:.2f} м; -КЖ: {2:.2f} м; -наружные: {3:.2f} м; -окна/двери: {4:.2f} м; ({5:.2f} м / {6}) = {7:.2f}; розеток: {8}'.format(
        label, perim_m, minus_kzh_m, minus_ext_m, minus_ops_m, base_m, divisor_txt, raw, int(count or 0)
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
