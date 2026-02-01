# -*- coding: utf-8 -*-

import System
from pyrevit import DB
from utils_revit import alert, set_comments, tx, find_nearest_level, trace
from utils_units import mm_to_ft
import link_reader
import placement_engine
import adapters
import domain
try:
    import socket_utils as su
except ImportError:
    # Fallback to lib in extension if path setup is weird
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su

from domain import (
    room_name,
    is_excluded_room,
    is_bathroom,
    is_toilet,
    find_best_door_for_room,
    get_above_door_point,
    get_room_centers_multi,
    filter_duplicate_rooms,
    is_too_close
)


def run_placement(doc, uidoc, output, script_module):
    try:
        System.GC.Collect()
    except Exception:
        pass

    output.print_md('# Размещение светильников по помещениям (правила)')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    trace('Place_Lights_RoomCenters: start')

    def _build_result(placed, skipped_ext, skipped_dup):
        skipped_total = skipped_ext + skipped_dup
        return {
            'placed': placed,
            'skipped': skipped_total,
            'skipped_ext': skipped_ext,
            'skipped_dup': skipped_dup,
        }

    rules = adapters.get_rules()

    # Defaults
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    ceiling_height_mm = rules.get('light_center_room_height_mm', 2700)
    ceiling_height_ft = mm_to_ft(ceiling_height_mm) or 0.0
    comment_value = '{0}:LIGHT_CENTER'.format(comment_tag)

    link_inst = adapters.select_link_instance_ru(doc, title='Выберите связь АР')
    if link_inst is None:
        output.print_md('**Отменено.**')
        return _build_result(0, 0, 0)
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её в «Управление связями» и повторите.')
        return _build_result(0, 0, 0)

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи. Убедитесь, что связь загружена.')
        return _build_result(0, 0, 0)

    link_transform = link_reader.get_total_transform(link_inst)

    # Levels
    trace('Select levels UI')
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
        return _build_result(0, 0, 0)

    def _norm_level_name(name):
        try:
            return (name or '').strip().lower()
        except Exception:
            return ''

    # Host doc levels indexed by name (prefer mapping by AR link level name).
    host_levels_by_name = {}
    try:
        for hl in DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements():
            try:
                key = _norm_level_name(getattr(hl, 'Name', None))
                if key and key not in host_levels_by_name:
                    host_levels_by_name[key] = hl
            except Exception:
                pass
    except Exception:
        host_levels_by_name = {}

    # Resolve families
    fam_names = rules.get('family_type_names', {}) or {}
    fam_ceiling = fam_names.get('light_ceiling_point') or ''
    fam_wall = fam_names.get('light_wall_bath') or '' # New wall type

    # Try to find specific family for wall lights if not configured
    if not fam_wall:
        # Look for something that looks like a wall light
        candidates = ['Бра', 'Настен', 'Wall', 'Указатель', 'Выход']
        exclude_candidates = [
            'розетк', 'socket', 'выключатель', 'switch', 'рамка', 'frame', 
            'коробка', 'box', 'control', 'датчик', 'sensor'
        ]
        
        sym_col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        for s in sym_col:
            fn = s.FamilyName
            try:
                fn_lower = (fn or "").lower()
            except:
                fn_lower = ""
            
            # Check exclusions
            if any(exc in fn_lower for exc in exclude_candidates):
                continue

            if any(c in fn for c in candidates):
                fam_wall = fn
                output.print_md('**Авто-выбор настенного светильника:** `{0}`'.format(fam_wall))
                break

    # Symbols
    sym_ceiling = adapters.find_family_symbol(doc, fam_ceiling, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    if not sym_ceiling:
        # Fallback: pick first valid lighting fixture
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        
        exclude_candidates = [
            'розетк', 'socket', 'выключатель', 'switch', 'рамка', 'frame', 
            'коробка', 'box', 'control', 'датчик', 'sensor'
        ]

        for e in col:
            if isinstance(e, DB.FamilySymbol):
                fn = e.FamilyName
                try:
                    fn_lower = (fn or "").lower()
                except:
                    fn_lower = ""
                
                if any(exc in fn_lower for exc in exclude_candidates):
                    continue

                sym_ceiling = e
                break

    sym_wall = adapters.find_family_symbol(doc, fam_wall, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    # If no wall symbol found, use ceiling symbol as fallback (better than nothing)
    if not sym_wall:
        sym_wall = sym_ceiling

    if not sym_ceiling:
        alert('Не найдено семейство светильника. Загрузите семейство и повторите.')
        return _build_result(0, 0, 0)

    # Activate symbols
    with tx('Activate Symbols', doc=doc):
        if not sym_ceiling.IsActive: sym_ceiling.Activate()
        if sym_wall and not sym_wall.IsActive: sym_wall.Activate()
        doc.Regenerate()

    # Pre-collect ALL existing lights (not just current type) to prevent overlap with anything
    existing_centers = adapters.collect_existing_lights_centers(doc, tolerance_ft=1.5)

    # Collect rooms
    rooms_raw = []
    for lvl in selected_levels:
        lid = lvl.Id
        rooms_raw.extend(adapters.iter_rooms(link_doc, level_id=lid))

    if not rooms_raw:
        alert('В выбранных уровнях не найдено помещений (Rooms).')
        return _build_result(0, 0, 0)

    # Deduplicate rooms (handle Design Options or bad links)
    rooms = filter_duplicate_rooms(rooms_raw)

    # Pre-collect doors for "Above Door" logic
    all_doors = list(adapters.iter_doors(link_doc))
    # Pre-collect plumbing for "Above Sink" logic
    all_plumbing = list(adapters.iter_plumbing_fixtures(link_doc))

    placed_ids = []
    debug_view = None

    # Main Transaction with SWALLOW WARNINGS
    count = 0
    skipped_ext = 0
    skipped_dup = 0
    with tx('Place Room Center Lights', doc=doc, swallow_warnings=True):
        count = 0
        skipped_ext = 0
        skipped_dup = 0

        # Try to prepare debug view for the first selected level
        try:
            first_r_level = selected_levels[0]
            first_host_level = host_levels_by_name.get(_norm_level_name(getattr(first_r_level, 'Name', None)))
            if not first_host_level:
                first_host_level = find_nearest_level(doc, first_r_level.Elevation + link_transform.Origin.Z)
            if first_host_level:
                debug_view = adapters.get_or_create_debug_view(doc, first_host_level.Id)
        except Exception:
            pass

        for r in rooms:
            # Check exclusions (balcony, loggia, technical)
            if is_excluded_room(r):
                skipped_ext += 1
                continue

            # Determine Placement Strategy
            target_pts = []
            target_symbol = sym_ceiling
            placement_z_mode = 'ceiling' # ceiling or door_relative or absolute_z

            if is_bathroom(r):
                # Bathroom Rule:
                # 1. Light over sink (height 2m)
                # Fallback: Center (Ceiling)
                
                target_symbol = sym_wall
                
                # Try Sink
                sink_height_ft = mm_to_ft(2000) # 2m above floor
                pt_sink = domain.get_above_sink_point(r, all_plumbing, sink_height_ft)
                
                if pt_sink:
                    target_pts = [pt_sink]
                    placement_z_mode = 'absolute_z_link'
                else:
                    # Fallback to Center (Ceiling)
                    target_pts = get_room_centers_multi(r)
                    target_symbol = sym_ceiling
                    placement_z_mode = 'ceiling'

            elif is_toilet(r):
                # Toilet Rule:
                # 1. Wall light over door
                # Fallback: Center (Ceiling)
                
                target_symbol = sym_wall
                
                # Try Door
                door = find_best_door_for_room(r, all_doors)
                found_door_pt = False
                
                if door:
                    pt = get_above_door_point(r, door)
                    if pt:
                        target_pts = [pt]
                        found_door_pt = True
                        placement_z_mode = 'door_relative'
                
                if not found_door_pt:
                    # Fallback to Center (Ceiling)
                    target_pts = get_room_centers_multi(r)
                    target_symbol = sym_ceiling
                    placement_z_mode = 'ceiling'

            else:
                # Strategy: Standard (Center or Corridor)
                target_pts = domain.get_room_centers_multi(r)
                placement_z_mode = 'ceiling'

            if not target_pts:
                continue

            # Place loop
            for p_link in target_pts:
                p_host = link_transform.OfPoint(p_link)

                # Find nearest host level
                try:
                    r_level_id = r.LevelId
                    r_level = link_doc.GetElement(r_level_id)
                    r_elev = r_level.Elevation

                    host_level = host_levels_by_name.get(_norm_level_name(getattr(r_level, 'Name', None)))
                    if not host_level:
                        host_level = find_nearest_level(doc, r_elev + link_transform.Origin.Z)
                except Exception:
                    host_level = None

                if not host_level:
                    continue

                # Calc Z
                if placement_z_mode == 'door_relative' or placement_z_mode == 'absolute_z_link':
                    # p_link.Z already includes height logic.
                    # p_host is transformed (includes link Z offset).
                    z = p_host.Z 
                else:
                    # Use AR link level elevation (transformed) as source of truth.
                    z = (r_elev + link_transform.Origin.Z) + ceiling_height_ft

                insert_point = DB.XYZ(p_host.X, p_host.Y, z)

                # Check duplicates (manual geometry check against ALL lights)
                if is_too_close(insert_point, existing_centers, tolerance_ft=1.5):
                    skipped_dup += 1
                    continue

                # Place
                try:
                    inst = doc.Create.NewFamilyInstance(insert_point, target_symbol, host_level, DB.Structure.StructuralType.NonStructural)
                    set_comments(inst, comment_value)
                    placed_ids.append(inst.Id)
                    # Add to existing list to prevent duplicates within same run
                    existing_centers.append(insert_point)
                    count += 1
                except Exception as e1:
                    # Plan B: Try using ceiling symbol (usually unhosted) if wall symbol failed (e.g. wall-hosted)
                    if target_symbol.Id != sym_ceiling.Id:
                        try:
                            inst = doc.Create.NewFamilyInstance(insert_point, sym_ceiling, host_level, DB.Structure.StructuralType.NonStructural)
                            set_comments(inst, comment_value)
                            placed_ids.append(inst.Id)
                            existing_centers.append(insert_point)
                            count += 1
                            continue
                        except Exception:
                            pass
                    print(u'DEBUG: ERROR creating instance at {0}: {1}'.format(insert_point, str(e1)))
                    continue

        output.print_md('**Готово.** Размещено светильников: {0}'.format(count))
        if skipped_ext > 0:
            output.print_md('Пропущено помещений (балкон/техн/МОП): {0}'.format(skipped_ext))
        if skipped_dup > 0:
            output.print_md('Пропущено дублей (уже есть светильник): {0}'.format(skipped_dup))

    # Activate debug view logic (Outside transaction)
    if debug_view:
        try:
            uidoc.ActiveView = debug_view
            if placed_ids:
                # Select placed elements
                net_ids = adapters.as_net_id_list(placed_ids)
                if net_ids:
                    uidoc.Selection.SetElementIds(net_ids)
                    uidoc.ShowElements(net_ids)
        except Exception:
            pass

    return _build_result(count, skipped_ext, skipped_dup)
