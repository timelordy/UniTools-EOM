# -*- coding: utf-8 -*-
"""
Script 04: AC Socket Placement
AUTO_EOM:SOCKET_AC
"""
import math
import re
import sys
import os

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

# Add lib path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
import config_loader
import link_reader
import socket_utils
import utils_revit
import utils_units


def _collect_ac_sockets(doc, comment_substr):
    ids = set()
    elems = []
    if not doc or not comment_substr:
        return ids, elems
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        try:
            col = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for e in col:
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                s = p.AsString() if p else None
                if s and (comment_substr in s):
                    ids.add(int(e.Id.IntegerValue))
                    elems.append(e)
            except Exception:
                continue
    return ids, elems


def _safe_inst_point(e):
    try:
        return socket_utils._inst_center_point(e)
    except Exception:
        return None


def _build_point_index(elems):
    idx = socket_utils._XYZIndex(cell_ft=1.0)
    for e in (elems or []):
        pt = _safe_inst_point(e)
        if pt is None:
            continue
        try:
            idx.add(pt.X, pt.Y, pt.Z)
        except Exception:
            pass
    return idx


def _expected_host_point_on_face(link_inst, t, wall_link, pt_link, faces_cache, prefer_n_link=None):
    """Return the host-space point that placement will actually use (projected to wall face when possible)."""
    if not t or pt_link is None:
        return None
    try:
        _r, proj_pt_link, _nn = socket_utils._get_linked_wall_face_ref_and_point(
            wall_link, link_inst, pt_link, faces_cache=faces_cache, prefer_n_link=prefer_n_link
        )
        if proj_pt_link is not None:
            return t.OfPoint(proj_pt_link)
    except Exception:
        pass
    try:
        return t.OfPoint(pt_link)
    except Exception:
        return None


def _dedupe_elems_by_xy(elems, tol_ft):
    if not elems:
        return []
    try:
        tol = float(tol_ft or 0.0)
    except Exception:
        tol = 0.0
    if tol <= 1e-9:
        return list(elems)

    kept = []
    pts = []
    for e in elems:
        if not e:
            continue
        pt = None
        try:
            pt = socket_utils._inst_center_point(e)
        except Exception:
            pt = None
        if pt is None:
            kept.append(e)
            continue

        dup = False
        for p in pts:
            try:
                if _dist_xy(pt, p) <= tol:
                    dup = True
                    break
            except Exception:
                continue

        if dup:
            continue
        pts.append(pt)
        kept.append(e)

    return kept


def _inst_host_wall(inst):
    if inst is None:
        return None
    try:
        h = getattr(inst, 'Host', None)
    except Exception:
        h = None
    if h is not None and isinstance(h, DB.Wall):
        return h
    return None


def _inst_wall_side_sign(inst, wall, eps_ft=None):
    """Return +1/-1 for which side of `wall` the instance center is on (host coords)."""
    if inst is None or wall is None:
        return None

    pt = None
    try:
        pt = socket_utils._inst_center_point(inst)
    except Exception:
        pt = None
    if pt is None:
        return None

    proj = _wall_axis_project_xy(pt, wall) or pt
    wdir = _wall_dir_xy(wall)
    if wdir is None:
        return None

    try:
        n = DB.XYZ(-float(wdir.Y), float(wdir.X), 0.0)
        n = n.Normalize() if n.GetLength() > 1e-9 else None
    except Exception:
        n = None
    if n is None:
        return None

    if eps_ft is None:
        try:
            eps_ft = utils_units.mm_to_ft(5)
        except Exception:
            eps_ft = 0.0

    d = None
    try:
        v = DB.XYZ(float(pt.X) - float(proj.X), float(pt.Y) - float(proj.Y), 0.0)
        d = float(v.DotProduct(n))
    except Exception:
        d = None

    if d is not None and abs(float(d)) > float(eps_ft or 0.0):
        return 1 if float(d) >= 0.0 else -1

    # Fallback: use facing orientation if point is too close to the axis
    try:
        fo = getattr(inst, 'FacingOrientation', None)
        if fo is not None:
            f2 = DB.XYZ(float(fo.X), float(fo.Y), 0.0)
            if f2.GetLength() > 1e-9:
                f2 = f2.Normalize()
                d2 = float(f2.DotProduct(n))
                if abs(d2) > 1e-6:
                    return 1 if d2 >= 0.0 else -1
    except Exception:
        pass

    return 1


def _cleanup_ac_sockets_same_side_duplicates(doc, comment_substr, spacing_ft, z_tol_ft=None):
    if doc is None:
        return 0
    try:
        spacing = float(spacing_ft or 0.0)
    except Exception:
        spacing = 0.0
    if spacing <= 1e-9:
        return 0

    try:
        ztol = float(z_tol_ft) if z_tol_ft is not None else float(utils_units.mm_to_ft(500))
    except Exception:
        ztol = float(utils_units.mm_to_ft(500))

    _ids, elems = _collect_ac_sockets(doc, comment_substr)
    if not elems:
        return 0

    # Cache host walls for assigning nearest wall to non-hosted instances
    walls_with_bb = []
    try:
        wcol = DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType()
        for w in wcol:
            bb = None
            try:
                bb = w.get_BoundingBox(None)
            except Exception:
                bb = None
            walls_with_bb.append((w, bb))
    except Exception:
        walls_with_bb = []

    groups = {}
    dir_items = []
    for e in elems:
        if not e:
            continue
        pt = None
        try:
            pt = socket_utils._inst_center_point(e)
        except Exception:
            pt = None
        if pt is None:
            continue

        # Collect for directional duplicate cleanup (works for linked-face hosted sockets too)
        fdir = None
        try:
            fo = getattr(e, 'FacingOrientation', None)
            if fo is not None:
                v = DB.XYZ(float(fo.X), float(fo.Y), 0.0)
                fdir = v.Normalize() if v.GetLength() > 1e-9 else None
        except Exception:
            fdir = None
        dir_items.append((pt, fdir, e))

        wall = _inst_host_wall(e)
        if wall is None and walls_with_bb:
            try:
                wall = _nearest_wall_to_point(walls_with_bb, pt, prefer_interior=False, max_dist_ft=utils_units.mm_to_ft(600))
            except Exception:
                wall = None
        if wall is None:
            continue

        try:
            wid = int(wall.Id.IntegerValue)
        except Exception:
            continue

        sgn = _inst_wall_side_sign(e, wall)
        if sgn not in (-1, 1):
            sgn = 1

        try:
            proj = _wall_axis_project_xy(pt, wall) or pt
            wdir = _wall_dir_xy(wall)
            if wdir is None:
                wdir = DB.XYZ.BasisX
            wdir2 = DB.XYZ(float(wdir.X), float(wdir.Y), 0.0)
            wdir2 = wdir2.Normalize() if wdir2.GetLength() > 1e-9 else DB.XYZ.BasisX
            along = float(proj.X) * float(wdir2.X) + float(proj.Y) * float(wdir2.Y)
        except Exception:
            along = 0.0

        key = (wid, int(sgn))
        groups.setdefault(key, []).append((along, pt, e))

    to_delete = set()
    for _k, items in groups.items():
        try:
            items = sorted(items, key=lambda x: float(x[0]))
        except Exception:
            pass

        keep_pt = None
        keep_z = None
        for _along, pt, e in items:
            if keep_pt is None:
                keep_pt = pt
                try:
                    keep_z = float(pt.Z)
                except Exception:
                    keep_z = None
                continue

            try:
                dz = abs(float(pt.Z) - float(keep_z)) if (keep_z is not None) else 0.0
            except Exception:
                dz = 0.0

            if dz <= float(ztol) and _dist_xy(pt, keep_pt) <= float(spacing):
                try:
                    to_delete.add(e.Id)
                except Exception:
                    continue
                continue

            keep_pt = pt
            try:
                keep_z = float(pt.Z)
            except Exception:
                keep_z = None

    # Fallback/extra: remove duplicates by proximity + same facing direction (covers linked-face hosted instances)
    try:
        cell = max(1.0, float(spacing))
    except Exception:
        cell = 1.0
    try:
        zcell = max(1.0, float(ztol))
    except Exception:
        zcell = 1.0

    grid = {}
    def _gkey(p):
        try:
            return (
                int(math.floor(float(p.X) / float(cell))),
                int(math.floor(float(p.Y) / float(cell))),
                int(math.floor(float(p.Z) / float(zcell))),
            )
        except Exception:
            return (0, 0, 0)

    for pt, fdir, e in dir_items:
        try:
            k = _gkey(pt)
            grid.setdefault(k, []).append((pt, fdir, e))
        except Exception:
            continue

    try:
        dir_items_sorted = sorted(dir_items, key=lambda x: int(x[2].Id.IntegerValue))
    except Exception:
        dir_items_sorted = dir_items

    for pt, fdir, e in dir_items_sorted:
        try:
            eid0 = e.Id
            iid0 = int(eid0.IntegerValue)
        except Exception:
            continue
        if eid0 in to_delete:
            continue

        k = _gkey(pt)
        for ix in (k[0] - 1, k[0], k[0] + 1):
            for iy in (k[1] - 1, k[1], k[1] + 1):
                for iz in (k[2] - 1, k[2], k[2] + 1):
                    for pt2, fdir2, e2 in grid.get((ix, iy, iz), []):
                        if not e2:
                            continue
                        try:
                            eid2 = e2.Id
                        except Exception:
                            continue
                        if eid2 == eid0 or (eid2 in to_delete):
                            continue

                        try:
                            if abs(float(pt2.Z) - float(pt.Z)) > float(ztol):
                                continue
                        except Exception:
                            pass

                        if _dist_xy(pt, pt2) > float(spacing):
                            continue

                        # Require same facing direction (same wall side). If facing missing, be conservative.
                        if fdir is not None and fdir2 is not None:
                            try:
                                if float(fdir.DotProduct(fdir2)) < 0.9:
                                    continue
                            except Exception:
                                continue
                        else:
                            # Without facing, only delete if extremely close
                            if _dist_xy(pt, pt2) > float(spacing) * 0.5:
                                continue

                        try:
                            iid2 = int(eid2.IntegerValue)
                        except Exception:
                            iid2 = None
                        if iid2 is None:
                            continue
                        if iid2 > iid0:
                            to_delete.add(eid2)

    if not to_delete:
        return 0

    deleted = 0
    try:
        with utils_revit.tx('ЭОМ: Удалить дубли розеток AC', doc=doc, swallow_warnings=True):
            for eid in list(to_delete):
                try:
                    doc.Delete(eid)
                    deleted += 1
                except Exception:
                    continue
    except Exception:
        return 0

    return int(deleted)


def _open_plan_check_view(doc, uidoc, elems, view_name='Plan_Check_AC_Sockets', pad_ft=3.0):
    if not doc or not uidoc or not elems:
        return

    min_x = min_y = min_z = 1e18
    max_x = max_y = max_z = -1e18
    z_samples = []
    ok = False

    for e in elems:
        if not e:
            continue

        bb = None
        try:
            bb = e.get_BoundingBox(None)
        except Exception:
            bb = None

        if bb:
            ok = True
            min_x = min(min_x, float(bb.Min.X))
            min_y = min(min_y, float(bb.Min.Y))
            min_z = min(min_z, float(bb.Min.Z))
            max_x = max(max_x, float(bb.Max.X))
            max_y = max(max_y, float(bb.Max.Y))
            max_z = max(max_z, float(bb.Max.Z))
            z_samples.append((float(bb.Min.Z) + float(bb.Max.Z)) * 0.5)
            continue

        try:
            loc = getattr(e, 'Location', None)
            pt = loc.Point if loc and hasattr(loc, 'Point') else None
            if pt:
                ok = True
                d = 1.0
                min_x = min(min_x, float(pt.X) - d)
                min_y = min(min_y, float(pt.Y) - d)
                min_z = min(min_z, float(pt.Z) - d)
                max_x = max(max_x, float(pt.X) + d)
                max_y = max(max_y, float(pt.Y) + d)
                max_z = max(max_z, float(pt.Z) + d)
                z_samples.append(float(pt.Z))
        except Exception:
            continue

    if not ok or (max_x <= min_x) or (max_y <= min_y):
        return

    z_mid = (sum(z_samples) / float(len(z_samples))) if z_samples else ((min_z + max_z) * 0.5)

    # Find level below/at z_mid and next above ("между этажами")
    levels = []
    try:
        levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements())
        levels.sort(key=lambda l: float(l.Elevation))
    except Exception:
        levels = []

    lvl_lo = None
    lvl_hi = None
    if levels:
        for idx, lvl in enumerate(levels):
            try:
                if float(lvl.Elevation) <= float(z_mid) + 1e-9:
                    lvl_lo = lvl
                    lvl_hi = levels[idx + 1] if (idx + 1) < len(levels) else None
                else:
                    break
            except Exception:
                continue
        if lvl_lo is None:
            lvl_lo = levels[0]
            lvl_hi = levels[1] if len(levels) > 1 else None

    if lvl_lo is None:
        return

    z_lo = float(lvl_lo.Elevation) if lvl_lo else (min_z - pad_ft)
    z_hi = float(lvl_hi.Elevation) if lvl_hi else (max_z + pad_ft)
    if z_hi <= z_lo + 1e-6:
        z_lo = min_z - pad_ft
        z_hi = max_z + pad_ft

    # Find or create FLOOR PLAN view
    vplan = None
    try:
        for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
            try:
                if not v or v.IsTemplate:
                    continue
                if v.Name == view_name:
                    vplan = v
                    break
            except Exception:
                continue
    except Exception:
        vplan = None

    if not vplan:
        vft = None
        try:
            for vt in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
                try:
                    if vt.ViewFamily == DB.ViewFamily.FloorPlan:
                        vft = vt
                        break
                except Exception:
                    continue
        except Exception:
            vft = None

        if not vft:
            raise Exception("Не найден ViewFamilyType для FloorPlan")

        with utils_revit.tx('EOM: Создать план проверки', doc=doc, swallow_warnings=True):
            vplan = DB.ViewPlan.Create(doc, vft.Id, lvl_lo.Id)
            try:
                vplan.Name = view_name
            except Exception:
                pass

    # Configure view range so cut plane is ABOVE sockets (so they appear in plan)
    try:
        cut_margin_ft = float(utils_units.mm_to_ft(50))
    except Exception:
        cut_margin_ft = 0.15

    try:
        cut_abs = float(max_z) + float(cut_margin_ft)
        try:
            cut_abs = min(float(cut_abs), float(z_hi) - float(cut_margin_ft))
        except Exception:
            pass
        cut_ft = float(cut_abs) - float(lvl_lo.Elevation)
    except Exception:
        try:
            cut_ft = float(z_mid) - float(lvl_lo.Elevation) if lvl_lo else 0.0
        except Exception:
            cut_ft = 0.0

    try:
        top_ft = float(z_hi) - float(lvl_lo.Elevation) if lvl_lo else float(pad_ft)
    except Exception:
        top_ft = float(pad_ft)

    if cut_ft < 0.0:
        cut_ft = 0.0
    if top_ft < cut_ft + 1e-3:
        top_ft = cut_ft + max(float(pad_ft or 0.0), 3.0)

    bottom_ft = 0.0
    depth_ft = 0.0

    with utils_revit.tx('EOM: Настроить план проверки', doc=doc, swallow_warnings=True):
        vr = None
        try:
            vr = vplan.GetViewRange()
        except Exception:
            vr = None

        if vr is not None:
            try:
                vr.SetOffset(DB.PlanViewPlane.CutPlane, float(cut_ft))
            except Exception:
                pass
            try:
                vr.SetOffset(DB.PlanViewPlane.TopClipPlane, float(top_ft))
            except Exception:
                pass
            try:
                vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, float(bottom_ft))
            except Exception:
                pass
            try:
                vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, float(depth_ft))
            except Exception:
                pass

            try:
                for plane in (
                    DB.PlanViewPlane.CutPlane,
                    DB.PlanViewPlane.TopClipPlane,
                    DB.PlanViewPlane.BottomClipPlane,
                    DB.PlanViewPlane.ViewDepthPlane,
                ):
                    try:
                        vr.SetLevelId(plane, lvl_lo.Id)
                    except Exception:
                        continue
            except Exception:
                pass

            try:
                vplan.SetViewRange(vr)
            except Exception:
                pass

    # Activate and zoom/select (outside transactions)
    uidoc.ActiveView = vplan
    try:
        ids = [e.Id for e in elems if e]
        try:
            from System.Collections.Generic import List
            id_list = List[DB.ElementId]()
            for eid in ids:
                id_list.Add(eid)
            uidoc.Selection.SetElementIds(id_list)
            uidoc.ShowElements(id_list)
        except Exception:
            uidoc.Selection.SetElementIds(ids)
            uidoc.ShowElements(ids)
    except Exception:
        pass


def _select_link_instances_multi(host_doc, title='Выберите связь(и) АР (Архитектура)'):
    try:
        links = link_reader.list_link_instances(host_doc)
    except Exception:
        links = []

    loaded = []
    for ln in links:
        try:
            if link_reader.is_link_loaded(ln):
                loaded.append(ln)
        except Exception:
            continue

    if not loaded:
        return []
    if len(loaded) == 1:
        return [loaded[0]]

    items = []
    for ln in loaded:
        try:
            name = ln.Name
        except Exception:
            name = '<Link>'
        items.append((u'{0}'.format(name), ln))

    items = sorted(items, key=lambda x: x[0].lower())
    labels = [x[0] for x in items]
    picked = forms.SelectFromList.show(
        labels,
        title=title,
        multiselect=True,
        button_name='Выбрать',
        allow_none=True,
    )
    if not picked:
        return []

    lbl2inst = {lbl: inst for (lbl, inst) in items}
    out = []
    for lbl in picked:
        inst = lbl2inst.get(lbl)
        if inst is not None:
            out.append(inst)
    return out


def _link_doc_key(link_doc):
    if link_doc is None:
        return ''
    try:
        pn = getattr(link_doc, 'PathName', None)
        if pn:
            return pn
    except Exception:
        pass
    try:
        t = getattr(link_doc, 'Title', None)
        if t:
            return t
    except Exception:
        pass
    try:
        return str(link_doc.GetHashCode())
    except Exception:
        return str(id(link_doc))


def _is_exterior_wall(wall):
    """Check if wall is exterior/facade by Function param or name keywords."""
    if wall is None or (not isinstance(wall, DB.Wall)):
        return False
    try:
        p = wall.get_Parameter(DB.BuiltInParameter.FUNCTION_PARAM)
        if p and p.AsInteger() == 1:
            return True
    except Exception:
        pass
    ext_kw = (u'фасад', u'наружн', u'внешн', u'exterior', u'facade', u'external', u'curtain', u'витраж', u'ограждающ')
    try:
        wt = wall.WallType
        if wt:
            wt_name = (wt.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or u'').lower()
            for kw in ext_kw:
                if kw in wt_name:
                    return True
    except Exception:
        pass
    try:
        w_name = (wall.Name or u'').lower()
        for kw in ext_kw:
            if kw in w_name:
                return True
    except Exception:
        pass
    return False


def _bbox_dist_xy(bb, pt):
    if not bb or not pt:
        return 1e18
    try:
        dx = 0.0
        if pt.X < bb.Min.X:
            dx = float(bb.Min.X) - float(pt.X)
        elif pt.X > bb.Max.X:
            dx = float(pt.X) - float(bb.Max.X)

        dy = 0.0
        if pt.Y < bb.Min.Y:
            dy = float(bb.Min.Y) - float(pt.Y)
        elif pt.Y > bb.Max.Y:
            dy = float(pt.Y) - float(bb.Max.Y)

        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return 1e18


def _find_room_at_point_in_rooms(rooms, pt_xyz, scan_bbox_ft=None, scan_limit=None):
    if pt_xyz is None:
        return None

    try:
        limit = int(scan_limit) if scan_limit is not None else None
    except Exception:
        limit = None

    scanned = 0
    for rr in (rooms or []):
        if limit is not None and scanned >= limit:
            break

        try:
            bb_r = rr.get_BoundingBox(None)
            if bb_r is not None and scan_bbox_ft and _bbox_dist_xy(bb_r, pt_xyz) > float(scan_bbox_ft):
                continue
        except Exception:
            pass

        scanned += 1
        try:
            if rr.IsPointInRoom(pt_xyz):
                return rr
        except Exception:
            continue

    return None


def _bbox_contains_xy(bb, pt, pad_ft=0.0):
    if not bb or not pt:
        return False
    try:
        pad = float(pad_ft or 0.0)
        return (
            float(pt.X) >= float(bb.Min.X) - pad and float(pt.X) <= float(bb.Max.X) + pad and
            float(pt.Y) >= float(bb.Min.Y) - pad and float(pt.Y) <= float(bb.Max.Y) + pad
        )
    except Exception:
        return False


def _bbox_contains_xy_z(bb, pt, pad_xy_ft=0.0, z_tol_ft=None):
    if not bb or not pt:
        return False
    if not _bbox_contains_xy(bb, pt, pad_ft=pad_xy_ft):
        return False
    try:
        if z_tol_ft is None:
            return True
        ztol = float(z_tol_ft or 0.0)
        if ztol <= 1e-9:
            return True
        z = float(pt.Z)
        if z < float(bb.Min.Z) - ztol or z > float(bb.Max.Z) + ztol:
            return False
    except Exception:
        pass
    return True


def _push_out_of_bbox_xy(pt, bb, dir_xy, pad_ft=0.0, step_ft=0.2, max_push_ft=2.5):
    if pt is None or bb is None or dir_xy is None:
        return pt
    try:
        d = DB.XYZ(float(dir_xy.X), float(dir_xy.Y), 0.0)
        if d.GetLength() <= 1e-9:
            return pt
        d = d.Normalize()
    except Exception:
        return pt

    try:
        step = float(step_ft or 0.0)
        max_push = float(max_push_ft or 0.0)
    except Exception:
        step = 0.2
        max_push = 2.5

    if step <= 1e-9 or max_push <= 1e-9:
        return pt

    p = pt
    pushed = 0.0
    while pushed <= max_push + 1e-9:
        if not _bbox_contains_xy(bb, p, pad_ft=pad_ft):
            return p
        try:
            p = DB.XYZ(float(p.X) + float(d.X) * step, float(p.Y) + float(d.Y) * step, float(p.Z))
        except Exception:
            return None
        pushed += step
    return None


def _nearest_wall_to_point(walls_with_bb, pt, prefer_interior=True, max_dist_ft=2.0):
    """Find nearest wall (by XY distance to location curve) within max_dist_ft."""
    if not walls_with_bb or not pt:
        return None

    best_w = None
    best_d = None

    for w, bb in walls_with_bb:
        if not w:
            continue
        if prefer_interior and _is_exterior_wall(w):
            continue

        if bb:
            try:
                if (
                    pt.X < bb.Min.X - max_dist_ft or pt.X > bb.Max.X + max_dist_ft or
                    pt.Y < bb.Min.Y - max_dist_ft or pt.Y > bb.Max.Y + max_dist_ft
                ):
                    continue
            except Exception:
                pass

        c = None
        try:
            loc = getattr(w, 'Location', None)
            if isinstance(loc, DB.LocationCurve):
                c = loc.Curve
        except Exception:
            c = None
        if not c:
            continue

        try:
            p = DB.XYZ(float(pt.X), float(pt.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p)
        except Exception:
            ir = None
        if not ir:
            continue

        try:
            proj = ir.XYZPoint
        except Exception:
            proj = None
        if not proj:
            continue

        try:
            dx = float(proj.X) - float(pt.X)
            dy = float(proj.Y) - float(pt.Y)
            d = (dx * dx + dy * dy) ** 0.5
        except Exception:
            continue

        if best_d is None or d < best_d:
            best_d = d
            best_w = w

    if best_w is None or best_d is None:
        return None

    try:
        if float(best_d) > float(max_dist_ft):
            return None
    except Exception:
        pass

    return best_w


def _nearest_wall_to_point_dir(
    walls_with_bb,
    pt,
    prefer_dir=None,
    min_parallel=0.85,
    prefer_interior=True,
    max_dist_ft=2.0,
    angle_weight_ft=2.0,
):
    """Find nearest wall by XY distance with optional direction preference.

    If prefer_dir is provided, walls must be roughly parallel to it (abs(dot) >= min_parallel).
    """
    if not walls_with_bb or not pt:
        return None

    pd = None
    if prefer_dir is not None:
        try:
            pd = DB.XYZ(float(prefer_dir.X), float(prefer_dir.Y), 0.0)
            pd = pd.Normalize() if pd.GetLength() > 1e-9 else None
        except Exception:
            pd = None

    best_w = None
    best_score = None
    best_dist = None

    for w, bb in walls_with_bb:
        if not w:
            continue
        if prefer_interior and _is_exterior_wall(w):
            continue

        if bb:
            try:
                if (
                    pt.X < bb.Min.X - max_dist_ft or pt.X > bb.Max.X + max_dist_ft or
                    pt.Y < bb.Min.Y - max_dist_ft or pt.Y > bb.Max.Y + max_dist_ft
                ):
                    continue
            except Exception:
                pass

        c = None
        try:
            loc = getattr(w, 'Location', None)
            if isinstance(loc, DB.LocationCurve):
                c = loc.Curve
        except Exception:
            c = None
        if not c:
            continue

        # Direction filter
        dotp = 1.0
        if pd is not None:
            try:
                dww = c.GetEndPoint(1) - c.GetEndPoint(0)
                dxy = DB.XYZ(float(dww.X), float(dww.Y), 0.0)
                dxy = dxy.Normalize() if dxy.GetLength() > 1e-9 else None
            except Exception:
                dxy = None
            if dxy is None:
                continue
            try:
                dotp = abs(float(dxy.DotProduct(pd)))
            except Exception:
                dotp = 0.0
            try:
                if float(dotp) < float(min_parallel or 0.0):
                    continue
            except Exception:
                continue

        # distance to curve in XY
        try:
            p = DB.XYZ(float(pt.X), float(pt.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p)
            proj = ir.XYZPoint if ir else None
        except Exception:
            proj = None
        if not proj:
            continue
        try:
            dx = float(proj.X) - float(pt.X)
            dy = float(proj.Y) - float(pt.Y)
            dist = (dx * dx + dy * dy) ** 0.5
        except Exception:
            continue

        try:
            if float(dist) > float(max_dist_ft):
                continue
        except Exception:
            pass

        try:
            pen = float(angle_weight_ft or 0.0) * (1.0 - float(dotp)) if pd is not None else 0.0
        except Exception:
            pen = 0.0

        score = float(dist) + float(pen)
        if best_score is None or score < best_score:
            best_score = score
            best_w = w
            best_dist = dist

    if best_w is None:
        return None

    try:
        if best_dist is not None and float(best_dist) > float(max_dist_ft):
            return None
    except Exception:
        pass

    return best_w


def _dist_xy(a, b):
    if a is None or b is None:
        return 1e18
    try:
        dx = float(a.X) - float(b.X)
        dy = float(a.Y) - float(b.Y)
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return 1e18


def _basket_dist_xy(pt_xy, pt_basket, bb_basket=None):
    d0 = _dist_xy(pt_xy, pt_basket)
    try:
        if bb_basket is not None and pt_xy is not None:
            d1 = _bbox_dist_xy(bb_basket, pt_xy)
            if d1 is not None and float(d1) < float(d0):
                d0 = float(d1)
    except Exception:
        pass
    try:
        return float(d0)
    except Exception:
        return d0


def _get_abs_z_from_level_offset(inst, host_doc):
    if inst is None or host_doc is None:
        return None
    try:
        lid = getattr(inst, 'LevelId', None)
        if not lid or lid == DB.ElementId.InvalidElementId:
            return None
        lvl = host_doc.GetElement(lid)
        if lvl is None or not hasattr(lvl, 'Elevation'):
            return None
        lvl_z = float(lvl.Elevation)
    except Exception:
        return None

    off = None
    try:
        p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and p.StorageType == DB.StorageType.Double:
            off = p.AsDouble()
    except Exception:
        off = None

    if off is None:
        for nm in (
            u'Отметка от уровня',
            u'Смещение от уровня',
            u'Elevation from Level',
            u'Offset from Level',
        ):
            try:
                p = inst.LookupParameter(nm)
                if p and p.StorageType == DB.StorageType.Double:
                    off = p.AsDouble()
                    break
            except Exception:
                continue

    if off is None:
        return None
    try:
        return float(lvl_z) + float(off)
    except Exception:
        return None


def _wall_axis_dist_xy(pt_link, wall):
    if pt_link is None or wall is None or (not isinstance(wall, DB.Wall)):
        return None
    c = None
    try:
        loc = getattr(wall, 'Location', None)
        if isinstance(loc, DB.LocationCurve):
            c = loc.Curve
    except Exception:
        c = None
    if not c:
        return None

    try:
        p = DB.XYZ(float(pt_link.X), float(pt_link.Y), float(c.GetEndPoint(0).Z))
        ir = c.Project(p)
        proj = ir.XYZPoint if ir else None
        if not proj:
            return None
        return _dist_xy(pt_link, proj)
    except Exception:
        return None


def _wall_axis_project_xy(pt_link, wall):
    """Project pt_link to wall location curve in XY (keeps pt_link.Z)."""
    if pt_link is None or wall is None or (not isinstance(wall, DB.Wall)):
        return None
    c = None
    try:
        loc = getattr(wall, 'Location', None)
        if isinstance(loc, DB.LocationCurve):
            c = loc.Curve
    except Exception:
        c = None
    if not c:
        return None

    try:
        p = DB.XYZ(float(pt_link.X), float(pt_link.Y), float(c.GetEndPoint(0).Z))
        ir = c.Project(p)
        proj = ir.XYZPoint if ir else None
        if not proj:
            return None
        return DB.XYZ(float(proj.X), float(proj.Y), float(pt_link.Z))
    except Exception:
        return None


def _wall_dir_xy(wall):
    if wall is None or (not isinstance(wall, DB.Wall)):
        return None
    c = None
    try:
        loc = getattr(wall, 'Location', None)
        if isinstance(loc, DB.LocationCurve):
            c = loc.Curve
    except Exception:
        c = None
    if not c:
        return None
    try:
        d = c.GetEndPoint(1) - c.GetEndPoint(0)
        v = DB.XYZ(float(d.X), float(d.Y), 0.0)
        return v.Normalize() if v.GetLength() > 1e-9 else None
    except Exception:
        return None


def _probe_ft_for_wall(wall, base_probe_ft, extra_mm=50):
    try:
        probe = float(base_probe_ft or 0.0)
    except Exception:
        probe = 0.0

    if wall is not None:
        try:
            w = getattr(wall, 'Width', None)
            if w is not None:
                extra_ft = utils_units.mm_to_ft(int(extra_mm or 50))
                probe = max(float(probe), float(w) + float(extra_ft))
        except Exception:
            pass

    if probe <= 1e-9:
        try:
            probe = float(utils_units.mm_to_ft(400))
        except Exception:
            probe = 0.5
    return probe


def _is_facade_wall_for_basket(wall, pt_on_wall, pt_basket, rooms_lvl, probe_ft, scan_bbox_ft=None, scan_limit=None):
    if wall is None or pt_on_wall is None or pt_basket is None or (not rooms_lvl) or (not probe_ft):
        return False

    wdir = _wall_dir_xy(wall)
    if wdir is None:
        return False

    try:
        n_ref = DB.XYZ(-float(wdir.Y), float(wdir.X), 0.0)
        n_ref = n_ref.Normalize() if n_ref.GetLength() > 1e-9 else None
    except Exception:
        n_ref = None
    if n_ref is None:
        return False

    pt_ref = _wall_axis_project_xy(pt_on_wall, wall) or pt_on_wall

    try:
        p_pos = DB.XYZ(
            float(pt_ref.X) + float(n_ref.X) * float(probe_ft),
            float(pt_ref.Y) + float(n_ref.Y) * float(probe_ft),
            float(pt_ref.Z),
        )
        p_neg = DB.XYZ(
            float(pt_ref.X) - float(n_ref.X) * float(probe_ft),
            float(pt_ref.Y) - float(n_ref.Y) * float(probe_ft),
            float(pt_ref.Z),
        )
    except Exception:
        return False

    rr_pos = _find_room_at_point_in_rooms(rooms_lvl, p_pos, scan_bbox_ft=scan_bbox_ft, scan_limit=scan_limit)
    rr_neg = _find_room_at_point_in_rooms(rooms_lvl, p_neg, scan_bbox_ft=scan_bbox_ft, scan_limit=scan_limit)

    # If the wall has rooms on both sides, it's not a facade wall.
    if rr_pos is not None and rr_neg is not None:
        return False
    # If we can't find any room on either side, fallback to exterior wall check.
    if rr_pos is None and rr_neg is None:
        return _is_exterior_wall(wall)

    try:
        v = DB.XYZ(float(pt_basket.X) - float(pt_ref.X), float(pt_basket.Y) - float(pt_ref.Y), 0.0)
        basket_side = 1 if float(v.DotProduct(n_ref)) >= 0.0 else -1
    except Exception:
        basket_side = 1

    # Facade wall if basket is on the side with NO room.
    if basket_side >= 0:
        return rr_pos is None
    return rr_neg is None


def _pick_room_side_normal_xy(room, wall, pt_link, step_ft=0.5):
    """Return a unit XY normal pointing into `room` for `wall` near `pt_link` (all in link coords)."""
    if room is None or wall is None or pt_link is None:
        return None

    wdir = _wall_dir_xy(wall)
    if wdir is None:
        return None

    try:
        n1 = DB.XYZ(-float(wdir.Y), float(wdir.X), 0.0)
        if n1.GetLength() > 1e-9:
            n1 = n1.Normalize()
        n2 = DB.XYZ(-float(n1.X), -float(n1.Y), 0.0)
    except Exception:
        return None

    z_vals = []
    try:
        z_vals.append(float(pt_link.Z))
    except Exception:
        pass

    try:
        bb = room.get_BoundingBox(None)
        if bb:
            z_vals.append((float(bb.Min.Z) + float(bb.Max.Z)) * 0.5)
            z_vals.append(float(bb.Min.Z) + 1.0)
    except Exception:
        pass

    # Deduplicate
    try:
        z_vals = [z for z in z_vals if z is not None]
        z_vals = list(dict.fromkeys([round(float(z), 4) for z in z_vals]))
    except Exception:
        pass

    def _in_room(p):
        try:
            return bool(room.IsPointInRoom(p))
        except Exception:
            return False

    for z in z_vals:
        try:
            p1 = DB.XYZ(float(pt_link.X) + float(n1.X) * float(step_ft), float(pt_link.Y) + float(n1.Y) * float(step_ft), float(z))
            p2 = DB.XYZ(float(pt_link.X) + float(n2.X) * float(step_ft), float(pt_link.Y) + float(n2.Y) * float(step_ft), float(z))
            in1 = _in_room(p1)
            in2 = _in_room(p2)
        except Exception:
            continue

        if in1 and (not in2):
            return n1
        if in2 and (not in1):
            return n2

    # Fallback
    return n1


def _room_center_point(room):
    if room is None:
        return None
    try:
        loc = getattr(room, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is not None:
            return pt
    except Exception:
        pass
    try:
        bb = room.get_BoundingBox(None)
        if bb is not None:
            return (bb.Min + bb.Max) * 0.5
    except Exception:
        pass
    return None


def _room_side_sign(room, wall, pt_link, step_ft=None):
    """Return +1/-1 which side of wall the room is on (in link XY)."""
    if room is None or wall is None or pt_link is None:
        return None

    # pt_link may be biased away from wall axis (bbox clearance / placement bias).
    # For stable side detection, always measure from the wall axis near the point.
    pt_ref = _wall_axis_project_xy(pt_link, wall) or pt_link

    wdir = _wall_dir_xy(wall)
    if wdir is None:
        return None

    try:
        n1 = DB.XYZ(-float(wdir.Y), float(wdir.X), 0.0)
        n1 = n1.Normalize() if n1.GetLength() > 1e-9 else None
    except Exception:
        n1 = None

    if n1 is None:
        return None

    c = _room_center_point(room)
    if c is not None:
        try:
            v = DB.XYZ(float(c.X) - float(pt_ref.X), float(c.Y) - float(pt_ref.Y), 0.0)
            if v.GetLength() > 1e-9:
                d = float(v.DotProduct(n1))
                if abs(d) > 1e-6:
                    return 1 if d > 0.0 else -1
        except Exception:
            pass

    try:
        if step_ft is None:
            step_ft = utils_units.mm_to_ft(200)
        n_in = _pick_room_side_normal_xy(room, wall, pt_ref, step_ft=float(step_ft))
        if n_in is not None:
            nn = DB.XYZ(float(n_in.X), float(n_in.Y), 0.0)
            if nn.GetLength() > 1e-9:
                nn = nn.Normalize()
                d = float(nn.DotProduct(n1))
                return 1 if d >= 0.0 else -1
    except Exception:
        pass

    return 1


def _min_room_corner_dist_xy(room, pt_link, opts):
    if room is None or pt_link is None:
        return None
    segs = None
    try:
        segs = socket_utils._get_room_outer_boundary_segments(room, opts=opts)
    except Exception:
        segs = None
    if not segs:
        return None

    best = None
    for s in segs:
        try:
            c = s.GetCurve()
            p0 = c.GetEndPoint(0)
            p1 = c.GetEndPoint(1)
        except Exception:
            continue
        for p in (p0, p1):
            d = _dist_xy(pt_link, p)
            if best is None or d < best:
                best = d

    return best


def _room_boundary_min_dist_xy(room, pt, opts):
    if room is None or pt is None:
        return None
    segs = None
    try:
        segs = socket_utils._get_room_outer_boundary_segments(room, opts=opts)
    except Exception:
        segs = None
    if not segs:
        return None

    best = None
    for s in segs:
        c = None
        try:
            c = s.GetCurve()
        except Exception:
            c = None
        if not c:
            continue
        try:
            p = DB.XYZ(float(pt.X), float(pt.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p)
            proj = ir.XYZPoint if ir else None
        except Exception:
            proj = None
        if not proj:
            continue
        d = _dist_xy(pt, proj)
        if best is None or d < best:
            best = d

    return best


def _calc_room_target_z(room, link_doc, h_ceiling_ft):
    if room is None or link_doc is None:
        return None

    z_floor = 0.0
    try:
        lvl = link_doc.GetElement(room.LevelId)
        if lvl and hasattr(lvl, 'Elevation'):
            z_floor = float(lvl.Elevation)
    except Exception:
        z_floor = 0.0

    calc_ceil_h = 0.0

    try:
        p_ub = room.get_Parameter(DB.BuiltInParameter.ROOM_UNBOUNDED_HEIGHT)
        if p_ub and p_ub.HasValue:
            calc_ceil_h = float(p_ub.AsDouble() or 0.0)
    except Exception:
        try:
            p_h = room.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT)
            if p_h and p_h.HasValue:
                calc_ceil_h = float(p_h.AsDouble() or 0.0)
        except Exception:
            pass

    if calc_ceil_h < 0.1:
        try:
            p_lim = room.get_Parameter(DB.BuiltInParameter.ROOM_UPPER_OFFSET)
            off = float(p_lim.AsDouble()) if p_lim else 0.0

            p_ul = room.get_Parameter(DB.BuiltInParameter.ROOM_UPPER_LEVEL)
            ul_id = p_ul.AsElementId() if p_ul else DB.ElementId.InvalidElementId

            if ul_id != DB.ElementId.InvalidElementId:
                ul = link_doc.GetElement(ul_id)
                if ul and hasattr(ul, 'Elevation'):
                    calc_ceil_h = float(ul.Elevation) + off - z_floor
            else:
                calc_ceil_h = off
        except Exception:
            pass

    if calc_ceil_h < 3.0:
        calc_ceil_h = 10.0

    try:
        return float(z_floor + calc_ceil_h - float(h_ceiling_ft or 0.0))
    except Exception:
        return float(z_floor + calc_ceil_h)


def _room_candidates_for_basket(link_doc, room, pt_basket, offset_corner_ft, z_target, opts, walls_with_bb=None):
    """Return (corner_int, corner_any, proj_int, proj_any) candidates.

    Candidate is tuple: (score_xy, wall, pt_final_link, dir_link, is_ext_wall, corner_origin)
    """
    if room is None or pt_basket is None or z_target is None:
        return None, None, None, None

    walls_with_bb = walls_with_bb or []

    segs = None
    try:
        segs = socket_utils._get_room_outer_boundary_segments(room, opts=opts)
    except Exception:
        segs = None

    if not segs:
        return None, None, None, None

    n = len(segs)
    if n < 2:
        return None, None, None, None

    # Wall indices and "exterior" indices (by Function parameter)
    wall_idxs = []
    ext_idxs = []
    for idx, s in enumerate(segs):
        try:
            w = link_doc.GetElement(s.ElementId)
        except Exception:
            w = None
        if w and isinstance(w, DB.Wall):
            wall_idxs.append(idx)
            if _is_exterior_wall(w):
                ext_idxs.append(idx)

    corner_int = None
    corner_any = None
    proj_int = None
    proj_any = None

    def _score_xy(pt_xy):
        try:
            dx = float(pt_xy.X) - float(pt_basket.X)
            dy = float(pt_xy.Y) - float(pt_basket.Y)
            return (dx * dx + dy * dy) ** 0.5
        except Exception:
            return 1e18

    # 1) Corner candidates: choose "facade-like" segment indices.
    # Prefer segments whose element is an exterior wall (Function=Exterior).
    # If none (e.g. wall types not classified), fall back to the segment(s) closest to the basket point.
    base_idxs = list(ext_idxs) if ext_idxs else []

    if not base_idxs:
        scored = []
        for idx, s in enumerate(segs):
            try:
                c = s.GetCurve()
            except Exception:
                c = None
            if not c:
                continue
            try:
                p = DB.XYZ(float(pt_basket.X), float(pt_basket.Y), float(c.GetEndPoint(0).Z))
                ir = c.Project(p)
                proj = ir.XYZPoint if ir else None
            except Exception:
                proj = None
            if not proj:
                continue
            try:
                d = _dist_xy(proj, pt_basket)
            except Exception:
                d = None
            if d is None:
                continue
            scored.append((float(d), idx))

        scored = sorted(scored, key=lambda x: x[0])
        base_idxs = [x[1] for x in scored[:2]]

    if not base_idxs:
        return None, None, None, None
    for idx in base_idxs:
        try:
            c_ext = segs[idx].GetCurve()
        except Exception:
            c_ext = None
        if not c_ext:
            continue

        for corner in (c_ext.GetEndPoint(0), c_ext.GetEndPoint(1)):
            prev_idx = (idx - 1) % n
            next_idx = (idx + 1) % n
            for adj_idx in (prev_idx, next_idx):
                s_adj = segs[adj_idx]
                try:
                    c_adj = s_adj.GetCurve()
                except Exception:
                    c_adj = None
                if not c_adj:
                    continue

                p0 = c_adj.GetEndPoint(0)
                p1 = c_adj.GetEndPoint(1)

                origin = None
                dir_vec = None
                try:
                    if p0.DistanceTo(corner) < 1e-3:
                        origin = p0
                        dir_vec = (p1 - p0)
                    elif p1.DistanceTo(corner) < 1e-3:
                        origin = p1
                        dir_vec = (p0 - p1)
                except Exception:
                    origin = None
                    dir_vec = None

                if origin is None or dir_vec is None:
                    continue
                try:
                    if dir_vec.GetLength() < 1e-6:
                        continue
                except Exception:
                    continue

                try:
                    dir_norm = dir_vec.Normalize()
                except Exception:
                    dir_norm = dir_vec

                try:
                    pt_xy = origin + dir_norm.Multiply(offset_corner_ft)
                except Exception:
                    continue

                wall_any = None
                wall_int = None
                try:
                    wall_side = link_doc.GetElement(s_adj.ElementId)
                except Exception:
                    wall_side = None

                if wall_side and isinstance(wall_side, DB.Wall):
                    wall_any = wall_side
                    if not _is_exterior_wall(wall_side):
                        wall_int = wall_side
                else:
                    # Boundary can be defined by room separation lines etc.
                    # Try to resolve to a real wall near the candidate point, preferring walls parallel to the boundary segment.
                    wall_int = _nearest_wall_to_point_dir(
                        walls_with_bb,
                        pt_xy,
                        prefer_dir=dir_norm,
                        min_parallel=0.75,
                        prefer_interior=True,
                        max_dist_ft=8.0,
                        angle_weight_ft=2.0,
                    )
                    wall_any = wall_int or _nearest_wall_to_point_dir(
                        walls_with_bb,
                        pt_xy,
                        prefer_dir=dir_norm,
                        min_parallel=0.75,
                        prefer_interior=False,
                        max_dist_ft=8.0,
                        angle_weight_ft=2.0,
                    )

                if not wall_any:
                    continue

                # Keep the point on the room boundary face when possible (avoids side ambiguity).
                # Only project to wall axis when boundary element is not a real wall.
                try:
                    resolved_by_proximity = not (wall_side and isinstance(wall_side, DB.Wall))
                except Exception:
                    resolved_by_proximity = True

                if resolved_by_proximity:
                    try:
                        loc = getattr(wall_any, 'Location', None)
                        if isinstance(loc, DB.LocationCurve):
                            cww = loc.Curve
                            p = DB.XYZ(float(pt_xy.X), float(pt_xy.Y), float(cww.GetEndPoint(0).Z))
                            ir = cww.Project(p)
                            proj = ir.XYZPoint if ir else None
                            if proj:
                                pt_xy = DB.XYZ(float(proj.X), float(proj.Y), float(pt_xy.Z))
                    except Exception:
                        pass

                is_ext = _is_exterior_wall(wall_any)

                score = _score_xy(pt_xy)
                pt_final = DB.XYZ(pt_xy.X, pt_xy.Y, z_target)

                cand_any = (score, wall_any, pt_final, dir_norm, is_ext, origin)
                if (corner_any is None) or (score < corner_any[0]):
                    corner_any = cand_any

                if wall_int is not None:
                    cand_int = (score, wall_int, pt_final, dir_norm, False, origin)
                    if (corner_int is None) or (score < corner_int[0]):
                        corner_int = cand_int

    # 2) Projection candidates: nearest point on any wall segment
    for idx in wall_idxs:
        s = segs[idx]
        try:
            wall = link_doc.GetElement(s.ElementId)
        except Exception:
            wall = None
        if not wall or (not isinstance(wall, DB.Wall)):
            continue

        try:
            c = s.GetCurve()
        except Exception:
            c = None
        if not c:
            continue

        try:
            p_b = DB.XYZ(float(pt_basket.X), float(pt_basket.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p_b)
        except Exception:
            ir = None
        if not ir:
            continue

        try:
            proj = ir.XYZPoint
        except Exception:
            proj = None
        if not proj:
            continue

        is_ext = _is_exterior_wall(wall)
        score = _score_xy(proj)
        pt_final = DB.XYZ(proj.X, proj.Y, z_target)

        try:
            d = c.GetEndPoint(1) - c.GetEndPoint(0)
            dir_vec = d.Normalize() if d.GetLength() > 1e-6 else DB.XYZ.BasisX
        except Exception:
            dir_vec = DB.XYZ.BasisX

        cand = (score, wall, pt_final, dir_vec, is_ext, None)

        if (proj_any is None) or (score < proj_any[0]):
            proj_any = cand
        if (not is_ext) and ((proj_int is None) or (score < proj_int[0])):
            proj_int = cand

    return corner_int, corner_any, proj_int, proj_any

def _get_config_rules():
    try:
        return config_loader.load_rules()
    except Exception:
        return None

def _find_room_for_basket(link_doc, basket_pt, search_radius_ft=5.0):
    """
    Find the room nearest to the basket, assuming the basket is on the facade.
    We search for rooms that are close to the basket point.
    Since IsPointInRoom requires the point to be INSIDE, and basket is OUTSIDE,
    we need to find the nearest wall, then check the room adjacent to it.
    
    Simplified approach:
    1. Find all rooms on the same level as the basket.
    2. Find the room with a boundary segment closest to the basket_pt.
    """
    # Finding nearest room by distance to boundary
    # This can be expensive if we iterate ALL rooms.
    # Optimization: Filter rooms by bounding box proximity first?
    pass

def _get_level_id_from_element(elem):
    try:
        return elem.LevelId
    except:
        return None

def main():
    doc = revit.doc
    output = script.get_output()
    logger = script.get_logger()
    
    # 1. Load Config
    rules = _get_config_rules()
    if not rules:
        utils_revit.alert("Не удалось загрузить правила (config/rules.default.json).")
        return

    cfg = script.get_config()

    # 2. Select AR Link(s)
    link_insts = _select_link_instances_multi(doc, title='Выберите связь(и) АР (Архитектура)')
    if not link_insts:
        return

    inst_data = []
    doc_data = {}

    # Prepare per-link-doc inputs (levels, rooms, baskets)
    for link_inst in link_insts:
        link_doc = link_reader.get_link_doc(link_inst)
        if not link_doc:
            continue

        doc_key = _link_doc_key(link_doc)
        inst_data.append((link_inst, link_doc, doc_key))

        if doc_key in doc_data:
            continue

        # Select levels once per linked document
        lvl_title = 'Выберите уровни для обработки'
        try:
            t = getattr(link_doc, 'Title', None)
            if t:
                lvl_title = u'Выберите уровни для обработки ({0})'.format(t)
        except Exception:
            pass

        levels = link_reader.select_levels_multi(link_doc, title=lvl_title, default_all=True)
        if not levels:
            doc_data[doc_key] = {'skip': True}
            continue

        level_ids = set([int(l.Id.IntegerValue) for l in levels])

        candidate_rooms = []
        for r in link_reader.iter_rooms(link_doc):
            try:
                if int(r.LevelId.IntegerValue) in level_ids:
                    candidate_rooms.append(r)
            except Exception:
                continue

        # If level filter yields nothing, fall back to all rooms (avoid missing baskets)
        if not candidate_rooms:
            try:
                candidate_rooms = list(link_reader.iter_rooms(link_doc))
            except Exception:
                candidate_rooms = []

        # Cache walls (for resolving room separation lines etc. to real walls)
        walls_with_bb = []
        try:
            wcol = DB.FilteredElementCollector(link_doc).OfClass(DB.Wall).WhereElementIsNotElementType()
            for w in wcol:
                bb = None
                try:
                    bb = w.get_BoundingBox(None)
                except Exception:
                    bb = None
                walls_with_bb.append((w, bb))
        except Exception:
            walls_with_bb = []

        # Collect baskets / outdoor AC units by keywords
        keywords = list(rules.get('ac_basket_family_keywords', []) or [])

        # Extend with safe AC-specific keywords (avoid raw short tokens like "ac" / "external")
        for kw in [
            u'кондиц', u'кондиционер', u'конд', u'конденс',
            u'наружный блок', u'внешний блок',
            u'external unit', u'outdoor unit', u'air conditioner'
        ]:
            if kw not in keywords:
                keywords.append(kw)

        keys = socket_utils._compile_patterns(keywords)

        # Guard against false positives: "basket/корзина" alone is too generic for some categories
        try:
            generic_basket_rx = re.compile(u'(корзин|\\bbasket\\b)', re.IGNORECASE)
        except Exception:
            generic_basket_rx = None
        try:
            ac_token_rx = re.compile(u'(кондиц|конд|наруж|внеш|external|outdoor|\\bair\\b)', re.IGNORECASE)
        except Exception:
            ac_token_rx = None

        def _basket_identity_text(e):
            parts = []
            try:
                parts.append(getattr(e, 'Name', u'') or u'')
            except Exception:
                pass
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
                if p:
                    parts.append(p.AsString() or u'')
            except Exception:
                pass
            try:
                sym = getattr(e, 'Symbol', None)
                if sym:
                    try:
                        parts.append(getattr(sym, 'Name', u'') or u'')
                    except Exception:
                        pass
                    try:
                        fam = getattr(sym, 'Family', None)
                        if fam:
                            parts.append(getattr(fam, 'Name', u'') or u'')
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                return u' '.join([p for p in parts if p])
            except Exception:
                return u''

        baskets = []
        weak_basket_ids = set()
        for bic in (
            DB.BuiltInCategory.OST_MechanicalEquipment,
            DB.BuiltInCategory.OST_ElectricalEquipment,
            DB.BuiltInCategory.OST_GenericModel,
            DB.BuiltInCategory.OST_SpecialityEquipment,
        ):
            try:
                col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
            except Exception:
                continue
            for e in col:
                try:
                    t = _basket_identity_text(e)
                except Exception:
                    t = ''
                if not t:
                    continue
                if socket_utils._match_any(keys, t):
                    # Reduce false positives: remember elements that only say "basket/корзина" without AC tokens.
                    # We'll still keep them, but can skip them later if they are clearly inside rooms.
                    try:
                        if bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_SpecialityEquipment):
                            if generic_basket_rx and ac_token_rx and generic_basket_rx.search(t) and (not ac_token_rx.search(t)):
                                try:
                                    weak_basket_ids.add(int(e.Id.IntegerValue))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    baskets.append(e)

        # De-dup baskets that represent the same physical outdoor unit (common: overlapping categories)
        try:
            basket_merge_ft = utils_units.mm_to_ft(int(rules.get('ac_basket_merge_mm', 600) or 600))
        except Exception:
            basket_merge_ft = utils_units.mm_to_ft(600)
        try:
            baskets = _dedupe_elems_by_xy(baskets, basket_merge_ft)
        except Exception:
            pass

        doc_data[doc_key] = {
            'skip': False,
            'link_doc': link_doc,
            'levels': levels,
            'level_ids': level_ids,
            'candidate_rooms': candidate_rooms,
            'walls_with_bb': walls_with_bb,
            'baskets': baskets,
            'weak_basket_ids': weak_basket_ids,
            'keywords': keywords,
            'batch': [],
            'skipped': [],
            'used_exterior': 0,
        }

    if not inst_data:
        utils_revit.alert("Не удалось открыть документ(ы) связи.")
        return

    total_found = 0
    for d in doc_data.values():
        if d and (not d.get('skip')):
            total_found += len(d.get('baskets') or [])

    if total_found <= 0:
        utils_revit.alert("Не найдено семейств корзин/кондиционеров в выбранных связях.")
        return

    # 3. Pick Socket Symbol
    fams = rules.get('family_type_names', {}) or {}
    prefer = fams.get('socket_ac') or ["TSL_EF_t_CT_b_IP20_P3t_1P+N+PE"]

    sym, sym_lbl, top10 = socket_utils._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_ac')
    if not sym:
        msg = u"Не найден тип розетки для кондиционеров.\nЗагрузите семейство/тип в проект и повторите."
        try:
            if top10:
                items = []
                for x in top10:
                    try:
                        items.append(unicode(x))
                    except Exception:
                        try:
                            items.append(str(x))
                        except Exception:
                            pass
                if items:
                    msg += u"\n\nДоступные варианты (top10):\n- " + u"\n- ".join(items)
        except Exception:
            pass
        utils_revit.alert(msg)
        return
    
    utils_revit.ensure_symbol_active(doc, sym)
    
    # Check placement capabilities
    is_wp = False
    is_ol = True # Allow point based by default
    try:
        # Simple check if face based
        if socket_utils._is_wall_or_face_based(sym):
            is_wp = True
    except: pass
    sym_flags = {sym.Id.IntegerValue: (is_wp, is_ol)}

    # 4. Parameters
    h_ceiling_mm = int(rules.get('socket_ac_height_from_ceiling_mm', 300) or 300)
    offset_corner_mm = int(rules.get('socket_ac_offset_from_corner_mm', 200) or 200)
    avoid_ext_wall = bool(rules.get('ac_socket_avoid_external_wall', True))

    # Allow placing on facade/exterior walls ONLY as a last resort (when no other candidates exist)
    try:
        allow_facade_last_resort = bool(rules.get('ac_allow_facade_wall_last_resort', True))
    except Exception:
        allow_facade_last_resort = True
    
    h_ceiling_ft = utils_units.mm_to_ft(h_ceiling_mm)
    offset_corner_ft = utils_units.mm_to_ft(offset_corner_mm)

    validate_match_tol_ft = utils_units.mm_to_ft(int(rules.get('kitchen_validate_match_tol_mm', 2000) or 2000))
    validate_height_tol_ft = utils_units.mm_to_ft(int(rules.get('kitchen_validate_height_tol_mm', 20) or 20))
    validate_wall_dist_ft = utils_units.mm_to_ft(int(rules.get('kitchen_validate_wall_dist_mm', 150) or 150))
    validate_offset_tol_ft = utils_units.mm_to_ft(int(rules.get('kitchen_validate_offset_tol_mm', 100) or 100))
    debug_skipped_limit = int(rules.get('kitchen_debug_skipped_rooms_limit', 20) or 20)
    debug_validation_limit = int(rules.get('ac_debug_validation_limit', 50) or 50)
    basket_max_dist_ft = utils_units.mm_to_ft(int(rules.get('ac_validate_basket_max_dist_mm', 2500) or 2500))
    max_per_basket = int(rules.get('ac_max_sockets_per_basket', 2) or 2)

    place_bias_ft = utils_units.mm_to_ft(int(rules.get('ac_place_interior_bias_mm', 150) or 150))
    basket_bbox_exclude_ft = utils_units.mm_to_ft(int(rules.get('ac_basket_exclude_bbox_mm', 200) or 200))
    try:
        basket_bbox_z_tol_ft = utils_units.mm_to_ft(int(rules.get('ac_basket_bbox_z_tol_mm', 1500) or 1500))
    except Exception:
        basket_bbox_z_tol_ft = utils_units.mm_to_ft(1500)

    room_search_ft = utils_units.mm_to_ft(int(rules.get('ac_room_search_boundary_mm', 2500) or 2500))
    room_fallback_ft = utils_units.mm_to_ft(int(rules.get('ac_room_search_boundary_fallback_mm', 4000) or 4000))
    room_search_limit = int(rules.get('ac_room_search_limit', 12) or 12)

    try:
        room_hard_ft = utils_units.mm_to_ft(int(rules.get('ac_room_hard_max_dist_mm', 8000) or 8000))
    except Exception:
        room_hard_ft = utils_units.mm_to_ft(8000)

    try:
        wall_search_ft = utils_units.mm_to_ft(int(rules.get('ac_wall_search_max_dist_mm', 10000) or 10000))
    except Exception:
        wall_search_ft = utils_units.mm_to_ft(10000)
    try:
        if room_hard_ft and float(room_hard_ft) > float(wall_search_ft):
            wall_search_ft = float(room_hard_ft)
    except Exception:
        pass

    try:
        facade_dir_hint_min_align = float(rules.get('ac_facade_dir_hint_min_align', 0.5) or 0.5)
    except Exception:
        facade_dir_hint_min_align = 0.5

    try:
        perp_dot_strict = float(rules.get('ac_perp_dot_strict', 0.35) or 0.35)
    except Exception:
        perp_dot_strict = 0.35
    try:
        perp_dot_max = float(rules.get('ac_perp_dot_max', 0.35) or 0.35)
    except Exception:
        perp_dot_max = 0.35
    try:
        perp_angle_weight_ft = utils_units.mm_to_ft(int(rules.get('ac_perp_angle_weight_mm', 2000) or 2000))
    except Exception:
        perp_angle_weight_ft = utils_units.mm_to_ft(2000)

    try:
        room_touch_ft = utils_units.mm_to_ft(int(rules.get('ac_room_touch_boundary_mm', 600) or 600))
    except Exception:
        room_touch_ft = utils_units.mm_to_ft(600)

    # Prevent placing AC sockets in undesired rooms (loggia/balcony/corridor/wet/etc.)
    ac_exclude_patterns = list(rules.get('ac_room_exclude_name_patterns', []) or [])
    if not ac_exclude_patterns:
        for _k in ('wet_room_name_patterns', 'wc_room_name_patterns', 'bath_room_name_patterns', 'hallway_room_name_patterns'):
            try:
                ac_exclude_patterns.extend(list(rules.get(_k, []) or []))
            except Exception:
                pass
        for _p in (u'балкон', u'лодж', u'loggia', u'balcony', u'клад', u'гардер', u'тамбур'):
            ac_exclude_patterns.append(_p)
    ac_exclude_rx = socket_utils._compile_patterns(ac_exclude_patterns)
    ac_exclude_keywords = list(rules.get('exclude_room_name_keywords', []) or [])

    def _room_is_excluded_for_ac(room):
        if room is None:
            return True
        try:
            if float(getattr(room, 'Area', 0.0) or 0.0) <= 1e-9:
                return True
        except Exception:
            pass
        txt = u''
        try:
            txt = socket_utils._room_text(room) or u''
        except Exception:
            try:
                txt = getattr(room, 'Name', u'') or u''
            except Exception:
                txt = u''
        try:
            txt_l = (txt or u'').lower()
        except Exception:
            txt_l = u''
        for kw in (ac_exclude_keywords or []):
            try:
                if kw and (kw.lower() in txt_l):
                    return True
            except Exception:
                continue
        try:
            if ac_exclude_rx and socket_utils._match_any(ac_exclude_rx, txt):
                return True
        except Exception:
            pass
        return False

    # 5. Build batches per linked document
    opts = DB.SpatialElementBoundaryOptions()
    for d in doc_data.values():
        if d and (not d.get('skip')):
            d['batch'] = []
            d['plans'] = []
            d['skipped'] = []
            d['used_exterior'] = 0

    # Flatten list for progress
    all_targets = []
    for key, d in doc_data.items():
        if not d or d.get('skip'):
            continue
        for b in (d.get('baskets') or []):
            all_targets.append((key, b))

    skip_counts = {}
    skipped_details = []
    skipped_details_more = [0]

    def _push_skip_basket(doc_key, basket, reason, details=None):
        try:
            skip_counts[reason] = int(skip_counts.get(reason, 0)) + 1
        except Exception:
            pass

        try:
            if int(len(skipped_details)) >= int(debug_skipped_limit):
                skipped_details_more[0] = int(skipped_details_more[0] or 0) + 1
                return
        except Exception:
            return

        bid = -1
        try:
            bid = int(basket.Id.IntegerValue)
        except Exception:
            bid = -1

        btxt = ''
        try:
            btxt = socket_utils._elem_text(basket) or ''
        except Exception:
            btxt = ''

        skipped_details.append({
            'doc_key': doc_key,
            'basket_id': bid,
            'basket_text': btxt,
            'reason': reason,
            'details': details,
        })

    r_search = 16.0
    z_tol = 20.0

    with forms.ProgressBar(title='Подготовка точек... {value}/{max_value}', cancellable=True) as pb:
        for i, (doc_key, basket) in enumerate(all_targets):
            if pb.cancelled:
                break
            pb.update_progress(i, len(all_targets))

            d = doc_data.get(doc_key) or {}
            if d.get('skip'):
                continue
            link_doc = d.get('link_doc')
            candidate_rooms = d.get('candidate_rooms') or []
            walls_with_bb = d.get('walls_with_bb') or []

            pt_basket = socket_utils._inst_center_point(basket)
            if not pt_basket:
                try:
                    d['skipped'].append((int(basket.Id.IntegerValue), 'no_point'))
                except Exception:
                    d['skipped'].append((-1, 'no_point'))
                _push_skip_basket(doc_key, basket, 'no_point')
                continue

            bb_basket = None
            try:
                bb_basket = basket.get_BoundingBox(None)
            except Exception:
                bb_basket = None

            facade_wall = None
            facade_dir = None

            # Basket level: strictly process only rooms on the same level (avoid picking rooms этажом выше)
            basket_level_id = None
            try:
                lid = _get_level_id_from_element(basket)
                if lid and lid != DB.ElementId.InvalidElementId:
                    basket_level_id = int(lid.IntegerValue)
            except Exception:
                basket_level_id = None

            if basket_level_id is None:
                try:
                    lvls = list(d.get('levels') or [])
                except Exception:
                    lvls = []

                try:
                    lvls = sorted(lvls, key=lambda x: float(getattr(x, 'Elevation', 0.0)))
                except Exception:
                    pass

                lvl_pick = None
                try:
                    for lvl in lvls:
                        if float(getattr(lvl, 'Elevation', 0.0)) <= float(pt_basket.Z) + 1e-6:
                            lvl_pick = lvl
                        else:
                            break
                except Exception:
                    lvl_pick = None

                if lvl_pick is None and lvls:
                    lvl_pick = lvls[0]

                try:
                    basket_level_id = int(lvl_pick.Id.IntegerValue) if lvl_pick else None
                except Exception:
                    basket_level_id = None

            if basket_level_id is None:
                try:
                    d['skipped'].append((int(basket.Id.IntegerValue), 'no_basket_level'))
                except Exception:
                    d['skipped'].append((-1, 'no_basket_level'))
                _push_skip_basket(doc_key, basket, 'no_basket_level')
                continue

            candidate_rooms_lvl = []
            for r in candidate_rooms:
                try:
                    if int(r.LevelId.IntegerValue) == int(basket_level_id):
                        candidate_rooms_lvl.append(r)
                except Exception:
                    continue

            candidate_rooms_lvl_placeable = []
            try:
                for rr in candidate_rooms_lvl:
                    if not _room_is_excluded_for_ac(rr):
                        candidate_rooms_lvl_placeable.append(rr)
            except Exception:
                candidate_rooms_lvl_placeable = list(candidate_rooms_lvl)

            if not candidate_rooms_lvl:
                try:
                    d['skipped'].append((int(basket.Id.IntegerValue), 'no_rooms_on_basket_level'))
                except Exception:
                    d['skipped'].append((-1, 'no_rooms_on_basket_level'))
                _push_skip_basket(
                    doc_key,
                    basket,
                    'no_rooms_on_basket_level',
                    'basket_level_id={0}, candidate_rooms={1}'.format(basket_level_id, len(candidate_rooms)),
                )
                continue

            # Facade direction: prefer a wall where the basket is on the "no-room" side (robust even if Wall.Function isn't set).
            base_probe_ft = None
            try:
                base_probe_ft = utils_units.mm_to_ft(int(rules.get('ac_room_side_probe_mm', 400) or 400))
            except Exception:
                base_probe_ft = utils_units.mm_to_ft(400)

            try:
                scan_bbox_ft = utils_units.mm_to_ft(int(rules.get('ac_room_side_scan_bbox_mm', 8000) or 8000))
            except Exception:
                scan_bbox_ft = utils_units.mm_to_ft(8000)
            try:
                scan_limit = int(rules.get('ac_room_side_scan_limit', 250) or 250)
            except Exception:
                scan_limit = 250

            z_probe = None
            try:
                z_probe = float(pt_basket.Z)
            except Exception:
                z_probe = 0.0

            try:
                lvl = link_doc.GetElement(DB.ElementId(int(basket_level_id)))
                if lvl and hasattr(lvl, 'Elevation'):
                    z_probe = float(lvl.Elevation) + float(utils_units.mm_to_ft(1500))
            except Exception:
                pass

            pt_basket_probe = DB.XYZ(float(pt_basket.X), float(pt_basket.Y), float(z_probe))

            # Weak "basket/корзина" without AC tokens: if it is clearly inside a room, treat as false positive.
            try:
                weak_ids = d.get('weak_basket_ids') or set()
            except Exception:
                weak_ids = set()
            is_weak_basket = False
            try:
                is_weak_basket = int(basket.Id.IntegerValue) in weak_ids
            except Exception:
                is_weak_basket = False
            if is_weak_basket:
                try:
                    rr_in = _find_room_at_point_in_rooms(
                        candidate_rooms_lvl,
                        pt_basket_probe,
                        scan_bbox_ft=scan_bbox_ft,
                        scan_limit=scan_limit,
                    )
                except Exception:
                    rr_in = None
                if rr_in is not None:
                    _push_skip_basket(doc_key, basket, 'weak_basket_inside_room', getattr(rr_in, 'Name', '') or '')
                    continue

            # Try to find the closest facade wall for this basket
            facade_wall = None
            closest_wall = None
            wall_scored_all = []
            try:
                wall_scored = []
                for ww, bb in (walls_with_bb or []):
                    if not ww:
                        continue
                    d_w = _wall_axis_dist_xy(pt_basket_probe, ww)
                    if d_w is None:
                        try:
                            d_w = _bbox_dist_xy(bb, pt_basket_probe) if bb is not None else None
                        except Exception:
                            d_w = None
                    if d_w is None:
                        continue
                    try:
                        if wall_search_ft and float(d_w) > float(wall_search_ft):
                            continue
                    except Exception:
                        pass
                    wall_scored.append((float(d_w), ww))

                wall_scored = sorted(wall_scored, key=lambda x: x[0])
                wall_scored_all = list(wall_scored)
                if wall_scored:
                    try:
                        closest_wall = wall_scored[0][1]
                    except Exception:
                        closest_wall = None
                for _dw, ww in wall_scored[:30]:
                    pt_on = _wall_axis_project_xy(pt_basket_probe, ww) or pt_basket_probe
                    probe_ft = _probe_ft_for_wall(ww, base_probe_ft)
                    if _is_facade_wall_for_basket(
                        ww,
                        pt_on,
                        pt_basket_probe,
                        candidate_rooms_lvl,
                        probe_ft,
                        scan_bbox_ft=scan_bbox_ft,
                        scan_limit=scan_limit,
                    ):
                        facade_wall = ww
                        break
            except Exception:
                facade_wall = None

            try:
                facade_dir = _wall_dir_xy(facade_wall) if facade_wall is not None else None
            except Exception:
                facade_dir = None

            facade_dir_hint = facade_dir
            if facade_dir_hint is None and closest_wall is not None:
                try:
                    facade_dir_hint = _wall_dir_xy(closest_wall)
                except Exception:
                    facade_dir_hint = None

            # IMPROVED FALLBACK: Compute facade direction from room center to basket
            if facade_dir_hint is None:
                try:
                    for r in candidate_rooms_lvl_placeable:
                        bb_r = r.get_BoundingBox(None)
                        if bb_r is None:
                            continue
                        room_center = DB.XYZ(
                            (float(bb_r.Min.X) + float(bb_r.Max.X)) * 0.5,
                            (float(bb_r.Min.Y) + float(bb_r.Max.Y)) * 0.5,
                            float(pt_basket.Z)
                        )
                        dir_to_basket = DB.XYZ(
                            float(pt_basket.X) - float(room_center.X),
                            float(pt_basket.Y) - float(room_center.Y),
                            0.0
                        )
                        if dir_to_basket.GetLength() > 1e-6:
                            facade_dir_hint = DB.XYZ(-float(dir_to_basket.Y), float(dir_to_basket.X), 0.0)
                            facade_dir_hint = facade_dir_hint.Normalize()
                            break
                except Exception:
                    pass

            try:
                if facade_dir_hint is not None:
                    fd = DB.XYZ(float(facade_dir_hint.X), float(facade_dir_hint.Y), 0.0)
                    facade_dir_hint = fd.Normalize() if fd.GetLength() > 1e-9 else None
            except Exception:
                facade_dir_hint = None

            # Rooms near the basket by boundary distance (strict) on the same level
            scored = []
            min_d = None
            for r in candidate_rooms_lvl_placeable:
                d0 = _room_boundary_min_dist_xy(r, pt_basket, opts)
                if d0 is None:
                    continue
                if min_d is None or float(d0) < float(min_d):
                    min_d = float(d0)
                scored.append((float(d0), r))

            scored = sorted(scored, key=lambda x: x[0])
            nearby_rooms = [x[1] for x in scored if x[0] <= float(room_search_ft)][:int(room_search_limit)]

            if not nearby_rooms:
                # Fallback: allow a bit further, but still capped
                nearby_rooms = [x[1] for x in scored if x[0] <= float(room_fallback_ft)][:int(room_search_limit)]

            if not nearby_rooms:
                # Final fallback: take the single closest room if within a hard cap (helps when basket point is far outside the facade)
                try:
                    if scored and room_hard_ft and float(scored[0][0]) <= float(room_hard_ft) + 1e-9:
                        nearby_rooms = [scored[0][1]]
                except Exception:
                    pass

            if not nearby_rooms:
                try:
                    d['skipped'].append((int(basket.Id.IntegerValue), 'no_nearby_rooms'))
                except Exception:
                    d['skipped'].append((-1, 'no_nearby_rooms'))
                det = 'candidate_rooms={0}'.format(len(candidate_rooms))
                try:
                    if min_d is not None:
                        det += ', min_boundary={0}mm'.format(int(round(utils_units.ft_to_mm(min_d))))
                except Exception:
                    pass
                _push_skip_basket(doc_key, basket, 'no_nearby_rooms', det)
                continue

            # Derive facade direction from the nearest room center (stable hint).
            fd0 = None
            try:
                r0 = scored[0][1] if scored else None
                cpt0 = _room_center_point(r0) if r0 is not None else None
                if cpt0 is not None:
                    v0 = DB.XYZ(float(cpt0.X) - float(pt_basket.X), float(cpt0.Y) - float(pt_basket.Y), 0.0)
                    v0 = v0.Normalize() if v0.GetLength() > 1e-9 else None
                else:
                    v0 = None
                if v0 is not None:
                    fd0 = DB.XYZ(-float(v0.Y), float(v0.X), 0.0)
                    fd0 = fd0.Normalize() if fd0.GetLength() > 1e-9 else None
            except Exception:
                fd0 = None

            if fd0 is not None:
                if facade_dir_hint is None:
                    facade_dir_hint = fd0
                else:
                    try:
                        if abs(float(facade_dir_hint.DotProduct(fd0))) < float(facade_dir_hint_min_align or 0.5):
                            facade_dir_hint = fd0
                    except Exception:
                        pass

            def _try_rehost_corner_hint(hint, cand_room):
                if not hint:
                    return None
                try:
                    _sc, _w0, pt0, vec0, _is_ext0, origin0 = hint
                except Exception:
                    return None

                wall_int = _nearest_wall_to_point(walls_with_bb, pt0, prefer_interior=True, max_dist_ft=5.0)

                # If we have a direction, prefer interior walls aligned to it
                if vec0 is not None and walls_with_bb:
                    try:
                        v = vec0.Normalize() if vec0.GetLength() > 1e-6 else None
                    except Exception:
                        v = None

                    if v is not None:
                        best_w = None
                        best_d = None
                        for ww, bb in walls_with_bb:
                            if not ww or _is_exterior_wall(ww):
                                continue
                            if bb:
                                try:
                                    if (
                                        pt0.X < bb.Min.X - 5.0 or pt0.X > bb.Max.X + 5.0 or
                                        pt0.Y < bb.Min.Y - 5.0 or pt0.Y > bb.Max.Y + 5.0
                                    ):
                                        continue
                                except Exception:
                                    pass

                            cww = None
                            try:
                                loc = getattr(ww, 'Location', None)
                                if isinstance(loc, DB.LocationCurve):
                                    cww = loc.Curve
                            except Exception:
                                cww = None
                            if not cww:
                                continue

                            try:
                                dww = cww.GetEndPoint(1) - cww.GetEndPoint(0)
                                dww = dww.Normalize() if dww.GetLength() > 1e-6 else None
                            except Exception:
                                dww = None
                            if dww is None:
                                continue

                            try:
                                if abs(float(dww.DotProduct(v))) < 0.85:
                                    continue
                            except Exception:
                                continue

                            # distance to curve in XY
                            try:
                                p = DB.XYZ(float(pt0.X), float(pt0.Y), float(cww.GetEndPoint(0).Z))
                                ir = cww.Project(p)
                                proj = ir.XYZPoint if ir else None
                            except Exception:
                                proj = None
                            if not proj:
                                continue
                            try:
                                dx = float(proj.X) - float(pt0.X)
                                dy = float(proj.Y) - float(pt0.Y)
                                dist = (dx * dx + dy * dy) ** 0.5
                            except Exception:
                                continue
                            if dist > 5.0:
                                continue
                            if best_d is None or dist < best_d:
                                best_d = dist
                                best_w = ww

                        if best_w is not None:
                            wall_int = best_w

                if wall_int is None:
                    return None

                # Keep original point so face projection can pick the correct side.
                return (_sc, wall_int, pt0, vec0, False, origin0)

            room_cands = []

            for r in nearby_rooms:
                z_target = _calc_room_target_z(r, link_doc, h_ceiling_ft)
                if z_target is None:
                    continue

                c_int, c_any, p_int, p_any = _room_candidates_for_basket(
                    link_doc, r, pt_basket, offset_corner_ft, z_target, opts, walls_with_bb
                )

                cand_opts = []
                if c_int:
                    cand_opts.append(('corner_int', c_int))

                if c_any:
                    try:
                        if not _is_exterior_wall(c_any[1]):
                            cand_opts.append(('corner_any_int', c_any))
                    except Exception:
                        pass

                if avoid_ext_wall and c_any:
                    cand_rehost = _try_rehost_corner_hint(c_any, r)
                    if cand_rehost:
                        cand_opts.append(('corner_rehosted', cand_rehost))

                if p_int:
                    cand_opts.append(('proj_int', p_int))

                if p_any:
                    try:
                        if not _is_exterior_wall(p_any[1]):
                            cand_opts.append(('proj_any_int', p_any))
                    except Exception:
                        pass

                if not avoid_ext_wall:
                    if c_any:
                        cand_opts.append(('corner_any', c_any))
                    if p_any:
                        cand_opts.append(('proj_any', p_any))

                picked = None
                for allow_non_perp in (False, True):
                    best_local = None
                    for ck, cc in cand_opts:
                        try:
                            wall0 = cc[1]
                            pt0 = cc[2]
                            dir0 = cc[3]
                            origin0 = cc[5]
                        except Exception:
                            continue

                        if wall0 is None or pt0 is None:
                            continue

                        try:
                            if avoid_ext_wall and _is_exterior_wall(wall0):
                                continue
                        except Exception:
                            pass

                        try:
                            if avoid_ext_wall and facade_wall is not None and int(wall0.Id.IntegerValue) == int(facade_wall.Id.IntegerValue):
                                continue
                        except Exception:
                            pass

                        perp_bad = False
                        dotv = None
                        try:
                            if facade_dir_hint is not None:
                                wdir = _wall_dir_xy(wall0)
                                cd = wdir or dir0
                                cd2 = DB.XYZ(float(cd.X), float(cd.Y), 0.0) if cd is not None else None
                                if cd2 is not None and cd2.GetLength() > 1e-9:
                                    cd2 = cd2.Normalize()
                                    dotv = abs(float(cd2.DotProduct(facade_dir_hint)))
                                    if float(dotv) > float(perp_dot_max):
                                        continue
                                    if float(dotv) > float(perp_dot_strict):
                                        if not allow_non_perp:
                                            continue
                                        perp_bad = True
                        except Exception:
                            perp_bad = False
                            dotv = None

                        pt_use = pt0

                        # If inside basket bbox, push deeper into the room instead of skipping
                        try:
                            if bb_basket is not None and basket_bbox_exclude_ft and _bbox_contains_xy_z(bb_basket, pt_use, pad_xy_ft=float(basket_bbox_exclude_ft), z_tol_ft=basket_bbox_z_tol_ft):
                                dir_push = None
                                try:
                                    dv = DB.XYZ(float(pt_use.X) - float(pt_basket.X), float(pt_use.Y) - float(pt_basket.Y), 0.0)
                                    dir_push = dv if dv.GetLength() > 1e-9 else None
                                except Exception:
                                    dir_push = None
                                if dir_push is None:
                                    try:
                                        dir_push = _pick_room_side_normal_xy(r, wall0, pt_use, step_ft=utils_units.mm_to_ft(150))
                                    except Exception:
                                        dir_push = None
                                if dir_push is None:
                                    continue
                                pt_fix = _push_out_of_bbox_xy(
                                    pt_use,
                                    bb_basket,
                                    dir_push,
                                    pad_ft=float(basket_bbox_exclude_ft),
                                    step_ft=utils_units.mm_to_ft(50),
                                    max_push_ft=utils_units.mm_to_ft(2000),
                                )
                                if pt_fix is None:
                                    continue
                                pt_use = pt_fix
                        except Exception:
                            pass

                        # Robust exterior/facade check (even if Wall.Function isn't set).
                        # Avoid false positives for perpendicular interior walls when some spaces have no Room.
                        try:
                            apply_facade_probe = True
                            if facade_dir_hint is not None and dotv is not None and float(dotv) <= float(perp_dot_strict) + 1e-9:
                                apply_facade_probe = False
                        except Exception:
                            apply_facade_probe = True

                        try:
                            if apply_facade_probe and avoid_ext_wall and pt_basket_probe is not None:
                                probe_ft_w = _probe_ft_for_wall(wall0, base_probe_ft)
                                if _is_facade_wall_for_basket(
                                    wall0,
                                    pt_use,
                                    pt_basket_probe,
                                    candidate_rooms_lvl,
                                    probe_ft_w,
                                    scan_bbox_ft=scan_bbox_ft,
                                    scan_limit=scan_limit,
                                ):
                                    continue
                        except Exception:
                            pass

                        try:
                            score_raw = _basket_dist_xy(pt_use, pt_basket, bb_basket)
                        except Exception:
                            try:
                                score_raw = float(cc[0])
                            except Exception:
                                score_raw = 1e18

                        # Hard distance guard
                        try:
                            if basket_max_dist_ft and float(score_raw) > float(basket_max_dist_ft) + 1e-9:
                                continue
                        except Exception:
                            pass

                        try:
                            is_ext0 = bool(_is_exterior_wall(wall0))
                        except Exception:
                            is_ext0 = False

                        score_pick = float(score_raw)
                        try:
                            if dotv is not None and perp_angle_weight_ft and float(perp_angle_weight_ft) > 1e-9:
                                score_pick = float(score_pick) + float(dotv) * float(perp_angle_weight_ft)
                        except Exception:
                            score_pick = float(score_raw)

                        pen0 = 0 if (ck or '').startswith('corner') else 1
                        pen_extra = 2 if perp_bad else 0
                        pen = int(pen0) + int(pen_extra)

                        cand_pack = (
                            pen,
                            float(score_pick),
                            ck,
                            (
                                float(score_raw),
                                wall0,
                                DB.XYZ(float(pt_use.X), float(pt_use.Y), float(z_target)),
                                dir0,
                                is_ext0,
                                origin0,
                            ),
                        )

                        if (best_local is None) or (cand_pack[0] < best_local[0]) or (cand_pack[0] == best_local[0] and cand_pack[1] < best_local[1]):
                            best_local = cand_pack

                    if best_local is not None:
                        picked = best_local
                        break

                if picked is None:
                    continue

                pen, picked_score, picked_kind, picked_cand = picked
                room_cands.append((int(pen), float(picked_score), r, picked_kind, picked_cand))

            # Fallback when room boundary candidates are missing (often happens with bad room boundaries near facade).
            if (not room_cands) and wall_scored_all:
                rooms_near_ids = set()
                try:
                    for rr in (nearby_rooms or []):
                        try:
                            rooms_near_ids.add(int(rr.Id.IntegerValue))
                        except Exception:
                            continue
                except Exception:
                    rooms_near_ids = set()

                # Emergency fallback can optionally relax exterior/facade avoidance to prevent no_candidate.
                strict_avoid_ext = bool(avoid_ext_wall and (not allow_facade_last_resort))

                added_fb = 0
                for _dw, ww in wall_scored_all[:40]:
                    if added_fb >= 10:
                        break
                    if ww is None:
                        continue

                    is_ext_wall = False
                    try:
                        is_ext_wall = bool(_is_exterior_wall(ww))
                    except Exception:
                        is_ext_wall = False

                    # In strict mode, never use exterior/facade walls.
                    if strict_avoid_ext and is_ext_wall:
                        continue

                    try:
                        if strict_avoid_ext and facade_wall is not None and int(ww.Id.IntegerValue) == int(facade_wall.Id.IntegerValue):
                            continue
                    except Exception:
                        pass

                    pt_on = _wall_axis_project_xy(pt_basket_probe, ww) or pt_basket_probe

                    # Angle preference (same as main selection)
                    dotv2 = None
                    perp_bad2 = False
                    try:
                        if facade_dir_hint is not None:
                            wdir = _wall_dir_xy(ww)
                            cd2 = DB.XYZ(float(wdir.X), float(wdir.Y), 0.0) if wdir is not None else None
                            if cd2 is not None and cd2.GetLength() > 1e-9:
                                cd2 = cd2.Normalize()
                                dotv2 = abs(float(cd2.DotProduct(facade_dir_hint)))
                                # In strict mode we still avoid walls too parallel to facade (likely facade).
                                # In last-resort mode we keep them but penalize later.
                                if float(dotv2) > float(perp_dot_max):
                                    if strict_avoid_ext:
                                        continue
                                    perp_bad2 = True
                                if float(dotv2) > float(perp_dot_strict):
                                    perp_bad2 = True
                    except Exception:
                        dotv2 = None
                        perp_bad2 = False

                    # Probe rooms on both sides of the wall near the basket
                    rr_pos = None
                    rr_neg = None
                    n_ref = None
                    try:
                        wdir0 = _wall_dir_xy(ww)
                        wdir0 = DB.XYZ(float(wdir0.X), float(wdir0.Y), 0.0)
                        wdir0 = wdir0.Normalize() if wdir0.GetLength() > 1e-9 else None
                    except Exception:
                        wdir0 = None
                    if wdir0 is not None:
                        try:
                            n_ref = DB.XYZ(-float(wdir0.Y), float(wdir0.X), 0.0)
                            n_ref = n_ref.Normalize() if n_ref.GetLength() > 1e-9 else None
                        except Exception:
                            n_ref = None

                    if n_ref is None:
                        continue

                    try:
                        probe_ft_w = _probe_ft_for_wall(ww, base_probe_ft)
                    except Exception:
                        probe_ft_w = base_probe_ft

                    try:
                        p_pos = DB.XYZ(float(pt_on.X) + float(n_ref.X) * float(probe_ft_w), float(pt_on.Y) + float(n_ref.Y) * float(probe_ft_w), float(pt_on.Z))
                        p_neg = DB.XYZ(float(pt_on.X) - float(n_ref.X) * float(probe_ft_w), float(pt_on.Y) - float(n_ref.Y) * float(probe_ft_w), float(pt_on.Z))
                        rr_pos = _find_room_at_point_in_rooms(candidate_rooms_lvl_placeable, p_pos, scan_bbox_ft=scan_bbox_ft, scan_limit=scan_limit)
                        rr_neg = _find_room_at_point_in_rooms(candidate_rooms_lvl_placeable, p_neg, scan_bbox_ft=scan_bbox_ft, scan_limit=scan_limit)
                    except Exception:
                        rr_pos = None
                        rr_neg = None

                    # If IsPointInRoom probing failed on BOTH sides (common for buggy room volumes),
                    # try a boundary-distance fallback using nearby rooms.
                    if rr_pos is None and rr_neg is None and nearby_rooms:
                        def _pick_rooms_by_boundary_dist(max_touch_ft):
                            best = {}
                            for rr0 in (nearby_rooms or []):
                                try:
                                    if _room_is_excluded_for_ac(rr0):
                                        continue
                                except Exception:
                                    pass

                                d_touch = None
                                try:
                                    d_touch = _room_boundary_min_dist_xy(rr0, pt_on, opts)
                                except Exception:
                                    d_touch = None
                                if d_touch is None:
                                    continue
                                try:
                                    if max_touch_ft and float(d_touch) > float(max_touch_ft) + 1e-9:
                                        continue
                                except Exception:
                                    pass

                                sgn = None
                                try:
                                    sgn = _room_side_sign(rr0, ww, pt_on, step_ft=float(probe_ft_w))
                                except Exception:
                                    sgn = None
                                if sgn not in (-1, 1):
                                    continue
                                if (sgn not in best) or (float(d_touch) < float(best[sgn][0])):
                                    best[sgn] = (float(d_touch), rr0)
                            out = {}
                            for sgn, pair in best.items():
                                out[int(sgn)] = pair[1]
                            return out

                        picked_by_sign = _pick_rooms_by_boundary_dist(room_touch_ft)
                        rr_pos = picked_by_sign.get(1)
                        rr_neg = picked_by_sign.get(-1)

                        # Relaxed pass: allow any nearby room within the room search radius
                        if rr_pos is None and rr_neg is None:
                            try:
                                touch_relax_ft = max(float(room_touch_ft or 0.0), float(room_search_ft or 0.0))
                            except Exception:
                                touch_relax_ft = float(room_search_ft or 0.0)
                            if touch_relax_ft and float(touch_relax_ft) > 1e-9:
                                picked_by_sign = _pick_rooms_by_boundary_dist(touch_relax_ft)
                                rr_pos = picked_by_sign.get(1)
                                rr_neg = picked_by_sign.get(-1)

                    for rr in (rr_pos, rr_neg):
                        if added_fb >= 10:
                            break
                        if rr is None:
                            continue
                        try:
                            if _room_is_excluded_for_ac(rr):
                                continue
                        except Exception:
                            pass

                        z_target = _calc_room_target_z(rr, link_doc, h_ceiling_ft)
                        if z_target is None:
                            continue

                        pt_use = DB.XYZ(float(pt_on.X), float(pt_on.Y), float(z_target))

                        # Skip obvious facade walls only when wall is close-to-parallel to facade dir.
                        try:
                            apply_facade_probe2 = True
                            if facade_dir_hint is not None and dotv2 is not None and float(dotv2) <= float(perp_dot_strict) + 1e-9:
                                apply_facade_probe2 = False
                        except Exception:
                            apply_facade_probe2 = True

                        try:
                            if apply_facade_probe2 and avoid_ext_wall and pt_basket_probe is not None:
                                is_facade_like = bool(_is_facade_wall_for_basket(
                                    ww,
                                    pt_use,
                                    pt_basket_probe,
                                    candidate_rooms_lvl,
                                    probe_ft_w,
                                    scan_bbox_ft=scan_bbox_ft,
                                    scan_limit=scan_limit,
                                ))
                                if is_facade_like and strict_avoid_ext:
                                    continue
                        except Exception:
                            is_facade_like = False

                        # Basket bbox clearance
                        try:
                            if bb_basket is not None and basket_bbox_exclude_ft and _bbox_contains_xy_z(bb_basket, pt_use, pad_xy_ft=float(basket_bbox_exclude_ft), z_tol_ft=basket_bbox_z_tol_ft):
                                dv = None
                                try:
                                    dv = DB.XYZ(float(pt_use.X) - float(pt_basket.X), float(pt_use.Y) - float(pt_basket.Y), 0.0)
                                except Exception:
                                    dv = None
                                if dv is None or dv.GetLength() <= 1e-9:
                                    dv = n_ref
                                pt_fix = _push_out_of_bbox_xy(
                                    pt_use,
                                    bb_basket,
                                    dv,
                                    pad_ft=float(basket_bbox_exclude_ft),
                                    step_ft=utils_units.mm_to_ft(50),
                                    max_push_ft=utils_units.mm_to_ft(2000),
                                )
                                if pt_fix is None:
                                    continue
                                pt_use = pt_fix
                        except Exception:
                            pass

                        try:
                            score_raw = _basket_dist_xy(pt_use, pt_basket, bb_basket)
                        except Exception:
                            score_raw = float(_dw or 0.0)

                        try:
                            if basket_max_dist_ft and float(score_raw) > float(basket_max_dist_ft) + 1e-9:
                                continue
                        except Exception:
                            pass

                        score_pick = float(score_raw)
                        try:
                            if dotv2 is not None and perp_angle_weight_ft and float(perp_angle_weight_ft) > 1e-9:
                                score_pick = float(score_pick) + float(dotv2) * float(perp_angle_weight_ft)
                        except Exception:
                            score_pick = float(score_raw)

                        pen = 5 + (2 if perp_bad2 else 0)
                        # Last-resort penalties (still allow, but prefer interior/non-facade walls)
                        try:
                            if is_ext_wall and (not strict_avoid_ext):
                                pen += 20
                        except Exception:
                            pass
                        try:
                            if is_facade_like and (not strict_avoid_ext):
                                pen += 20
                        except Exception:
                            pass
                        try:
                            rid0 = int(rr.Id.IntegerValue)
                            if rooms_near_ids and (rid0 not in rooms_near_ids):
                                pen += 2
                        except Exception:
                            pass

                        cand = (float(score_raw), ww, DB.XYZ(float(pt_use.X), float(pt_use.Y), float(z_target)), wdir0, bool(is_ext_wall), None)
                        room_cands.append((int(pen), float(score_pick), rr, 'wall_fallback', cand))
                        added_fb += 1

            room_cands = sorted(room_cands, key=lambda x: (x[0], x[1]))

            picked = 0
            used_room_ids = set()

            # Choose a single interior wall for this basket and reuse ONE anchor point for all sockets on that wall
            chosen_wall = None
            chosen_anchor = None
            chosen_anchor_kind = None
            chosen_corner_origin = None
            chosen_items = []
            best_by_sign = None
            wdir_use = None
            kind_out = None

            # When max_per_basket > 1 we *prefer* a wall that has rooms on BOTH sides.
            # Missing one side is a strong signal that we accidentally picked a facade/exterior boundary.
            wall_order = []
            wall_to_items = {}
            if room_cands:
                for it in room_cands:
                    try:
                        ww = it[4][1]
                        wid = int(ww.Id.IntegerValue) if ww is not None else None
                    except Exception:
                        wid = None
                    if wid is None:
                        continue
                    wall_to_items.setdefault(wid, []).append(it)

                for wid, items in wall_to_items.items():
                    try:
                        items_sorted = sorted(items, key=lambda x: (x[0], x[1]))
                    except Exception:
                        items_sorted = items
                    wall_to_items[wid] = items_sorted
                    if items_sorted:
                        try:
                            wall_order.append((items_sorted[0][0], items_sorted[0][1], wid))
                        except Exception:
                            continue

                try:
                    wall_order = sorted(wall_order, key=lambda x: (x[0], x[1]))
                except Exception:
                    pass

            has_non_facade_wall = True
            try:
                if facade_wall is not None:
                    fid = int(facade_wall.Id.IntegerValue)
                    has_non_facade_wall = any(int(wid) != int(fid) for wid in (wall_to_items.keys() or []))
            except Exception:
                has_non_facade_wall = True

            def _try_pick_wall_with_two_sides(wid_try, require_two_sides=True):
                try:
                    items0 = wall_to_items.get(wid_try) or []
                except Exception:
                    items0 = []
                if not items0:
                    return False

                anchor_item0 = items0[0]
                try:
                    cand0 = anchor_item0[4]
                    wall0 = cand0[1]
                    anchor0 = cand0[2]
                    kind0 = anchor_item0[3] or ''
                    corner0 = cand0[5]
                except Exception:
                    return False

                if wall0 is None or anchor0 is None:
                    return False

                # Prefer not to pick the facade wall itself unless it's the only viable option (emergency fallback).
                try:
                    if facade_wall is not None and int(wall0.Id.IntegerValue) == int(facade_wall.Id.IntegerValue):
                        if avoid_ext_wall and (not allow_facade_last_resort or has_non_facade_wall):
                            return False
                except Exception:
                    pass

                try:
                    wdir0 = _wall_dir_xy(wall0) or items0[0][4][3]
                except Exception:
                    wdir0 = None
                if wdir0 is None:
                    wdir0 = DB.XYZ.BasisX

                try:
                    probe_ft0 = _probe_ft_for_wall(wall0, base_probe_ft)
                except Exception:
                    try:
                        probe_ft0 = utils_units.mm_to_ft(400)
                    except Exception:
                        probe_ft0 = 0.5

                # Ensure: one socket per side of the wall (one room on each side)
                try:
                    cands_for_sides0 = sorted(room_cands, key=lambda x: (x[0], x[1]))
                except Exception:
                    cands_for_sides0 = list(room_cands)

                # Reference wall normal for stable side classification
                try:
                    wdir_s0 = _wall_dir_xy(wall0) or wdir0
                except Exception:
                    wdir_s0 = wdir0
                try:
                    wdir_s0 = DB.XYZ(float(wdir_s0.X), float(wdir_s0.Y), 0.0)
                    wdir_s0 = wdir_s0.Normalize() if wdir_s0.GetLength() > 1e-9 else DB.XYZ.BasisX
                except Exception:
                    wdir_s0 = DB.XYZ.BasisX
                try:
                    n_ref0 = DB.XYZ(-float(wdir_s0.Y), float(wdir_s0.X), 0.0)
                    n_ref0 = n_ref0.Normalize() if n_ref0.GetLength() > 1e-9 else DB.XYZ.BasisY
                except Exception:
                    n_ref0 = DB.XYZ.BasisY

                best0 = {}
                for it0 in cands_for_sides0:
                    try:
                        _p0, _s0, rr0, _kk0, cc0 = it0
                    except Exception:
                        continue

                    try:
                        z0 = float(cc0[2].Z)
                    except Exception:
                        z0 = float(getattr(anchor0, 'Z', 0.0))

                    pt_ref0 = DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z0))
                    pt_ref0 = _wall_axis_project_xy(pt_ref0, wall0) or pt_ref0

                    # Only accept rooms that really touch this wall near the anchor point.
                    # Prefer direct point-in-room tests on both sides of the wall normal.
                    sgn0 = None
                    try:
                        p_pos0 = DB.XYZ(
                            float(pt_ref0.X) + float(n_ref0.X) * float(probe_ft0),
                            float(pt_ref0.Y) + float(n_ref0.Y) * float(probe_ft0),
                            float(pt_ref0.Z),
                        )
                        p_neg0 = DB.XYZ(
                            float(pt_ref0.X) - float(n_ref0.X) * float(probe_ft0),
                            float(pt_ref0.Y) - float(n_ref0.Y) * float(probe_ft0),
                            float(pt_ref0.Z),
                        )
                        in_pos0 = bool(rr0.IsPointInRoom(p_pos0))
                        in_neg0 = bool(rr0.IsPointInRoom(p_neg0))
                        if in_pos0 and (not in_neg0):
                            sgn0 = 1
                        elif in_neg0 and (not in_pos0):
                            sgn0 = -1
                    except Exception:
                        sgn0 = None

                    if sgn0 is None:
                        try:
                            n_probe0 = _pick_room_side_normal_xy(rr0, wall0, pt_ref0, step_ft=float(probe_ft0))
                        except Exception:
                            n_probe0 = None
                        if n_probe0 is None:
                            continue
                        try:
                            p_test0 = DB.XYZ(
                                float(pt_ref0.X) + float(n_probe0.X) * float(probe_ft0),
                                float(pt_ref0.Y) + float(n_probe0.Y) * float(probe_ft0),
                                float(pt_ref0.Z),
                            )
                            if not rr0.IsPointInRoom(p_test0):
                                continue
                        except Exception:
                            continue

                        try:
                            nn0 = DB.XYZ(float(n_probe0.X), float(n_probe0.Y), 0.0)
                            nn0 = nn0.Normalize() if nn0.GetLength() > 1e-9 else None
                        except Exception:
                            nn0 = None
                        if nn0 is None:
                            continue

                        try:
                            sgn0 = 1 if float(nn0.DotProduct(n_ref0)) >= 0.0 else -1
                        except Exception:
                            sgn0 = 1
                    if sgn0 in best0:
                        continue
                    best0[sgn0] = it0
                    if 1 in best0 and -1 in best0:
                        break

                # Fallback: search ALL rooms on this level for the missing side (room may be far from basket)
                if int(max_per_basket) > 1 and ((1 not in best0) or (-1 not in best0)):
                    used_rids = set()
                    try:
                        for _itx in best0.values():
                            try:
                                used_rids.add(int(_itx[2].Id.IntegerValue))
                            except Exception:
                                continue
                    except Exception:
                        pass

                    try:
                        scan_bbox_ft = utils_units.mm_to_ft(int(rules.get('ac_room_side_scan_bbox_mm', 8000) or 8000))
                    except Exception:
                        scan_bbox_ft = utils_units.mm_to_ft(8000)
                    try:
                        scan_limit = int(rules.get('ac_room_side_scan_limit', 250) or 250)
                    except Exception:
                        scan_limit = 250

                    try:
                        need_signs = []
                        if 1 not in best0:
                            need_signs.append(1)
                        if -1 not in best0:
                            need_signs.append(-1)
                    except Exception:
                        need_signs = [1, -1]

                    scored_fill = []
                    scanned = 0
                    for rr0 in (candidate_rooms_lvl_placeable or []):
                        if scanned >= int(scan_limit):
                            break

                        rid0 = None
                        try:
                            rid0 = int(rr0.Id.IntegerValue)
                        except Exception:
                            rid0 = None
                        if rid0 is not None and rid0 in used_rids:
                            continue

                        z0 = _calc_room_target_z(rr0, link_doc, h_ceiling_ft)
                        if z0 is None:
                            continue

                        pt_ref1 = DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z0))
                        pt_ref1 = _wall_axis_project_xy(pt_ref1, wall0) or pt_ref1

                        # bbox prefilter (cheap)
                        try:
                            bb_r = rr0.get_BoundingBox(None)
                            if bb_r is not None and scan_bbox_ft and _bbox_dist_xy(bb_r, pt_ref1) > float(scan_bbox_ft):
                                continue
                        except Exception:
                            pass

                        # Count only rooms that pass the cheap bbox prefilter
                        scanned += 1

                        try:
                            n_probe1 = _pick_room_side_normal_xy(rr0, wall0, pt_ref1, step_ft=float(probe_ft0))
                        except Exception:
                            n_probe1 = None
                        if n_probe1 is None:
                            continue

                        try:
                            p_test1 = DB.XYZ(
                                float(pt_ref1.X) + float(n_probe1.X) * float(probe_ft0),
                                float(pt_ref1.Y) + float(n_probe1.Y) * float(probe_ft0),
                                float(pt_ref1.Z),
                            )
                            if not rr0.IsPointInRoom(p_test1):
                                continue
                        except Exception:
                            continue

                        try:
                            nn1 = DB.XYZ(float(n_probe1.X), float(n_probe1.Y), 0.0)
                            nn1 = nn1.Normalize() if nn1.GetLength() > 1e-9 else None
                        except Exception:
                            nn1 = None
                        if nn1 is None:
                            continue

                        try:
                            sgn1 = 1 if float(nn1.DotProduct(n_ref0)) >= 0.0 else -1
                        except Exception:
                            sgn1 = 1
                        if sgn1 not in need_signs or sgn1 in best0:
                            continue

                        dist1 = None
                        try:
                            dist1 = _room_boundary_min_dist_xy(rr0, pt_ref1, opts)
                        except Exception:
                            dist1 = None

                        # Require room to touch the wall near the anchor (prevents picking unrelated/far rooms on fallback).
                        try:
                            if dist1 is None:
                                continue
                            if room_touch_ft and float(dist1) > float(room_touch_ft) + 1e-9:
                                continue
                        except Exception:
                            pass

                        scored_fill.append((float(dist1 or 0.0), int(sgn1), rr0, float(z0)))

                    try:
                        scored_fill = sorted(scored_fill, key=lambda x: x[0])
                    except Exception:
                        pass

                    for _d1, sgn1, rr1, z1 in scored_fill:
                        if sgn1 in best0:
                            continue
                        cc1 = (0.0, wall0, DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z1)), wdir0, False, corner0)
                        it_fb = (99, float(_d1), rr1, 'fallback', cc1)
                        best0[sgn1] = it_fb
                        if 1 in best0 and -1 in best0:
                            break

                # Final fallback: probe points on BOTH sides of wall normal and find a containing room.
                # This helps when boundary-based side detection fails for one of the rooms.
                if int(max_per_basket) > 1 and ((1 not in best0) or (-1 not in best0)):
                    try:
                        z_probe = float(getattr(anchor0, 'Z', 0.0))
                    except Exception:
                        z_probe = 0.0

                    # Probe with multiple Z values (rooms may not respond to IsPointInRoom near ceiling Z)
                    z_list = []
                    try:
                        z_list.append(float(getattr(anchor0, 'Z', 0.0)))
                    except Exception:
                        pass
                    try:
                        z_list.append(float(getattr(pt_basket_probe, 'Z', 0.0)))
                    except Exception:
                        pass
                    try:
                        lvl0 = link_doc.GetElement(DB.ElementId(int(basket_level_id)))
                        if lvl0 and hasattr(lvl0, 'Elevation'):
                            z0 = float(lvl0.Elevation)
                            z_list.append(z0 + float(utils_units.mm_to_ft(1500)))
                            z_list.append(z0 + float(utils_units.mm_to_ft(1200)))
                            z_list.append(z0 + float(utils_units.mm_to_ft(900)))
                    except Exception:
                        pass

                    z_seen = set()
                    for _z in z_list:
                        try:
                            z_key = int(round(float(_z) * 1000.0))
                            if z_key in z_seen:
                                continue
                            z_seen.add(z_key)
                        except Exception:
                            pass

                        pt_probe = DB.XYZ(float(anchor0.X), float(anchor0.Y), float(_z))
                        pt_probe = _wall_axis_project_xy(pt_probe, wall0) or pt_probe

                        p_pos = None
                        p_neg = None
                        try:
                            p_pos = DB.XYZ(
                                float(pt_probe.X) + float(n_ref0.X) * float(probe_ft0),
                                float(pt_probe.Y) + float(n_ref0.Y) * float(probe_ft0),
                                float(pt_probe.Z),
                            )
                            p_neg = DB.XYZ(
                                float(pt_probe.X) - float(n_ref0.X) * float(probe_ft0),
                                float(pt_probe.Y) - float(n_ref0.Y) * float(probe_ft0),
                                float(pt_probe.Z),
                            )
                        except Exception:
                            p_pos = None
                            p_neg = None

                        if 1 not in best0 and p_pos is not None:
                            rr1 = _find_room_at_point_in_rooms(
                                candidate_rooms_lvl_placeable,
                                p_pos,
                                scan_bbox_ft=scan_bbox_ft,
                                scan_limit=scan_limit,
                            )
                            if rr1 is not None:
                                z1 = _calc_room_target_z(rr1, link_doc, h_ceiling_ft)
                                if z1 is not None:
                                    cc1 = (0.0, wall0, DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z1)), wdir0, False, corner0)
                                    best0[1] = (99, 0.0, rr1, 'fallback_probe', cc1)

                        if -1 not in best0 and p_neg is not None:
                            rr2 = _find_room_at_point_in_rooms(
                                candidate_rooms_lvl_placeable,
                                p_neg,
                                scan_bbox_ft=scan_bbox_ft,
                                scan_limit=scan_limit,
                            )
                            if rr2 is not None:
                                z2 = _calc_room_target_z(rr2, link_doc, h_ceiling_ft)
                                if z2 is not None:
                                    cc2 = (0.0, wall0, DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z2)), wdir0, False, corner0)
                                    best0[-1] = (99, 0.0, rr2, 'fallback_probe', cc2)

                        if 1 in best0 and -1 in best0:
                            break

                # FINAL FALLBACK: Create synthetic entries for missing sides
                if int(max_per_basket) > 1 and ((1 not in best0) or (-1 not in best0)):
                    try:
                        z_synth = float(getattr(anchor0, 'Z', 0.0))
                    except Exception:
                        z_synth = 0.0
                    placeholder_room = None
                    if best0:
                        try:
                            placeholder_room = list(best0.values())[0][2]
                        except Exception:
                            placeholder_room = None
                    if placeholder_room is None and candidate_rooms_lvl_placeable:
                        try:
                            placeholder_room = candidate_rooms_lvl_placeable[0]
                        except Exception:
                            placeholder_room = None
                    if placeholder_room is not None:
                        try:
                            z_synth = _calc_room_target_z(placeholder_room, link_doc, h_ceiling_ft) or z_synth
                        except Exception:
                            pass
                    for missing_sgn in (1, -1):
                        if missing_sgn not in best0:
                            cc_synth = (0.0, wall0, DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z_synth)), wdir0, False, corner0)
                            best0[missing_sgn] = (99, 0.0, placeholder_room, 'synthetic_both_sides', cc_synth)

                # Accept this wall if we either need only 1 socket, or we have both sides.
                # Also allow a fallback "best wall" even if only one side exists.
                if (not require_two_sides) or int(max_per_basket) <= 1 or (1 in best0 and -1 in best0):
                    return (wall0, anchor0, kind0, corner0, items0, wdir0, best0)

                return None

            # Try candidate walls in order
            picked_data = None
            if wall_order:
                for _p, _s, wid_try in wall_order:
                    try:
                        res0 = _try_pick_wall_with_two_sides(wid_try, require_two_sides=(int(max_per_basket) > 1))
                    except Exception:
                        res0 = None
                    if res0:
                        picked_data = res0
                        break

            # Fallback: use the best wall even if it has only one side
            if picked_data is None and wall_order:
                try:
                    _p, _s, wid0 = wall_order[0]
                    picked_data = _try_pick_wall_with_two_sides(wid0, require_two_sides=False)
                except Exception:
                    picked_data = None

            if picked_data:
                try:
                    chosen_wall, chosen_anchor, chosen_anchor_kind, chosen_corner_origin, chosen_items, wdir_use, best_by_sign = picked_data
                    kind_out = 'corner_anchor' if (chosen_anchor_kind or '').startswith('corner') else 'proj_anchor'
                except Exception:
                    chosen_wall = None
                    chosen_anchor = None
                    chosen_items = []
                    wdir_use = None
                    best_by_sign = None
                    kind_out = None
            if chosen_wall is not None and chosen_anchor is not None and chosen_items and best_by_sign is not None:
                try:
                    chosen_items_sorted = sorted(chosen_items, key=lambda x: (x[0], x[1]))
                except Exception:
                    chosen_items_sorted = list(chosen_items)
                try:
                    cands_for_sides = sorted(room_cands, key=lambda x: (x[0], x[1]))
                except Exception:
                    cands_for_sides = list(room_cands)

                to_place = []
                if int(max_per_basket) <= 1:
                    it0 = None
                    if chosen_items_sorted:
                        it0 = chosen_items_sorted[0]
                    elif cands_for_sides:
                        it0 = cands_for_sides[0]

                    if it0 is not None:
                        try:
                            rr0 = it0[2]
                            z0 = float(it0[4][2].Z)
                        except Exception:
                            rr0 = it0[2] if len(it0) > 2 else None
                            z0 = float(getattr(chosen_anchor, 'Z', 0.0))
                        sgn0 = _room_side_sign(rr0, chosen_wall, DB.XYZ(float(chosen_anchor.X), float(chosen_anchor.Y), float(z0))) if rr0 is not None else 1
                        if sgn0 not in (-1, 1):
                            sgn0 = 1
                        to_place = [(sgn0, it0)]
                else:
                    # Prefer both sides if available
                    for sgn in (1, -1):
                        if sgn in best_by_sign:
                            to_place.append((sgn, best_by_sign[sgn]))

                # Base wall normals
                try:
                    wdir0 = _wall_dir_xy(chosen_wall) or wdir_use
                except Exception:
                    wdir0 = wdir_use
                try:
                    wdir0 = DB.XYZ(float(wdir0.X), float(wdir0.Y), 0.0)
                    wdir0 = wdir0.Normalize() if wdir0.GetLength() > 1e-9 else DB.XYZ.BasisX
                except Exception:
                    wdir0 = DB.XYZ.BasisX
                try:
                    n1_base = DB.XYZ(-float(wdir0.Y), float(wdir0.X), 0.0)
                    n1_base = n1_base.Normalize() if n1_base.GetLength() > 1e-9 else DB.XYZ.BasisY
                    n2_base = DB.XYZ(-float(n1_base.X), -float(n1_base.Y), 0.0)
                except Exception:
                    n1_base = DB.XYZ.BasisY
                    n2_base = DB.XYZ(0.0, -1.0, 0.0)

                bias_ft_base = 0.0
                try:
                    bias_ft_base = float(place_bias_ft or 0.0)
                except Exception:
                    bias_ft_base = 0.0
                try:
                    wth = float(getattr(chosen_wall, 'Width', 0.0) or 0.0)
                    if wth > 1e-6:
                        # Some linked AR walls use a non-centered location line (e.g. Finish Face). To reliably
                        # land on the intended wall side face, push at least the full wall thickness + small pad.
                        bias_ft_base = max(float(bias_ft_base), float(wth) + float(utils_units.mm_to_ft(50)))
                except Exception:
                    pass

                for sgn, it in to_place:
                    if picked >= int(max_per_basket):
                        break
                    try:
                        _pen, _score, cand_room, _cand_kind, cand = it
                    except Exception:
                        continue

                    rid = None
                    try:
                        rid = int(cand_room.Id.IntegerValue)
                    except Exception:
                        rid = None

                    if rid is not None and rid in used_room_ids:
                        continue
                    if rid is not None:
                        used_room_ids.add(rid)

                    # Use the SAME XY anchor, but keep per-room Z (ceiling-based)
                    try:
                        z_target = float(cand[2].Z)
                    except Exception:
                        z_target = float(chosen_anchor.Z)

                    pt_anchor = DB.XYZ(float(chosen_anchor.X), float(chosen_anchor.Y), float(z_target))
                    # Keep the shared anchor on the wall axis so opposite-side bias reliably crosses the wall.
                    pt_base = _wall_axis_project_xy(pt_anchor, chosen_wall) or pt_anchor
                    pt_use = pt_base

                    # Bias into the selected room: strictly by side sign
                    try:
                        n_in = n1_base if int(sgn) >= 0 else n2_base
                        n_try = _pick_room_side_normal_xy(cand_room, chosen_wall, pt_base, step_ft=utils_units.mm_to_ft(200))
                        if n_try is not None:
                            nn = DB.XYZ(float(n_try.X), float(n_try.Y), 0.0)
                            if nn.GetLength() > 1e-9:
                                nn = nn.Normalize()
                                s_try = 1 if float(nn.DotProduct(n1_base)) >= 0.0 else -1
                                if s_try == int(sgn):
                                    n_in = nn
                        if bias_ft_base and float(bias_ft_base) > 1e-9 and n_in is not None:
                            pt_use = DB.XYZ(
                                float(pt_base.X) + float(n_in.X) * float(bias_ft_base),
                                float(pt_base.Y) + float(n_in.Y) * float(bias_ft_base),
                                float(pt_base.Z),
                            )
                    except Exception:
                        pt_use = pt_base

                    # Final guard: do not place inside basket bbox
                    try:
                        if bb_basket is not None and basket_bbox_exclude_ft and _bbox_contains_xy_z(bb_basket, pt_use, pad_xy_ft=float(basket_bbox_exclude_ft), z_tol_ft=basket_bbox_z_tol_ft):
                            dir_push = None
                            try:
                                dv = DB.XYZ(float(pt_use.X) - float(pt_basket.X), float(pt_use.Y) - float(pt_basket.Y), 0.0)
                                dir_push = dv if dv.GetLength() > 1e-9 else None
                            except Exception:
                                dir_push = None
                            if dir_push is None:
                                dir_push = n1_base if int(sgn) >= 0 else n2_base
                            if dir_push is None:
                                continue
                            pt_fix = _push_out_of_bbox_xy(
                                pt_use,
                                bb_basket,
                                dir_push,
                                pad_ft=float(basket_bbox_exclude_ft),
                                step_ft=utils_units.mm_to_ft(50),
                                max_push_ft=utils_units.mm_to_ft(2000),
                            )
                            if pt_fix is None:
                                continue
                            pt_use = pt_fix
                    except Exception:
                        pass

                    try:
                        sc2 = _basket_dist_xy(pt_use, pt_basket, bb_basket)
                    except Exception:
                        sc2 = _score

                    try:
                        if basket_max_dist_ft and float(sc2) > float(basket_max_dist_ft) + 1e-9:
                            continue
                    except Exception:
                        pass

                    # Store stable metadata for idempotency key: (basket_id, wall_side_sign)
                    try:
                        bid_key = int(basket.Id.IntegerValue) if basket else -1
                    except Exception:
                        bid_key = -1
                    try:
                        sgn_key = int(sgn)
                        if sgn_key not in (-1, 1):
                            sgn_key = 1 if sgn_key >= 0 else -1
                    except Exception:
                        sgn_key = 1

                    try:
                        if avoid_ext_wall and pt_basket_probe is not None:
                            probe_ft_w = _probe_ft_for_wall(chosen_wall, base_probe_ft)
                            if _is_facade_wall_for_basket(
                                chosen_wall,
                                pt_use,
                                pt_basket_probe,
                                candidate_rooms_lvl,
                                probe_ft_w,
                                scan_bbox_ft=scan_bbox_ft,
                                scan_limit=scan_limit,
                            ):
                                d['used_exterior'] = int(d.get('used_exterior') or 0) + 1
                    except Exception:
                        pass

                    d['batch'].append((chosen_wall, pt_use, wdir_use, sym, 0.0, (bid_key, sgn_key)))

                    rname = ''
                    try:
                        rname = getattr(cand_room, 'Name', '') or ''
                    except Exception:
                        rname = ''

                    d['plans'].append({
                        'doc_key': doc_key,
                        'kind': kind_out,
                        'room_id': rid,
                        'room_name': rname,
                        'room_obj': cand_room,
                        'basket_id': int(basket.Id.IntegerValue) if basket else -1,
                        'basket_pt_link': pt_basket,
                        'basket_bb': bb_basket,
                        'pt_link': pt_use,
                        'wall_link': chosen_wall,
                        'wall_id': int(chosen_wall.Id.IntegerValue) if chosen_wall is not None else None,
                        'corner_origin': chosen_corner_origin,
                        'side_sign': int(sgn_key),
                        'score_ft': sc2,
                    })

                    picked += 1

            if picked <= 0:
                try:
                    d['skipped'].append((int(basket.Id.IntegerValue), 'no_candidate'))
                except Exception:
                    d['skipped'].append((-1, 'no_candidate'))
                _push_skip_basket(
                    doc_key,
                    basket,
                    'no_candidate',
                    'nearby_rooms={0}, room_cands={1}, avoid_ext={2}'.format(
                        len(nearby_rooms),
                        len(room_cands),
                        bool(avoid_ext_wall),
                    ),
                )
                continue

    total_prepared = 0
    total_skipped = 0
    total_used_ext = 0
    for d in doc_data.values():
        if not d or d.get('skip'):
            continue
        total_prepared += len(d.get('batch') or [])
        total_skipped += len(d.get('skipped') or [])
        total_used_ext += int(d.get('used_exterior') or 0)

    if total_prepared <= 0:
        details = ''
        try:
            if skip_counts:
                keys = sorted(skip_counts.keys())
                parts = []
                for k in keys:
                    parts.append('{0}={1}'.format(k, skip_counts.get(k)))
                if parts:
                    details = '\nПричины пропусков: ' + ', '.join(parts)
        except Exception:
            details = ''
        utils_revit.alert(
            "Не удалось определить места установки розеток.\n"
            "Чаще всего причина — помещение не дает корректные boundary сегменты у фасада или корзина не попадает рядом с помещениями." + details
        )
        return

    planned_instances = 0
    for link_inst, link_doc, doc_key in inst_data:
        d = doc_data.get(doc_key) or {}
        if d.get('skip'):
            continue
        planned_instances += len(d.get('batch') or [])

    # 6. Execute placement for each selected link instance
    sp_cache = {}
    comment_val = (rules.get('comment_tag', 'AUTO_EOM') or 'AUTO_EOM') + ":SOCKET_AC"

    dedupe_tol_ft = utils_units.mm_to_ft(int(rules.get('ac_dedupe_tol_mm', 50) or 50))

    # Sanity: clean up duplicate sockets on the same wall side (too close to each other)
    sanity_deleted_before = 0
    sanity_deleted_after = 0
    try:
        sanity_cleanup = bool(rules.get('ac_sanity_cleanup_duplicates', True))
    except Exception:
        sanity_cleanup = True
    try:
        sanity_spacing_ft = utils_units.mm_to_ft(int(rules.get('ac_sanity_same_side_min_spacing_mm', 250) or 250))
    except Exception:
        sanity_spacing_ft = utils_units.mm_to_ft(250)

    if sanity_cleanup and sanity_spacing_ft and float(sanity_spacing_ft) > 1e-9:
        try:
            sanity_deleted_before = _cleanup_ac_sockets_same_side_duplicates(doc, comment_val, sanity_spacing_ft)
        except Exception:
            sanity_deleted_before = 0

    before_ids, before_elems = _collect_ac_sockets(doc, comment_val)
    existing_idx = _build_point_index(before_elems)
    skipped_existing = 0
    skipped_spacing = 0
    skipped_spacing_keys = set()

    # Key-based idempotency: reuse existing sockets by stable key stored in Comments
    existing_keys = set()
    key_seen = set()
    _key_rx = None
    try:
        _key_rx = re.compile(r'K=(L-?\d+\|B-?\d+\|W-?\d+\|S-?1)(?:\||\s|$)')
    except Exception:
        _key_rx = None

    # Prevent creating duplicates that would later be deleted by sanity cleanup (same wall + side, min spacing)
    side_idx = {}
    if _key_rx and before_elems and sanity_spacing_ft and float(sanity_spacing_ft) > 1e-9:
        for e in before_elems:
            s = None
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                s = p.AsString() if p else None
            except Exception:
                s = None
            if not s or (comment_val not in s):
                continue
            m = None
            try:
                m = _key_rx.search(s)
            except Exception:
                m = None
            if not m:
                continue
            try:
                key0 = m.group(1)
            except Exception:
                continue
            wall_id0 = None
            side0 = None
            try:
                for part in (key0.split('|') or []):
                    if part.startswith('W'):
                        wall_id0 = int(part[1:])
                    elif part.startswith('S'):
                        side0 = int(part[1:])
            except Exception:
                wall_id0 = None
                side0 = None
            if wall_id0 is None or side0 not in (-1, 1):
                continue
            pt0 = None
            try:
                pt0 = socket_utils._inst_center_point(e)
            except Exception:
                pt0 = None
            if pt0 is None:
                continue
            idx0 = side_idx.get((int(wall_id0), int(side0)))
            if idx0 is None:
                idx0 = socket_utils._XYZIndex(cell_ft=1.0)
                side_idx[(int(wall_id0), int(side0))] = idx0
            try:
                idx0.add(pt0.X, pt0.Y, pt0.Z)
            except Exception:
                pass
    if _key_rx and before_elems:
        for e in before_elems:
            s = None
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                s = p.AsString() if p else None
            except Exception:
                s = None
            if not s or (comment_val not in s):
                continue
            m = None
            try:
                m = _key_rx.search(s)
            except Exception:
                m = None
            if not m:
                continue
            try:
                existing_keys.add(m.group(1))
            except Exception:
                continue
    key_seen = set(existing_keys)

    created = created_face = created_wp = created_pt = 0
    skip_nf = skip_np = created_ver = 0

    instances_processed = 0
    for link_inst, link_doc, doc_key in inst_data:
        d = doc_data.get(doc_key) or {}
        if d.get('skip'):
            continue
        batch = d.get('batch') or []
        if not batch:
            continue

        t_total = link_reader.get_total_transform(link_inst)

        # Skip duplicates (existing sockets or duplicated baskets/links)
        link_inst_id = -1
        try:
            link_inst_id = int(link_inst.Id.IntegerValue)
        except Exception:
            try:
                link_inst_id = int(link_inst.Id)
            except Exception:
                link_inst_id = -1

        faces_cache = {}
        filtered_batch = []
        for item in (batch or []):
            try:
                wall_link, pt_link, wall_dir_link, sym_inst, seg_len = item[:5]
            except Exception:
                continue

            meta = None
            try:
                if len(item) > 5:
                    meta = item[5]
            except Exception:
                meta = None

            basket_id = None
            side_sign = None
            if meta is not None:
                try:
                    basket_id = int(meta[0])
                    side_sign = int(meta[1])
                except Exception:
                    basket_id = None
                    side_sign = None
            if side_sign not in (-1, 1):
                side_sign = 1

            wall_id = None
            try:
                wall_id = int(wall_link.Id.IntegerValue) if wall_link else None
            except Exception:
                wall_id = None

            key = None
            item_comment = comment_val
            if basket_id is not None and wall_id is not None and int(link_inst_id) >= 0:
                try:
                    key = u'L{0}|B{1}|W{2}|S{3}'.format(int(link_inst_id), int(basket_id), int(wall_id), int(side_sign))
                    item_comment = u'{0}|K={1}'.format(comment_val, key)
                except Exception:
                    key = None
                    item_comment = comment_val

            if key and (key in key_seen):
                skipped_existing += 1
                continue

            prefer_n_link = None
            try:
                wdir_n = _wall_dir_xy(wall_link) or wall_dir_link
                if wdir_n is not None:
                    wdir_n = DB.XYZ(float(wdir_n.X), float(wdir_n.Y), 0.0)
                    wdir_n = wdir_n.Normalize() if wdir_n.GetLength() > 1e-9 else None
                if wdir_n is not None:
                    n1 = DB.XYZ(-float(wdir_n.Y), float(wdir_n.X), 0.0)
                    n1 = n1.Normalize() if n1.GetLength() > 1e-9 else None
                else:
                    n1 = None
                if n1 is not None:
                    prefer_n_link = n1 if int(side_sign) >= 0 else DB.XYZ(-float(n1.X), -float(n1.Y), 0.0)
            except Exception:
                prefer_n_link = None

            exp_host = _expected_host_point_on_face(link_inst, t_total, wall_link, pt_link, faces_cache, prefer_n_link=prefer_n_link)
            if exp_host is not None and dedupe_tol_ft and existing_idx.has_near(exp_host.X, exp_host.Y, exp_host.Z, dedupe_tol_ft):
                skipped_existing += 1
                continue

            # Same wall-side spacing guard (prevents post-sanity deletions / duplicate outputs)
            try:
                if exp_host is not None and wall_id is not None and sanity_spacing_ft and float(sanity_spacing_ft) > 1e-9:
                    idx_s = side_idx.get((int(wall_id), int(side_sign)))
                    if idx_s is None:
                        idx_s = socket_utils._XYZIndex(cell_ft=1.0)
                        side_idx[(int(wall_id), int(side_sign))] = idx_s
                    if idx_s.has_near(exp_host.X, exp_host.Y, exp_host.Z, float(sanity_spacing_ft)):
                        skipped_spacing += 1
                        try:
                            if key:
                                skipped_spacing_keys.add(key)
                        except Exception:
                            pass
                        continue
            except Exception:
                pass

            # Keep per-item comment and pass preferred wall-side normal (optional) for robust face selection
            filtered_batch.append((wall_link, pt_link, wall_dir_link, sym_inst, seg_len, item_comment, prefer_n_link))

            if key:
                try:
                    key_seen.add(key)
                except Exception:
                    pass

            if exp_host is not None and dedupe_tol_ft:
                try:
                    existing_idx.add(exp_host.X, exp_host.Y, exp_host.Z)
                except Exception:
                    pass

            if exp_host is not None and wall_id is not None and sanity_spacing_ft and float(sanity_spacing_ft) > 1e-9:
                try:
                    idx_s = side_idx.get((int(wall_id), int(side_sign)))
                    if idx_s is None:
                        idx_s = socket_utils._XYZIndex(cell_ft=1.0)
                        side_idx[(int(wall_id), int(side_sign))] = idx_s
                    idx_s.add(exp_host.X, exp_host.Y, exp_host.Z)
                except Exception:
                    pass

        if not filtered_batch:
            instances_processed += 1
            continue

        res = socket_utils._place_socket_batch(
            doc,
            link_inst,
            t_total,
            filtered_batch,
            sym_flags,
            sp_cache,
            comment_val,
            strict_hosting=True,
        )

        try:
            c, cf, cwp, cpt, snf, snp, cver = res
        except Exception:
            try:
                c, cf, cwp, cpt, snf, snp = res
                cver = 0
            except Exception:
                continue

        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)
        skip_nf += int(snf)
        skip_np += int(snp)
        created_ver += int(cver)
        instances_processed += 1

    # Sanity cleanup again after placement (catches duplicates caused by overlapping baskets/links)
    if sanity_cleanup and sanity_spacing_ft and float(sanity_spacing_ft) > 1e-9:
        try:
            sanity_deleted_after = _cleanup_ac_sockets_same_side_duplicates(doc, comment_val, sanity_spacing_ft)
        except Exception:
            sanity_deleted_after = 0

    after_ids, after_elems = _collect_ac_sockets(doc, comment_val)
    new_ids = after_ids.difference(before_ids)
    if new_ids and after_elems:
        after_by_id = {int(e.Id.IntegerValue): e for e in after_elems if e}
        new_elems = [after_by_id[i] for i in new_ids if i in after_by_id]
    else:
        new_elems = []

    # 7. Post-validation (like kitchen tools)
    validation = []
    try:
        plans_expanded = []
        for link_inst, link_doc, doc_key in inst_data:
            d = doc_data.get(doc_key) or {}
            if d.get('skip'):
                continue
            t = link_reader.get_total_transform(link_inst)
            t_inv = None
            try:
                t_inv = t.Inverse
            except Exception:
                t_inv = None

            link_inst_id = None
            try:
                link_inst_id = int(link_inst.Id.IntegerValue)
            except Exception:
                link_inst_id = -1
            for pl in (d.get('plans') or []):
                try:
                    exp_pt = t.OfPoint(pl.get('pt_link')) if t and pl.get('pt_link') else None
                except Exception:
                    exp_pt = None

                wall_id_pl = None
                side_sign_pl = None
                try:
                    wall_id_pl = pl.get('wall_id')
                    side_sign_pl = pl.get('side_sign')
                except Exception:
                    wall_id_pl = None
                    side_sign_pl = None

                plan_key = None
                allow_shared = False
                try:
                    if link_inst_id is not None and int(link_inst_id) >= 0 and pl.get('basket_id') is not None and wall_id_pl is not None and side_sign_pl is not None:
                        plan_key = u'L{0}|B{1}|W{2}|S{3}'.format(int(link_inst_id), int(pl.get('basket_id')), int(wall_id_pl), int(side_sign_pl))
                        allow_shared = bool(plan_key in skipped_spacing_keys)
                except Exception:
                    plan_key = None
                    allow_shared = False
                plans_expanded.append({
                    'doc_key': pl.get('doc_key') or doc_key,
                    'kind': pl.get('kind'),
                    'room_id': pl.get('room_id'),
                    'room_name': pl.get('room_name'),
                    'room_obj': pl.get('room_obj'),
                    'basket_id': pl.get('basket_id'),
                    'basket_pt_link': pl.get('basket_pt_link'),
                    'basket_bb': pl.get('basket_bb'),
                    'wall_link': pl.get('wall_link'),
                    'wall_id': wall_id_pl,
                    'corner_origin': pl.get('corner_origin'),
                    'side_sign': side_sign_pl,
                    'pt_link': pl.get('pt_link'),
                    'expected_pt_host': exp_pt,
                    'plan_key': plan_key,
                    'allow_shared_match': allow_shared,
                    't': t,
                    't_inv': t_inv,
                })

        inst_items = []
        for e in after_elems:
            if not e:
                continue
            try:
                iid = int(e.Id.IntegerValue)
            except Exception:
                iid = None
            pt = socket_utils._inst_center_point(e)
            if pt is None:
                continue
            abs_z = None
            try:
                abs_z = _get_abs_z_from_level_offset(e, doc)
            except Exception:
                abs_z = None
            z_key = abs_z if abs_z is not None else float(pt.Z)
            inst_items.append((iid, e, pt, float(z_key)))

        used_inst = set()
        fix_ops = []
        fix_ids = set()
        fixed_facing = [0]
        opts_v = DB.SpatialElementBoundaryOptions()
        for pl in plans_expanded:
            exp_pt = pl.get('expected_pt_host')
            if exp_pt is None:
                validation.append({
                    'status': 'missing',
                    'doc_key': pl.get('doc_key'),
                    'basket_id': pl.get('basket_id'),
                    'room_id': pl.get('room_id'),
                    'room_name': pl.get('room_name'),
                    'kind': pl.get('kind'),
                })
                continue

            best = None
            best_key = None
            best_dxy = None
            exp_z = float(exp_pt.Z) if hasattr(exp_pt, 'Z') else None

            allow_shared = False
            try:
                allow_shared = bool(pl.get('allow_shared_match'))
            except Exception:
                allow_shared = False

            for iid, inst, pt, z_key in inst_items:
                if (not allow_shared) and (iid in used_inst):
                    continue
                dxy = _dist_xy(pt, exp_pt)
                if validate_match_tol_ft and dxy > float(validate_match_tol_ft):
                    continue
                dz = abs(float(z_key) - float(exp_z)) if exp_z is not None else 0.0
                key = (dz, dxy)
                if best_key is None or key < best_key:
                    best_key = key
                    best = (iid, inst, pt, z_key)
                    best_dxy = dxy

            if best is None or best_dxy is None:
                validation.append({
                    'status': 'missing',
                    'doc_key': pl.get('doc_key'),
                    'basket_id': pl.get('basket_id'),
                    'room_id': pl.get('room_id'),
                    'room_name': pl.get('room_name'),
                    'kind': pl.get('kind'),
                })
                continue

            iid, inst, inst_pt_host, z_key = best
            if not allow_shared:
                used_inst.add(iid)

            # Fix facing direction: face into the intended wall side (stable via stored side_sign)
            try:
                wall_link = pl.get('wall_link')
                side_sign_pl = pl.get('side_sign')
                t0 = pl.get('t')

                wdir = _wall_dir_xy(wall_link)
                if wdir is not None:
                    wdir2 = DB.XYZ(float(wdir.X), float(wdir.Y), 0.0)
                    wdir2 = wdir2.Normalize() if wdir2.GetLength() > 1e-9 else None
                else:
                    wdir2 = None

                if wdir2 is not None:
                    n1 = DB.XYZ(-float(wdir2.Y), float(wdir2.X), 0.0)
                    n1 = n1.Normalize() if n1.GetLength() > 1e-9 else None
                else:
                    n1 = None

                if n1 is not None:
                    n_link = n1 if int(side_sign_pl or 1) >= 0 else DB.XYZ(-float(n1.X), -float(n1.Y), 0.0)
                else:
                    n_link = None

                n_host_want = t0.OfVector(n_link) if (t0 is not None and n_link is not None) else None
            except Exception:
                n_host_want = None

            try:
                if n_host_want is not None and hasattr(inst, 'FacingOrientation'):
                    cur = inst.FacingOrientation
                    cur2 = DB.XYZ(float(cur.X), float(cur.Y), 0.0)
                    want2 = DB.XYZ(float(n_host_want.X), float(n_host_want.Y), 0.0)
                    if cur2.GetLength() > 1e-9 and want2.GetLength() > 1e-9:
                        cur2 = cur2.Normalize()
                        want2 = want2.Normalize()
                        dot = float(cur2.DotProduct(want2))
                        if dot < 0.0:
                            if iid not in fix_ids:
                                fix_ids.add(iid)
                                fix_ops.append((inst, inst_pt_host))
            except Exception:
                pass

            # Height check
            abs_z = None
            try:
                abs_z = _get_abs_z_from_level_offset(inst, doc)
            except Exception:
                abs_z = None
            z_to_check = abs_z if abs_z is not None else float(inst_pt_host.Z)
            height_ok = (exp_z is not None) and (abs(float(z_to_check) - float(exp_z)) <= float(validate_height_tol_ft or utils_units.mm_to_ft(20)))
            dz_ft = abs(float(z_to_check) - float(exp_z)) if exp_z is not None else None

            # Transform instance point to link coordinates (for wall/basket/corner checks)
            inst_pt_link = None
            try:
                inst_pt_link = pl.get('t_inv').OfPoint(inst_pt_host) if pl.get('t_inv') else None
            except Exception:
                inst_pt_link = None

            # On-wall check vs planned wall axis
            wall_link = pl.get('wall_link')
            dist_wall = _wall_axis_dist_xy(inst_pt_link, wall_link) if inst_pt_link is not None else None
            try:
                wall_tol = float(validate_wall_dist_ft or utils_units.mm_to_ft(150))
            except Exception:
                wall_tol = float(utils_units.mm_to_ft(150))

            on_wall_ok = False
            if dist_wall is not None:
                try:
                    dw = float(dist_wall)
                except Exception:
                    dw = None

                if dw is not None:
                    # Basic check (close to wall location line)
                    if float(dw) <= float(wall_tol) + 1e-9:
                        on_wall_ok = True
                    else:
                        # Account for wall thickness when distance is measured to a face-based location line.
                        try:
                            wth = float(getattr(wall_link, 'Width', 0.0) or 0.0)
                        except Exception:
                            wth = 0.0
                        if wth and float(wth) > 1e-6:
                            try:
                                if abs(float(dw) - (float(wth) * 0.5)) <= float(wall_tol) + 1e-9:
                                    on_wall_ok = True
                                elif abs(float(dw) - float(wth)) <= float(wall_tol) + 1e-9:
                                    on_wall_ok = True
                            except Exception:
                                pass

            # Exterior wall check
            ext_wall_ok = True
            if avoid_ext_wall:
                try:
                    ext_wall_ok = bool(wall_link is not None) and (not _is_exterior_wall(wall_link))
                except Exception:
                    ext_wall_ok = True

            # Basket distance check (in link XY)
            basket_pt = pl.get('basket_pt_link')
            bb_basket = pl.get('basket_bb')
            dist_basket = _basket_dist_xy(inst_pt_link, basket_pt, bb_basket) if (inst_pt_link is not None and basket_pt is not None) else None
            basket_ok = (dist_basket is not None) and (float(dist_basket) <= float(basket_max_dist_ft or utils_units.mm_to_ft(3000)))

            # Basket bbox clearance check (avoid placing inside the basket itself)
            basket_clear_ok = True
            try:
                if bb_basket is not None and basket_bbox_exclude_ft:
                    basket_clear_ok = (not _bbox_contains_xy_z(bb_basket, inst_pt_link, pad_xy_ft=float(basket_bbox_exclude_ft), z_tol_ft=basket_bbox_z_tol_ft))
            except Exception:
                basket_clear_ok = True

            # Corner offset check (only for corner-based candidates)
            corner_ok = True
            corner_d = None
            try:
                kind = pl.get('kind') or ''
            except Exception:
                kind = ''
            if kind.startswith('corner'):
                corner_origin = pl.get('corner_origin')
                if inst_pt_link is not None:
                    if corner_origin is not None:
                        # Prefer along-wall distance so perpendicular bias doesn't skew the corner offset.
                        wdir = _wall_dir_xy(pl.get('wall_link'))
                        if wdir is not None:
                            try:
                                wdir2 = DB.XYZ(float(wdir.X), float(wdir.Y), 0.0)
                                wdir2 = wdir2.Normalize() if wdir2.GetLength() > 1e-9 else None
                            except Exception:
                                wdir2 = None
                        else:
                            wdir2 = None

                        if wdir2 is not None:
                            try:
                                vv = DB.XYZ(
                                    float(inst_pt_link.X) - float(corner_origin.X),
                                    float(inst_pt_link.Y) - float(corner_origin.Y),
                                    0.0,
                                )
                                corner_d = abs(float(vv.DotProduct(wdir2)))
                            except Exception:
                                corner_d = _dist_xy(inst_pt_link, corner_origin)
                        else:
                            corner_d = _dist_xy(inst_pt_link, corner_origin)
                    else:
                        corner_d = _min_room_corner_dist_xy(pl.get('room_obj'), inst_pt_link, opts_v)

                # bbox clearance can move the point farther from the corner; enforce only the minimum offset
                tol_ft = float(validate_offset_tol_ft or utils_units.mm_to_ft(100))
                corner_ok = (corner_d is not None) and (float(corner_d) + float(tol_ft) >= float(offset_corner_ft))

            ok = bool(height_ok and on_wall_ok and ext_wall_ok and basket_ok and basket_clear_ok and corner_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'doc_key': pl.get('doc_key'),
                'basket_id': pl.get('basket_id'),
                'room_id': pl.get('room_id'),
                'room_name': pl.get('room_name'),
                'kind': kind,
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
                'ext_wall_ok': bool(ext_wall_ok),
                'basket_ok': bool(basket_ok),
                'basket_clear_ok': bool(basket_clear_ok),
                'corner_ok': bool(corner_ok),
                'match_dxy_ft': best_dxy,
                'dist_wall_ft': dist_wall,
                'dist_basket_ft': dist_basket,
                'corner_dist_ft': corner_d,
                'dz_ft': dz_ft,
            })

        if fix_ops:
            try:
                with utils_revit.tx('ЭОМ: Развернуть розетки AC', doc=doc, swallow_warnings=True):
                    for inst, pt0 in fix_ops:
                        if not inst:
                            continue
                        try:
                            loc = getattr(inst, 'Location', None)
                            p = loc.Point if loc and hasattr(loc, 'Point') else None
                        except Exception:
                            p = None
                        origin = p or pt0
                        if origin is None:
                            continue
                        try:
                            axis = DB.Line.CreateBound(origin, origin + DB.XYZ.BasisZ)
                            inst.Location.Rotate(axis, math.pi)
                            fixed_facing[0] = int(fixed_facing[0] or 0) + 1
                        except Exception:
                            continue
            except Exception:
                pass
    except Exception:
        try:
            logger.error('Validation failed')
        except Exception:
            pass

    # 8. Output logging (pyRevit output)
    try:
        output.print_md(
            'Тип: **{0}**\n\nПодготовлено: **{1}**\nОжидалось: **{2}**\nСоздано: **{3}** (Face: {4}, WorkPlane: {5}, Point: {6}, Verified: {7})\nПропущено: **{8}** (no_face: {9}, no_place: {10})\nПропущено (уже есть): **{11}**\nПропущено (spacing): **{12}**\nУдалено дублей (sanity): **{13}**'.format(
                sym_lbl or u'<Розетка>',
                total_prepared,
                planned_instances,
                created,
                created_face,
                created_wp,
                created_pt,
                created_ver,
                total_skipped,
                skip_nf,
                skip_np,
                skipped_existing,
                skipped_spacing,
                int(sanity_deleted_before or 0) + int(sanity_deleted_after or 0),
            )
        )
    except Exception:
        pass

    if validation:
        okc = len([x for x in validation if x.get('status') == 'ok'])
        failc = len([x for x in validation if x.get('status') == 'fail'])
        missc = len([x for x in validation if x.get('status') == 'missing'])
        try:
            output.print_md('Проверка: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(okc, failc, missc))
        except Exception:
            pass

        if failc or missc:
            try:
                output.print_md('Нарушения (первые {0}):'.format(int(debug_validation_limit)))
            except Exception:
                pass
            shown = 0
            for x in validation:
                st = x.get('status')
                if st == 'ok':
                    continue
                if shown >= int(debug_validation_limit):
                    break
                shown += 1

                doc_key = x.get('doc_key')
                bid = x.get('basket_id')
                rid = x.get('room_id')
                rnm = x.get('room_name')
                kind = x.get('kind')

                if st == 'missing':
                    try:
                        output.print_md('- basket #{0} / room #{1} {2} ({3}) [{4}]: не найден созданный экземпляр'.format(
                            bid, rid, rnm, kind, doc_key
                        ))
                    except Exception:
                        pass
                    continue

                dw = utils_units.ft_to_mm(x.get('dist_wall_ft'))
                db = utils_units.ft_to_mm(x.get('dist_basket_ft'))
                dc = utils_units.ft_to_mm(x.get('corner_dist_ft'))
                dz = utils_units.ft_to_mm(x.get('dz_ft'))
                md = utils_units.ft_to_mm(x.get('match_dxy_ft'))

                try:
                    output.print_md(
                        '- id {0} / basket #{1} / room #{2} {3} ({4}) [{5}]: height={6}, on_wall={7}, corner={8}, basket={9}, basket_clear={10}, avoid_ext={11} (match={12}mm, wall={13}mm, basket={14}mm, corner={15}mm, dz={16}mm)'.format(
                            x.get('id'),
                            bid,
                            rid,
                            rnm,
                            kind,
                            doc_key,
                            x.get('height_ok'),
                            x.get('on_wall_ok'),
                            x.get('corner_ok'),
                            x.get('basket_ok'),
                            x.get('basket_clear_ok'),
                            x.get('ext_wall_ok'),
                            int(round(md)) if md is not None else u'-',
                            int(round(dw)) if dw is not None else u'-',
                            int(round(db)) if db is not None else u'-',
                            int(round(dc)) if dc is not None else u'-',
                            int(round(dz)) if dz is not None else u'-',
                        )
                    )
                except Exception:
                    pass

    if skip_counts:
        try:
            keys = sorted(skip_counts.keys())
            parts = []
            for k in keys:
                parts.append('{0}={1}'.format(k, skip_counts.get(k)))
            output.print_md('Причины пропусков (шт.): {0}'.format(', '.join(parts)))
        except Exception:
            pass

    if skipped_details:
        try:
            output.print_md('Пропущенные корзины/блоки (первые {0}):'.format(len(skipped_details)))
        except Exception:
            pass
        for x in skipped_details:
            try:
                output.print_md('- [{0}] basket #{1}: {2}{3}'.format(
                    x.get('doc_key'),
                    x.get('basket_id'),
                    x.get('reason') or '',
                    (u' — ' + x.get('details')) if x.get('details') else u'',
                ))
            except Exception:
                pass
        if skipped_details_more[0]:
            try:
                output.print_md('- …и еще пропущено: **{0}** (увеличьте kitchen_debug_skipped_rooms_limit)'.format(int(skipped_details_more[0])))
            except Exception:
                pass

    # 9. Summary
    msg = (
        "Связей обработано: {inst}\n"
        "Найдено корзин/блоков (в файлах связи): {found}\n"
        "Подготовлено точек: {prep} (пропущено: {sk})\n"
        "Ожидалось розеток (с учетом связей): {plan}\n\n"
        "Создано розеток: {c}\n(Face: {cf}, WorkPlane: {cwp}, Point: {cpt})\n\n"
        "Пропущено при установке: {snp}\n"
        "Пропущено (уже есть): {se}\n"
        "Пропущено (spacing): {ssp}\n"
        "Удалено дублей (sanity): {sd}\n"
    ).format(
        inst=instances_processed,
        found=total_found,
        prep=total_prepared,
        sk=total_skipped,
        plan=planned_instances,
        c=created,
        cf=created_face,
        cwp=created_wp,
        cpt=created_pt,
        snp=skip_np,
        se=skipped_existing,
        ssp=skipped_spacing,
        sd=int(sanity_deleted_before or 0) + int(sanity_deleted_after or 0),
    )

    if validation:
        try:
            okc = len([x for x in validation if x.get('status') == 'ok'])
            failc = len([x for x in validation if x.get('status') == 'fail'])
            missc = len([x for x in validation if x.get('status') == 'missing'])
            msg += "\nПроверка: OK={0}, FAIL={1}, MISSING={2} (см. Output)".format(okc, failc, missc)
        except Exception:
            pass

    if total_skipped > 0:
        ids = []
        try:
            for dd in doc_data.values():
                for sid, _reason in (dd.get('skipped') or []):
                    if sid and sid > 0:
                        ids.append(str(sid))
                        if len(ids) >= 10:
                            break
                if len(ids) >= 10:
                    break
        except Exception:
            ids = []
        if ids:
            msg += "\nПропущены корзины/блоки (ID, первые 10): " + ", ".join(ids)

    if total_used_ext > 0 and avoid_ext_wall:
        msg += "\nВНИМАНИЕ: для {0} точек выбранa внешняя стена (fallback).".format(total_used_ext)

    choice = forms.alert(
        msg + "\n\nОткрыть план для проверки?",
        title="Готово",
        warn_icon=False,
        options=["Открыть (План)", "Закрыть"],
    )

    if choice == "Открыть (План)":
        try:
            elems_for_view = new_elems if new_elems else after_elems
            _open_plan_check_view(doc, revit.uidoc, elems_for_view)
        except Exception as e:
            utils_revit.alert("Не удалось открыть план: {}".format(e))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        utils_revit.log_exception('Error in 04_AC')





