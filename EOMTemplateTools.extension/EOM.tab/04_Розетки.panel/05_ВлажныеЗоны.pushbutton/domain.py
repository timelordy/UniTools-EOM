# -*- coding: utf-8 -*-

import math
from pyrevit import DB
import socket_utils as su
import constants
from utils_units import mm_to_ft, ft_to_mm


class Fixture2D(object):
    __slots__ = ('element', 'center', 'bbox_min', 'bbox_max', 'kind')

    def __init__(self, element, center, bbox_min, bbox_max, kind=None):
        self.element = element
        self.center = center
        self.bbox_min = bbox_min
        self.bbox_max = bbox_max
        self.kind = kind or 'wm'


def fixture_priority(kind):
    k = (kind or '').lower()
    if 'boiler' in k or 'bk' in k:
        return 0
    if 'rail' in k:
        return 1
    if 'wm' in k or 'wash' in k:
        return 2
    if 'sink' in k:
        return 3
    if 'fallback' in k:
        return 9
    return 5


def get_room_boundary_segments_2d(room, boundary_opts):
    segs_2d = []
    if room is None:
        return segs_2d
    try:
        seglists = room.GetBoundarySegments(boundary_opts)
    except Exception:
        return segs_2d
    if not seglists:
        return segs_2d

    def _total_length(segs):
        total = 0.0
        for seg in segs:
            try:
                curve = seg.GetCurve()
                if curve:
                    total += float(curve.Length)
            except Exception:
                pass
        return total

    loop = max(seglists, key=_total_length)
    for seg in loop:
        try:
            curve = seg.GetCurve()
            if curve is None:
                continue
            wall = room.Document.GetElement(seg.ElementId)
            
            is_valid_bound = False
            if isinstance(wall, DB.Wall): is_valid_bound = True
            elif isinstance(wall, DB.FamilyInstance):
                try:
                    cat = wall.Category
                    if cat:
                        bic = cat.Id.IntegerValue
                        if bic in (int(DB.BuiltInCategory.OST_Columns), int(DB.BuiltInCategory.OST_StructuralColumns)):
                            is_valid_bound = True
                except: pass
            
            if not is_valid_bound:
                continue
                
            if isinstance(wall, DB.Wall) and su._is_curtain_wall(wall):
                continue
                
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            if not p0 or not p1:
                continue
            if p0.DistanceTo(p1) <= 1e-6:
                continue
            segs_2d.append((p0, p1, wall))
        except Exception:
            continue
    return segs_2d


def get_2d_bbox(element):
    if element is None:
        return None
    try:
        bb = element.get_BoundingBox(None)
        if not bb:
            return None
        return DB.XYZ(bb.Min.X, bb.Min.Y, 0.0), DB.XYZ(bb.Max.X, bb.Max.Y, 0.0)
    except Exception:
        return None


def segments_intersect(p1, p2, p3, p4, tol=1e-9):
    r = DB.XYZ(p2.X - p1.X, p2.Y - p1.Y, 0.0)
    s = DB.XYZ(p4.X - p3.X, p4.Y - p3.Y, 0.0)
    denom = r.X * s.Y - r.Y * s.X
    if abs(denom) < tol:
        return False, None, None, None
    qp = DB.XYZ(p3.X - p1.X, p3.Y - p1.Y, 0.0)
    t = (qp.X * s.Y - qp.Y * s.X) / denom
    u = (qp.X * r.Y - qp.Y * r.X) / denom
    if -tol <= t <= 1.0 + tol and -tol <= u <= 1.0 + tol:
        ix = p1.X + r.X * t
        iy = p1.Y + r.Y * t
        return True, t, u, DB.XYZ(ix, iy, p1.Z)
    return False, None, None, None


def closest_point_on_segment_xy(pt, a, b):
    if pt is None or a is None or b is None:
        return None
    abx = float(b.X) - float(a.X)
    aby = float(b.Y) - float(a.Y)
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return None
    apx = float(pt.X) - float(a.X)
    apy = float(pt.Y) - float(a.Y)
    t = (apx * abx + apy * aby) / denom
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return DB.XYZ(float(a.X) + abx * t, float(a.Y) + aby * t, float(pt.Z))


def raycast_to_walls(origin_pt, directions, wall_segments, max_distance_ft):
    hits = []
    if not wall_segments or not directions or max_distance_ft is None:
        return hits
    max_dist = float(max_distance_ft)
    for dir_vec in directions:
        dir_xy = DB.XYZ(dir_vec.X, dir_vec.Y, 0.0)
        try:
            length = dir_xy.GetLength()
        except Exception:
            length = None
        if not length or length <= 1e-6:
            continue
        dir_unit = dir_xy.Normalize()
        ray_end = DB.XYZ(
            origin_pt.X + dir_unit.X * max_dist,
            origin_pt.Y + dir_unit.Y * max_dist,
            origin_pt.Z
        )
        best_hit = None
        for p1, p2, wall in wall_segments:
            ok, t_ray, _, hit_pt = segments_intersect(origin_pt, ray_end, p1, p2)
            if not ok or t_ray is None or hit_pt is None:
                continue
            if t_ray < 0.0:
                continue
            dist = t_ray * max_dist
            if dist <= 1e-6:
                continue
            if dist > max_dist + 1e-6:
                continue
            wall_vec = DB.XYZ(p2.X - p1.X, p2.Y - p1.Y, 0.0)
            try:
                wall_len = wall_vec.GetLength()
            except Exception:
                wall_len = None
            if not wall_len or wall_len <= 1e-6:
                continue
            wall_dir = wall_vec.Normalize()
            if best_hit is None or dist < best_hit['distance']:
                best_hit = {
                    'distance': dist,
                    'point': DB.XYZ(hit_pt.X, hit_pt.Y, origin_pt.Z),
                    'wall': wall,
                    'wall_dir': wall_dir,
                    'seg_p1': p1,
                    'seg_p2': p2
                }
        if best_hit:
            hits.append(best_hit)
    return hits


def inward_normal_xy(wall_dir_xy, hit_pt_xy, room_center_xy):
    if wall_dir_xy is None or hit_pt_xy is None or room_center_xy is None:
        return None
    try:
        wd = DB.XYZ(float(wall_dir_xy.X), float(wall_dir_xy.Y), 0.0)
        if wd.GetLength() <= 1e-6:
            return None
        wd = wd.Normalize()
        n1 = DB.XYZ(0, 0, 1).CrossProduct(wd)  # left
        n2 = wd.CrossProduct(DB.XYZ(0, 0, 1))  # right
        to_c = DB.XYZ(float(room_center_xy.X - hit_pt_xy.X), float(room_center_xy.Y - hit_pt_xy.Y), 0.0)
        if to_c.GetLength() <= 1e-6:
            return n1.Normalize()
        to_c = to_c.Normalize()
        return n1.Normalize() if n1.Normalize().DotProduct(to_c) >= n2.Normalize().DotProduct(to_c) else n2.Normalize()
    except Exception:
        return None


def push_point_inside_room(room, pt, in_dir_xy=None, wall_dir_xy=None, room_center_xy=None, room_bb=None, z_test=None, max_push_mm=650):
    if room is None or pt is None:
        return pt
    z = None
    try:
        if z_test is not None:
            z = float(z_test)
    except Exception:
        z = None
    if z is None:
        try:
            if room_bb:
                z = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
        except Exception:
            z = None
    if z is None:
        try:
            z = float(pt.Z)
        except Exception:
            z = 0.0

    dir_in = None
    try:
        if wall_dir_xy is not None and room_center_xy is not None:
            dir_in = inward_normal_xy(wall_dir_xy, pt, room_center_xy)
    except Exception:
        dir_in = None

    if dir_in is None and in_dir_xy is not None:
        try:
            v = DB.XYZ(float(in_dir_xy.X), float(in_dir_xy.Y), 0.0)
            if v.GetLength() > 1e-6:
                dir_in = v.Normalize()
        except Exception:
            dir_in = None

    if dir_in is None and room_center_xy is not None:
        try:
            v = DB.XYZ(float(room_center_xy.X - pt.X), float(room_center_xy.Y - pt.Y), 0.0)
            if v.GetLength() > 1e-6:
                dir_in = v.Normalize()
        except Exception:
            dir_in = None

    if dir_in is None:
        return pt

    try:
        mmax = int(max_push_mm or 650)
    except Exception:
        mmax = 650
    mmax = max(mmax, 60)

    steps_mm = [20, 60, 120, 200, 300, 450, 650]
    out = pt
    for dmm in steps_mm:
        if dmm <= 0 or dmm > mmax:
            continue
        try:
            out = DB.XYZ(pt.X + dir_in.X * mm_to_ft(dmm), pt.Y + dir_in.Y * mm_to_ft(dmm), pt.Z)
            if is_point_in_room(room, DB.XYZ(float(out.X), float(out.Y), z)):
                return out
        except Exception:
            continue
    return out


def bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    x, y = float(pt.X), float(pt.Y)
    minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
    maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
    return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)


def dist_point_to_rect_xy(pt, r_min, r_max):
    if pt is None or r_min is None or r_max is None:
        return None
    try:
        px, py = float(pt.X), float(pt.Y)
        minx, miny = float(min(r_min.X, r_max.X)), float(min(r_min.Y, r_max.Y))
        maxx, maxy = float(max(r_min.X, r_max.X)), float(max(r_min.Y, r_max.Y))
        dx = max(minx - px, 0.0, px - maxx)
        dy = max(miny - py, 0.0, py - maxy)
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return None


def bbox_intersects_xy(bmin_a, bmax_a, bmin_b, bmax_b):
    if not all([bmin_a, bmax_a, bmin_b, bmax_b]):
        return False
    minx_a, maxx_a = sorted([bmin_a.X, bmax_a.X])
    miny_a, maxy_a = sorted([bmin_a.Y, bmax_a.Y])
    minx_b, maxx_b = sorted([bmin_b.X, bmax_b.X])
    miny_b, maxy_b = sorted([bmin_b.Y, bmax_b.Y])
    return not (maxx_a < minx_b or maxx_b < minx_a or maxy_a < miny_b or maxy_b < miny_a)


def expand_bbox_xy(bmin, bmax, buffer_ft):
    if bmin is None or bmax is None or buffer_ft is None:
        return bmin, bmax
    buf = float(buffer_ft)
    return (
        DB.XYZ(min(bmin.X, bmax.X) - buf, min(bmin.Y, bmax.Y) - buf, 0.0),
        DB.XYZ(max(bmin.X, bmax.X) + buf, max(bmin.Y, bmax.Y) + buf, 0.0)
    )


def is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        if room.IsPointInRoom(point):
            return True
    except Exception:
        pass
        
    # Manual check with BoundingBox (fast fail)
    try:
        bb = room.get_BoundingBox(None)
        if bb:
            if point.X < bb.Min.X - 1.0 or point.X > bb.Max.X + 1.0: return False
            if point.Y < bb.Min.Y - 1.0 or point.Y > bb.Max.Y + 1.0: return False
    except: pass

    # Check against segments (Ray casting or Polygon check)
    # Since we don't have full polygon geometry easily available here without heavy calculation,
    # rely on IsPointInRoom but try Z-adjustments
    
    # Try different Z heights?
    # Sometimes point is below floor or above ceiling
    try:
        # Check at +100mm, +500mm, +1500mm from base
        bb = room.get_BoundingBox(None)
        if bb:
            base_z = bb.Min.Z
            for offset_ft in [0.5, 1.5, 3.0, 5.0]:
                pt_z = DB.XYZ(point.X, point.Y, base_z + offset_ft)
                if room.IsPointInRoom(pt_z):
                    return True
    except: pass
    
    return False


def bbox_corners_xy(bmin, bmax):
    if bmin is None or bmax is None:
        return []
    minx = float(min(bmin.X, bmax.X))
    maxx = float(max(bmin.X, bmax.X))
    miny = float(min(bmin.Y, bmax.Y))
    maxy = float(max(bmin.Y, bmax.Y))
    return [
        DB.XYZ(minx, miny, 0.0),
        DB.XYZ(minx, maxy, 0.0),
        DB.XYZ(maxx, miny, 0.0),
        DB.XYZ(maxx, maxy, 0.0),
    ]


def bbox_interval_on_segment_ft(bmin, bmax, seg_p1, seg_p2):
    if bmin is None or bmax is None or seg_p1 is None or seg_p2 is None:
        return None, None, None, None
    try:
        v = DB.XYZ(float(seg_p2.X - seg_p1.X), float(seg_p2.Y - seg_p1.Y), 0.0)
        seg_len = float(v.GetLength())
        if seg_len <= 1e-6:
            return None, None, None, None
        seg_dir = v.Normalize()
    except Exception:
        return None, None, None, None

    try:
        corners = bbox_corners_xy(bmin, bmax)
        if not corners:
            return None, None, None, None
        svals = []
        for c in corners:
            dv = DB.XYZ(float(c.X - seg_p1.X), float(c.Y - seg_p1.Y), 0.0)
            svals.append(float(dv.DotProduct(seg_dir)))
        lo = max(0.0, min(svals))
        hi = min(seg_len, max(svals))
        return lo, hi, seg_dir, seg_len
    except Exception:
        return None, None, None, None


def wm_bbox_contains_point_on_segment_xy(pt_on_wall, bmin, bmax, seg_p1, seg_p2, tol_mm=30):
    if pt_on_wall is None:
        return False
    lo, hi, seg_dir, seg_len = bbox_interval_on_segment_ft(bmin, bmax, seg_p1, seg_p2)
    if lo is None or hi is None or seg_dir is None or seg_len is None:
        return False
    if hi - lo <= mm_to_ft(50):
        return False
    try:
        s_pt = DB.XYZ(float(pt_on_wall.X - seg_p1.X), float(pt_on_wall.Y - seg_p1.Y), 0.0).DotProduct(seg_dir)
    except Exception:
        return False
    try:
        tol = mm_to_ft(tol_mm or 30)
    except Exception:
        tol = mm_to_ft(30)
    return (s_pt >= (lo - tol)) and (s_pt <= (hi + tol))


def min_dist_to_rects_xy(pt_xy, rects):
    if pt_xy is None or not rects:
        return None
    best = None
    for bmin, bmax in rects or []:
        try:
            d = dist_point_to_rect_xy(pt_xy, bmin, bmax)
        except Exception:
            d = None
        if d is None:
            continue
        if best is None or d < best:
            best = d
    return best


def dist_xy(a, b):
    try:
        return ((float(a.X) - float(b.X)) ** 2 + (float(a.Y) - float(b.Y)) ** 2) ** 0.5
    except Exception:
        return 1e9


def points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []
    
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
        
    selected = []
    for pt in points:
        if pt is None:
            continue
            
        # Z adjust
        pt_room = pt
        try:
            if room_bb:
                zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), zmid)
        except Exception:
            pt_room = pt
            
        try:
            if room_bb:
                if not (room_bb.Min.X - padding_ft <= pt.X <= room_bb.Max.X + padding_ft and
                        room_bb.Min.Y - padding_ft <= pt.Y <= room_bb.Max.Y + padding_ft):
                    continue
        except Exception: pass
        
        try:
            if room.IsPointInRoom(pt_room):
                selected.append(pt)
        except: pass
        
    return selected


def get_wall_segments(room, link_doc):
    segs = []
    if room is None or link_doc is None:
        return segs
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglist = su._get_room_outer_boundary_segments(room, opts)
    except Exception:
        seglist = None
    if not seglist:
        return segs

    for bs in seglist:
        try:
            curve = bs.GetCurve()
        except Exception:
            curve = None
        if curve is None:
            continue
        try:
            eid = bs.ElementId
        except Exception:
            eid = DB.ElementId.InvalidElementId
        if not eid or eid == DB.ElementId.InvalidElementId:
            continue
        try:
            el = link_doc.GetElement(eid)
        except Exception:
            el = None
        if el is None or (not isinstance(el, DB.Wall)):
            continue
        try:
            if su._is_curtain_wall(el):
                continue
        except Exception:
            pass
        try:
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            if p0.DistanceTo(p1) <= 1e-6:
                continue
            segs.append((p0, p1, el))
        except Exception:
            continue
    return segs


def fixtures_in_room(fixtures_all, room):
    out = []
    if not fixtures_all or not room:
        return out
        
    for f in fixtures_all:
        if not f: continue
        
        # Primary check
        if is_point_in_room(room, f.center):
            out.append(f)
            continue
            
        # Fallback: Check surroundings (in case origin is on wall line)
        # Try 150mm offsets (approx 0.5 ft)
        offsets = [
            (0.5, 0.0), (-0.5, 0.0),
            (0.0, 0.5), (0.0, -0.5)
        ]
        found = False
        for dx, dy in offsets:
            try:
                pt_test = DB.XYZ(f.center.X + dx, f.center.Y + dy, f.center.Z)
                if is_point_in_room(room, pt_test):
                    found = True
                    break
            except: pass
            
        if found:
            out.append(f)
            
    return out


def generate_candidates(room, segs, fixtures, door_pts, rules):
    candidates = []
    if not room or not segs:
        return candidates

    # Prefer WM > Rail > Sink > Boiler
    # This is handled by orchestrator collecting them, but here we process.
    
    # 1. WM
    wms = [f for f in fixtures if f.kind == 'wm']
    # Safety: Filter out potential false positives (Sinks detected as WMs)
    wms = [f for f in wms if not any(x in su._elem_text(f.element).lower() for x in ['sink', 'раковин', 'мойк', 'умывал'])]
    
    for wm in wms:
        # Place near WM center, projected to wall
        proj_pt = None
        best_seg = None
        best_d = 1e9
        
        for p0, p1, wall in segs:
            pr = closest_point_on_segment_xy(wm.center, p0, p1)
            if pr:
                d = dist_xy(wm.center, pr)
                if d < best_d:
                    best_d = d
                    proj_pt = pr
                    best_seg = (p0, p1, wall)
        
        if proj_pt and best_seg and best_d < mm_to_ft(1000):
            candidates.append({
                'pt': proj_pt,
                'seg': best_seg,
                'kind': 'wm',
                'priority': 1
            })

    # 2. Boiler
    boilers = [f for f in fixtures if f.kind == 'boiler']
    for b in boilers:
        proj_pt = None
        best_seg = None
        best_d = 1e9
        for p0, p1, wall in segs:
            pr = closest_point_on_segment_xy(b.center, p0, p1)
            if pr:
                d = dist_xy(b.center, pr)
                if d < best_d:
                    best_d = d
                    proj_pt = pr
                    best_seg = (p0, p1, wall)
        if proj_pt and best_seg and best_d < mm_to_ft(1000):
            candidates.append({
                'pt': proj_pt,
                'seg': best_seg,
                'kind': 'boiler',
                'priority': 2
            })

    # 3. Towel Rail
    rails = [f for f in fixtures if f.kind == 'rail']
    for r in rails:
        proj_pt = None
        best_seg = None
        best_d = 1e9
        for p0, p1, wall in segs:
            pr = closest_point_on_segment_xy(r.center, p0, p1)
            if pr:
                d = dist_xy(r.center, pr)
                if d < best_d:
                    best_d = d
                    proj_pt = pr
                    best_seg = (p0, p1, wall)
        if proj_pt and best_seg and best_d < mm_to_ft(1000):
            candidates.append({
                'pt': proj_pt,
                'seg': best_seg,
                'kind': 'rail',
                'priority': 3
            })
            
    # 4. Sink (offset 600mm)
    # User request: "if there is no washing machine"
    if wms:
        sinks = []
    else:
        sinks = [f for f in fixtures if f.kind == 'sink']
    
    offset_mm = 600
    offset_ft = mm_to_ft(offset_mm)
    
    for s in sinks:
        # Check if sink is in "05_Wet" set (optional safeguard, though we filter rooms)
        # Find wall behind sink
        proj_pt = None
        best_seg = None
        best_d = 1e9
        
        # Try to determine back wall via orientation
        try:
            # Need to get Transform from element to get orientation in World coordinates if it's nested or rotated?
            # FacingOrientation is usually sufficient for instances.
            facing = s.element.FacingOrientation
            # Check HandOrientation too if needed? Usually Facing is "Forward" (away from wall).
            # So Back is -Facing.
            # Wall direction should be perpendicular to Facing.
            if abs(facing.Z) < 0.9: 
                facing = DB.XYZ(facing.X, facing.Y, 0.0).Normalize()
            else:
                 # If facing Z, maybe check rotation?
                 facing = None
        except:
            facing = None
            
        # Get Hand Orientation for side determination?
        try:
             hand = s.element.HandOrientation
             if abs(hand.Z) < 0.9:
                 hand = DB.XYZ(hand.X, hand.Y, 0.0).Normalize()
             else:
                 hand = None
        except:
             hand = None

        for p0, p1, wall in segs:
            pr = closest_point_on_segment_xy(s.center, p0, p1)
            if pr:
                d = dist_xy(s.center, pr)
                
                # Heuristic: Prefer wall behind the sink.
                if facing:
                    v_wall = DB.XYZ(p1.X - p0.X, p1.Y - p0.Y, 0.0)
                    if v_wall.GetLength() > 0.01:
                         v_wall = v_wall.Normalize()
                         # Wall should be perpendicular to Facing
                         # Dot(wall, facing) should be near 0.
                         if abs(v_wall.DotProduct(facing)) > 0.7: # > 45 deg
                             d += mm_to_ft(5000) # Penalty for side walls
                             
                    # Also check if wall is "Behind"
                    # Vector Sink->Proj should be roughly same direction as -Facing?
                    # Or Facing is usually OUT from wall.
                    # So Wall->Sink is Facing.
                    # Sink->Wall is -Facing.
                    v_to_wall = DB.XYZ(pr.X - s.center.X, pr.Y - s.center.Y, 0.0)
                    if v_to_wall.GetLength() > 0.01:
                        v_to_wall = v_to_wall.Normalize()
                        # Dot(v_to_wall, facing) should be negative (approx -1)
                        if v_to_wall.DotProduct(facing) > 0: # Pointing same way -> Wall is in front!
                             d += mm_to_ft(10000)

                if d < best_d:
                    best_d = d
                    proj_pt = pr
                    best_seg = (p0, p1, wall)
                    
        if proj_pt and best_seg and best_d < mm_to_ft(1000):
            p0, p1, wall = best_seg
            v = DB.XYZ(p1.X - p0.X, p1.Y - p0.Y, 0.0).Normalize()
            
            opts = []

            # Point 1 (Right)
            pt1 = DB.XYZ(proj_pt.X + v.X * offset_ft, proj_pt.Y + v.Y * offset_ft, proj_pt.Z)
            d1 = min(dist_xy(pt1, p0), dist_xy(pt1, p1))
            opts.append({'pt': pt1, 'dist': d1, 'kind': 'sink_right'})
            
            # Point 2 (Left)
            pt2 = DB.XYZ(proj_pt.X - v.X * offset_ft, proj_pt.Y - v.Y * offset_ft, proj_pt.Z)
            d2 = min(dist_xy(pt2, p0), dist_xy(pt2, p1))
            opts.append({'pt': pt2, 'dist': d2, 'kind': 'sink_left'})
            
            # Sort by distance to wall end (prefer further from corner)
            opts.sort(key=lambda x: x['dist'], reverse=True)
            
            for o in opts:
                candidates.append({
                    'pt': o['pt'],
                    'seg': best_seg,
                    'kind': o['kind'],
                    'priority': 4
                })

    return candidates


def collect_tagged_instances(host_doc, tag_value):
    ids = set()
    elems = []
    pts = []
    if host_doc is None or not tag_value:
        return ids, elems, pts

    for bic in (
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_Furniture,
    ):
        try:
            col = (
                DB.FilteredElementCollector(host_doc)
                .OfCategory(bic)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
            )
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                c = su._get_comments_text(e)
            except Exception:
                c = u''
            if not c:
                continue
            try:
                if tag_value not in c:
                    continue
            except Exception:
                continue

            try:
                ids.add(int(e.Id.IntegerValue))
            except Exception:
                pass
            elems.append(e)
            try:
                pt = su._inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    return ids, elems, pts
