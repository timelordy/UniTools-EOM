# -*- coding: utf-8 -*-

import socket_utils as su
import domain
from utils_units import mm_to_ft

def validate_results(doc, plans, new_elems, validate_match_tol_ft, validate_height_tol_ft, validate_wall_dist_ft, validate_offset_tol_ft, clear_sink_ft, clear_stove_ft, t_inv=None):
    validation = []
    if not plans: return validation

    inst_items = []
    for e in (new_elems or []):
        pt = su._inst_center_point(e)
        if pt is None: continue
        try: iid = int(e.Id.IntegerValue)
        except: iid = None
        abs_z = None
        try: abs_z = su._get_abs_z_from_level_offset(e, doc)
        except: abs_z = None
        z_key = abs_z if abs_z is not None else float(pt.Z)
        inst_items.append((iid, e, pt, float(z_key)))

    used_inst = set()
    for pl in plans:
        exp_pt = pl.get('expected_pt_host')
        if exp_pt is None: continue
        try: exp_z = float(exp_pt.Z)
        except: exp_z = None

        best = None
        best_key = None
        best_dxy = None

        for iid, e, pt, z_key in inst_items:
            if iid in used_inst: continue
            dxy = domain.dist_xy(pt, exp_pt)
            if validate_match_tol_ft and dxy > validate_match_tol_ft: continue
            dz = abs(float(z_key) - float(exp_z)) if exp_z is not None else 0.0
            key = (float(dz), float(dxy))
            if best_key is None or key < best_key:
                best_key = key
                best_dxy = dxy
                best = (iid, e, pt)

        if best is None or best_dxy is None:
            validation.append({
                'status': 'missing',
                'room_id': pl.get('room_id'),
                'room_name': pl.get('room_name'),
            })
            continue

        iid, inst, inst_pt = best
        used_inst.add(iid)

        try: exp_z = float(pl['expected_pt_host'].Z)
        except: exp_z = float(inst_pt.Z)

        abs_z = None
        try: abs_z = su._get_abs_z_from_level_offset(inst, doc)
        except: abs_z = None
        z_to_check = abs_z if abs_z is not None else float(inst_pt.Z)
        height_ok = abs(float(z_to_check) - float(exp_z)) <= float(validate_height_tol_ft or mm_to_ft(20))

        try: inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
        except: inst_pt_link = inst_pt

        p0 = pl.get('seg_p0')
        p1 = pl.get('seg_p1')
        try: seg_len = domain.dist_xy(p0, p1) if p0 and p1 else 0.0
        except: seg_len = 0.0

        proj = domain.closest_point_on_segment_xy(inst_pt_link, p0, p1) if p0 and p1 else None
        dist_wall = domain.dist_xy(inst_pt_link, proj) if proj else None
        on_wall_ok = (dist_wall is not None) and (dist_wall <= float(validate_wall_dist_ft or mm_to_ft(150)))

        ti = None
        if proj and seg_len and seg_len > 1e-6:
            try: ti = domain.dist_xy(p0, proj) / seg_len
            except: ti = None

        wall_id = pl.get('wall_id')

        def _axis_dist_ft(axis_pt):
            if axis_pt is None: return None
            if not (p0 and p1) or (not seg_len) or seg_len <= 1e-6 or ti is None: return None
            proj_a = domain.closest_point_on_segment_xy(axis_pt, p0, p1)
            if proj_a is None: return None
            try: ta = domain.dist_xy(p0, proj_a) / seg_len
            except: return None
            try: return abs(float(ti) - float(ta)) * float(seg_len)
            except: return None

        sink_clear_ok = True
        stove_clear_ok = True
        sink_pt = pl.get('sink_pt')
        stove_pt = pl.get('stove_pt')

        if sink_pt is not None:
            sink_d = _axis_dist_ft(sink_pt) if (wall_id is not None and pl.get('sink_wall_id') == wall_id) else domain.dist_xy(inst_pt_link, sink_pt)
            sink_clear_ok = (sink_d + 1e-9) >= float(clear_sink_ft)
        if stove_pt is not None:
            stove_d = _axis_dist_ft(stove_pt) if (wall_id is not None and pl.get('stove_wall_id') == wall_id) else domain.dist_xy(inst_pt_link, stove_pt)
            stove_clear_ok = (stove_d + 1e-9) >= float(clear_stove_ft)

        offset_ok = True
        kind = pl.get('kind')
        want_offset = float(pl.get('offset_ft') or 0.0)
        if kind == u'sink' and sink_pt is not None:
            d = _axis_dist_ft(sink_pt) if (wall_id is not None and pl.get('sink_wall_id') == wall_id) else None
            if d is not None: offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))
        elif kind == u'stove' and stove_pt is not None:
            d = _axis_dist_ft(stove_pt) if (wall_id is not None and pl.get('stove_wall_id') == wall_id) else None
            if d is not None: offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))

        ok = bool(height_ok and on_wall_ok and sink_clear_ok and stove_clear_ok and offset_ok)
        validation.append({'status': 'ok' if ok else 'fail', 'id': iid, 'room_id': pl['room_id'], 'room_name': pl['room_name'], 'height_ok': bool(height_ok), 'on_wall_ok': bool(on_wall_ok), 'sink_clear_ok': bool(sink_clear_ok), 'stove_clear_ok': bool(stove_clear_ok), 'offset_ok': bool(offset_ok)})
    return validation