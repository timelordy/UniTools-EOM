# -*- coding: utf-8 -*-

import math
from pyrevit import DB, forms, script
import adapters
import constants
import domain
try:
    import socket_utils as su
except ImportError:
    import sys, os
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as su
from utils_revit import alert, log_exception
from utils_units import mm_to_ft


def run(doc, output):
    output.print_md('# 06. Розетки: Слаботочка (домофон + роутер)')

    rules = adapters.get_rules()
    cfg = adapters.get_config()
    
    comment_tag = rules.get('comment_tag', constants.COMMENT_TAG_DEFAULT)
    batch_size = int(rules.get('batch_size', constants.BATCH_SIZE) or constants.BATCH_SIZE)

    intercom_h_mm = float(rules.get('low_voltage_intercom_height_mm', constants.DEFAULT_INTERCOM_HEIGHT_MM) or constants.DEFAULT_INTERCOM_HEIGHT_MM)
    router_h_mm = float(rules.get('low_voltage_router_height_mm', rules.get('socket_height_mm', constants.DEFAULT_ROUTER_HEIGHT_MM) or constants.DEFAULT_ROUTER_HEIGHT_MM) or constants.DEFAULT_ROUTER_HEIGHT_MM)
    search_r_mm = float(rules.get('low_voltage_search_radius_mm', constants.DEFAULT_SEARCH_RADIUS_MM) or constants.DEFAULT_SEARCH_RADIUS_MM)
    door_offset_mm = float(rules.get('avoid_door_mm', constants.DEFAULT_DOOR_OFFSET_MM) or constants.DEFAULT_DOOR_OFFSET_MM)
    
    intercom_offset_mm = float(rules.get('low_voltage_intercom_offset_mm', constants.DEFAULT_INTERCOM_OFFSET_MM) or constants.DEFAULT_INTERCOM_OFFSET_MM)
    router_offset_mm = float(rules.get('low_voltage_router_offset_mm', constants.DEFAULT_ROUTER_OFFSET_MM) or constants.DEFAULT_ROUTER_OFFSET_MM)

    intercom_h_ft = mm_to_ft(intercom_h_mm)
    router_h_ft = mm_to_ft(router_h_mm)
    search_r_ft = mm_to_ft(search_r_mm)
    door_offset_ft = mm_to_ft(door_offset_mm)
    door_probe_ft = mm_to_ft(constants.DEFAULT_DOOR_PROBE_MM)
    
    intercom_offset_ft = mm_to_ft(intercom_offset_mm)
    router_offset_ft = mm_to_ft(router_offset_mm)

    fams = rules.get('family_type_names', {})
    lv_types = fams.get('socket_low_voltage') or fams.get('power_socket')
    intercom_types = fams.get('socket_intercom') or lv_types
    router_types = fams.get('socket_router') or lv_types

    sym_intercom, _, _ = adapters.pick_socket_symbol(doc, cfg, intercom_types, cache_prefix='socket_intercom')
    sym_router, _, _ = adapters.pick_socket_symbol(doc, cfg, router_types, cache_prefix='socket_router')
    if not sym_intercom or not sym_router:
        alert('Не найден тип розетки для слаботочки (домофон/роутер). Проверьте config/rules.default.json.')
        return 0

    try:
        su._store_symbol_id(cfg, 'last_socket_intercom_symbol_id', sym_intercom)
        su._store_symbol_unique_id(cfg, 'last_socket_intercom_symbol_uid', sym_intercom)
        su._store_symbol_id(cfg, 'last_socket_router_symbol_id', sym_router)
        su._store_symbol_unique_id(cfg, 'last_socket_router_symbol_uid', sym_router)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, 'Выберите связь АР')
    if not link_inst:
        return 0
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc:
        return 0

    rooms = adapters.get_all_linked_rooms(link_doc)
    global LAST_ROOM_COUNT
    try:
        LAST_ROOM_COUNT = len(rooms)
    except Exception:
        LAST_ROOM_COUNT = None
    if not rooms:
        alert('Rooms в связи АР не найдены.')
        return 0

    doors = []
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
        for d in col:
            doors.append(d)
    except Exception:
        doors = []

    intercom_keys = rules.get('intercom_keywords', constants.INTERCOM_KEYWORDS)
    cabinet_keys = rules.get('low_voltage_cabinet_keywords', constants.CABINET_KEYWORDS)

    entrance_door_patterns = rules.get('entrance_door_name_patterns', [
        'вход', 'входн', 'entry', 'entrance', 'тамбур', 'вестиб', 'металл', 'сталь', 'дм_'
    ])

    # Priority for Router placement: Hallway
    hallway_keys = ['прихож', 'холл', 'hall', 'corridor', 'коридор']

    intercom_pts = []
    cabinet_pts = []

    try:
        intercom_pts.extend(adapters.collect_textnote_points(link_doc, intercom_keys))
        intercom_pts.extend(adapters.collect_independent_tag_points(link_doc, intercom_keys))
        for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_ElectricalEquipment, DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_CommunicationDevices):
            intercom_pts.extend(adapters.collect_points_by_keywords(link_doc, intercom_keys, bic))
    except Exception:
        pass

    try:
        cabinet_pts.extend(adapters.collect_textnote_points(link_doc, cabinet_keys))
        cabinet_pts.extend(adapters.collect_independent_tag_points(link_doc, cabinet_keys))
        for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_ElectricalEquipment, DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_CommunicationDevices):
            cabinet_pts.extend(adapters.collect_points_by_keywords(link_doc, cabinet_keys, bic))
    except Exception:
        pass

    if (not intercom_pts) and (not cabinet_pts) and (not doors):
        alert('В АР не найдены маркеры "домофон" и/или "шкаф/коробка СС" (TextNote/Tag/элементы), и двери не найдены.')
        return 0

    t = adapters.get_total_transform(link_inst)

    idx = su._XYZIndex(cell_ft=5.0)
    dedupe_ft = mm_to_ft(rules.get('socket_dedupe_radius_mm', constants.DEFAULT_DEDUPE_MM) or constants.DEFAULT_DEDUPE_MM)

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

    max_wall_dist_ft = mm_to_ft(rules.get('ac_wall_search_max_dist_mm', constants.DEFAULT_MAX_WALL_DIST_MM) or constants.DEFAULT_MAX_WALL_DIST_MM)

    with forms.ProgressBar(title='06. Слаботочка...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(i, pb.max_value)

            base_z = su._room_level_elevation_ft(room, link_doc)

            center_xy = None
            try:
                loc = getattr(room, 'Location', None)
                center_xy = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                center_xy = None
            
            room_name = getattr(room, 'Name', '').lower()
            is_hallway = any(k in room_name for k in hallway_keys)

            placed_intercom = False
            
            # --- INTERCOM ---
            if intercom_pts:
                pts_in = []
                try:
                    pts_in = su._points_in_room(intercom_pts, room, padding_ft=float(search_r_ft or 0.0))
                except Exception:
                    pts_in = []
                if pts_in:
                    p_ic, _ = domain.closest_point_xy(pts_in, center_xy or pts_in[0])
                    if p_ic is not None:
                        wall, curve = domain.find_wall_near_point(link_doc, p_ic, max_dist_ft=max_wall_dist_ft)
                        if wall and curve:
                            # Apply offset for intercom (shift along wall tangent)
                            tan = domain.wall_tangent_xy(curve, p_ic)
                            pt_base_xy = DB.XYZ(float(p_ic.X), float(p_ic.Y), 0)
                            
                            # Shift 200mm to the right (or left? usually right of intercom)
                            # Let's try to detect "right" based on room center?
                            # For simplicity, just add +tangent * offset
                            pt_shifted_xy = pt_base_xy + tan * float(intercom_offset_ft)
                            
                            pt_link = DB.XYZ(float(pt_shifted_xy.X), float(pt_shifted_xy.Y), float(base_z + intercom_h_ft))
                            
                            # Recalculate tangent at new point just in case
                            tan_final = domain.wall_tangent_xy(curve, pt_link)
                            
                            pt_host = t.OfPoint(pt_link)
                            if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                                idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                                pending.append((wall, pt_link, tan_final, sym_intercom, None, '{0}{1}'.format(comment_tag, constants.COMMENT_INTERCOM)))
                                placed_intercom = True

            # Fallback Intercom placement near door handle
            if (not placed_intercom) and doors and is_hallway: # Only in Hallway
                # 1) Сначала пробуем входные/стальные двери
                pick = domain.pick_room_door_handle_side(
                    room,
                    doors,
                    center_xy,
                    door_probe_ft,
                    only_entrance=True,
                    entrance_patterns=entrance_door_patterns
                )

                # 2) Если не нашли - fallback на любую подходящую дверь
                if pick is None:
                    pick = domain.pick_room_door_handle_side(room, doors, center_xy, door_probe_ft)

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
                        wall, curve = domain.find_wall_near_point(link_doc, cdoor, max_dist_ft=max_wall_dist_ft)
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
                        tan = domain.wall_tangent_xy(curve, pt_xy)
                        pt_host = t.OfPoint(pt_xy)
                        if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                            idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                            pending.append((wall, pt_xy, tan, sym_intercom, None, '{0}{1}'.format(comment_tag, constants.COMMENT_INTERCOM), room_normal))
                            placed_intercom = True

            # --- ROUTER ---
            # Ideally only in Hallway or where explicitly found
            if cabinet_pts:
                pts_in = []
                try:
                    pts_in = su._points_in_room(cabinet_pts, room, padding_ft=float(search_r_ft or 0.0))
                except Exception:
                    pts_in = []
                if pts_in:
                    p_cb, _ = domain.closest_point_xy(pts_in, center_xy or pts_in[0])
                    if p_cb is not None:
                        wall, curve = domain.find_wall_near_point(link_doc, p_cb, max_dist_ft=max_wall_dist_ft)
                        if wall and curve:
                            # Shift router socket nearby
                            tan = domain.wall_tangent_xy(curve, p_cb)
                            pt_base_xy = DB.XYZ(float(p_cb.X), float(p_cb.Y), 0)
                            pt_shifted_xy = pt_base_xy + tan * float(router_offset_ft)
                            
                            pt_link = DB.XYZ(float(pt_shifted_xy.X), float(pt_shifted_xy.Y), float(base_z + router_h_ft))
                            tan_final = domain.wall_tangent_xy(curve, pt_link)
                            
                            pt_host = t.OfPoint(pt_link)
                            if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                                idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                                pending.append((wall, pt_link, tan_final, sym_router, None, '{0}{1}'.format(comment_tag, constants.COMMENT_ROUTER)))

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

    try:
        fallback_wall_dist_ft = max(float(max_wall_dist_ft or 0.0), float(mm_to_ft(6000)))
    except Exception:
        fallback_wall_dist_ft = float(mm_to_ft(6000))

    def _room_center_xy(room_obj):
        try:
            loc = getattr(room_obj, 'Location', None)
            return loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            return None

    def _collect_hallway_rooms():
        out = []
        for r in (rooms or []):
            try:
                room_name = (getattr(r, 'Name', '') or '').lower()
            except Exception:
                room_name = ''
            if any(k in room_name for k in hallway_keys):
                out.append(r)
        return out

    def _collect_entrance_doors():
        out = []
        for d in (doors or []):
            try:
                if domain.is_entrance_door(d, entrance_door_patterns):
                    out.append(d)
            except Exception:
                continue
        return out

    def _sorted_doors_for_room(room_obj, door_pool):
        center = _room_center_xy(room_obj)
        ranked = []
        for d in (door_pool or []):
            c = su._inst_center_point(d)
            if c is None:
                continue
            try:
                dxy = su._dist_xy(c, center) if center is not None else 0.0
            except Exception:
                dxy = 0.0
            ranked.append((float(dxy), d))
        ranked.sort(key=lambda x: x[0])
        return [x[1] for x in ranked]

    def _try_place_intercom_for_room_door(room_obj, door_obj, strict_mode, room_normal=None, handle_dir=None):
        if room_obj is None or door_obj is None:
            return 0

        cdoor = su._inst_center_point(door_obj)
        if cdoor is None:
            return 0

        wall = None
        curve = None
        try:
            wall = getattr(door_obj, 'Host', None)
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
            wall, curve = domain.find_wall_near_point(link_doc, cdoor, max_dist_ft=fallback_wall_dist_ft)
        if not wall or not curve:
            return 0

        try:
            w_ft = su._get_opening_width_ft(door_obj, primary_bip=DB.BuiltInParameter.DOOR_WIDTH, fallback_width_mm=900)
        except Exception:
            w_ft = None
        try:
            offset = (float(w_ft) * 0.5 if w_ft else 0.0) + float(door_offset_ft or 0.0)
        except Exception:
            offset = float(door_offset_ft or 0.0)

        def _append_unique_xy_vec(dst, vec):
            v = domain.xy_unit(vec)
            if v is None:
                return
            for e in dst:
                try:
                    if abs(float(e.X) - float(v.X)) <= 1e-6 and abs(float(e.Y) - float(v.Y)) <= 1e-6:
                        return
                except Exception:
                    continue
            dst.append(v)

        def _append_unique_float(dst, value, eps=1e-4):
            try:
                v = float(value)
            except Exception:
                return
            for e in dst:
                try:
                    if abs(float(e) - v) <= float(eps):
                        return
                except Exception:
                    continue
            dst.append(v)

        if handle_dir is None:
            handle_dir = domain.door_handle_dir_xy(door_obj)

        facing = None
        if handle_dir is None:
            facing = domain.try_get_door_facing_xy(door_obj)
            if facing is not None:
                try:
                    handle_dir = domain.xy_unit(DB.XYZ(-float(facing.Y), float(facing.X), 0.0))
                    if room_normal is None:
                        room_normal = domain.room_side_normal_from_facing(room_obj, cdoor, facing, door_probe_ft) or facing
                except Exception:
                    handle_dir = None

        wall_tan = domain.wall_tangent_xy(curve, cdoor)
        if wall_tan is None or wall_tan.GetLength() < 1e-9:
            wall_tan = DB.XYZ.BasisX

        if handle_dir is None:
            handle_dir = wall_tan

        if handle_dir is None or handle_dir.GetLength() < 1e-9:
            handle_dir = DB.XYZ.BasisX

        if room_normal is None:
            if facing is None:
                facing = domain.try_get_door_facing_xy(door_obj)
            if facing is not None:
                room_normal = domain.room_side_normal_from_facing(room_obj, cdoor, facing, door_probe_ft) or facing

        dir_candidates = []
        _append_unique_xy_vec(dir_candidates, handle_dir)
        try:
            _append_unique_xy_vec(dir_candidates, DB.XYZ(-float(handle_dir.X), -float(handle_dir.Y), 0.0))
        except Exception:
            pass
        _append_unique_xy_vec(dir_candidates, wall_tan)
        try:
            _append_unique_xy_vec(dir_candidates, DB.XYZ(-float(wall_tan.X), -float(wall_tan.Y), 0.0))
        except Exception:
            pass
        if not dir_candidates:
            dir_candidates = [DB.XYZ.BasisX]

        base_z_candidates = []
        _append_unique_float(base_z_candidates, su._room_level_elevation_ft(room_obj, link_doc))
        try:
            room_bb = room_obj.get_BoundingBox(None)
            if room_bb is not None:
                _append_unique_float(base_z_candidates, room_bb.Min.Z)
        except Exception:
            pass
        try:
            door_bb = door_obj.get_BoundingBox(None)
            if door_bb is not None:
                _append_unique_float(base_z_candidates, door_bb.Min.Z)
        except Exception:
            pass
        if not base_z_candidates:
            _append_unique_float(base_z_candidates, 0.0)

        offset_candidates = []
        try:
            main_offset = float(offset)
        except Exception:
            main_offset = float(door_offset_ft or 0.0)
        min_offset = float(mm_to_ft(150))
        _append_unique_float(offset_candidates, main_offset)
        _append_unique_float(offset_candidates, max(main_offset * 0.5, min_offset))
        _append_unique_float(offset_candidates, max(float(door_offset_ft or 0.0), min_offset))
        _append_unique_float(offset_candidates, min_offset)
        _append_unique_float(offset_candidates, 0.0)

        tried_pts = set()

        for base_z in base_z_candidates:
            for dvec in dir_candidates:
                for off in offset_candidates:
                    pt_xy = DB.XYZ(
                        float(cdoor.X) + float(dvec.X) * float(off),
                        float(cdoor.Y) + float(dvec.Y) * float(off),
                        float(base_z + intercom_h_ft),
                    )

                    try:
                        p_key = (round(float(pt_xy.X), 4), round(float(pt_xy.Y), 4), round(float(pt_xy.Z), 4))
                    except Exception:
                        p_key = None
                    if p_key is not None:
                        if p_key in tried_pts:
                            continue
                        tried_pts.add(p_key)

                    tan = domain.wall_tangent_xy(curve, pt_xy)
                    if tan is None or tan.GetLength() < 1e-9:
                        tan = wall_tan

                    prefer_room_normal = room_normal
                    if prefer_room_normal is None:
                        try:
                            prefer_room_normal = domain.xy_unit(DB.XYZ(-float(tan.Y), float(tan.X), 0.0))
                        except Exception:
                            prefer_room_normal = None

                    item = (wall, pt_xy, tan, sym_intercom, None, '{0}{1}'.format(comment_tag, constants.COMMENT_INTERCOM), prefer_room_normal)

                    try:
                        c_all, c_face, c_wp, c_onface, sk_face, sk_place, c_verified = su._place_socket_batch(
                            doc,
                            link_inst,
                            t,
                            [item],
                            sym_flags,
                            sp_cache,
                            comment_value='',
                            strict_hosting=bool(strict_mode),
                            wall_search_ft=fallback_wall_dist_ft
                        )
                        placed_add = int(c_all or 0)
                    except Exception:
                        log_exception()
                        placed_add = 0

                    if placed_add > 0:
                        try:
                            pt_host = t.OfPoint(pt_xy)
                            if not idx.has_near(pt_host.X, pt_host.Y, pt_host.Z, dedupe_ft):
                                idx.add(pt_host.X, pt_host.Y, pt_host.Z)
                        except Exception:
                            pass
                        return placed_add

        return 0

    hallway_rooms = _collect_hallway_rooms()
    fallback_rooms = hallway_rooms if hallway_rooms else list(rooms)

    entrance_doors = _collect_entrance_doors()
    fallback_doors = entrance_doors if entrance_doors else list(doors)

    # Final guarantee: если не поставили ни одной слаботочной розетки,
    # пытаемся поставить минимум одну домофонную у входной двери.
    if placed_total <= 0 and doors:
        try:
            placed_guarantee = False
            for room in fallback_rooms:
                center_xy = _room_center_xy(room)
                for door in _sorted_doors_for_room(room, fallback_doors):
                    pick = domain.pick_room_door_handle_side(room, [door], center_xy, door_probe_ft)
                    room_normal = pick[2] if pick is not None else None
                    handle_dir = pick[3] if pick is not None else None

                    placed_add = _try_place_intercom_for_room_door(
                        room,
                        door,
                        strict_mode=True,
                        room_normal=room_normal,
                        handle_dir=handle_dir,
                    )
                    if placed_add > 0:
                        placed_total += placed_add
                        placed_guarantee = True
                        output.print_md('- Guarantee fallback: поставлена 1 розетка домофона у входной двери')
                        break
                if placed_guarantee:
                    break

            if not placed_guarantee:
                output.print_md(
                    '- Guarantee fallback: не удалось создать розетку у входной двери (rooms={0}, doors={1}, entrance={2}; переход к упрощенному режиму)'.format(
                        len(fallback_rooms),
                        len(fallback_doors),
                        len(entrance_doors),
                    )
                )
        except Exception:
            log_exception()

    if placed_total <= 0 and doors:
        # Last-resort fallback: без строгого хостинга и с максимально мягким подбором двери/направления.
        try:
            placed_last_resort = False
            for room in fallback_rooms:
                for door in _sorted_doors_for_room(room, fallback_doors):
                    placed_add = _try_place_intercom_for_room_door(
                        room,
                        door,
                        strict_mode=False,
                        room_normal=None,
                        handle_dir=None,
                    )
                    if placed_add > 0:
                        placed_total += placed_add
                        placed_last_resort = True
                        output.print_md('- Last-resort fallback: поставлена 1 розетка домофона у двери (без строгого хостинга)')
                        break
                if placed_last_resort:
                    break

            if (not placed_last_resort) and placed_total <= 0:
                output.print_md(
                    '- Last-resort fallback: не удалось создать розетку даже в упрощенном режиме (rooms={0}, doors={1}, entrance={2})'.format(
                        len(fallback_rooms),
                        len(fallback_doors),
                        len(entrance_doors),
                    )
                )
        except Exception:
            log_exception()

    # Recovery pass: если общий результат все еще слишком мал,
    # пытаемся доразместить домофонные розетки по входным дверям (мягкий режим).
    try:
        recovery_threshold = int(rules.get('low_voltage_min_intercom_recovery_count', 2) or 2)
    except Exception:
        recovery_threshold = 2

    if doors and placed_total < recovery_threshold:
        try:
            recovery_pool = list(entrance_doors) if entrance_doors else list(fallback_doors)
            if recovery_pool:
                placed_recovery = 0
                for room in fallback_rooms:
                    center_xy = _room_center_xy(room)
                    for door in _sorted_doors_for_room(room, recovery_pool):
                        if placed_total >= recovery_threshold:
                            break

                        pick = domain.pick_room_door_handle_side(room, [door], center_xy, door_probe_ft)
                        room_normal = pick[2] if pick is not None else None
                        handle_dir = pick[3] if pick is not None else None

                        placed_add = _try_place_intercom_for_room_door(
                            room,
                            door,
                            strict_mode=False,
                            room_normal=room_normal,
                            handle_dir=handle_dir,
                        )
                        if placed_add > 0:
                            placed_total += placed_add
                            placed_recovery += placed_add
                    if placed_total >= recovery_threshold:
                        break

                if placed_recovery > 0:
                    output.print_md(
                        '- Recovery fallback: дополнительно создано {0} розеток домофона (цель минимум: {1})'.format(
                            placed_recovery,
                            recovery_threshold,
                        )
                    )
        except Exception:
            log_exception()

    output.print_md('## Результат')
    output.print_md('- Создано розеток (слаботочка): **{0}**'.format(placed_total))
    return int(placed_total or 0)


