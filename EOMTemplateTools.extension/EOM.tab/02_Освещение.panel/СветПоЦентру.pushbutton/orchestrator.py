# -*- coding: utf-8 -*-

import System
from pyrevit import DB
from utils_revit import alert, set_comments, tx, find_nearest_level, trace
from utils_units import mm_to_ft
import link_reader
import placement_engine
import adapters
import domain
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

    rules = adapters.get_rules()

    # DEBUG: List all lighting fixture symbols
    sym_col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
    print(u'--- AVAILABLE LIGHTING FIXTURE SYMBOLS ---')
    for s in sym_col:
        try:
            sym_name = s.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or str(s.Id.IntegerValue)
        except:
            sym_name = str(s.Id.IntegerValue)
        try:
            fam_name = s.get_Parameter(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString() or u""
        except:
            fam_name = u""
        print(u'Name: {0} | Family: {1}'.format(sym_name, fam_name))
    print(u'------------------------------------------')

    # Defaults
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    ceiling_height_mm = rules.get('light_center_room_height_mm', 2700)
    ceiling_height_ft = mm_to_ft(ceiling_height_mm) or 0.0
    comment_value = '{0}:LIGHT_CENTER'.format(comment_tag)

    link_inst = adapters.select_link_instance_ru(doc, title='Выберите связь АР')
    if link_inst is None:
        output.print_md('**Отменено.**')
        return
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её в «Управление связями» и повторите.')
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи. Убедитесь, что связь загружена.')
        return

    # Levels
    trace('Select levels UI')
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
        return

    # Resolve families
    fam_names = rules.get('family_type_names', {}) or {}
    fam_ceiling = fam_names.get('light_ceiling_point') or ''
    fam_wall = fam_names.get('light_wall_bath') or '' # New wall type

    # Try to find specific family for wall lights if not configured
    if not fam_wall:
        # Look for something that looks like a wall light
        candidates = ['Бра', 'Настен', 'Wall', 'Указатель', 'Выход']
        sym_col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        for s in sym_col:
            fn = s.FamilyName
            if any(c in fn for c in candidates):
                fam_wall = fn
                output.print_md('**Авто-выбор настенного светильника:** `{0}`'.format(fam_wall))
                break

    # Symbols
    sym_ceiling = adapters.find_family_symbol(doc, fam_ceiling, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    if not sym_ceiling:
        # Fallback: pick first valid lighting fixture
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        for e in col:
            if isinstance(e, DB.FamilySymbol):
                sym_ceiling = e
                break

    sym_wall = adapters.find_family_symbol(doc, fam_wall, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    # If no wall symbol found, use ceiling symbol as fallback (better than nothing)
    if not sym_wall:
        sym_wall = sym_ceiling

    if not sym_ceiling:
        alert('Не найдено семейство светильника. Загрузите семейство и повторите.')
        return

    # Activate symbols
    with tx('Activate Symbols', doc=doc):
        if not sym_ceiling.IsActive: sym_ceiling.Activate()
        if sym_wall and not sym_wall.IsActive: sym_wall.Activate()
        doc.Regenerate()

    # Pre-collect ALL existing lights (not just current type) to prevent overlap with anything
    existing_centers = adapters.collect_existing_lights_centers(doc, tolerance_ft=1.5)

    link_transform = link_inst.GetTotalTransform()

    # Collect rooms
    rooms_raw = []
    for lvl in selected_levels:
        lid = lvl.Id
        rooms_raw.extend(adapters.iter_rooms(link_doc, level_id=lid))

    if not rooms_raw:
        alert('В выбранных уровнях не найдено помещений (Rooms).')
        return

    # Deduplicate rooms (handle Design Options or bad links)
    rooms = filter_duplicate_rooms(rooms_raw)

    # Pre-collect doors for "Above Door" logic
    all_doors = list(adapters.iter_doors(link_doc))
    # Pre-collect plumbing for "Above Sink" logic
    all_plumbing = list(adapters.iter_plumbing_fixtures(link_doc))

    placed_ids = []
    debug_view = None

    # Main Transaction with SWALLOW WARNINGS
    with tx('Place Room Center Lights', doc=doc, swallow_warnings=True):
        count = 0
        skipped_ext = 0
        skipped_dup = 0

        # Try to prepare debug view for the first selected level
        try:
            first_r_level = link_doc.GetElement(selected_levels[0].Id)
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
                    print(u'DEBUG: Bathroom "{0}" -> SINK found'.format(room_name(r)))
                else:
                    # Fallback to Center (Ceiling)
                    target_pts = get_room_centers_multi(r)
                    target_symbol = sym_ceiling
                    placement_z_mode = 'ceiling'
                    print(u'DEBUG: Bathroom "{0}" -> No sink, fallback to CENTER'.format(room_name(r)))

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
                        # Enhanced debug: show door ID and location
                        try:
                            door_loc = door.Location.Point if door.Location else None
                            door_z = door_loc.Z if door_loc else 'N/A'
                            print(u'DEBUG: Toilet "{0}" -> Door ID {1}, DoorZ={2:.2f}, LightZ={3:.2f}'.format(
                                room_name(r), door.Id.IntegerValue, door_z, pt.Z))
                        except:
                            print(u'DEBUG: Toilet "{0}" -> Door found'.format(room_name(r)))
                
                if not found_door_pt:
                    # Fallback to Center (Ceiling)
                    target_pts = get_room_centers_multi(r)
                    target_symbol = sym_ceiling
                    placement_z_mode = 'ceiling'
                    print(u'DEBUG: Toilet "{0}" -> No door/calc failed, fallback to CENTER'.format(room_name(r)))

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
                    z = host_level.Elevation + ceiling_height_ft

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
                    print(u'DEBUG: Created ID {0} at {1}'.format(inst.Id, insert_point))
                except Exception as e1:
                    # Plan B: Try using ceiling symbol (usually unhosted) if wall symbol failed (e.g. wall-hosted)
                    if target_symbol.Id != sym_ceiling.Id:
                         try:
                             print(u'DEBUG: Failed with wall symbol. Retrying with ceiling symbol...')
                             inst = doc.Create.NewFamilyInstance(insert_point, sym_ceiling, host_level, DB.Structure.StructuralType.NonStructural)
                             set_comments(inst, comment_value)
                             placed_ids.append(inst.Id)
                             existing_centers.append(insert_point)
                             count += 1
                             print(u'DEBUG: Created ID {0} (Plan B) at {1}'.format(inst.Id, insert_point))
                         except Exception as e2:
                             print(u'DEBUG: ERROR creating instance (Plan B) at {0}: {1}'.format(insert_point, str(e2)))
                    else:
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
