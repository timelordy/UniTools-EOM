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
    output.print_md('# 06. Р РѕР·РµС‚РєРё: РЎР»Р°Р±РѕС‚РѕС‡РєР° (РґРѕРјРѕС„РѕРЅ + СЂРѕСѓС‚РµСЂ)')

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
        alert('РќРµ РЅР°Р№РґРµРЅ С‚РёРї СЂРѕР·РµС‚РєРё РґР»СЏ СЃР»Р°Р±РѕС‚РѕС‡РєРё (РґРѕРјРѕС„РѕРЅ/СЂРѕСѓС‚РµСЂ). РџСЂРѕРІРµСЂСЊС‚Рµ config/rules.default.json.')
        return

    try:
        su._store_symbol_id(cfg, 'last_socket_intercom_symbol_id', sym_intercom)
        su._store_symbol_unique_id(cfg, 'last_socket_intercom_symbol_uid', sym_intercom)
        su._store_symbol_id(cfg, 'last_socket_router_symbol_id', sym_router)
        su._store_symbol_unique_id(cfg, 'last_socket_router_symbol_uid', sym_router)
        adapters.save_config()
    except Exception:
        pass

    link_inst = adapters.select_link_instance(doc, 'Р’С‹Р±РµСЂРёС‚Рµ СЃРІСЏР·СЊ РђР ')
    if not link_inst:
        return
    link_doc = adapters.get_link_doc(link_inst)
    if not link_doc:
        return

    rooms = adapters.get_all_linked_rooms(link_doc)
    global LAST_ROOM_COUNT
    try:
        LAST_ROOM_COUNT = len(rooms)
    except Exception:
        LAST_ROOM_COUNT = None
    if not rooms:
        alert('Rooms РІ СЃРІСЏР·Рё РђР  РЅРµ РЅР°Р№РґРµРЅС‹.')
        return

    doors = []
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
        for d in col:
            doors.append(d)
    except Exception:
        doors = []

    intercom_keys = rules.get('intercom_keywords', constants.INTERCOM_KEYWORDS)
    cabinet_keys = rules.get('low_voltage_cabinet_keywords', constants.CABINET_KEYWORDS)
    
    # Priority for Router placement: Hallway
    hallway_keys = ['РїСЂРёС…РѕР¶', 'С…РѕР»Р»', 'hall', 'corridor', 'РєРѕСЂРёРґРѕСЂ']

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
        alert('Р’ РђР  РЅРµ РЅР°Р№РґРµРЅС‹ РјР°СЂРєРµСЂС‹ "РґРѕРјРѕС„РѕРЅ" Рё/РёР»Рё "С€РєР°С„/РєРѕСЂРѕР±РєР° РЎРЎ" (TextNote/Tag/СЌР»РµРјРµРЅС‚С‹), Рё РґРІРµСЂРё РЅРµ РЅР°Р№РґРµРЅС‹.')
        return

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

    with forms.ProgressBar(title='06. РЎР»Р°Р±РѕС‚РѕС‡РєР°...', cancellable=True) as pb:
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

    output.print_md('## Р РµР·СѓР»СЊС‚Р°С‚')
    output.print_md('- РЎРѕР·РґР°РЅРѕ СЂРѕР·РµС‚РѕРє (СЃР»Р°Р±РѕС‚РѕС‡РєР°): **{0}**'.format(placed_total))

