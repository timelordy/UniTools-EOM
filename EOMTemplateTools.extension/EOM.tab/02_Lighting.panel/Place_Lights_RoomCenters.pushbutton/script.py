# -*- coding: utf-8 -*-

import math
import time
import System

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception, set_comments, tx, find_nearest_level, trace
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


_ROOM_MIN_WALL_CLEAR_FT = 0.0

# NOTE: Linked-room geometry APIs (Room.GetBoundarySegments / Room.IsPointInRoom)
# are known to hard-crash Revit on some models. Keep these OFF by default.
_USE_BOUNDARY_ROOM_CENTER = False
_USE_NATIVE_IS_POINT_IN_ROOM = False

# Extra duplicate-room detection by geometric overlap can be unsafe when we do not
# have a reliable point-in-room test (bbox-only checks cause many false positives).
# Keep it disabled unless explicitly enabled AND native Room.IsPointInRoom is enabled.
_ENABLE_OVERLAP_ROOM_DEDUPE = False


def _as_net_id_list(ids):
    """Convert python list[ElementId] to .NET List[ElementId] for Revit API calls."""
    try:
        from System.Collections.Generic import List
        lst = List[DB.ElementId]()
        for i in ids or []:
            try:
                if i is not None:
                    lst.Add(i)
            except Exception:
                continue
        return lst
    except Exception:
        return None


def _get_room_centers_multi(room):
    """Return placement points.
    
    Logic:
    - Corridors: Linear array (spacing ~2.5m / 8.2ft).
    - Others: Single center point.
    """
    
    if _is_corridor(room):
        pts = _get_corridor_points(room)
        if pts:
            return pts
        # Fallback to single center if linear calculation failed or room too small
    
    c = _get_room_center_link(room)
    return [c] if c else []


def _is_corridor(room):
    """Check if room is a corridor/hallway/elevator hall/vestibule."""
    name = _room_name(room).lower()
    keywords = [
        u'коридор', u'холл', u'corridor', u'hall', u'прихожая', u'вестибюль',
        u'лифтов', u'тамбур'
    ]
    return any(k in name for k in keywords)


def _is_wet_room(room):
    """Check if room is a Bath/WC/Toilet (Wet Area)."""
    name = _room_name(room).lower()
    keywords = [
        u'ванная', u'санузел', u'сан. узел', u'туалет', u'уборная', 
        u'bath', u'toilet', u'wc', u'restroom', u'shower', u'душевая'
    ]
    return any(k in name for k in keywords)


def _get_corridor_points(room):
    """Generate linear points for corridors along the long axis."""
    bb = room.get_BoundingBox(None)
    if not bb:
        return []
    
    # 1. Determine Dimensions
    min_pt, max_pt = bb.Min, bb.Max
    width_x = max_pt.X - min_pt.X
    width_y = max_pt.Y - min_pt.Y
    
    # 2. Identify Axis (Long side)
    is_x_long = width_x > width_y
    long_len = width_x if is_x_long else width_y
    short_len = width_y if is_x_long else width_x
    
    # 3. Spacing Rules
    SPACING_FT = mm_to_ft(2500)
    
    # If room is small/square-ish, treat as single point (return empty -> fallback to single)
    if long_len < (SPACING_FT * 1.5) or (long_len / short_len) < 2.0:
        return []
    
    # 4. Calculate Points
    count = int(round(long_len / SPACING_FT))
    count = max(2, count) # At least 2 for long corridors
    
    mid_short = (min_pt.Y + max_pt.Y)*0.5 if is_x_long else (min_pt.X + max_pt.X)*0.5
    start_long = min_pt.X if is_x_long else min_pt.Y
    
    points = []
    step = long_len / float(count)
    current = start_long + (step / 2.0)
    
    # Z coordinate: Raise slightly (1ft) above floor to avoid intersecting floor slabs
    z = min_pt.Z + 1.0
    
    for _ in range(count):
        if is_x_long:
            pt = DB.XYZ(current, mid_short, z)
        else:
            pt = DB.XYZ(mid_short, current, z)
            
        # Verify point is actually inside (corridors are often L-shaped)
        if _is_point_inside_safe(room, pt):
            points.append(pt)
            
        current += step
        
    return points


def _is_point_inside_safe(room, pt):
    """Safely check if point is inside room (swallowing exceptions)."""
    # DISABLED: Room.IsPointInRoom crashes Revit on linked rooms
    # Return True to skip verification (use bbox center as-is)
    return True
    """
    try:
        return room.IsPointInRoom(pt)
    except:
        return False
    """

def _get_room_center_link(room):
    """Return room center in LINK coordinates using robust methods.
    
    Priority:
    1. BoundingBox Center (Geometric Center) - verified to be inside room
    2. Location Point (Revit's insertion point, often offset)
    3. BoundingBox Center (Fallback, even if verification fails or is skipped)
    """
    
    # 1. Try BBox Center + Verification
    p_bbox = None
    try:
        bb = room.get_BoundingBox(None)
        if bb:
            p_bbox = (bb.Min + bb.Max) * 0.5
            # Raise Z for check
            check_pt = DB.XYZ(p_bbox.X, p_bbox.Y, p_bbox.Z + 1.0)
            # Verify it's actually inside (for L-shaped rooms)
            if _is_point_inside_safe(room, check_pt):
                return p_bbox
    except Exception:
        pass

    # 2. Fallback: Location Point (Revit guaranteed point inside)
    p_loc = _room_center_location_first(room)
    if p_loc is not None:
        return p_loc

    # 3. Last Resort: BBox Center (unverified)
    if p_bbox is not None:
        return p_bbox

    return None


def _room_center_location_first(room):
    if room is None:
        return None
    try:
        loc = getattr(room, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is None:
            return None
        return pt
    except Exception:
        return None


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _get_param_as_string(elem, bip=None, name=None):
    if elem is None:
        return u''
    p = None
    try:
        if bip is not None:
            p = elem.get_Parameter(bip)
    except Exception:
        p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return u''
    try:
        s = p.AsString()
        return s if s is not None else u''
    except Exception:
        return u''


def _room_name(room):
    """Return normalized room name."""
    val = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME)
    if not val:
        val = getattr(room, 'Name', '')
    return _norm(val)


def _is_excluded_room(room):
    """Check if room should be skipped based on EXACT names found in the model."""
    name = _room_name(room).lower()
    
    # Exclude keywords
    exclude_keywords = [
        # Exterior
        u'лоджия', u'loggia',
        u'терраса', u'terrace',
        u'балкон', u'balcony',
        u'кровля', u'roof',
        
        # Technical
        u'тбо',
        u'венткамер',
        u'помещение сс',
        u'технич',
        u'лестничн', # Stairwells
        u'форкамер',
        u'мусоросбор'
    ]
    
    for kw in exclude_keywords:
        if kw in name:
            return True
    return False


def _select_link_instance_ru(host_doc, title):
    links = link_reader.list_link_instances(host_doc)
    if not links:
        return None

    items = []
    for ln in links:
        try:
            name = ln.Name
        except Exception:
            name = u'<Связь>'
        status = u'Загружена' if link_reader.is_link_loaded(ln) else u'Не загружена'
        items.append((u'{0}  [{1}]'.format(name, status), ln))

    items = sorted(items, key=lambda x: _norm(x[0]))
    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False,
        button_name='Выбрать',
        allow_none=True
    )
    if not picked:
        return None

    for lbl, inst in items:
        if lbl == picked:
            return inst
    return None


def _get_or_create_debug_view(doc, level_id):
    """Create or return a FloorPlan view named 'DEBUG_LIGHTS_<LevelName>'."""
    if doc is None or not level_id:
        return None
    
    level = doc.GetElement(level_id)
    if not level:
        return None
        
    view_name = 'DEBUG_LIGHTS_{0}'.format(level.Name)
    
    # Check existing
    col = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan).WhereElementIsNotElementType()
    for v in col:
        if v.Name == view_name and not v.IsTemplate:
            return v
            
    # Create new
    vft_id = None
    for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
        if vft.ViewFamily == DB.ViewFamily.FloorPlan:
            vft_id = vft.Id
            break
            
    if not vft_id:
        return None
        
    view = DB.ViewPlan.Create(doc, vft_id, level.Id)
    try:
        view.Name = view_name
        # Try to set view range to show lights (cut plane at 1500mm, top at 4000mm)
        vr = view.GetViewRange()
        vr.SetOffset(DB.PlanViewPlane.CutPlane, 5.0) # ~1500mm
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, 15.0) # ~4500mm
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, 0.0)
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, 0.0)
        view.SetViewRange(vr)
    except Exception:
        pass 
        
    return view

def _collect_existing_lights_centers(doc, tolerance_ft=1.5):
    """Return list of (X, Y, Z) for ALL existing lights in project."""
    centers = []
    # Collect ALL lighting fixtures, regardless of type
    col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsNotElementType()
    for e in col:
        try:
            loc = e.Location
            if loc and hasattr(loc, 'Point'):
                centers.append(loc.Point)
        except Exception:
            continue
    return centers

def _is_too_close(p, existing_points, tolerance_ft=1.5):
    tol2 = tolerance_ft * tolerance_ft
    for ex in existing_points:
        dx = float(p.X) - float(ex.X)
        dy = float(p.Y) - float(ex.Y)
        # Check XY distance primarily
        if (dx*dx + dy*dy) < tol2:
            return True
    return False

def _filter_duplicate_rooms(rooms):
    """Filter out rooms that are effectively duplicates (same location)."""
    unique_rooms = []
    seen_locs = []
    
    for r in rooms:
        # Get center
        p = _get_room_center_link(r)
        if not p:
            continue
            
        is_dup = False
        for sl in seen_locs:
            if _is_too_close(p, [sl], tolerance_ft=1.0):
                is_dup = True
                break
        
        if not is_dup:
            unique_rooms.append(r)
            seen_locs.append(p)
            
    return unique_rooms

def _find_best_door_for_room(room, all_doors):
    """Find door for room using GEOMETRIC proximity (avoids FromRoom/ToRoom crash).
    
    Logic:
    1. Get room bounding box
    2. Find doors whose location is within/near the room bbox
    3. Return the closest door to room center
    """
    if room is None or not all_doors:
        return None
    
    try:
        bb = room.get_BoundingBox(None)
        if not bb:
            return None
        
        # Expand bbox generously (2.5 ft = ~750mm) to catch doors in thick walls
        expand = 2.5
        min_x = bb.Min.X - expand
        min_y = bb.Min.Y - expand
        max_x = bb.Max.X + expand
        max_y = bb.Max.Y + expand
        min_z = bb.Min.Z - 1.0
        max_z = bb.Max.Z + 1.0
        
        room_center = _get_room_center_link(room)
        if not room_center:
            return None
        
        candidates = []
        for d in all_doors:
            try:
                loc = d.Location
                if not loc or not hasattr(loc, 'Point'):
                    continue
                pt = loc.Point
                
                # Check if door is within expanded room bbox
                if (min_x <= pt.X <= max_x and 
                    min_y <= pt.Y <= max_y and 
                    min_z <= pt.Z <= max_z):
                    
                    # Calculate distance to room center (XY only)
                    dx = pt.X - room_center.X
                    dy = pt.Y - room_center.Y
                    dist = (dx*dx + dy*dy) ** 0.5
                    candidates.append((d, dist))
            except Exception:
                continue
        
        if not candidates:
            return None
        
        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
        
    except Exception:
        return None

def _get_above_door_point(room, door):
    """Calculate point above the center of the door, slightly inside the room."""
    if not door or not room:
        return None
    
    # 1. Door Center & Orientation
    # We need the point on the wall boundary.
    # LocationPoint of door is usually center of wall thickness.
    try:
        loc = door.Location
        if not loc: return None
        door_pt = loc.Point
        
        # Orientation: Door instances have FacingOrientation and HandOrientation
        # FacingOrientation usually points In/Out.
        # We need to determine which way is "In" relative to OUR room.
        
        facing = door.FacingOrientation
        
        # Check vector from door to room center
        center = _get_room_center_link(room)
        if not center: return None
        
        vec_to_center = DB.XYZ(center.X - door_pt.X, center.Y - door_pt.Y, 0).Normalize()
        
        # Dot product to check alignment
        # if dot > 0, facing is towards center. if < 0, away.
        dot = facing.DotProduct(vec_to_center)
        
        inward_vec = facing if dot > 0 else facing.Negate()
        
        # Offset: 200mm (0.65 ft) into the room from the door center
        offset_ft = mm_to_ft(200)
        
        # XY position
        x = door_pt.X + inward_vec.X * offset_ft
        y = door_pt.Y + inward_vec.Y * offset_ft
        
        # Z position: Top of door + 200mm
        # Default door height ~2100mm = 6.9ft
        # Try to get actual height parameter
        h_ft = mm_to_ft(2100) # Fallback
        try:
            p = door.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM)
            if p: h_ft = p.AsDouble()
        except:
            pass
            
        z_offset_ft = mm_to_ft(200)
        z = door_pt.Z + h_ft + z_offset_ft # Relative to door Z (usually level)
        
        # Create Point
        # Warning: door_pt.Z is absolute? Or relative to level? 
        # Link coordinates are absolute.
        # usually door_pt.Z is at the bottom of the door.
        
        return DB.XYZ(x, y, z)
        
    except Exception as e:
        # print("Error calc door point: " + str(e))
        return None

def main():
    try:
        System.GC.Collect()
    except Exception:
        pass

    output.print_md('# Размещение светильников по помещениям (правила)')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    trace('Place_Lights_RoomCenters: start')

    rules = config_loader.load_rules()
    
    # DEBUG: List all lighting fixture symbols
    sym_col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
    print(u'--- AVAILABLE LIGHTING FIXTURE SYMBOLS ---')
    for s in sym_col:
        print(u'Name: {0} | Family: {1}'.format(s.Name, s.FamilyName))
    print(u'------------------------------------------')

    # Defaults
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    ceiling_height_mm = rules.get('light_center_room_height_mm', 2700)
    ceiling_height_ft = mm_to_ft(ceiling_height_mm) or 0.0
    comment_value = '{0}:LIGHT_CENTER'.format(comment_tag)

    link_inst = _select_link_instance_ru(doc, title='Выберите связь АР')
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
    sym_ceiling = placement_engine.find_family_symbol(doc, fam_ceiling, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
    if not sym_ceiling:
        # Fallback: pick first valid lighting fixture
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsElementType()
        for e in col:
            if isinstance(e, DB.FamilySymbol):
                sym_ceiling = e
                break
    
    sym_wall = placement_engine.find_family_symbol(doc, fam_wall, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
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
    existing_centers = _collect_existing_lights_centers(doc, tolerance_ft=1.5)

    link_transform = link_inst.GetTotalTransform()

    # Collect rooms
    rooms_raw = []
    for lvl in selected_levels:
        lid = lvl.Id
        rooms_raw.extend(link_reader.iter_rooms(link_doc, level_id=lid))

    if not rooms_raw:
        alert('В выбранных уровнях не найдено помещений (Rooms).')
        return

    # Deduplicate rooms (handle Design Options or bad links)
    rooms = _filter_duplicate_rooms(rooms_raw)
    
    # Pre-collect doors for "Above Door" logic
    all_doors = list(link_reader.iter_doors(link_doc))

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
                debug_view = _get_or_create_debug_view(doc, first_host_level.Id)
        except Exception:
            pass

        for r in rooms:
            # Check exclusions (balcony, loggia, technical)
            if _is_excluded_room(r):
                skipped_ext += 1
                continue

            # Determine Placement Strategy
            target_pts = []
            target_symbol = sym_ceiling
            placement_z_mode = 'ceiling' # ceiling or door_relative
            
            if _is_wet_room(r):
                # Strategy: Above Door
                target_symbol = sym_wall
                placement_z_mode = 'door_relative'
                door = _find_best_door_for_room(r, all_doors)
                found_door_pt = False
                if door:
                    pt = _get_above_door_point(r, door)
                    if pt:
                        target_pts = [pt]
                        found_door_pt = True
                        print(u'DEBUG: Wet room "{0}" -> Door found, Point OK'.format(_room_name(r)))
                    else:
                        print(u'DEBUG: Wet room "{0}" -> Door found, but calc point FAILED'.format(_room_name(r)))
                else:
                    print(u'DEBUG: Wet room "{0}" -> No door found'.format(_room_name(r)))
                
                if not found_door_pt:
                    # Fallback if no door found (e.g. opening instead of door family) -> Center
                    target_pts = _get_room_centers_multi(r)
                    placement_z_mode = 'ceiling'
                    target_symbol = sym_ceiling # Revert to ceiling type for center placement
                    print(u'DEBUG: Wet room "{0}" -> Fallback to CENTER. Pts: {1}'.format(_room_name(r), len(target_pts)))
            else:
                # Strategy: Standard (Center or Corridor)
                target_pts = _get_room_centers_multi(r)
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
                if placement_z_mode == 'door_relative':
                    # p_link.Z already includes door height + offset. 
                    # But we need to be careful about relative/absolute.
                    # p_link comes from door location in link.
                    # p_host is transformed.
                    z = p_host.Z # Use calculated absolute Z
                else:
                    z = host_level.Elevation + ceiling_height_ft
                
                insert_point = DB.XYZ(p_host.X, p_host.Y, z)

                # Check duplicates (manual geometry check against ALL lights)
                if _is_too_close(insert_point, existing_centers, tolerance_ft=1.5):
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
                net_ids = _as_net_id_list(placed_ids)
                if net_ids:
                    uidoc.Selection.SetElementIds(net_ids)
                    uidoc.ShowElements(net_ids)
        except Exception:
            pass

if __name__ == '__main__':
    main()
