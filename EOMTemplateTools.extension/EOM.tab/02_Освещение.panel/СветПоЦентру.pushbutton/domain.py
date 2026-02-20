# -*- coding: utf-8 -*-

import math
from pyrevit import DB
from utils_units import mm_to_ft
import constants

SQFT_TO_SQM = 0.092903

DEFAULT_APARTMENT_PARAM_NAMES = [
    u'Квартира',
    u'Номер квартиры',
    u'ADSK_Номер квартиры',
    u'ADSK_Номер_квартиры',
    u'Apartment',
    u'Flat',
]

INVALID_APARTMENT_NUMBERS = set([
    u'квартира', u'apartment', u'flat', u'room', u'моп'
])

OUTSIDE_APARTMENT_KEYWORDS = [
    u'внекварт', u'лестнич', u'подъезд', u'колясоч', u'моп', u'вестиб', u'лифтов',
    u'тамбур', u'шлюз',
]

def _are_collinear(p1, p2, p3, tolerance=0.01):
    """Check if three points are collinear."""
    # Vector p1 -> p2
    v1x = p2.X - p1.X
    v1y = p2.Y - p1.Y
    
    # Vector p2 -> p3
    v2x = p3.X - p2.X
    v2y = p3.Y - p2.Y
    
    # Cross product (2D)
    cross = v1x * v2y - v1y * v2x
    return abs(cross) < tolerance

def _simplify_polygon(pts):
    """Remove collinear vertices from polygon."""
    if not pts or len(pts) < 3:
        return pts
        
    # Filter very close points first
    unique_pts = []
    if pts:
        unique_pts.append(pts[0])
        for i in range(1, len(pts)):
            prev = unique_pts[-1]
            curr = pts[i]
            dist = prev.DistanceTo(curr)
            if dist > 0.01: # 0.01 ft ~ 3mm
                unique_pts.append(curr)
                
        # Check wrap around (first and last)
        if len(unique_pts) > 1 and unique_pts[0].DistanceTo(unique_pts[-1]) < 0.01:
            unique_pts.pop()
            
    if len(unique_pts) < 3:
        return unique_pts

    # Remove collinear
    # Iterate multiple times until stable (simplistic approach)
    for _ in range(3):
        to_keep = []
        n = len(unique_pts)
        if n < 3: break
        
        for i in range(n):
            p_prev = unique_pts[i-1]
            p_curr = unique_pts[i]
            p_next = unique_pts[(i+1) % n]
            
            if not _are_collinear(p_prev, p_curr, p_next):
                to_keep.append(p_curr)
        
        if len(to_keep) == len(unique_pts):
            break
        unique_pts = to_keep
        
    return unique_pts


def _get_room_boundary_points(room):
    """Get outer boundary loop points for room. Returns list of XYZ or None."""
    if room is None:
        return None
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglists = room.GetBoundarySegments(opts)
        if not seglists or len(seglists) == 0:
            return None
        
        # Get first (outer) loop points
        pts = []
        for s in seglists[0]:
            try:
                c = s.GetCurve()
                if c:
                    pts.append(c.GetEndPoint(0))
            except Exception:
                continue
        
        # Simplify polygon (remove collinear points)
        if pts:
            pts = _simplify_polygon(pts)
            
        return pts if len(pts) >= 3 else None
    except Exception:
        return None


def _get_l_shape_intersection_center(boundary_pts, fallback_z):
    """
    For 6-vertex L-shaped rooms, find the center of the INTERSECTION area.
    
    L-shape is formed by two overlapping rectangles. This function finds
    the center of their intersection (the "elbow" of the L).
    
    Returns XYZ or None if not an L-shape.
    """
    if not boundary_pts or len(boundary_pts) != 6:
        return None
    
    pts = boundary_pts
    
    # Get sorted unique X and Y coordinates
    try:
        xs = sorted(set(round(float(p.X), 3) for p in pts))
        ys = sorted(set(round(float(p.Y), 3) for p in pts))
    except Exception:
        return None
    
    # L-shape should have exactly 3 unique X and 3 unique Y values
    if len(xs) != 3 or len(ys) != 3:
        return None
    
    x0, x1, x2 = xs
    y0, y1, y2 = ys
    
    # Outer corners of bounding box
    outer_corners = {(x0, y0), (x0, y2), (x2, y0), (x2, y2)}
    pt_coords = {(round(float(p.X), 3), round(float(p.Y), 3)) for p in pts}
    
    # Find which outer corner is NOT in the boundary (the "notch")
    notch_corners = outer_corners - pt_coords
    if len(notch_corners) != 1:
        return None  # Not a simple L-shape
    
    notch = list(notch_corners)[0]
    nx, ny = notch
    
    # The intersection cell is DIAGONALLY OPPOSITE to the notch
    # Use the opposite x-range and y-range from the notch corner
    if nx == x0:
        cx = (x1 + x2) / 2.0  # notch on left -> intersection on right
    else:  # nx == x2
        cx = (x0 + x1) / 2.0  # notch on right -> intersection on left
    
    if ny == y0:
        cy = (y1 + y2) / 2.0  # notch on bottom -> intersection on top
    else:  # ny == y2
        cy = (y0 + y1) / 2.0  # notch on top -> intersection on bottom
    
    # Use Z from first boundary point or fallback
    try:
        z = float(pts[0].Z)
    except Exception:
        z = fallback_z
    
    return DB.XYZ(cx, cy, z)


def _get_l_shape_rect_centers(boundary_pts, fallback_z):
    """
    For 6-vertex L-shaped rooms, return centers of the two rectangles
    that form the "L" (arms).

    Returns list[XYZ] or None.
    """
    if not boundary_pts or len(boundary_pts) != 6:
        return None

    try:
        xs = sorted(set(round(float(p.X), 3) for p in boundary_pts))
        ys = sorted(set(round(float(p.Y), 3) for p in boundary_pts))
    except Exception:
        return None

    # L-shape should have exactly 3 unique X and 3 unique Y values
    if len(xs) != 3 or len(ys) != 3:
        return None

    x0, x1, x2 = xs
    y0, y1, y2 = ys

    outer_corners = {(x0, y0), (x0, y2), (x2, y0), (x2, y2)}
    pt_coords = {(round(float(p.X), 3), round(float(p.Y), 3)) for p in boundary_pts}

    notch_corners = outer_corners - pt_coords
    if len(notch_corners) != 1:
        return None

    nx, ny = list(notch_corners)[0]

    # Horizontal bar spans full width; choose top or bottom depending on notch Y.
    if ny == y0:
        hy0, hy1 = y1, y2
    else:
        hy0, hy1 = y0, y1

    # Vertical bar spans full height; choose left or right depending on notch X.
    if nx == x0:
        vx0, vx1 = x1, x2
    else:
        vx0, vx1 = x0, x1

    try:
        z = float(boundary_pts[0].Z)
    except Exception:
        z = fallback_z

    c_h = DB.XYZ((x0 + x2) / 2.0, (hy0 + hy1) / 2.0, z)
    c_v = DB.XYZ((vx0 + vx1) / 2.0, (y0 + y2) / 2.0, z)

    # Guard against accidental duplicates
    try:
        if abs(c_h.X - c_v.X) < 0.001 and abs(c_h.Y - c_v.Y) < 0.001:
            return [c_h]
    except Exception:
        pass

    return [c_h, c_v]


def _room_area_sqm(room):
    """Return room area in square meters (m^2) or None."""
    try:
        area_ft2 = getattr(room, 'Area', None)
        if area_ft2 is None:
            return None
        return float(area_ft2) * SQFT_TO_SQM
    except Exception:
        return None


def norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def get_param_as_string(elem, bip=None, name=None):
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


def room_name(room):
    """Return normalized room name."""
    val = get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME)
    if not val:
        val = getattr(room, 'Name', '')
    return norm(val)


def room_number(room):
    val = get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER)
    if not val:
        val = get_param_as_string(room, name='Number')
    return val or u''


def room_department(room):
    val = get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT)
    if not val:
        val = get_param_as_string(room, name='Department')
    return val or u''


def room_name_matches(room, patterns):
    if room is None:
        return False
    text = room_name(room)
    for p in (patterns or []):
        token = norm(p)
        if token and token in text:
            return True
    return False


def clean_apartment_number(val):
    if not val:
        return u''
    try:
        txt = val.strip()
    except Exception:
        txt = val
    try:
        prefixes = [u'кв.', u'кв', u'apt.', u'apt', u'квартира']
        low = txt.lower()
        for pref in prefixes:
            if low.startswith(pref):
                txt = txt[len(pref):].strip()
                break
    except Exception:
        pass
    try:
        return txt.upper()
    except Exception:
        return txt


def is_valid_apartment_number(val):
    if not val:
        return False
    v = norm(val)
    if not v:
        return False
    if v in INVALID_APARTMENT_NUMBERS:
        return False
    return any(ch.isdigit() for ch in v)


def get_room_apartment_number(room, param_names=None, allow_department=False, allow_number=False):
    if room is None:
        return None

    names = list(param_names or DEFAULT_APARTMENT_PARAM_NAMES)
    for pname in names:
        try:
            value = get_param_as_string(room, name=pname)
            clean = clean_apartment_number(value)
            if is_valid_apartment_number(clean):
                return clean
        except Exception:
            continue

    if allow_department:
        try:
            value = room_department(room)
            clean = clean_apartment_number(value)
            if is_valid_apartment_number(clean):
                return clean
        except Exception:
            pass

    if allow_number:
        try:
            value = room_number(room)
            if value:
                parts = value.split('.')
                if parts and parts[0].isdigit():
                    clean = clean_apartment_number(parts[0])
                    if is_valid_apartment_number(clean):
                        return clean
        except Exception:
            pass

    return None


def is_apartment_room(room,
                      apartment_param_names=None,
                      require_param=True,
                      allow_department=False,
                      allow_number=False,
                      apartment_name_patterns=None,
                      public_name_patterns=None):
    """Return True only for apartment rooms."""
    if room is None:
        return False

    name = room_name(room)
    # Hard stop for clearly non-apartment zones, even when parameters are noisy.
    for kw in OUTSIDE_APARTMENT_KEYWORDS:
        token = norm(kw)
        if token and token in name:
            return False

    apt_num = get_room_apartment_number(
        room,
        param_names=apartment_param_names,
        allow_department=allow_department,
        allow_number=allow_number,
    )
    if apt_num:
        return True

    if require_param:
        return False

    # With relaxed mode, still reject explicit public/common patterns.
    for kw in (public_name_patterns or []):
        token = norm(kw)
        if token and token in name:
            return False

    # Optional soft fallback for projects without apartment parameters.
    for kw in (apartment_name_patterns or []):
        token = norm(kw)
        if token and token in name:
            return True
    return False


def is_corridor(room):
    """Check if room is a corridor/hallway/elevator hall/vestibule."""
    name = room_name(room).lower()
    keywords = [
        u'коридор', u'холл', u'corridor', u'hall', u'прихожая', u'вестибюль',
        u'лифтов', u'тамбур'
    ]
    return any(k in name for k in keywords)


def is_wet_room(room):
    """Check if room is a Bath/WC/Toilet (Wet Area)."""
    # DEPRECATED: Use is_bathroom or is_toilet for specific logic
    return is_bathroom(room) or is_toilet(room)


def _is_bathroom_name(name):
    keywords = [
        u'ванная', u'ванн', u'bath', u'shower', u'душевая', u'душ'
    ]
    return any(k in name for k in keywords)


def _is_toilet_name(name):
    keywords = [
        u'санузел', u'сан. узел', u'сан.узел', u'туалет', u'уборная',
        u'с/у', u'с.у.', u'с.у',
        u'toilet', u'wc', u'restroom'
    ]
    if any(k in name for k in keywords):
        return True
    # Fallback: check split "сан ... узел" wording.
    return (u'сан' in name and u'узел' in name)


def is_bathroom(room):
    """Check if room is a Bathroom (has bath/shower)."""
    name = room_name(room).lower()
    return _is_bathroom_name(name)


def is_toilet(room):
    """Check if room is a Toilet/WC/Restroom."""
    try:
        raw_name = room_name(room).lower()
        # Normalize: remove weird spaces, standardise dots
        name = raw_name.replace(u'\xa0', u' ').replace(u'\u202f', u' ')

        # "Санузел без ванной": if bath is present, classify as bathroom instead.
        if _is_bathroom_name(name):
            return False

        return _is_toilet_name(name)
    except:
        return False


def is_excluded_room(room):
    """Check if room should be skipped based on EXACT names found in the model."""
    if is_toilet(room) or is_bathroom(room):
        return False
    name = room_name(room).lower()

    # Exclude keywords
    exclude_keywords = [
        # Exterior
        u'лоджия', u'loggia',
        u'терраса', u'terrace',
        u'балкон', u'balcony',
        u'кровля', u'roof',

        # Technical
        u'внекварт',
        u'колясоч',
        u'моп',
        u'тбо',
        u'венткамер',
        u'помещение сс',
        u'технич',
        u'лестничн', # Stairwells
        u'тамбур',
        u'шлюз',
        u'форкамер',
        u'мусоросбор'
    ]

    for kw in exclude_keywords:
        if kw in name:
            return True
    return False


def is_point_inside_safe(room, pt):
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


def room_center_location_first(room):
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


def get_room_center_link(room):
    """Return room center in LINK coordinates using robust methods.

    Priority:
    1. L-shape intersection center (for L-shaped rooms with 6 vertices)
    2. BoundingBox Center (Geometric Center) - verified to be inside room
    3. Location Point (Revit's insertion point, often offset)
    4. BoundingBox Center (Fallback, even if verification fails or is skipped)
    """

    # Get fallback Z from bbox
    fallback_z = 0.0
    p_bbox = None
    try:
        bb = room.get_BoundingBox(None)
        if bb:
            p_bbox = (bb.Min + bb.Max) * 0.5
            fallback_z = bb.Min.Z
    except Exception:
        pass

    # 1. Try L-shape larger part center (for 6-vertex L-shaped rooms)
    try:
        boundary_pts = _get_room_boundary_points(room)
        if boundary_pts:
            n_pts = len(boundary_pts)
            rname = room_name(room)
            if n_pts == 6:
                l_center = _get_l_shape_intersection_center(boundary_pts, fallback_z)
                if l_center:
                    return l_center
        else:
            pass
    except Exception as e:
        pass

    # 2. Try BBox Center + Verification
    try:
        if p_bbox:
            # Raise Z for check
            check_pt = DB.XYZ(p_bbox.X, p_bbox.Y, p_bbox.Z + 1.0)
            # Verify it's actually inside (for L-shaped rooms)
            if is_point_inside_safe(room, check_pt):
                return p_bbox
    except Exception:
        pass

    # 3. Fallback: Location Point (Revit guaranteed point inside)
    p_loc = room_center_location_first(room)
    if p_loc is not None:
        return p_loc

    # 4. Last Resort: BBox Center (unverified)
    if p_bbox is not None:
        return p_bbox

    return None


def get_corridor_points(room):
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
        if is_point_inside_safe(room, pt):
            points.append(pt)

        current += step

    return points


def get_room_centers_multi(room):
    """Return placement points.

    Logic:
    - One room -> one point.
    - Use robust room center calculation and avoid multi-point placements
      because they often create duplicate fixtures in one room.
    """

    c = get_room_center_link(room)
    return [c] if c else []


def is_too_close(p, existing_points, tolerance_ft=1.5):
    tol2 = tolerance_ft * tolerance_ft
    # Vertical tolerance to distinguish levels (~600mm)
    z_tol = 2.0

    for ex in existing_points:
        # Check Z first (optimization for multi-story)
        if abs(float(p.Z) - float(ex.Z)) > z_tol:
            continue

        dx = float(p.X) - float(ex.X)
        dy = float(p.Y) - float(ex.Y)
        
        # Check XY distance
        if (dx*dx + dy*dy) < tol2:
            return True
    return False


def filter_duplicate_rooms(rooms):
    """Filter out rooms that are effectively duplicates (same location)."""
    unique_rooms = []
    seen_locs = []
    seen_keys = set()

    for r in rooms:
        # 1) Prefer deterministic key by level+number+name where possible.
        try:
            lvl = getattr(getattr(r, 'LevelId', None), 'IntegerValue', None)
        except Exception:
            lvl = None
        num = norm(room_number(r))
        nam = room_name(r)
        if lvl is not None and num and nam:
            key = (int(lvl), num, nam)
            if key in seen_keys:
                continue
            seen_keys.add(key)

        # Get center
        p = get_room_center_link(r)
        if not p:
            continue

        is_dup = False
        for sl in seen_locs:
            if is_too_close(p, [sl], tolerance_ft=2.0):
                is_dup = True
                break

        if not is_dup:
            unique_rooms.append(r)
            seen_locs.append(p)

    return unique_rooms


def find_best_door_for_room(room, all_doors):
    """Find door for room using GEOMETRIC proximity + Name Priority + Z Level Match.

    Logic:
    1. Filter doors geometrically (inside/near bbox XY, STRICT Z match to room level).
    2. Score candidates:
       - Bonus for "toilet/с/у" in name if room is toilet.
       - Bonus for Z proximity to room floor level.
       - Penalty/Exclusion for "opening/проем/shaft/люк".
       - Distance tie-breaker.
    3. Return best candidate.
    """
    if room is None or not all_doors:
        return None

    try:
        bb = room.get_BoundingBox(None)
        if not bb:
            return None

        # Expand XY bbox generously (3.5 ft = ~1067mm) to catch doors in thick walls
        expand = 3.5
        min_x = bb.Min.X - expand
        min_y = bb.Min.Y - expand
        max_x = bb.Max.X + expand
        max_y = bb.Max.Y + expand
        
        # STRICT Z filter: door must be within 2 ft of room floor level
        # This prevents picking doors from other floors
        room_floor_z = bb.Min.Z
        z_tolerance = 2.0  # ft (~600mm)
        min_z = room_floor_z - z_tolerance
        max_z = room_floor_z + z_tolerance

        room_center = get_room_center_link(room)
        if not room_center:
            return None
            
        is_toilet_room = is_toilet(room)

        candidates = []
        for d in all_doors:
            try:
                # 1. Geometric Check
                loc = d.Location
                if not loc or not hasattr(loc, 'Point'):
                    continue
                pt = loc.Point

                # XY check with expansion
                if not (min_x <= pt.X <= max_x and min_y <= pt.Y <= max_y):
                    continue
                    
                # STRICT Z check - door must be on same level as room
                if not (min_z <= pt.Z <= max_z):
                    continue

                # 2. Name Analysis
                try:
                    # Get Name (Family + Type)
                    if hasattr(d, 'Symbol'):
                        fam = get_param_as_string(d.Symbol, name='Family Name')
                        typ = get_param_as_string(d.Symbol, name='Type Name')
                        full_name = (fam + ' ' + typ).lower()
                    else:
                        full_name = (d.Name or '').lower()
                except:
                    full_name = ''

                # Exclusions
                if any(bad in full_name for bad in [u'проем', u'opening', u'шахта', u'shaft', u'люк', u'hatch']):
                    continue

                # Scoring
                score = 0
                
                # Priority for Toilet Doors
                if is_toilet_room and any(k in full_name for k in [u'с/у', u'санузел', u'toilet']):
                    score += 100
                    
                # Bonus for Z proximity to room floor (prefer doors exactly on level)
                z_diff = abs(pt.Z - room_floor_z)
                if z_diff < 0.5:  # Very close to floor level
                    score += 50

                # Calculate distance to room center (XY only)
                dx = pt.X - room_center.X
                dy = pt.Y - room_center.Y
                dist = (dx*dx + dy*dy) ** 0.5
                
                candidates.append((d, score, dist))
                
            except Exception:
                continue

        if not candidates:
            return None

        # Sort: High Score first, then Low Distance
        # Key: (-score, dist) -> Highest score first, then smallest distance
        candidates.sort(key=lambda x: (-x[1], x[2]))
        
        return candidates[0][0]

    except Exception:
        return None


def get_above_sink_point(room, all_plumbing, target_height_ft):
    """
    Find a sink/basin in the room and return a point above it.
    target_height_ft: The desired Z height for the light (e.g. 2m).
    """
    if not room or not all_plumbing:
        return None
        
    # Keywords for sink families (strict match on family name when available).
    # Avoid overly broad matches like "wash" to prevent false positives.
    sink_keywords = [
        u'раковина', u'умывальник',
        u'130_сантехнические приборы_2d',
        u'сантехнические',
        u'sink', u'washbasin', u'basin'
    ]
    
    # 1. Get room bbox with tolerance
    try:
        bb = room.get_BoundingBox(None)
        if not bb:
            return None
        
        # Expand slightly to catch fixtures embedded in walls/counters
        tol = 1.0 # ft
        min_x = bb.Min.X - tol
        min_y = bb.Min.Y - tol
        max_x = bb.Max.X + tol
        max_y = bb.Max.Y + tol
        min_z = bb.Min.Z - tol
        max_z = bb.Max.Z + 3.0 # Look higher for plumbing
        
    except Exception:
        return None
        
    candidates = []
    
    for pf in all_plumbing:
        try:
            # Check name first (performance optimization)
            # Prefer strict family name match when available.
            family_name = u''
            type_name = u''
            if hasattr(pf, 'Symbol'):
                sym = pf.Symbol
                family_name = get_param_as_string(sym, name='Family Name') or u''
                type_name = get_param_as_string(sym, name='Type Name') or u''
                if not family_name:
                    try:
                        if sym and getattr(sym, 'Family', None):
                            family_name = sym.Family.Name or u''
                    except Exception:
                        family_name = u''
            else:
                try:
                    type_name = pf.Name or u''
                except Exception:
                    type_name = u''

            family_name = family_name.lower().strip()
            type_name = type_name.lower().strip()

            if family_name:
                if not any(k in family_name for k in sink_keywords):
                    continue
            else:
                name = u' '.join(filter(None, [family_name, type_name])).lower()
                if not name or not any(k in name for k in sink_keywords):
                    continue
                
            # Check location
            loc = pf.Location
            if not loc or not hasattr(loc, 'Point'):
                continue
            pt = loc.Point
            
            # BBox check
            if (min_x <= pt.X <= max_x and
                min_y <= pt.Y <= max_y and
                min_z <= pt.Z <= max_z):
                
                # Verify geometrically?
                # For now trust bbox + name match
                candidates.append(pt)
                
        except Exception:
            continue
            
    if not candidates:
        return None
        
    # Return point above the first found sink
    # Z = height from floor + target_height
    # Assuming target_height_ft is absolute or relative?
    # Usually passed relative to level.
    # But here we return a LINK coordinate point.
    # Let's return the Sink XY + Room Floor Z + 2m
    
    sink_pt = candidates[0] # Pick first one found
    
    # Calculate Z
    # Use room's bottom Z + 2m (approx 6.56 ft)
    room_z = bb.Min.Z
    # If target_height_ft is passed as absolute, use it. But usually we want relative to floor.
    # But wait, orchestrator passes target_height_ft which is usually ceiling height?
    # No, for wall lights we want explicit 2m.
    
    # Let's assume target_height_ft is RELATIVE to floor (2000mm)
    z = room_z + target_height_ft
    
    return DB.XYZ(sink_pt.X, sink_pt.Y, z)


def get_above_door_point(room, door):
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
        center = get_room_center_link(room)
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
