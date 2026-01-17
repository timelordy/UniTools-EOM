# -*- coding: utf-8 -*-
import math

from pyrevit import DB, forms, revit, script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception, tx
from utils_units import mm_to_ft
import socket_utils as su


doc = revit.doc
output = script.get_output()


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _dist_xy(a, b):
    try:
        return ((float(a.X) - float(b.X)) ** 2 + (float(a.Y) - float(b.Y)) ** 2) ** 0.5
    except Exception:
        return 1e9


def _closest_point_on_segment_xy(p, a, b):
    if p is None or a is None or b is None:
        return None
    try:
        ax, ay = float(a.X), float(a.Y)
        bx, by = float(b.X), float(b.Y)
        px, py = float(p.X), float(p.Y)
        vx, vy = (bx - ax), (by - ay)
        denom = (vx * vx + vy * vy)
        if denom <= 1e-12:
            return DB.XYZ(ax, ay, float(p.Z) if hasattr(p, 'Z') else 0.0)
        t = ((px - ax) * vx + (py - ay) * vy) / denom
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        return DB.XYZ(ax + vx * t, ay + vy * t, float(p.Z) if hasattr(p, 'Z') else 0.0)
    except Exception:
        return None


def _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    try:
        x, y = float(pt.X), float(pt.Y)
        minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
        maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
        return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)
    except Exception:
        return False


def _is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        return bool(room.IsPointInRoom(point))
    except Exception:
        return False


def _points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []

    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None

    zmid = None
    zmin = None
    zmax = None
    ztol = mm_to_ft(200)
    if room_bb:
        try:
            zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
            zmin = float(min(room_bb.Min.Z, room_bb.Max.Z)) - float(ztol)
            zmax = float(max(room_bb.Min.Z, room_bb.Max.Z)) + float(ztol)
        except Exception:
            zmid = None
            zmin = None
            zmax = None

    selected = []
    for pt in points:
        if pt is None:
            continue

        if (zmin is not None) and (zmax is not None):
            try:
                z = float(pt.Z)
                if z < float(zmin) or z > float(zmax):
                    continue
            except Exception:
                pass

        if room_bb:
            try:
                min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, room_bb.Min.Z)
                max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, room_bb.Max.Z)
                if not _bbox_contains_point_xy(pt, min_exp, max_exp):
                    continue
            except Exception:
                pass

        if _is_point_in_room(room, pt):
            selected.append(pt)
            continue

        pt_room = None
        if zmid is not None:
            try:
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), float(zmid))
            except Exception:
                pt_room = None

        if pt_room and _is_point_in_room(room, pt_room):
            selected.append(pt)
            continue

        # Boundary-adjacent tolerance: probe inward towards room bbox center
        try:
            if room_bb:
                rc = DB.XYZ(
                    (room_bb.Min.X + room_bb.Max.X) * 0.5,
                    (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                    float(pt_room.Z) if pt_room else float(pt.Z)
                )
                v = rc - (pt_room if pt_room else pt)
                if v and v.GetLength() > mm_to_ft(1):
                    vn = v.Normalize()
                    for dmm in (200, 500, 900):
                        probe = (pt_room if pt_room else pt) + vn * mm_to_ft(dmm)
                        if _is_point_in_room(room, probe):
                            selected.append(pt)
                            break
        except Exception:
            pass

    return selected


def _nearest_segment(pt, segs):
    best = None
    best_proj = None
    best_d = None
    for p0, p1, wall in segs or []:
        proj = _closest_point_on_segment_xy(pt, p0, p1)
        if proj is None:
            continue
        d = _dist_xy(pt, proj)
        if best_d is None or d < best_d:
            best = (p0, p1, wall)
            best_proj = proj
            best_d = d
    return best, best_proj, best_d


def _cross2d(ax, ay, bx, by):
    return float(ax) * float(by) - float(ay) * float(bx)


def _ray_segment_intersection_2d(ro, rd, a, b):
    if ro is None or rd is None or a is None or b is None:
        return None
    try:
        rdx, rdy = float(rd.X), float(rd.Y)
        sdx, sdy = float(b.X - a.X), float(b.Y - a.Y)
        denom = _cross2d(rdx, rdy, sdx, sdy)
        if abs(float(denom)) < 1e-9:
            return None
        qpx, qpy = float(a.X - ro.X), float(a.Y - ro.Y)
        t = _cross2d(qpx, qpy, sdx, sdy) / float(denom)
        u = _cross2d(qpx, qpy, rdx, rdy) / float(denom)
        if t >= 0.0 and 0.0 <= u <= 1.0:
            return float(t)
    except Exception:
        return None
    return None


def _get_wall_segments(room, link_doc):
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
        if su._is_curtain_wall(el):
            continue

        try:
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
        except Exception:
            continue
        segs.append((p0, p1, el))

    return segs


def _get_comments_text(elem):
    if elem is None:
        return u''
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    for nm in (u'Комментарии', u'Comments'):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsString()
                if v:
                    return v
        except Exception:
            continue
    return u''


def _collect_tagged_instances(host_doc, tag_value):
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
                c = _get_comments_text(e)
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


def _try_set_offset_from_level(inst, off_ft):
    if inst is None or off_ft is None:
        return False
    try:
        off = float(off_ft)
    except Exception:
        return False

    try:
        p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
            p.Set(off)
            return True
    except Exception:
        pass

    for nm in (
        u'Отметка от уровня',
        u'Смещение от уровня',
        u'Elevation from Level',
        u'Offset from Level',
    ):
        try:
            p = inst.LookupParameter(nm)
            if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                p.Set(off)
                return True
        except Exception:
            continue

    return False


def _is_socket_instance(inst):
    if inst is None:
        return False
    try:
        sym = inst.Symbol
    except Exception:
        sym = None
    try:
        lbl = placement_engine.format_family_type(sym) if sym else ''
    except Exception:
        lbl = ''
    t = _norm(lbl)
    if not t:
        return False
    return (
        (u'рзт' in t)
        or (u'р3т' in t)
        or (u'p3t' in t)
        or (u'розет' in t)
        or (u'socket' in t)
        or (u'outlet' in t)
    )


def _collect_host_socket_instances(host_doc):
    items = []
    if host_doc is None:
        return items
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
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
            if not _is_socket_instance(e):
                continue
            pt = su._inst_center_point(e)
            if pt:
                items.append((e, pt))
    return items


def _collect_family_instance_points_by_symbol_id(link_doc, symbol_id_int):
    pts = []
    if link_doc is None or symbol_id_int is None:
        return pts
    try:
        want = int(symbol_id_int)
    except Exception:
        return pts
    try:
        col = (
            DB.FilteredElementCollector(link_doc)
            .OfClass(DB.FamilyInstance)
            .WhereElementIsNotElementType()
        )
    except Exception:
        col = None
    if not col:
        return pts
    for inst in col:
        try:
            sid = int(inst.Symbol.Id.IntegerValue)
        except Exception:
            continue
        if sid != want:
            continue
        try:
            pt = su._inst_center_point(inst)
        except Exception:
            pt = None
        if pt:
            pts.append(pt)
    return pts


def _pick_linked_element_any(link_inst, prompt):
    if link_inst is None:
        return None

    uidoc = revit.uidoc
    if uidoc is None:
        return None

    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class _AnyLinkedFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return elem and elem.Id == link_inst.Id
            except Exception:
                return False

        def AllowReference(self, reference, position):
            try:
                if reference is None:
                    return False
                if reference.ElementId != link_inst.Id:
                    return False
                if reference.LinkedElementId is None or reference.LinkedElementId == DB.ElementId.InvalidElementId:
                    return False
                return True
            except Exception:
                return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.LinkedElement, _AnyLinkedFilter(), prompt)
    except Exception:
        return None

    try:
        if r is None or r.ElementId != link_inst.Id:
            return None
    except Exception:
        return None

    ldoc = link_inst.GetLinkDocument()
    if ldoc is None:
        return None
    try:
        return ldoc.GetElement(r.LinkedElementId)
    except Exception:
        return None


def _try_get_room_at_point(doc_, pt):
    if doc_ is None or pt is None:
        return None
    try:
        r = doc_.GetRoomAtPoint(pt)
        if r is not None:
            return r
    except Exception:
        pass
    for z in (0.0, mm_to_ft(1500), mm_to_ft(3000)):
        try:
            r = doc_.GetRoomAtPoint(DB.XYZ(float(pt.X), float(pt.Y), float(z)))
            if r is not None:
                return r
        except Exception:
            continue
    return None


def _seg_dir(p0, p1):
    try:
        v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
        if v.GetLength() <= 1e-9:
            return None
        return v.Normalize()
    except Exception:
        return None


def _seg_len_ft(p0, p1):
    try:
        return float(p0.DistanceTo(p1))
    except Exception:
        try:
            return float(_dist_xy(p0, p1))
        except Exception:
            return 0.0


def _point_at_t(p0, p1, t, z=None):
    try:
        tt = float(t)
    except Exception:
        return None
    try:
        z0 = float(z) if z is not None else float(p0.Z)
    except Exception:
        z0 = 0.0
    try:
        return DB.XYZ(
            float(p0.X) + (float(p1.X) - float(p0.X)) * tt,
            float(p0.Y) + (float(p1.Y) - float(p0.Y)) * tt,
            z0,
        )
    except Exception:
        return None


def main():
    output.print_md('# 03. Кухня: Общие (вне гарнитура) (300мм)')

    rules = config_loader.load_rules()
    cfg = script.get_config()

    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SOCKET_KITCHEN_GENERAL'.format(comment_tag)
    comment_value_unit = '{0}:SOCKET_KITCHEN_UNIT'.format(comment_tag)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or [u'кухн', u'kitchen', u'столов']
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    total_target = int(rules.get('kitchen_total_sockets', 4) or 4)

    height_mm = int(rules.get('kitchen_general_height_mm', 300) or 300)
    height_ft = mm_to_ft(height_mm)

    fridge_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fridge_max_dist_mm', 1500) or 1500))

    wall_end_clear_mm = int(rules.get('kitchen_wall_end_clear_mm', 100) or 100)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', 300) or 300)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', 25) or 25)

    validate_match_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_match_tol_mm', 2000) or 2000))
    validate_height_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_height_tol_mm', 20) or 20))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('kitchen_validate_wall_dist_mm', 150) or 150))
    debug_no_candidates_limit = int(rules.get('kitchen_debug_no_candidates_limit', 3) or 3)
    debug_skipped_rooms_limit = int(rules.get('kitchen_debug_skipped_rooms_limit', 20) or 20)
    existing_dedupe_mm = int(rules.get('kitchen_existing_dedupe_mm', 200) or 200)

    fams = rules.get('family_type_names', {})
    prefer = (
        fams.get('socket_kitchen_general')
        or fams.get('socket_ac')
        or fams.get('socket_general')
        or fams.get('power_socket')
    )
    sym, sym_lbl, top10 = su._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_kitchen_general')
    if not sym:
        # Fallback: pick by exact names even if placement type is unsupported
        def _try_pick_any(names):
            if not names: return None
            if not isinstance(names, (list, tuple)):
                names = [names]
            for n in names:
                if not n: continue
                try: sym0 = su._find_symbol_by_fullname(doc, n)
                except Exception: sym0 = None
                if sym0: return sym0
            return None

        sym = _try_pick_any(prefer)
        if sym:
            try: sym_lbl = placement_engine.format_family_type(sym)
            except Exception: sym_lbl = None
            output.print_md(u'**Внимание:** выбранный тип розетки не поддерживает размещение по грани/стене. Будет использован OneLevel/WorkPlane режим, если доступно.')
        else:
            alert('Не найден тип розетки для кухни (общие, вне гарнитура).')
            if top10:
                output.print_md('Доступные варианты:')
                for x in top10:
                    output.print_md('- {0}'.format(x))
            return

    try:
        su._store_symbol_id(cfg, 'last_socket_kitchen_general_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_general_symbol_uid', sym)
        script.save_config()
    except Exception:
        pass

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst:
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        return

    t = link_reader.get_total_transform(link_inst)
    try:
        t_inv = t.Inverse if t else None
    except Exception:
        t_inv = None

    raw_rooms = su._get_all_linked_rooms(link_doc, limit=int(rules.get('scan_limit_rooms', 200) or 200))

    # --- sinks / stoves / fridges detection ---
    sinks_all = []
    try:
        sink_sym_uid = getattr(cfg, 'kitchen_sink_link_symbol_uid', None)
        sink_sym_id = getattr(cfg, 'kitchen_sink_link_symbol_id', None)
        sink_sym = None
        if sink_sym_uid:
            try:
                sink_sym = link_doc.GetElement(str(sink_sym_uid))
            except Exception:
                sink_sym = None
        if (sink_sym is None) and sink_sym_id is not None:
            try:
                sink_sym = link_doc.GetElement(DB.ElementId(int(sink_sym_id)))
            except Exception:
                sink_sym = None
        if sink_sym is not None:
            try:
                sinks_all = _collect_family_instance_points_by_symbol_id(link_doc, int(sink_sym.Id.IntegerValue))
            except Exception:
                sinks_all = []
    except Exception:
        sinks_all = []

    if not sinks_all:
        sinks_all = su._collect_sinks_points(link_doc, rules)

    if not sinks_all:
        try:
            pick = forms.alert(
                'Не найдено раковин в связи АР.\n\nВыберите ОДНУ мойку в связи, чтобы скрипт смог найти все такие мойки (по типу).',
                yes=True, no=True
            )
        except Exception:
            pick = False
        if pick:
            e = _pick_linked_element_any(link_inst, 'Выберите мойку (связь АР)')
            if e is not None and isinstance(e, DB.FamilyInstance):
                try:
                    sym0 = e.Symbol
                except Exception:
                    sym0 = None
                if sym0 is not None:
                    try:
                        sinks_all = _collect_family_instance_points_by_symbol_id(link_doc, int(sym0.Id.IntegerValue))
                    except Exception:
                        sinks_all = []
                    if sinks_all:
                        try:
                            setattr(cfg, 'kitchen_sink_link_symbol_id', int(sym0.Id.IntegerValue))
                        except Exception:
                            pass
                        try:
                            setattr(cfg, 'kitchen_sink_link_symbol_uid', str(sym0.UniqueId))
                        except Exception:
                            pass
                        try:
                            script.save_config()
                        except Exception:
                            pass

    stoves_all = su._collect_stoves_points(link_doc, rules)

    fridges_all = []
    try:
        fridge_sym_uid = getattr(cfg, 'kitchen_fridge_link_symbol_uid', None)
        fridge_sym_id = getattr(cfg, 'kitchen_fridge_link_symbol_id', None)
        fridge_sym = None
        if fridge_sym_uid:
            try:
                fridge_sym = link_doc.GetElement(str(fridge_sym_uid))
            except Exception:
                fridge_sym = None
        if (fridge_sym is None) and fridge_sym_id is not None:
            try:
                fridge_sym = link_doc.GetElement(DB.ElementId(int(fridge_sym_id)))
            except Exception:
                fridge_sym = None
        if fridge_sym is not None:
            try:
                fridges_all = _collect_family_instance_points_by_symbol_id(link_doc, int(fridge_sym.Id.IntegerValue))
            except Exception:
                fridges_all = []
    except Exception:
        fridges_all = []

    if not fridges_all:
        try:
            fridges_all = su._collect_fridges_points(link_doc, rules)
        except Exception:
            fridges_all = []

    if not fridges_all:
        try:
            pick = forms.alert(
                'Не найдено холодильников в связи АР.\n\nВыберите ОДИН холодильник в связи, чтобы скрипт смог найти все такие холодильники (по типу).',
                yes=True, no=True
            )
        except Exception:
            pick = False
        if pick:
            e = _pick_linked_element_any(link_inst, 'Выберите холодильник (связь АР)')
            if e is not None and isinstance(e, DB.FamilyInstance):
                try:
                    sym0 = e.Symbol
                except Exception:
                    sym0 = None
                if sym0 is not None:
                    try:
                        fridges_all = _collect_family_instance_points_by_symbol_id(link_doc, int(sym0.Id.IntegerValue))
                    except Exception:
                        fridges_all = []
                    if fridges_all:
                        try:
                            setattr(cfg, 'kitchen_fridge_link_symbol_id', int(sym0.Id.IntegerValue))
                        except Exception:
                            pass
                        try:
                            setattr(cfg, 'kitchen_fridge_link_symbol_uid', str(sym0.UniqueId))
                        except Exception:
                            pass
                        try:
                            script.save_config()
                        except Exception:
                            pass

    output.print_md(
        'Раковины: **{0}**; Электроплиты: **{1}**; Холодильники: **{2}**'.format(
            len(sinks_all or []), len(stoves_all or []), len(fridges_all or [])
        )
    )

    # Rooms selection: by name patterns + rooms that contain a stove
    rooms_by_id = {}
    for r in (raw_rooms or []):
        try:
            if kitchen_rx and (not su._match_any(kitchen_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    for pt in (stoves_all or []):
        r = _try_get_room_at_point(link_doc, pt)
        if r is None:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    # Also include sink-rooms only if they match kitchen patterns (avoid bathrooms)
    for pt in (sinks_all or []):
        r = _try_get_room_at_point(link_doc, pt)
        if r is None:
            continue
        try:
            if kitchen_rx and (not su._match_any(kitchen_rx, su._room_text(r))):
                continue
        except Exception:
            continue
        try:
            rooms_by_id[int(r.Id.IntegerValue)] = r
        except Exception:
            continue

    rooms = [rooms_by_id[k] for k in sorted(rooms_by_id.keys())]
    if not rooms:
        alert('Нет помещений кухни (по паттернам и/или по электроплите).')
        return

    host_sockets = _collect_host_socket_instances(doc)

    # Existing kitchen-unit sockets (to infer kitchen unit wall)
    try:
        _ids_unit, _elems_unit, pts_unit_host = _collect_tagged_instances(doc, comment_value_unit)
    except Exception:
        pts_unit_host = []

    pts_unit_link = []
    if pts_unit_host and t_inv:
        for p in pts_unit_host:
            try:
                pts_unit_link.append(t_inv.OfPoint(p))
            except Exception:
                continue

    try:
        ids_before, _elems_before, _pts_before = _collect_tagged_instances(doc, comment_value)
    except Exception:
        ids_before = set()
        _pts_before = []

    tagged_link_pts = []
    if _pts_before and t_inv:
        for p in _pts_before:
            try:
                tagged_link_pts.append(t_inv.OfPoint(p))
            except Exception:
                continue

    # Fix height for already placed kitchen-general sockets (tagged)
    fixed_existing = 0
    try:
        _ids0, elems0, _pts0 = _collect_tagged_instances(doc, comment_value)
        if elems0:
            with tx('ЭОМ: Кухня общие — исправить высоту', doc=doc, swallow_warnings=True):
                for e0 in elems0:
                    if _try_set_offset_from_level(e0, height_ft):
                        fixed_existing += 1
    except Exception:
        fixed_existing = 0

    sym_flags = {}
    try:
        pt_enum = sym.Family.FamilyPlacementType
        sym_flags[int(sym.Id.IntegerValue)] = (
            pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
            pt_enum == DB.FamilyPlacementType.OneLevelBased,
        )
    except Exception:
        sym_flags[int(sym.Id.IntegerValue)] = (False, False)

    strict_hosting_mode = True
    try:
        if sym_flags.get(int(sym.Id.IntegerValue), (False, False))[1]:
            strict_hosting_mode = False
            output.print_md(u'**Внимание:** тип розетки OneLevelBased - размещение будет без хоста.')
    except Exception:
        pass

    sp_cache = {}
    pending = []
    plans = []

    created = created_face = created_wp = created_pt = 0
    skipped = 0
    skip_no_segs = 0
    skip_full = 0
    skip_no_fixtures = 0
    skip_not_kitchen = 0
    skip_no_candidates = 0
    prepared = 0
    debug_no_candidates_shown = 0

    skipped_details = []
    skipped_details_more = [0]

    def _push_skip(room, reason, details=None):
        try:
            lim = int(debug_skipped_rooms_limit or 0)
        except Exception:
            lim = 0
        if lim <= 0:
            return
        if len(skipped_details) >= lim:
            skipped_details_more[0] += 1
            return
        try:
            rid = int(room.Id.IntegerValue)
        except Exception:
            rid = None
        try:
            rnm = su._room_text(room)
        except Exception:
            rnm = u''
        skipped_details.append({
            'room_id': rid,
            'room_name': rnm,
            'reason': reason,
            'details': details or u''
        })

    parallel_tol = 0.95

    with forms.ProgressBar(title='03. Кухня (общие)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            segs = _get_wall_segments(room, link_doc)
            if not segs:
                skipped += 1
                skip_no_segs += 1
                _push_skip(room, 'segs', u'нет сегментов стен')
                continue

            sinks = _points_in_room(sinks_all, room)
            stoves = _points_in_room(stoves_all, room)
            fridges = _points_in_room(fridges_all, room)

            if not sinks and not stoves and not fridges:
                skipped += 1
                skip_no_fixtures += 1
                _push_skip(room, 'fixtures', u'не найдены мойка/плита/холодильник')
                continue

            # For rooms that don't look like a kitchen by name (e.g. "Гостиная"),
            # only proceed when BOTH sink and stove are detected in-room.
            is_named_kitchen = True
            try:
                is_named_kitchen = (not kitchen_rx) or su._match_any(kitchen_rx, su._room_text(room))
            except Exception:
                is_named_kitchen = True
            if (not is_named_kitchen) and (not (sinks and stoves) and not fridges):
                skipped += 1
                skip_not_kitchen += 1
                _push_skip(
                    room,
                    'fixtures',
                    u'не кухня по названию и нет пары (мойка+плита/холодильник); sinks={0}, stoves={1}, fridges={2}'.format(
                        len(sinks or []), len(stoves or []), len(fridges or [])
                    )
                )
                continue

            base_z = su._room_level_elevation_ft(room, link_doc)
            z_target = float(base_z) + float(height_ft)
            height_match_tol_ft = max(float(validate_height_tol_ft or 0.0), mm_to_ft(200))

            # Count existing sockets in this kitchen room (all sockets)
            # Dedupe near-coincident sockets (e.g., double sockets made of two shared instances)
            existing_link_pts = []
            existing_cnt = 0
            existing_idx = su._XYZIndex(cell_ft=1.0)
            existing_dedupe_ft = mm_to_ft(existing_dedupe_mm)
            if host_sockets and t_inv:
                for inst, pt_host in host_sockets:
                    try:
                        pt_link = t_inv.OfPoint(pt_host)
                    except Exception:
                        continue
                    if not pt_link:
                        continue
                    if _points_in_room([pt_link], room):
                        existing_link_pts.append(pt_link)
                        if not existing_idx.has_near(float(pt_link.X), float(pt_link.Y), float(pt_link.Z), float(existing_dedupe_ft)):
                            existing_cnt += 1
                            existing_idx.add(float(pt_link.X), float(pt_link.Y), float(pt_link.Z))

            # Dedupe index in link XY
            idx = su._XYZIndex(cell_ft=5.0)
            for ep in existing_link_pts:
                try:
                    idx.add(float(ep.X), float(ep.Y), float(ep.Z))
                except Exception:
                    continue

            # Choose best sink-stove pair (for unit wall inference)
            best_sink = sinks[0] if sinks else None
            best_stove = stoves[0] if stoves else None
            if sinks and stoves:
                best_d = None
                for s in sinks:
                    for p in stoves:
                        d = _dist_xy(s, p)
                        if best_d is None or d < best_d:
                            best_d = d
                            best_sink = s
                            best_stove = p

            # Choose best fridge (closest to stove if possible)
            best_fridge = fridges[0] if fridges else None
            if fridges and best_stove:
                try:
                    fr_sorted = sorted(fridges, key=lambda x: _dist_xy(x, best_stove))
                    best_fridge = fr_sorted[0] if fr_sorted else best_fridge
                except Exception:
                    pass

            # Infer unit wall by already placed kitchen-unit sockets (preferred)
            unit_wall_id = None
            unit_seg = None
            unit_dir = None
            unit_pts_room = _points_in_room(pts_unit_link, room) if pts_unit_link else []
            if unit_pts_room:
                counts = {}
                for pt_u in unit_pts_room:
                    sg, _pr, _d = _nearest_segment(pt_u, segs)
                    if not sg:
                        continue
                    try:
                        wid = int(sg[2].Id.IntegerValue)
                    except Exception:
                        wid = None
                    if wid is None:
                        continue
                    counts[wid] = int(counts.get(wid, 0)) + 1
                if counts:
                    unit_wall_id = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]

            # Fallback: infer unit wall by sink/stove
            if unit_wall_id is None:
                sg_sink, _ps, _ds = _nearest_segment(best_sink, segs) if best_sink else (None, None, None)
                sg_stove, _pp, _dp = _nearest_segment(best_stove, segs) if best_stove else (None, None, None)
                wid_sink = None
                wid_stove = None
                try:
                    wid_sink = int(sg_sink[2].Id.IntegerValue) if sg_sink and sg_sink[2] else None
                except Exception:
                    wid_sink = None
                try:
                    wid_stove = int(sg_stove[2].Id.IntegerValue) if sg_stove and sg_stove[2] else None
                except Exception:
                    wid_stove = None
                if wid_stove is not None and wid_sink is not None and wid_stove == wid_sink:
                    unit_wall_id = wid_stove
                elif wid_stove is not None:
                    unit_wall_id = wid_stove
                elif wid_sink is not None:
                    unit_wall_id = wid_sink

            # Extra fallback: infer unit wall by fridge (when sinks/stoves not detected)
            if unit_wall_id is None and best_fridge is not None:
                sg_fr, _pf, _df = _nearest_segment(best_fridge, segs)
                try:
                    unit_wall_id = int(sg_fr[2].Id.IntegerValue) if sg_fr and sg_fr[2] else None
                except Exception:
                    unit_wall_id = None

            if unit_wall_id is not None:
                # pick the longest segment of that wall (also sum total length)
                best_len = None
                unit_len_total = 0.0
                for p0, p1, w in segs:
                    try:
                        wid = int(w.Id.IntegerValue)
                    except Exception:
                        continue
                    if wid != unit_wall_id:
                        continue
                    sl = _seg_len_ft(p0, p1)
                    try:
                        unit_len_total += float(sl)
                    except Exception:
                        pass
                    if best_len is None or sl > best_len:
                        best_len = sl
                        unit_seg = (p0, p1, w)
                if unit_seg:
                    unit_dir = _seg_dir(unit_seg[0], unit_seg[1])

            # Opposite wall selection (parallel & far)
            opp_wall_id = None
            opp_seg = None
            if unit_seg and unit_dir and unit_wall_id is not None:
                n = DB.XYZ(-float(unit_dir.Y), float(unit_dir.X), 0.0)
                try:
                    if n.GetLength() > 1e-9:
                        n = n.Normalize()
                except Exception:
                    pass

                # Determine ray direction towards room center (for opposite wall hit test)
                unit_mid = _point_at_t(unit_seg[0], unit_seg[1], 0.5, z=float(unit_seg[0].Z)) if unit_seg else None
                n_dir = n
                try:
                    room_bb = room.get_BoundingBox(None)
                except Exception:
                    room_bb = None
                if room_bb and unit_mid:
                    try:
                        rc = DB.XYZ(
                            (room_bb.Min.X + room_bb.Max.X) * 0.5,
                            (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                            float(unit_mid.Z)
                        )
                        vrc = rc - unit_mid
                        if vrc and vrc.GetLength() > 1e-9:
                            if float(vrc.DotProduct(n)) < 0.0:
                                n_dir = DB.XYZ(-float(n.X), -float(n.Y), 0.0)
                    except Exception:
                        pass

                # Prefer opposite wall by ray hit; fallback to far+long heuristic
                wall_info = {}
                p_base = unit_seg[0]
                for p0, p1, w in segs:
                    try:
                        wid = int(w.Id.IntegerValue)
                    except Exception:
                        continue
                    if wid == unit_wall_id:
                        continue
                    ddir = _seg_dir(p0, p1)
                    if ddir is None:
                        continue
                    try:
                        if abs(float(ddir.DotProduct(unit_dir))) < float(parallel_tol):
                            continue
                    except Exception:
                        continue
                    mid = _point_at_t(p0, p1, 0.5, z=float(p0.Z))
                    if mid is None:
                        continue
                    try:
                        d = abs(float((mid - p_base).DotProduct(n)))
                    except Exception:
                        d = None
                    if d is None:
                        continue
                    sl = _seg_len_ft(p0, p1)
                    if wid not in wall_info:
                        wall_info[wid] = {'len': 0.0, 'dist': d}
                    wall_info[wid]['len'] += float(sl)
                    if d > wall_info[wid]['dist']:
                        wall_info[wid]['dist'] = d


                # min length filter for opposite wall
                min_opp_len = None
                try:
                    if unit_len_total and float(unit_len_total) > 1e-6:
                        min_opp_len = max(mm_to_ft(600), float(unit_len_total) * 0.4)
                    else:
                        min_opp_len = mm_to_ft(600)
                except Exception:
                    min_opp_len = None

                ray_hits = []
                if wall_info and unit_mid and n_dir:
                    for p0, p1, w in segs:
                        try:
                            wid = int(w.Id.IntegerValue)
                        except Exception:
                            continue
                        if wid == unit_wall_id:
                            continue
                        ddir = _seg_dir(p0, p1)
                        if ddir is None:
                            continue
                        try:
                            if abs(float(ddir.DotProduct(unit_dir))) < float(parallel_tol):
                                continue
                        except Exception:
                            continue
                        try:
                            if min_opp_len is not None and float(wall_info.get(wid, {}).get('len', 0.0)) < float(min_opp_len):
                                continue
                        except Exception:
                            pass
                        t_hit = _ray_segment_intersection_2d(unit_mid, n_dir, p0, p1)
                        if t_hit is None:
                            continue
                        if float(t_hit) < float(mm_to_ft(300)):
                            continue
                        ray_hits.append((float(t_hit), int(wid)))

                if ray_hits:
                    ray_hits = sorted(
                        ray_hits,
                        key=lambda x: (float(x[0]), -float(wall_info.get(x[1], {}).get('len', 0.0)), x[1])
                    )
                    opp_wall_id = ray_hits[0][1]
                elif wall_info:
                    # Fallback: farthest wall, then longest (avoid picking near long walls).
                    wall_items = list(wall_info.items())
                    filtered = wall_items
                    if min_opp_len is not None:
                        filtered = [x for x in wall_items if float(x[1].get('len', 0.0)) >= float(min_opp_len)]
                        if not filtered:
                            filtered = wall_items

                    max_dist = 0.0
                    try:
                        max_dist = max([float(x[1].get('dist', 0.0)) for x in filtered])
                    except Exception:
                        max_dist = 0.0
                    dist_tol = max(mm_to_ft(150), float(max_dist) * 0.05) if max_dist > 1e-9 else mm_to_ft(150)

                    far = [x for x in filtered if float(x[1].get('dist', 0.0)) >= float(max_dist) - float(dist_tol)]
                    if not far:
                        far = filtered

                    opp_wall_id = sorted(
                        far,
                        key=lambda x: (-float(x[1].get('len', 0.0)), x[0])
                    )[0][0]
                    # pick longest segment on that wall (often split by doors)
                    best_len = None
                    for p0, p1, w in segs:
                        try:
                            wid = int(w.Id.IntegerValue)
                        except Exception:
                            continue
                        if wid != opp_wall_id:
                            continue
                        sl = _seg_len_ft(p0, p1)
                        if best_len is None or sl > best_len:
                            best_len = sl
                            opp_seg = (p0, p1, w)
                # Fallback: if wall chosen but no segment picked
                if opp_wall_id is not None and opp_seg is None:
                    for p0, p1, w in segs:
                        try:
                            wid = int(w.Id.IntegerValue)
                        except Exception:
                            continue
                        if wid == opp_wall_id:
                            opp_seg = (p0, p1, w)
                            break

            else:
                _push_skip(
                    room,
                    'opp_wall',
                    u'unit_wall_id={0}, unit_seg={1}, unit_dir={2}'.format(
                        unit_wall_id,
                        'ok' if unit_seg else 'none',
                        'ok' if unit_dir else 'none'
                    )
                )

            # Fridge candidate segment
            seg_fr, proj_fr, _df = _nearest_segment(best_fridge, segs) if best_fridge else (None, None, None)
            fridge_wall_id = None
            try:
                fridge_wall_id = int(seg_fr[2].Id.IntegerValue) if seg_fr and seg_fr[2] else None
            except Exception:
                fridge_wall_id = None

            # Check whether requirements are already satisfied by existing sockets
            has_fridge_socket = False
            if best_fridge and fridge_max_dist_ft and tagged_link_pts:
                for ep in tagged_link_pts:
                    try:
                        if _dist_xy(ep, best_fridge) > float(fridge_max_dist_ft):
                            continue
                    except Exception:
                        continue
                    try:
                        if abs(float(ep.Z) - float(z_target)) > float(height_match_tol_ft):
                            continue
                    except Exception:
                        pass

                    # Prefer sockets on the same wall as the fridge.
                    if fridge_wall_id is not None:
                        sg0, _pr0, dd0 = _nearest_segment(ep, segs)
                        if (not sg0) or dd0 is None:
                            continue
                        try:
                            wid0 = int(sg0[2].Id.IntegerValue) if sg0[2] else None
                        except Exception:
                            wid0 = None
                        if wid0 is None or int(wid0) != int(fridge_wall_id):
                            continue
                        try:
                            if float(dd0) > float(validate_wall_dist_ft or mm_to_ft(150)):
                                continue
                        except Exception:
                            continue

                    has_fridge_socket = True
                    break

            has_opp_socket = False
            if opp_wall_id is not None and tagged_link_pts:
                for ep in tagged_link_pts:
                    try:
                        if abs(float(ep.Z) - float(z_target)) > float(height_match_tol_ft):
                            continue
                    except Exception:
                        pass
                    sg, pr, dd = _nearest_segment(ep, segs)
                    if not sg or pr is None or dd is None:
                        continue
                    try:
                        wid = int(sg[2].Id.IntegerValue)
                    except Exception:
                        wid = None
                    if wid is None:
                        continue
                    if wid != opp_wall_id:
                        continue
                    if float(dd) <= float(validate_wall_dist_ft or mm_to_ft(150)):
                        has_opp_socket = True
                        break
            elif opp_wall_id is None:
                _push_skip(room, 'opp_wall', u'opp_wall_id not found')

            # Capacity after we know fridge/opposite needs
            fridge_need = bool(best_fridge and (not has_fridge_socket))
            opp_need = bool(opp_wall_id is not None and (not has_opp_socket))

            if existing_cnt >= total_target and not (fridge_need or opp_need):
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток в помещении'.format(int(existing_cnt), int(total_target)))
                continue

            capacity = max(0, int(total_target) - int(existing_cnt))
            # Always place both fridge + opposite if needed, regardless of total_target
            if fridge_need and opp_need:
                capacity = max(int(capacity), 2)
            elif (fridge_need or opp_need) and capacity <= 0:
                capacity = 1
            to_place = min(2, int(capacity))
            if fridge_need and opp_need:
                to_place = 2
            if to_place <= 0:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток в помещении'.format(int(existing_cnt), int(total_target)))
                continue

            # If only one slot left and both fridge/opposite are needed, prefer opposite
            prefer_opposite = bool(to_place == 1 and fridge_need and opp_need)

            candidates = []
            if seg_fr and proj_fr and (not has_fridge_socket):
                pr = 1 if prefer_opposite else 0
                candidates.append({'priority': pr, 'kind': u'fridge', 'seg': seg_fr, 'proj': proj_fr})
            if opp_seg and (not has_opp_socket):
                pr = 0 if prefer_opposite else 1
                candidates.append({'priority': pr, 'kind': u'opposite', 'seg': opp_seg, 'proj': _point_at_t(opp_seg[0], opp_seg[1], 0.5, z=float(opp_seg[0].Z))})

            if not candidates:
                skipped += 1
                skip_no_candidates += 1
                _push_skip(
                    room,
                    'candidates',
                    u'existing={0}, capacity={1}, has_fridge={2}, has_opposite={3}'.format(
                        int(existing_cnt), int(capacity), bool(has_fridge_socket), bool(has_opp_socket)
                    )
                )
                if debug_no_candidates_shown < debug_no_candidates_limit:
                    try:
                        output.print_md('Нет кандидатов: room #{0} **{1}**'.format(int(room.Id.IntegerValue), su._room_text(room)))
                        output.print_md('- existing={0}, capacity={1}, has_fridge={2}, has_opposite={3}'.format(
                            int(existing_cnt), int(capacity), bool(has_fridge_socket), bool(has_opp_socket)
                        ))
                    except Exception:
                        pass
                    debug_no_candidates_shown += 1
                continue

            candidates = sorted(candidates, key=lambda x: int(x.get('priority', 9)))
            picked = 0
            for cand in candidates:
                if picked >= to_place:
                    break

                kind = cand.get('kind')
                seg = cand.get('seg')
                proj = cand.get('proj')
                if (not seg) or (proj is None):
                    continue

                p0, p1, wall = seg
                try:
                    sl = _seg_len_ft(p0, p1)
                except Exception:
                    sl = 0.0
                if sl <= 1e-6:
                    continue
                end_tol = float(wall_end_clear_ft or 0.0) / float(sl) if sl > 1e-6 else 0.0

                # Clamp along wall away from ends
                tt = None
                try:
                    tt = _dist_xy(p0, proj) / float(sl)
                except Exception:
                    tt = None
                if tt is None:
                    continue
                if tt < (0.0 + end_tol):
                    tt = 0.0 + end_tol
                if tt > (1.0 - end_tol):
                    tt = 1.0 - end_tol

                pt_xy = _point_at_t(p0, p1, tt, z=float(proj.Z))
                if pt_xy is None:
                    continue

                # Dedupe by existing sockets
                if idx.has_near(float(pt_xy.X), float(pt_xy.Y), float(z_target), float(dedupe_ft or mm_to_ft(300))):
                    continue

                idx.add(float(pt_xy.X), float(pt_xy.Y), float(z_target))

                v = _seg_dir(p0, p1)
                if v is None:
                    continue
                seg_len = _seg_len_ft(p0, p1)

                pt_link = DB.XYZ(float(pt_xy.X), float(pt_xy.Y), float(base_z) + float(height_ft))
                pt_host = t.OfPoint(pt_link) if t else pt_link

                pending.append((wall, pt_link, v, sym, seg_len))

                plan = {
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'expected_pt_host': pt_host,
                    'kind': kind,
                    'seg_p0': p0,
                    'seg_p1': p1,
                    'unit_wall_id': unit_wall_id,
                    'opposite_wall_id': opp_wall_id,
                    'fridge_wall_id': fridge_wall_id,
                    'fridge_pt': best_fridge,
                }
                plans.append(plan)
                prepared += 1
                picked += 1

                if len(pending) >= batch_size:
                    c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
                        doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode
                    )
                    created += int(c)
                    created_face += int(cf)
                    created_wp += int(cwp)
                    created_pt += int(cpt)
                    pending = []

    if pending:
        c, cf, cwp, cpt, _snf, _snp, _cver = su._place_socket_batch(
            doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode
        )
        created += int(c)
        created_face += int(cf)
        created_wp += int(cwp)
        created_pt += int(cpt)

    ids_after, elems_after, _pts_after = _collect_tagged_instances(doc, comment_value)
    new_ids = set(ids_after or set()) - set(ids_before or set())
    try:
        elems_by_id = {int(e.Id.IntegerValue): e for e in (elems_after or [])}
    except Exception:
        elems_by_id = {}
    new_elems = [elems_by_id[i] for i in sorted(new_ids) if i in elems_by_id]

    validation = []
    if plans:
        inst_items = []
        for e in (new_elems or []):
            pt = su._inst_center_point(e)
            if pt is None:
                continue
            try:
                iid = int(e.Id.IntegerValue)
            except Exception:
                iid = None

            abs_z = None
            try:
                abs_z = _get_abs_z_from_level_offset(e, doc)
            except Exception:
                abs_z = None
            z_key = abs_z if abs_z is not None else float(pt.Z)

            inst_items.append((iid, e, pt, float(z_key)))

        used_inst = set()
        for pl in plans:
            exp_pt = pl.get('expected_pt_host')
            if exp_pt is None:
                continue
            try:
                exp_z = float(exp_pt.Z)
            except Exception:
                exp_z = None

            best = None
            best_key = None  # (dZ, dXY)
            best_dxy = None

            for iid, e, pt, z_key in inst_items:
                if iid in used_inst:
                    continue
                dxy = _dist_xy(pt, exp_pt)
                if validate_match_tol_ft and dxy > validate_match_tol_ft:
                    continue
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
                    'kind': pl.get('kind'),
                })
                continue

            iid, inst, inst_pt = best
            used_inst.add(iid)

            abs_z = None
            try:
                abs_z = _get_abs_z_from_level_offset(inst, doc)
            except Exception:
                abs_z = None
            z_to_check = abs_z if abs_z is not None else float(inst_pt.Z)
            exp_z2 = float(exp_pt.Z) if hasattr(exp_pt, 'Z') else float(inst_pt.Z)
            height_ok = abs(float(z_to_check) - float(exp_z2)) <= float(validate_height_tol_ft or mm_to_ft(20))

            try:
                inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
            except Exception:
                inst_pt_link = inst_pt

            p0 = pl.get('seg_p0')
            p1 = pl.get('seg_p1')
            proj = _closest_point_on_segment_xy(inst_pt_link, p0, p1) if p0 and p1 else None
            dist_wall = _dist_xy(inst_pt_link, proj) if proj else None
            on_wall_ok = (dist_wall is not None) and (dist_wall <= float(validate_wall_dist_ft or mm_to_ft(150)))

            kind = pl.get('kind')
            fridge_ok = True
            opposite_ok = True

            if kind == u'fridge':
                fp = pl.get('fridge_pt')
                if fp is None:
                    fridge_ok = False
                else:
                    try:
                        fridge_ok = _dist_xy(inst_pt_link, fp) <= float(fridge_max_dist_ft or mm_to_ft(1500))
                    except Exception:
                        fridge_ok = False

            if kind == u'opposite':
                want = pl.get('opposite_wall_id')
                closest = None
                if want is not None:
                    for p0, p1, w in segs or []:
                        try:
                            wid = int(w.Id.IntegerValue) if w else None
                        except Exception:
                            wid = None
                        if wid is None or int(wid) != int(want):
                            continue
                        proj0 = _closest_point_on_segment_xy(inst_pt_link, p0, p1)
                        if proj0 is None:
                            continue
                        d0 = _dist_xy(inst_pt_link, proj0)
                        if d0 is None:
                            continue
                        if closest is None or float(d0) < float(closest):
                            closest = float(d0)
                try:
                    opposite_ok = (want is not None) and (closest is not None) and (float(closest) <= float(validate_wall_dist_ft or mm_to_ft(150)))
                except Exception:
                    opposite_ok = False

            ok = bool(height_ok and on_wall_ok and fridge_ok and opposite_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'room_id': pl.get('room_id'),
                'room_name': pl.get('room_name'),
                'kind': kind,
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
                'fridge_ok': bool(fridge_ok),
                'opposite_ok': bool(opposite_ok),
            })

    output.print_md(
        'Тип: **{0}**\n\nПодготовлено: **{1}**\nСоздано: **{2}** (Face: {3}, WorkPlane: {4}, Point: {5})\nПропущено: **{6}**'.format(
            sym_lbl or u'<Розетка>', prepared, created, created_face, created_wp, created_pt, skipped
        )
    )

    if fixed_existing:
        output.print_md('Исправлено высот (существующие): **{0}**'.format(fixed_existing))

    if validation:
        okc = len([x for x in validation if x.get('status') == 'ok'])
        failc = len([x for x in validation if x.get('status') == 'fail'])
        missc = len([x for x in validation if x.get('status') == 'missing'])
        output.print_md('Проверка: OK=**{0}**, FAIL=**{1}**, MISSING=**{2}**'.format(okc, failc, missc))
        if failc or missc:
            output.print_md('Нарушения:')
            for x in validation:
                st = x.get('status')
                if st == 'ok':
                    continue
                rid = x.get('room_id')
                rnm = x.get('room_name')
                if st == 'missing':
                    output.print_md('- room #{0} {1}: не найден созданный экземпляр (kind={2}, tag={3})'.format(
                        rid, rnm, x.get('kind'), comment_value
                    ))
                else:
                    output.print_md('- id {0} / room #{1} {2} ({3}): height={4}, on_wall={5}, fridge={6}, opposite={7}'.format(
                        x.get('id'), rid, rnm, x.get('kind'),
                        x.get('height_ok'), x.get('on_wall_ok'), x.get('fridge_ok'), x.get('opposite_ok')
                    ))

    if skipped:
        output.print_md('Причины пропусков (шт.): segs={0}, full={1}, fixtures={2}, candidates={3}'.format(
            skip_no_segs, skip_full, (skip_no_fixtures + skip_not_kitchen), skip_no_candidates
        ))

    if skipped_details:
        output.print_md('Пропущенные помещения (первые {0}):'.format(len(skipped_details)))
        for x in skipped_details:
            output.print_md('- room #{0} **{1}**: {2}{3}'.format(
                x.get('room_id'), x.get('room_name') or u'',
                x.get('reason') or u'',
                (u' — ' + x.get('details')) if x.get('details') else u''
            ))
        if skipped_details_more[0]:
            output.print_md('- …и еще пропущено: **{0}** (увеличьте kitchen_debug_skipped_rooms_limit)'.format(int(skipped_details_more[0])))


try:
    main()
except Exception:
    log_exception('Error in 03_Kitchen_General')
