# -*- coding: utf-8 -*-
import math
import re
import io
import json
from pyrevit import DB, forms, revit, script
import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception
from utils_units import mm_to_ft, ft_to_mm
import socket_utils as su

doc = revit.doc
output = script.get_output()
logger = script.get_logger()

def main():
    output.print_md('# 01. Розетки: Общие (жилые/коридоры)')
    
    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SOCKET_GENERAL'.format(comment_tag)

    spacing_mm = rules.get('socket_spacing_mm', 3000)
    height_mm = rules.get('socket_height_mm', 300)
    avoid_door_mm = rules.get('avoid_door_mm', 300)
    avoid_radiator_mm = rules.get('avoid_radiator_mm', 500)
    dedupe_mm = rules.get('socket_dedupe_radius_mm', 300)
    batch_size = int(rules.get('batch_size', 25) or 25)

    spacing_ft = mm_to_ft(spacing_mm)
    height_ft = mm_to_ft(height_mm)
    avoid_door_ft = mm_to_ft(avoid_door_mm)
    avoid_radiator_ft = mm_to_ft(avoid_radiator_mm)
    dedupe_ft = mm_to_ft(dedupe_mm)

    cfg = script.get_config()
    fams = rules.get('family_type_names', {})
    fam_gen = fams.get('socket_general') or fams.get('power_socket')
    sym_gen, lbl_gen, top10 = su._pick_socket_symbol(doc, cfg, fam_gen, cache_prefix='socket_general')

    if not sym_gen:
        # Fallback: pick by exact names even if placement type is unsupported
        def _try_pick_any(names):
            if not names: return None
            if not isinstance(names, (list, tuple)):
                names = [names]
            for n in names:
                if not n: continue
                try: sym = su._find_symbol_by_fullname(doc, n)
                except Exception: sym = None
                if sym: return sym
            return None

        sym_gen = _try_pick_any(fam_gen)
        if sym_gen:
            try: lbl_gen = placement_engine.format_family_type(sym_gen)
            except Exception: lbl_gen = None
            output.print_md('**Warning:** socket type is not wall/face-based; will place without host if possible.')
        else:
            # Auto-pick best socket from project if config doesn't match
            sym_auto, lbl_auto, top10_auto = su._auto_pick_socket_symbol(doc, prefer_fullname=None)
            if sym_auto:
                sym_gen = sym_auto
                lbl_gen = lbl_auto
                output.print_md('**Auto-pick:** {0}'.format(lbl_gen or '<unnamed>'))
                # Persist to rules.default.json for future runs
                try:
                    rules_path = config_loader.get_default_rules_path()
                    with io.open(rules_path, 'r', encoding='utf-8') as fp:
                        data = json.load(fp)
                    fams2 = data.get('family_type_names', {}) or {}
                    arr = fams2.get('socket_general', [])
                    if not isinstance(arr, list):
                        arr = [arr] if arr else []
                    if lbl_gen and lbl_gen not in arr:
                        arr.insert(0, lbl_gen)
                    fams2['socket_general'] = arr
                    data['family_type_names'] = fams2
                    with io.open(rules_path, 'w', encoding='utf-8') as fp:
                        json.dump(data, fp, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            else:
                alert('Socket type not found (General). Check config.')
                return

    # Store last used
    su._store_symbol_id(cfg, 'last_socket_general_symbol_id', sym_gen)
    su._store_symbol_unique_id(cfg, 'last_socket_general_symbol_uid', sym_gen)
    script.save_config()

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst: return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc: return

    raw_rooms = su._get_all_linked_rooms(link_doc)
    
    # Patterns
    hallway_patterns = rules.get('hallway_room_name_patterns', [])
    hallway_rx = su._compile_patterns(hallway_patterns)
    
    wet_patterns = rules.get('wet_room_name_patterns', [])
    wet_rx = su._compile_patterns(wet_patterns)

    # Apartment-only filter (reuse entrance patterns)
    apartment_patterns = list(rules.get('entrance_apartment_room_name_patterns', []) or [])
    public_patterns = list(rules.get('entrance_public_room_name_patterns', []) or [])

    # Ensure apartment corridors are treated as apartment rooms
    for p in (u'корид', u'hall', u'corridor'):
        if p not in apartment_patterns:
            apartment_patterns.append(p)

    # Avoid excluding apartment corridors by overly generic public patterns
    public_patterns = [
        p for p in public_patterns
        if p and (u'корид' not in p) and (u'hall' not in p) and (u'corridor' not in p)
    ]
    apt_rx = su._compile_patterns(apartment_patterns)
    public_rx = su._compile_patterns(public_patterns)
    
    # Exclude kitchens? Rule 2/3 cover kitchens.
    kitchen_patterns = [u'кухн', u'kitchen', u'столов'] # Basic defaults
    kitchen_rx = su._compile_patterns(kitchen_patterns)

    rooms = []
    for r in raw_rooms:
        txt = su._room_text(r)
        # Skip public/common rooms (MOP)
        if public_rx and su._match_any(public_rx, txt):
            continue
        # Keep only apartment rooms
        if apt_rx and (not su._match_any(apt_rx, txt)):
            continue
        # Exclude Wet Rooms (includes WC / Сан. узел)
        if su._match_any(wet_rx, txt):
            continue
        # Hard exclude WC by room params/name (handles 'Сан. узел' variants)
        if su._room_is_wc(r, rules):
            continue
        # Exclude Kitchens (handled by other scripts)
        if su._match_any(kitchen_rx, txt): continue
        rooms.append(r)

    if not rooms:
        alert('Нет подходящих помещений (исключены кухни и санузлы).')
        return

    openings_cache = {}
    radiator_pts = su._collect_radiator_points(link_doc)
    radiator_idx = None
    if radiator_pts:
        radiator_idx = su._XYZIndex(cell_ft=5.0)
        for p in radiator_pts: radiator_idx.add(p.X, p.Y, 0.0)

    t = link_reader.get_total_transform(link_inst)
    idx = su._XYZIndex(cell_ft=5.0) # Dedupe index
    
    sym_flags = {}
    sid = sym_gen.Id.IntegerValue
    # Detect placement type
    pt_enum = None
    try: pt_enum = sym_gen.Family.FamilyPlacementType
    except: pass
    is_wp = (pt_enum == DB.FamilyPlacementType.WorkPlaneBased)
    is_ol = (pt_enum == DB.FamilyPlacementType.OneLevelBased)
    sym_flags[sid] = (is_wp, is_ol)
    strict_hosting_mode = True
    if is_ol:
        strict_hosting_mode = False
        output.print_md(u'**Внимание:** тип розетки OneLevelBased — размещение будет без хоста.')

    sp_cache = {}
    pending = []
    
    created = 0
    boundary_opts = DB.SpatialElementBoundaryOptions()

    with forms.ProgressBar(title='01. Общие розетки...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for i, r in enumerate(rooms):
            if pb.cancelled: break
            pb.update_progress(i, pb.max_value)

            txt_r = su._room_text(r)
            is_hallway = su._match_any(hallway_rx, txt_r)
            
            segs = su._get_room_outer_boundary_segments(r, boundary_opts)
            if not segs: continue
            
            base_z = su._room_level_elevation_ft(r, link_doc)
            
            # Build path
            allowed_path = []
            effective_len_ft = 0.0
            
            for seg in segs:
                c = seg.GetCurve()
                if not c: continue
                seg_len = c.Length
                if seg_len < 1e-9: continue
                
                wall = link_doc.GetElement(seg.ElementId)
                if not isinstance(wall, DB.Wall): continue
                if su._is_curtain_wall(wall): continue
                
                # Check for Window on this wall -> Exclude wall completely?
                # User rule: "не ставим на стену с окном" (do not place on wall with window).
                # Does this apply to ALL rooms or just hallways/wet? 
                # "каждые 3 метра периметра комнат, не ставим на стену с окном" -> Applies to general rooms too.
                ops = su._get_wall_openings_cached(link_doc, wall, openings_cache)
                if ops.get('windows'):
                    continue # Skip this wall entirely
                
                # Doors
                blocked = []
                for pt, w in ops.get('doors', []):
                    half = (float(w)*0.5) if w else 1.5 # fallback 1.5ft
                    d0 = su._project_dist_on_curve_xy_ft(c, seg_len, pt, tol_ft=2.0)
                    if d0 is not None:
                        blocked.append((d0 - half - avoid_door_ft, d0 + half + avoid_door_ft))
                        
                # Radiators (if close to wall)
                # Actually radiator check is usually point-based later.
                # But if "behind radiator", we can block intervals.
                # Let's stick to point filtering for radiators for now.

                merged = su._merge_intervals(blocked, 0.0, seg_len)
                allowed = su._invert_intervals(merged, 0.0, seg_len)
                
                for a, b in allowed:
                    if (b - a) > 1e-6:
                        allowed_path.append((wall, c, seg_len, a, b))
                        effective_len_ft += (b - a)

            if effective_len_ft <= 1e-6: continue

            # Strategy
            candidates = []
            
            if is_hallway:
                area_sqm = 0.0
                try: area_sqm = r.Area * 0.092903
                except: pass
                
                target_count = 1 if area_sqm <= 10.0 else 2
                
                # Generate fine-grained candidates along allowed path (e.g. every 1 ft)
                # to pick best spots. Or just use midpoints of segments.
                # Midpoints of valid segments are good candidates.
                fine_candidates = []
                for w, c, sl, a, b in allowed_path:
                    mid = (a + b) * 0.5
                    pt = c.Evaluate(mid/sl, True)
                    # Dir
                    d = c.ComputeDerivatives(mid/sl, True)
                    v = d.BasisX.Normalize()
                    fine_candidates.append((w, pt, v, (b-a))) # store length as score
                
                if not fine_candidates: continue
                
                if target_count == 1:
                    # Pick longest segment
                    fine_candidates.sort(key=lambda x: x[3], reverse=True)
                    candidates.append(fine_candidates[0][:3])
                else:
                    # Pick 2 farthest
                    best_pair = None
                    max_d = -1.0
                    for i1 in range(len(fine_candidates)):
                        for i2 in range(i1+1, len(fine_candidates)):
                            d = su._dist_xy(fine_candidates[i1][1], fine_candidates[i2][1])
                            if d > max_d:
                                max_d = d
                                best_pair = (fine_candidates[i1][:3], fine_candidates[i2][:3])
                    if best_pair:
                        candidates.extend(best_pair)
                    else:
                        candidates.append(fine_candidates[0][:3])
                        if len(fine_candidates) > 1: candidates.append(fine_candidates[1][:3])

            else:
                # Normal Room: Spacing
                try: num = int(math.floor(effective_len_ft / spacing_ft))
                except: num = 0
                if num < 1: continue
                
                # We need to distribute 'num' points along 'effective_len_ft'
                # Simple approach: Step by spacing_ft.
                step = spacing_ft
                # Or distribute evenly? "каждые 3 метра" usually means max spacing 3m.
                # If we have 10m perimeter, 3 sockets -> 3.3m? Or 4 sockets 2.5m?
                # Usually standard requires "no more than X meters".
                # If effective is 10m, and spacing is 3m. 10/3 = 3.33. We need 4 sockets to keep < 3m?
                # Or just place at 3, 6, 9. 
                # "каждые 3 метра" -> step 3m.
                
                current_d = spacing_ft # Start at 1 spacing
                # Actually, maybe start at spacing/2? or just spacing.
                # Let's stick to previous logic: k * spacing
                
                acc = 0.0
                path_idx = 0
                
                # Flatten path for calculation
                # We iterate global distance
                for k in range(1, num + 1):
                    target_d = k * spacing_ft
                    
                    # Find where target_d falls
                    # Reset traversal or continue? 
                    # We can traverse linear.
                    
                    while path_idx < len(allowed_path):
                        w, c, sl, a, b = allowed_path[path_idx]
                        seg_len_eff = b - a
                        if target_d <= (acc + seg_len_eff):
                            # Found it
                            local_d = a + (target_d - acc)
                            pt = c.Evaluate(local_d/sl, True)
                            d = c.ComputeDerivatives(local_d/sl, True)
                            v = d.BasisX.Normalize()
                            candidates.append((w, pt, v))
                            break
                        else:
                            acc += seg_len_eff
                            path_idx += 1
            
            # Place candidates
            for w, pt, v in candidates:
                p_link = DB.XYZ(pt.X, pt.Y, base_z + height_ft)
                
                # Radiator check
                if radiator_idx and radiator_idx.has_near(p_link.X, p_link.Y, 0.0, avoid_radiator_ft):
                    continue
                
                # Dedupe
                if idx.has_near(p_link.X, p_link.Y, p_link.Z, dedupe_ft):
                    continue
                
                idx.add(p_link.X, p_link.Y, p_link.Z)
                pending.append((w, p_link, v, sym_gen, 0.0))
                
                if len(pending) >= batch_size:
                    c0, _, _, _, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
                    created += c0
                    pending = []

    if pending:
        c0, _, _, _, _, _, _ = su._place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
        created += c0

    output.print_md('Готово. Создано розеток: **{0}**'.format(created))

try:
    main()
except Exception:
    log_exception('Error in 01_General')

