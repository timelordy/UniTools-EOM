# -*- coding: utf-8 -*-

import domain
from pyrevit import DB
from utils_units import mm_to_ft

def get_candidates(segs, best_sink, best_stove, offset_sink_ft, offset_stove_ft, fixture_wall_max_dist_ft, wall_end_clear_ft):
    candidates = []
    seg_sink, proj_sink, _ = domain.nearest_segment(best_sink, segs) if best_sink else (None, None, None)
    seg_stove, proj_stove, _ = domain.nearest_segment(best_stove, segs) if best_stove else (None, None, None)

    def _seg_dir(p0, p1):
        try:
            v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
            if v.GetLength() <= 1e-9: return None
            return v.Normalize()
        except: return None

    def _offset_candidates_for_fixture(src_pt, seg0, offset_ft, prefer_sign=None, priority=0, kind=u''):
        if src_pt is None or not seg0: return
        segs_try = []
        try: wid0 = int(seg0[2].Id.IntegerValue) if seg0[2] else None
        except: wid0 = None
        if wid0 is not None:
            for sg in segs or []:
                try:
                    if int(sg[2].Id.IntegerValue) == wid0: segs_try.append(sg)
                except: continue
        if not segs_try: segs_try = [seg0]

        scored = []
        for sg in segs_try:
            p0, p1, wall = sg
            proj = domain.closest_point_on_segment_xy(src_pt, p0, p1)
            if proj is None: continue
            try: dperp = domain.dist_xy(src_pt, proj)
            except: dperp = None
            if dperp is not None and fixture_wall_max_dist_ft and dperp > float(fixture_wall_max_dist_ft): continue
            scored.append((dperp if dperp is not None else 1e9, sg, proj))

        scored.sort(key=lambda x: x[0])
        for _dperp, sg, proj in scored:
            p0, p1, wall = sg
            try: seg_len = domain.dist_xy(p0, p1)
            except: seg_len = 0.0
            if seg_len <= 1e-6: continue
            try: t0 = domain.dist_xy(p0, proj) / seg_len
            except: continue
            dt = float(offset_ft or 0.0) / float(seg_len)
            if dt <= 1e-9: continue
            end_tol = float(wall_end_clear_ft or 0.0) / float(seg_len) if seg_len > 1e-6 else 0.0

            signs = []
            if prefer_sign in (-1, 1): signs = [int(prefer_sign), int(-prefer_sign)]
            else: signs = [-1, 1]

            added = False
            for sgn in signs:
                tt = float(t0) + float(sgn) * dt
                if tt < (0.0 + end_tol) or tt > (1.0 - end_tol): continue
                try:
                    pt = DB.XYZ(
                        float(p0.X) + (float(p1.X) - float(p0.X)) * tt,
                        float(p0.Y) + (float(p1.Y) - float(p0.Y)) * tt,
                        float(proj.Z)
                    )
                except: continue
                candidates.append({'priority': priority, 'seg': sg, 'pt': pt, 'kind': kind})
                added = True
            if added: break

    if seg_sink and proj_sink:
        _offset_candidates_for_fixture(best_sink, seg_sink, offset_sink_ft, priority=0, kind=u'sink')
    if seg_stove and proj_stove:
        _offset_candidates_for_fixture(best_stove, seg_stove, offset_stove_ft, priority=1, kind=u'stove')

    return candidates, seg_sink, seg_stove, proj_sink, proj_stove
