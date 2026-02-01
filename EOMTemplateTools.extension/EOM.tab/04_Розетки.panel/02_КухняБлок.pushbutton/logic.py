# -*- coding: utf-8 -*-

import domain
from pyrevit import DB
from utils_units import mm_to_ft
import socket_utils as su

def midpoint_between_projections_xy(pt1, pt2, p0, p1, end_clear=0.0, point_factory=None):
    if not pt1 or not pt2 or not p0 or not p1: return None
    proj1 = domain.closest_point_on_segment_xy(pt1, p0, p1)
    proj2 = domain.closest_point_on_segment_xy(pt2, p0, p1)
    if not proj1 or not proj2: return None
    
    mid_x = (proj1.X + proj2.X) * 0.5
    mid_y = (proj1.Y + proj2.Y) * 0.5
    mid_z = (proj1.Z + proj2.Z) * 0.5
    mid_pt = point_factory(mid_x, mid_y, mid_z) if point_factory else DB.XYZ(mid_x, mid_y, mid_z)
    
    dist_total = domain.dist_xy(p0, p1)
    if dist_total < 1e-6: return None
    
    final_proj = domain.closest_point_on_segment_xy(mid_pt, p0, p1)
    d_start = domain.dist_xy(p0, final_proj)
    d_end = domain.dist_xy(p1, final_proj)
    
    if d_start < end_clear or d_end < end_clear: return None
    return final_proj

def _nearest_segment_smart(pt, segs, other_pt=None):
    if not segs: return None, None, None
    best_any, proj_any, dist_any = domain.nearest_segment(pt, segs)
    if not other_pt:
        return best_any, proj_any, dist_any
    
    # Calc alignment direction
    align_dir = None
    try:
        v = other_pt - pt
        v_xy = DB.XYZ(v.X, v.Y, 0)
        if v_xy.GetLength() > 0.1:
            align_dir = v_xy.Normalize()
    except: pass
    
    if not align_dir:
        return best_any, proj_any, dist_any

    # Filter aligned
    aligned_segs = []
    for s in segs:
        p0, p1, wall = s
        try:
            v_seg = p1 - p0
            v_seg_xy = DB.XYZ(v_seg.X, v_seg.Y, 0)
            if v_seg_xy.GetLength() < 1e-6: continue
            v_seg_norm = v_seg_xy.Normalize()
            dot = v_seg_norm.DotProduct(align_dir)
            if abs(dot) > 0.5: # Parallel-ish
                aligned_segs.append(s)
        except: continue
        
    if aligned_segs:
        best_aligned, proj_aligned, dist_aligned = domain.nearest_segment(pt, aligned_segs)
        if dist_aligned is not None:
            try:
                tol = float(mm_to_ft(300))
            except Exception:
                tol = 0.0
            try:
                da = float(dist_any) if dist_any is not None else None
            except Exception:
                da = None

            # Prefer aligned wall only if it's not significantly worse than the closest one.
            if da is None or float(dist_aligned) <= (float(da) + float(tol)):
                return best_aligned, proj_aligned, dist_aligned

    return best_any, proj_any, dist_any

def get_candidates(segs, best_sink, best_stove, offset_sink_ft, offset_stove_ft, fixture_wall_max_dist_ft, wall_end_clear_ft):
    candidates = []
    # Use smart selection: if we have both sink and stove, use the other as reference for alignment
    seg_sink, proj_sink, d_sink = _nearest_segment_smart(best_sink, segs, other_pt=best_stove) if best_sink else (None, None, None)
    seg_stove, proj_stove, d_stove = _nearest_segment_smart(best_stove, segs, other_pt=best_sink) if best_stove else (None, None, None)

    # Guard: ignore walls that are too far from the fixture point
    try:
        max_d = float(fixture_wall_max_dist_ft) if fixture_wall_max_dist_ft is not None else None
    except Exception:
        max_d = None
    try:
        if max_d is not None and d_sink is not None and float(d_sink) > max_d:
            seg_sink, proj_sink = None, None
    except Exception:
        pass
    try:
        if max_d is not None and d_stove is not None and float(d_stove) > max_d:
            seg_stove, proj_stove = None, None
    except Exception:
        pass

    # 1. "Between" Candidate (Priority 0 - The Main Unit Socket)
    has_between = False
    if seg_sink and seg_stove:
        try:
            if seg_sink[2] and seg_stove[2] and seg_sink[2].Id == seg_stove[2].Id:
                pt_between = midpoint_between_projections_xy(
                    best_sink, best_stove, seg_sink[0], seg_sink[1],
                    end_clear=wall_end_clear_ft, point_factory=DB.XYZ
                )
                if pt_between:
                    candidates.append({'priority': 0, 'seg': seg_sink, 'pt': pt_between, 'kind': u'between'})
                    has_between = True
        except: pass

    # 2. Offset Candidates (Fallback if "Between" not possible or desired)
    # Only generated if we don't have a "between" candidate? 
    # The orchestrator can filter. We generate them just in case.
    
    def _add_offset_cand(src_pt, seg, offset, kind, priority):
        if not src_pt or not seg: return
        p0, p1, wall = seg
        proj = domain.closest_point_on_segment_xy(src_pt, p0, p1)
        if not proj: return
        
        seg_len = domain.dist_xy(p0, p1)
        if seg_len <= 1e-6: return
        t0 = domain.dist_xy(p0, proj) / seg_len
        dt = float(offset) / float(seg_len)
        
        # Try both directions
        for sgn in [-1, 1]:
            tt = t0 + sgn * dt
            if tt < 0.02 or tt > 0.98: continue # More lenient bounds
            
            # Check if this direction moves away from the OTHER fixture
            # REMOVED strict check to ensure we generate candidates even if "between" failed.
            # We just want valid points on the wall.
            
            try:
                pt = DB.XYZ(p0.X + (p1.X - p0.X)*tt, p0.Y + (p1.Y - p0.Y)*tt, proj.Z)
                candidates.append({'priority': priority, 'seg': seg, 'pt': pt, 'kind': kind})
                break # Only one per fixture
            except: pass

    if seg_sink: _add_offset_cand(best_sink, seg_sink, offset_sink_ft, 'sink', 1)
    if seg_stove: _add_offset_cand(best_stove, seg_stove, offset_stove_ft, 'stove', 2)

    return candidates, seg_sink, seg_stove, proj_sink, proj_stove

def get_perimeter_candidates(link_doc, segs, sink_pt, stove_pt, fridge_pt, count=2, min_spacing_ft=mm_to_ft(3000)):
    """
    Generates perimeter candidates.
    Excludes: 
    - Area between Sink and Stove (Headset).
    - Fridge area.
    - Doors/Windows.
    Enforces min_spacing_ft (default 3m = ~9.84ft).
    """
    candidates = []
    if not segs: return candidates
    
    # 1. Identify Walls and Exclusion Intervals
    wall_exclusions = {} # {wall_id: [(start, end), ...]}
    
    def add_excl(wid, s, e, L):
        if wid not in wall_exclusions: wall_exclusions[wid] = []
        # Clamp
        s = max(0.0, s); e = min(L, e)
        if s < e: wall_exclusions[wid].append((s, e))

    # Analyze Fixtures to block wall segments
    # Find nearest segments for fixtures using SMART selection
    s_sink, _, d_sink = _nearest_segment_smart(sink_pt, segs, other_pt=stove_pt) if sink_pt else (None, None, None)
    s_stove, _, d_stove = _nearest_segment_smart(stove_pt, segs, other_pt=sink_pt) if stove_pt else (None, None, None)
    s_fridge, _, d_fridge = domain.nearest_segment(fridge_pt, segs) if fridge_pt else (None, None, None)
    
    # Block Unit (Sink <-> Stove)
    if s_sink and s_stove and s_sink[2].Id == s_stove[2].Id:
        # Same wall
        w = s_sink[2]
        wid = w.Id.IntegerValue
        L = domain.dist_xy(s_sink[0], s_sink[1])
        
        proj_sink = domain.closest_point_on_segment_xy(sink_pt, s_sink[0], s_sink[1])
        proj_stove = domain.closest_point_on_segment_xy(stove_pt, s_sink[0], s_sink[1])
        
        d1 = domain.dist_xy(s_sink[0], proj_sink)
        d2 = domain.dist_xy(s_sink[0], proj_stove)
        
        # Block from min to max plus margins (e.g. 600mm)
        margin = mm_to_ft(600)
        start = min(d1, d2) - margin
        end = max(d1, d2) + margin
        add_excl(wid, start, end, L)
    else:
        # Different walls or missing one -> block individually
        margin = mm_to_ft(600)
        for s, pt in [(s_sink, sink_pt), (s_stove, stove_pt)]:
            if s and pt:
                wid = s[2].Id.IntegerValue
                L = domain.dist_xy(s[0], s[1])
                proj = domain.closest_point_on_segment_xy(pt, s[0], s[1])
                d = domain.dist_xy(s[0], proj)
                add_excl(wid, d - margin, d + margin, L)

    # Block Fridge
    if s_fridge:
        wid = s_fridge[2].Id.IntegerValue
        L = domain.dist_xy(s_fridge[0], s_fridge[1])
        proj = domain.closest_point_on_segment_xy(fridge_pt, s_fridge[0], s_fridge[1])
        d = domain.dist_xy(s_fridge[0], proj)
        margin = mm_to_ft(600)
        add_excl(wid, d - margin, d + margin, L)

    # Process Segments
    free_intervals = []
    
    for wall, curve, seg_len, p0, p1 in _iterate_segs(segs, link_doc):
        wid = wall.Id.IntegerValue
        blocked = wall_exclusions.get(wid, [])
        
        # Add corners exclusion (100mm)
        blocked.append((0.0, mm_to_ft(100)))
        blocked.append((seg_len - mm_to_ft(100), seg_len))
        
        # Add Windows/Doors
        ops = su._get_wall_openings_cached(link_doc, wall, {})
        for pt, w in ops.get('windows', []) + ops.get('doors', []):
            half = (float(w) * 0.5) if w else mm_to_ft(450)
            d0 = su._project_dist_on_curve_xy_ft(curve, seg_len, pt, tol_ft=2.0)
            if d0 is not None:
                m = mm_to_ft(100) # Margin
                blocked.append((d0 - half - m, d0 + half + m))
        
        # Merge and Invert
        merged = su._merge_intervals(blocked, 0.0, seg_len)
        allowed = su._invert_intervals(merged, 0.0, seg_len)
        
        for a, b in allowed:
            if (b - a) > mm_to_ft(300):
                free_intervals.append({
                    'wall': wall, 'curve': curve, 'seg_len': seg_len,
                    'start': a, 'end': b, 'len': (b - a),
                    'mid_pt': curve.Evaluate((a+b)/2/seg_len, True)
                })

    # Generate Candidates with Spacing Check
    if not free_intervals: return candidates
    
    # Sort by length descending
    free_intervals.sort(key=lambda x: x['len'], reverse=True)
    
    placed_pts = []
    
    def is_spaced(pt):
        for p in placed_pts:
            if domain.dist_xy(p, pt) < min_spacing_ft:
                return False
        return True

    # Try to place 'count' sockets
    # Heuristic: Try center of largest intervals first
    for interval in free_intervals:
        if len(candidates) >= count: break
        
        # Try center
        pt = interval['mid_pt']
        if is_spaced(pt):
            _add_cand_direct(candidates, interval['wall'], pt)
            placed_pts.append(pt)
            continue
            
        # If center failed or segment is huge, try 1/3 and 2/3
        if interval['len'] > min_spacing_ft * 1.5:
             # Try splitting
             p1 = interval['curve'].Evaluate((interval['start'] + interval['len']*0.33) / interval['seg_len'], True)
             if is_spaced(p1):
                 _add_cand_direct(candidates, interval['wall'], p1)
                 placed_pts.append(p1)
                 if len(candidates) >= count: break
                 
             p2 = interval['curve'].Evaluate((interval['start'] + interval['len']*0.66) / interval['seg_len'], True)
             if is_spaced(p2):
                 _add_cand_direct(candidates, interval['wall'], p2)
                 placed_pts.append(p2)

    return candidates

def _add_cand_direct(candidates, wall, pt):
    candidates.append({'pt': pt, 'wall': wall, 'kind': 'general'})

def _iterate_segs(segs, link_doc):
    for s in segs:
        p0, p1, wall = s
        try:
            line = DB.Line.CreateBound(p0, p1)
            yield wall, line, line.Length, p0, p1
        except: continue
