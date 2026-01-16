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
logger = script.get_logger()


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


def _try_get_room_at_point(doc_, pt):
    if doc_ is None or pt is None:
        return None
    # Try as-is first
    try:
        r = doc_.GetRoomAtPoint(pt)
        if r is not None:
            return r
    except Exception:
        pass
    # Fallbacks: same XY, typical Z probes
    for z in (0.0, mm_to_ft(1500), mm_to_ft(3000)):
        try:
            r = doc_.GetRoomAtPoint(DB.XYZ(float(pt.X), float(pt.Y), float(z)))
            if r is not None:
                return r
        except Exception:
            continue
    return None


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


def main():
    output.print_md('# 02. Кухня: Гарнитур (1100мм)')

    rules = config_loader.load_rules()
    cfg = script.get_config()

    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SOCKET_KITCHEN_UNIT'.format(comment_tag)

    kitchen_patterns = rules.get('kitchen_room_name_patterns', None) or [u'кухн', u'kitchen', u'столов']
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    total_target = int(rules.get('kitchen_total_sockets', 4) or 4)

    height_mm = int(rules.get('kitchen_unit_height_mm', 1100) or 1100)
    height_ft = mm_to_ft(height_mm)

    clear_sink_mm = int(rules.get('kitchen_sink_clear_mm', 600) or 600)
    clear_stove_mm = int(rules.get('kitchen_stove_clear_mm', 600) or 600)
    clear_sink_ft = mm_to_ft(clear_sink_mm)
    clear_stove_ft = mm_to_ft(clear_stove_mm)

    offset_sink_mm = int(rules.get('kitchen_sink_offset_mm', 600) or 600)
    offset_stove_mm = int(rules.get('kitchen_stove_offset_mm', 600) or 600)
    offset_sink_ft = mm_to_ft(offset_sink_mm)
    offset_stove_ft = mm_to_ft(offset_stove_mm)

    wall_end_clear_mm = int(rules.get('kitchen_wall_end_clear_mm', 100) or 100)
    wall_end_clear_ft = mm_to_ft(wall_end_clear_mm)

    fixture_wall_max_dist_ft = mm_to_ft(int(rules.get('kitchen_fixture_wall_max_dist_mm', 2000) or 2000))

    dedupe_mm = int(rules.get('socket_dedupe_radius_mm', 300) or 300)
    dedupe_ft = mm_to_ft(dedupe_mm)
    batch_size = int(rules.get('batch_size', 25) or 25)

    validate_match_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_match_tol_mm', 2000) or 2000))
    validate_height_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_height_tol_mm', 20) or 20))
    validate_wall_dist_ft = mm_to_ft(int(rules.get('kitchen_validate_wall_dist_mm', 150) or 150))
    validate_offset_tol_ft = mm_to_ft(int(rules.get('kitchen_validate_offset_tol_mm', 100) or 100))
    debug_no_candidates_limit = int(rules.get('kitchen_debug_no_candidates_limit', 3) or 3)
    debug_skipped_rooms_limit = int(rules.get('kitchen_debug_skipped_rooms_limit', 20) or 20)
    existing_dedupe_mm = int(rules.get('kitchen_existing_dedupe_mm', 200) or 200)

    fams = rules.get('family_type_names', {})
    prefer = fams.get('socket_kitchen_unit') or (
        u'TSL_EF_т_СТ_в_IP20_Рзт_1P+N+PE_2п : TSL_EF_т_СТ_в_IP20_Рзт_1P+N+PE_2п'
    )
    if isinstance(prefer, (list, tuple)):
        prefer = sorted(prefer, key=lambda x: (0 if u'_2п' in (x or u'') else 1))
    sym, sym_lbl, top10 = su._pick_socket_symbol(doc, cfg, prefer, cache_prefix='socket_kitchen_unit')
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
            alert('Не найден тип розетки для кухни (гарнитур).')
            if top10:
                output.print_md('Доступные варианты:')
                for x in top10:
                    output.print_md('- {0}'.format(x))
            return

    try:
        su._store_symbol_id(cfg, 'last_socket_kitchen_unit_symbol_id', sym)
        su._store_symbol_unique_id(cfg, 'last_socket_kitchen_unit_symbol_uid', sym)
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

    # --- sinks/stoves detection ---
    sinks_all = []
    try:
        # Try last picked sink symbol in link (stored in pyRevit config)
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
        # Fallback: ask user to pick one sink instance in the link to learn its type.
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

    output.print_md('Раковины: **{0}**; Электроплиты: **{1}**'.format(len(sinks_all or []), len(stoves_all or [])))

    # Rooms selection:
    # 1) rooms by name patterns (fast, limited scan)
    # 2) rooms that contain a stove (kitchen-living can be named "Гостиная")
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

    try:
        ids_before, _elems_before, _pts_before = _collect_tagged_instances(doc, comment_value)
    except Exception:
        ids_before = set()

    # Fix height for already placed kitchen-unit sockets (tagged)
    fixed_existing = 0
    try:
        _ids0, elems0, _pts0 = _collect_tagged_instances(doc, comment_value)
    except Exception:
        elems0 = []
    if elems0:
        try:
            with tx('ЭОМ: Кухня гарнитур — исправить высоту', doc=doc, swallow_warnings=True):
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

    debug_no_candidates_shown = 0

    created = created_face = created_wp = created_pt = 0
    skipped = 0
    skip_no_segs = 0
    skip_full = 0
    skip_no_fixtures = 0
    skip_not_kitchen = 0
    skip_no_candidates = 0
    prepared = 0

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

    with forms.ProgressBar(title='02. Кухня (гарнитур)...', cancellable=True) as pb:
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
            if not sinks and not stoves:
                skipped += 1
                skip_no_fixtures += 1
                _push_skip(room, 'fixtures', u'не найдены мойка/плита')
                continue

            # For rooms that don't look like a kitchen by name (e.g. "Гостиная"),
            # only proceed when BOTH sink and stove are detected in-room.
            # This prevents placing "kitchen unit" sockets in plain living rooms.
            is_named_kitchen = True
            try:
                is_named_kitchen = (not kitchen_rx) or su._match_any(kitchen_rx, su._room_text(room))
            except Exception:
                is_named_kitchen = True
            if (not is_named_kitchen) and (not (sinks and stoves)):
                skipped += 1
                skip_not_kitchen += 1
                _push_skip(
                    room,
                    'fixtures',
                    u'не кухня по названию и нет пары (мойка+плита); sinks={0}, stoves={1}'.format(len(sinks or []), len(stoves or []))
                )
                continue

            # Choose best sink-stove pair if both exist
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

            base_z = su._room_level_elevation_ft(room, link_doc)

            # Count existing sockets in this kitchen room (all sockets, incl. out of unit zone)
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

            if existing_cnt >= total_target:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток в помещении'.format(int(existing_cnt), int(total_target)))
                continue
            need = max(0, int(total_target) - int(existing_cnt))
            # Требование: ставим только ОДНУ двойную розетку в зоне гарнитура.
            need = min(int(need), 1)
            if need <= 0:
                skipped += 1
                skip_full += 1
                _push_skip(room, 'full', u'уже {0}/{1} розеток в помещении'.format(int(existing_cnt), int(total_target)))
                continue

            # Build dedupe index in link XY
            idx = su._XYZIndex(cell_ft=5.0)
            for ep in existing_link_pts:
                try:
                    idx.add(float(ep.X), float(ep.Y), 0.0)
                except Exception:
                    continue

            seg_sink, proj_sink, _ = _nearest_segment(best_sink, segs) if best_sink else (None, None, None)
            seg_stove, proj_stove, _ = _nearest_segment(best_stove, segs) if best_stove else (None, None, None)
            sink_wall_id = None
            stove_wall_id = None
            try:
                sink_wall_id = int(seg_sink[2].Id.IntegerValue) if seg_sink and seg_sink[2] else None
            except Exception:
                sink_wall_id = None
            try:
                stove_wall_id = int(seg_stove[2].Id.IntegerValue) if seg_stove and seg_stove[2] else None
            except Exception:
                stove_wall_id = None

            candidates = []

            def _seg_dir(p0, p1):
                try:
                    v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
                    if v.GetLength() <= 1e-9:
                        return None
                    return v.Normalize()
                except Exception:
                    return None

            def _offset_candidates_for_fixture(src_pt, seg0, offset_ft, prefer_sign=None, priority=0, kind=u''):
                if src_pt is None or not seg0:
                    return
                # Try all boundary segments of the same wall (room boundary can split wall into small pieces).
                segs_try = []
                try:
                    wid0 = int(seg0[2].Id.IntegerValue) if seg0[2] else None
                except Exception:
                    wid0 = None
                if wid0 is not None:
                    for sg in segs or []:
                        try:
                            if int(sg[2].Id.IntegerValue) == wid0:
                                segs_try.append(sg)
                        except Exception:
                            continue
                if not segs_try:
                    segs_try = [seg0]

                scored = []
                for sg in segs_try:
                    p0, p1, wall = sg
                    proj = _closest_point_on_segment_xy(src_pt, p0, p1)
                    if proj is None:
                        continue
                    try:
                        dperp = _dist_xy(src_pt, proj)
                    except Exception:
                        dperp = None
                    if dperp is not None and fixture_wall_max_dist_ft and dperp > float(fixture_wall_max_dist_ft):
                        continue
                    scored.append((dperp if dperp is not None else 1e9, sg, proj))

                scored.sort(key=lambda x: x[0])
                for _dperp, sg, proj in scored:
                    p0, p1, wall = sg
                    try:
                        seg_len = _dist_xy(p0, p1)
                    except Exception:
                        seg_len = 0.0
                    if seg_len <= 1e-6:
                        continue
                    try:
                        t0 = _dist_xy(p0, proj) / seg_len
                    except Exception:
                        continue
                    dt = float(offset_ft or 0.0) / float(seg_len)
                    if dt <= 1e-9:
                        continue
                    end_tol = float(wall_end_clear_ft or 0.0) / float(seg_len) if seg_len > 1e-6 else 0.0

                    signs = []
                    if prefer_sign in (-1, 1):
                        signs = [int(prefer_sign), int(-prefer_sign)]
                    else:
                        signs = [1, -1]

                    added = False
                    for sgn in signs:
                        tt = float(t0) + float(sgn) * dt
                        if tt < (0.0 + end_tol) or tt > (1.0 - end_tol):
                            continue
                        try:
                            pt = DB.XYZ(
                                float(p0.X) + (float(p1.X) - float(p0.X)) * tt,
                                float(p0.Y) + (float(p1.Y) - float(p0.Y)) * tt,
                                float(proj.Z)
                            )
                        except Exception:
                            continue
                        candidates.append({'priority': priority, 'seg': sg, 'pt': pt, 'kind': kind})
                        added = True
                    if added:
                        break

            # Offset candidates near sink/stove
            if seg_sink and proj_sink:
                prefer_sign = None
                if seg_stove and proj_stove:
                    try:
                        if int(seg_sink[2].Id.IntegerValue) == int(seg_stove[2].Id.IntegerValue):
                            v = _seg_dir(seg_sink[0], seg_sink[1])
                            if v:
                                d = (proj_stove - proj_sink).DotProduct(v)
                                prefer_sign = -1 if d > 0 else 1
                    except Exception:
                        prefer_sign = None
                _offset_candidates_for_fixture(best_sink, seg_sink, offset_sink_ft, prefer_sign=prefer_sign, priority=0, kind=u'sink')

            if seg_stove and proj_stove:
                prefer_sign = None
                if seg_sink and proj_sink:
                    try:
                        if int(seg_sink[2].Id.IntegerValue) == int(seg_stove[2].Id.IntegerValue):
                            v = _seg_dir(seg_stove[0], seg_stove[1])
                            if v:
                                d = (proj_sink - proj_stove).DotProduct(v)
                                prefer_sign = -1 if d > 0 else 1
                    except Exception:
                        prefer_sign = None
                _offset_candidates_for_fixture(best_stove, seg_stove, offset_stove_ft, prefer_sign=prefer_sign, priority=1, kind=u'stove')

            if not candidates:
                skipped += 1
                skip_no_candidates += 1
                _push_skip(room, 'candidates', u'нет подходящих точек для размещения (после фильтров)')
                if debug_no_candidates_shown < debug_no_candidates_limit:
                    try:
                        output.print_md('Нет кандидатов: room #{0} **{1}**'.format(int(room.Id.IntegerValue), su._room_text(room)))
                        if best_stove and seg_stove:
                            p0, p1, _w = seg_stove
                            seg_len = _dist_xy(p0, p1)
                            proj0 = _closest_point_on_segment_xy(best_stove, p0, p1)
                            t0 = (_dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_stove_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md('- stove: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                        if best_sink and seg_sink:
                            p0, p1, _w = seg_sink
                            seg_len = _dist_xy(p0, p1)
                            proj0 = _closest_point_on_segment_xy(best_sink, p0, p1)
                            t0 = (_dist_xy(p0, proj0) / seg_len) if (proj0 and seg_len and seg_len > 1e-6) else None
                            dt = (float(offset_sink_ft) / float(seg_len)) if (seg_len and seg_len > 1e-6) else None
                            output.print_md('- sink: seg_len_ft={0}, t0={1}, dt={2}'.format(seg_len, t0, dt))
                    except Exception:
                        pass
                    debug_no_candidates_shown += 1
                continue

            # Sort by priority and keep unique-ish by XY
            candidates = sorted(candidates, key=lambda x: (x.get('priority', 9)))

            picked = 0
            for cand in candidates:
                if picked >= need:
                    break
                pt_xy = cand.get('pt')
                seg = cand.get('seg')
                kind = cand.get('kind')
                if pt_xy is None or seg is None:
                    continue

                # clearance checks (>= 600mm by default)
                if best_sink and clear_sink_ft and (_dist_xy(pt_xy, best_sink) + 1e-9) < float(clear_sink_ft):
                    continue
                if best_stove and clear_stove_ft and (_dist_xy(pt_xy, best_stove) + 1e-9) < float(clear_stove_ft):
                    continue

                # on-wall proximity (segment projection)
                p0, p1, wall = seg
                proj = _closest_point_on_segment_xy(pt_xy, p0, p1)
                if proj is None:
                    continue
                if _dist_xy(pt_xy, proj) > float(validate_wall_dist_ft or mm_to_ft(150)):
                    continue

                # dedupe (XY)
                if idx.has_near(float(pt_xy.X), float(pt_xy.Y), 0.0, float(dedupe_ft or mm_to_ft(300))):
                    continue

                idx.add(float(pt_xy.X), float(pt_xy.Y), 0.0)

                v = DB.XYZ(float(p1.X) - float(p0.X), float(p1.Y) - float(p0.Y), 0.0)
                if v.GetLength() <= 1e-9:
                    continue
                v = v.Normalize()
                seg_len = p0.DistanceTo(p1)

                try:
                    wall_id = int(wall.Id.IntegerValue)
                except Exception:
                    wall_id = None
                offset_ft = float(offset_sink_ft) if kind == u'sink' else (float(offset_stove_ft) if kind == u'stove' else 0.0)

                pt_link = DB.XYZ(float(proj.X), float(proj.Y), float(base_z) + float(height_ft))
                pt_host = t.OfPoint(pt_link) if t else pt_link

                pending.append((wall, pt_link, v, sym, seg_len))
                plans.append({
                    'room_id': int(room.Id.IntegerValue),
                    'room_name': su._room_text(room),
                    'expected_pt_host': pt_host,
                    'kind': kind,
                    'offset_ft': float(offset_ft),
                    'wall_id': wall_id,
                    'sink_wall_id': sink_wall_id,
                    'stove_wall_id': stove_wall_id,
                    'sink_pt': best_sink,
                    'stove_pt': best_stove,
                    'seg_p0': p0,
                    'seg_p1': p1,
                })
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
                    'room_id': pl['room_id'],
                    'room_name': pl['room_name'],
                })
                continue

            iid, inst, inst_pt = best
            used_inst.add(iid)

            try:
                exp_z = float(pl['expected_pt_host'].Z)
            except Exception:
                exp_z = float(inst_pt.Z)

            abs_z = None
            try:
                abs_z = _get_abs_z_from_level_offset(inst, doc)
            except Exception:
                abs_z = None
            z_to_check = abs_z if abs_z is not None else float(inst_pt.Z)
            height_ok = abs(float(z_to_check) - float(exp_z)) <= float(validate_height_tol_ft or mm_to_ft(20))

            try:
                inst_pt_link = t_inv.OfPoint(inst_pt) if t_inv else inst_pt
            except Exception:
                inst_pt_link = inst_pt

            p0 = pl.get('seg_p0')
            p1 = pl.get('seg_p1')
            try:
                seg_len = _dist_xy(p0, p1) if p0 and p1 else 0.0
            except Exception:
                seg_len = 0.0

            # On-wall check vs planned segment
            proj = _closest_point_on_segment_xy(inst_pt_link, p0, p1) if p0 and p1 else None
            dist_wall = _dist_xy(inst_pt_link, proj) if proj else None
            on_wall_ok = (dist_wall is not None) and (dist_wall <= float(validate_wall_dist_ft or mm_to_ft(150)))

            # Compute position along segment
            ti = None
            if proj and seg_len and seg_len > 1e-6:
                try:
                    ti = _dist_xy(p0, proj) / seg_len
                except Exception:
                    ti = None

            wall_id = pl.get('wall_id')

            def _axis_dist_ft(axis_pt):
                if axis_pt is None:
                    return None
                if not (p0 and p1) or (not seg_len) or seg_len <= 1e-6 or ti is None:
                    return None
                proj_a = _closest_point_on_segment_xy(axis_pt, p0, p1)
                if proj_a is None:
                    return None
                try:
                    ta = _dist_xy(p0, proj_a) / seg_len
                except Exception:
                    return None
                try:
                    return abs(float(ti) - float(ta)) * float(seg_len)
                except Exception:
                    return None

            # Clearance checks (по оси вдоль стены, если ось на этой же стене)
            sink_clear_ok = True
            stove_clear_ok = True

            sink_pt = pl.get('sink_pt')
            stove_pt = pl.get('stove_pt')

            if sink_pt is not None:
                sink_d = None
                if wall_id is not None and pl.get('sink_wall_id') == wall_id:
                    sink_d = _axis_dist_ft(sink_pt)
                if sink_d is None:
                    sink_d = _dist_xy(inst_pt_link, sink_pt)
                sink_clear_ok = (sink_d + 1e-9) >= float(clear_sink_ft)

            if stove_pt is not None:
                stove_d = None
                if wall_id is not None and pl.get('stove_wall_id') == wall_id:
                    stove_d = _axis_dist_ft(stove_pt)
                if stove_d is None:
                    stove_d = _dist_xy(inst_pt_link, stove_pt)
                stove_clear_ok = (stove_d + 1e-9) >= float(clear_stove_ft)

            # Offset check: 600мм от оси «своего» прибора (вдоль стены)
            offset_ok = True
            kind = pl.get('kind')
            want_offset = float(pl.get('offset_ft') or 0.0)
            if kind == u'sink' and sink_pt is not None:
                d = _axis_dist_ft(sink_pt) if (wall_id is not None and pl.get('sink_wall_id') == wall_id) else None
                if d is not None:
                    offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))
            elif kind == u'stove' and stove_pt is not None:
                d = _axis_dist_ft(stove_pt) if (wall_id is not None and pl.get('stove_wall_id') == wall_id) else None
                if d is not None:
                    offset_ok = abs(float(d) - want_offset) <= float(validate_offset_tol_ft or mm_to_ft(100))

            ok = bool(height_ok and on_wall_ok and sink_clear_ok and stove_clear_ok and offset_ok)
            validation.append({
                'status': 'ok' if ok else 'fail',
                'id': iid,
                'room_id': pl['room_id'],
                'room_name': pl['room_name'],
                'height_ok': bool(height_ok),
                'on_wall_ok': bool(on_wall_ok),
                'sink_clear_ok': bool(sink_clear_ok),
                'stove_clear_ok': bool(stove_clear_ok),
                'offset_ok': bool(offset_ok),
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
                    output.print_md('- room #{0} {1}: не найден созданный экземпляр (tag={2})'.format(rid, rnm, comment_value))
                else:
                    output.print_md('- id {0} / room #{1} {2}: height={3}, on_wall={4}, offset={5}, sink_clear={6}, stove_clear={7}'.format(
                        x.get('id'), rid, rnm,
                        x.get('height_ok'), x.get('on_wall_ok'), x.get('offset_ok'), x.get('sink_clear_ok'), x.get('stove_clear_ok')
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
    log_exception('Error in 02_Kitchen_Unit')
