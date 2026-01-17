# -*- coding: utf-8 -*-

import math

from pyrevit import DB, forms, revit, script

import config_loader
import link_reader
import socket_utils as su
from utils_revit import alert, log_exception
from utils_units import mm_to_ft


doc = revit.doc
output = script.get_output()
logger = script.get_logger()


def _closest_point_xy(points, target_pt):
    if not points or target_pt is None:
        return None, None
    best = None
    best_d = None
    for p in points:
        if p is None:
            continue
        try:
            d = ((float(p.X) - float(target_pt.X)) ** 2 + (float(p.Y) - float(target_pt.Y)) ** 2) ** 0.5
        except Exception:
            continue
        if best is None or d < best_d:
            best, best_d = p, d
    return best, best_d


def _find_wall_near_point(link_doc, pt_link, max_dist_ft):
    if link_doc is None or pt_link is None:
        return None, None

    best_wall = None
    best_curve = None
    best_d = None

    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None

    for w in col:
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue
            ir = curve.Project(pt_link)
            if not ir:
                continue
            d = float(ir.Distance)
            if d > float(max_dist_ft or 0.0):
                continue
            if best_wall is None or d < best_d:
                best_wall, best_curve, best_d = w, curve, d
        except Exception:
            continue

    return best_wall, best_curve


def _wall_tangent_xy(curve, pt_link):
    if curve is None or pt_link is None:
        return DB.XYZ.BasisX
    try:
        ir = curve.Project(pt_link)
        if not ir:
            return DB.XYZ.BasisX
        p = ir.Parameter
        d = curve.ComputeDerivatives(p, True)
        v = d.BasisX
        v2 = DB.XYZ(float(v.X), float(v.Y), 0.0)
        return v2.Normalize() if v2.GetLength() > 1e-9 else DB.XYZ.BasisX
    except Exception:
        return DB.XYZ.BasisX


def _xy_unit(vec):
    if vec is None:
        return None
    try:
        v = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
        return v.Normalize() if v.GetLength() > 1e-9 else None
    except Exception:
        return None


def _try_get_door_facing_xy(door):
    if door is None:
        return None
    try:
        v = _xy_unit(getattr(door, "FacingOrientation", None))
        if v is not None:
            return v
    except Exception:
        pass
    try:
        host = getattr(door, "Host", None)
        v = _xy_unit(getattr(host, "Orientation", None)) if host is not None else None
        if v is not None:
            return v
    except Exception:
        pass
    return None


def _try_get_door_hand_xy(door):
    if door is None:
        return None
    try:
        v = _xy_unit(getattr(door, "HandOrientation", None))
        if v is not None:
            return v
    except Exception:
        pass
    return None


def _door_handle_dir_xy(door):
    hand = _try_get_door_hand_xy(door)
    if hand is None:
        return None
    try:
        return _xy_unit(DB.XYZ(-float(hand.X), -float(hand.Y), 0.0))
    except Exception:
        return None


def _room_side_normal_from_facing(room, door_center, facing_xy, probe_ft):
    if room is None or door_center is None or facing_xy is None:
        return None
    n = _xy_unit(facing_xy)
    if n is None:
        return None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
    try:
        z0 = float((room_bb.Min.Z + room_bb.Max.Z) * 0.5) if room_bb else float(door_center.Z)
    except Exception:
        z0 = float(getattr(door_center, "Z", 0.0) or 0.0)
    base = DB.XYZ(float(door_center.X), float(door_center.Y), float(z0))
    eps = float(probe_ft or 0.0)
    if eps <= 1e-9:
        return None
    try:
        p_plus = base + (n * eps)
        p_minus = base - (n * eps)
        in_plus = bool(room.IsPointInRoom(p_plus))
        in_minus = bool(room.IsPointInRoom(p_minus))
        if in_plus and (not in_minus):
            return n
        if in_minus and (not in_plus):
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)
    except Exception:
        return None
    return None


def _pick_room_door_handle_side(room, doors, room_center, probe_ft):
    if room is None or not doors:
        return None
    best = None
    best_d = None
    for d in doors:
        c = su._inst_center_point(d)
        if c is None:
            continue
        facing = _try_get_door_facing_xy(d)
        if facing is None:
            continue
        room_normal = _room_side_normal_from_facing(room, c, facing, probe_ft)
        if room_normal is None:
            continue
        handle = _door_handle_dir_xy(d)
        if handle is None:
            continue
        try:
            d0 = su._dist_xy(c, room_center) if room_center is not None else 0.0
        except Exception:
            d0 = 0.0
        if best is None or d0 < best_d:
            best = (d, c, room_normal, handle)
            best_d = d0
    return best


def main():
    output.print_md('# 06. Розетки: Слаботочка (домофон + роутер)')

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    batch_size = int(rules.get('batch_size', 25) or 25)

    intercom_h_mm = float(rules.get('low_voltage_intercom_height_mm', 1400) or 1400)
    router_h_mm = float(rules.get('low_voltage_router_height_mm', rules.get('socket_height_mm', 300) or 300) or 300)
    search_r_mm = float(rules.get('low_voltage_search_radius_mm', 1500) or 1500)
    door_offset_mm = float(rules.get('avoid_door_mm', 300) or 300)

    intercom_h_ft = mm_to_ft(intercom_h_mm)
    router_h_ft = mm_to_ft(router_h_mm)
    search_r_ft = mm_to_ft(search_r_mm)
    door_offset_ft = mm_to_ft(door_offset_mm)
    door_probe_ft = mm_to_ft(400)

    cfg = script.get_config()
    fams = rules.get('family_type_names', {})
    lv_types = fams.get('socket_low_voltage') or fams.get('power_socket')
    intercom_types = fams.get('socket_intercom') or lv_types
    router_types = fams.get('socket_router') or lv_types

    sym_intercom, _, _ = su._pick_socket_symbol(doc, cfg, intercom_types, cache_prefix='socket_intercom')
    sym_router, _, _ = su._pick_socket_symbol(doc, cfg, router_types, cache_prefix='socket_router')
    if not sym_intercom or not sym_router:
        alert('Не найден тип розетки для слаботочки (домофон/роутер). Проверьте config/rules.default.json.')
        return

    su._store_symbol_id(cfg, 'last_socket_intercom_symbol_id', sym_intercom)
    su._store_symbol_unique_id(cfg, 'last_socket_intercom_symbol_uid', sym_intercom)
    su._store_symbol_id(cfg, 'last_socket_router_symbol_id', sym_router)
    su._store_symbol_unique_id(cfg, 'last_socket_router_symbol_uid', sym_router)
    script.save_config()

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst:
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        return

    rooms = su._get_all_linked_rooms(link_doc)
    if not rooms:
        alert('Rooms в связи АР не найдены.')
        return

    doors = []
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
        for d in col:
            doors.append(d)
    except Exception:
        doors = []

    intercom_keys = rules.get('intercom_keywords', [u'домоф', u'intercom'])
    cabinet_keys = rules.get('low_voltage_cabinet_keywords', [u'сск', u'слаботоч', u'щит сс', u'шкаф сс', u'роутер', u'router'])

    intercom_pts = []
    cabinet_pts = []

    try:
        intercom_pts.extend(su._collect_textnote_points(link_doc, intercom_keys))
        intercom_pts.extend(su._collect_independent_tag_points(link_doc, intercom_keys))
        for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_ElectricalEquipment, DB.BuiltInCategory.OST_ElectricalFixtures):
            intercom_pts.extend(su._collect_points_by_keywords(link_doc, intercom_keys, bic))
    except Exception:
        pass

    try:
        cabinet_pts.extend(su._collect_textnote_points(link_doc, cabinet_keys))
        cabinet_pts.extend(su._collect_independent_tag_points(link_doc, cabinet_keys))
        for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_ElectricalEquipment, DB.BuiltInCategory.OST_ElectricalFixtures):
            cabinet_pts.extend(su._collect_points_by_keywords(link_doc, cabinet_keys, bic))
    except Exception:
        pass

    if (not intercom_pts) and (not cabinet_pts) and (not doors):
        alert('В АР не найдены маркеры "домофон" и/или "шкаф/коробка СС" (TextNote/Tag/элементы), и двери не найдены.')
        return

    t = link_reader.get_total_transform(link_inst)

    idx = su._XYZIndex(cell_ft=5.0)
    dedupe_ft = mm_to_ft(rules.get('socket_dedupe_radius_mm', 300) or 300)

    sym_flags = {}
    for s in (sym_intercom, sym_router):
        sid = s.Id.IntegerValue
        pt_enum = None
        try:
            pt_enum = s.Family.FamilyPlacementType
        except Exception:
            pt_enum = None
        sym_flags[sid] = (
            pt_enum == DB.FamilyPlacementType.WorkPlaneBased,
            pt_enum == DB.FamilyPlacementType.OneLevelBased,
        )

    sp_cache = {}
    pending = []
    placed_total = 0

    max_wall_dist_ft = mm_to_ft(rules.get('ac_wall_search_max_dist_mm', 2500) or 2500)

    with forms.ProgressBar(title='06. Слаботочка...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            txt = su._room_text(room)

            base_z = su._room_level_elevation_ft(room, link_doc)

            # Use room center as tie-break for closest marker
            center_xy = None
            try:
                loc = getattr(room, 'Location', None)
                center_xy = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                center_xy = None

            # Intercom
            placed_intercom = False
            if intercom_pts:
                pts_in = []
                try:
                    pts_in = su._points_in_room(intercom_pts, room, padding_ft=float(search_r_ft or 0.0))
                except Exception:
                    pts_in = []
                if pts_in:
                    p_ic, _ = _closest_point_xy(pts_in, center_xy or pts_in[0])
                    if p_ic is not None:
                        wall, curve = _find_wall_near_point(link_doc, p_ic, max_dist_ft=max_wall_dist_ft)
                        if wall and curve:
                            pt_link = DB.XYZ(float(p_ic.X), float(p_ic.Y), float(base_z + intercom_h_ft))
                            tan = _wall_tangent_xy(curve, pt_link)
                            pt_host = t.OfPoint(pt_link)
                            if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                                idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                                pending.append((wall, pt_link, tan, sym_intercom, None, '{0}:SOCKET_INTERCOM'.format(comment_tag)))
                                placed_intercom = True

            if (not placed_intercom) and doors:
                pick = _pick_room_door_handle_side(room, doors, center_xy, door_probe_ft)
                if pick is not None:
                    door, cdoor, room_normal, handle_dir = pick
                    wall = None
                    curve = None
                    try:
                        wall = getattr(door, 'Host', None)
                        if not isinstance(wall, DB.Wall):
                            wall = None
                    except Exception:
                        wall = None
                    if wall is not None:
                        try:
                            loc = getattr(wall, 'Location', None)
                            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
                        except Exception:
                            curve = None
                    if wall is None or curve is None:
                        wall, curve = _find_wall_near_point(link_doc, cdoor, max_dist_ft=max_wall_dist_ft)
                    if wall and curve:
                        try:
                            w_ft = su._get_opening_width_ft(door, primary_bip=DB.BuiltInParameter.DOOR_WIDTH, fallback_width_mm=900)
                        except Exception:
                            w_ft = None
                        try:
                            offset = (float(w_ft) * 0.5 if w_ft else 0.0) + float(door_offset_ft or 0.0)
                        except Exception:
                            offset = float(door_offset_ft or 0.0)
                        pt_xy = DB.XYZ(
                            float(cdoor.X) + float(handle_dir.X) * float(offset),
                            float(cdoor.Y) + float(handle_dir.Y) * float(offset),
                            float(base_z + intercom_h_ft),
                        )
                        tan = _wall_tangent_xy(curve, pt_xy)
                        pt_host = t.OfPoint(pt_xy)
                        if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                            idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                            pending.append((wall, pt_xy, tan, sym_intercom, None, '{0}:SOCKET_INTERCOM'.format(comment_tag), room_normal))
                            placed_intercom = True

            # Router
            if cabinet_pts:
                pts_in = []
                try:
                    pts_in = su._points_in_room(cabinet_pts, room, padding_ft=float(search_r_ft or 0.0))
                except Exception:
                    pts_in = []
                if pts_in:
                    p_cb, _ = _closest_point_xy(pts_in, center_xy or pts_in[0])
                    if p_cb is not None:
                        wall, curve = _find_wall_near_point(link_doc, p_cb, max_dist_ft=max_wall_dist_ft)
                        if wall and curve:
                            pt_link = DB.XYZ(float(p_cb.X), float(p_cb.Y), float(base_z + router_h_ft))
                            tan = _wall_tangent_xy(curve, pt_link)
                            pt_host = t.OfPoint(pt_link)
                            if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                                idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                                pending.append((wall, pt_link, tan, sym_router, None, '{0}:SOCKET_ROUTER'.format(comment_tag)))

            if len(pending) >= batch_size:
                try:
                    c_all, c_face, c_wp, c_onface, sk_face, sk_place, c_verified = su._place_socket_batch(
                        doc,
                        link_inst,
                        t,
                        pending,
                        sym_flags,
                        sp_cache,
                        comment_value='',
                        strict_hosting=True
                    )
                    placed_total += int(c_all or 0)
                except Exception:
                    log_exception()
                pending = []

    if pending:
        try:
            c_all, c_face, c_wp, c_onface, sk_face, sk_place, c_verified = su._place_socket_batch(
                doc,
                link_inst,
                t,
                pending,
                sym_flags,
                sp_cache,
                comment_value='',
                strict_hosting=True
            )
            placed_total += int(c_all or 0)
        except Exception:
            log_exception()

    output.print_md('## Результат')
    output.print_md('- Создано розеток (слаботочка): **{0}**'.format(placed_total))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception()
        alert('Ошибка. Подробности в pyRevit output.')
