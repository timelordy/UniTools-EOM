# -*- coding: utf-8 -*-

import System
from pyrevit import DB, forms
import adapters
import constants
import domain

def run(doc, uidoc, output):
    output.print_md("# AC Socket Placement (V2)")
    
    # 1. Load Symbol
    symbol = adapters.get_socket_symbol(doc)
    if not symbol:
        forms.alert("Family symbol not found: {}".format(constants.SOCKET_FAMILY_NAME), exitscript=True)
        return
        
    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()
        
    output.print_md("Socket Family: **{}**".format(constants.SOCKET_FAMILY_NAME))
    
    # 2. Collect Data
    output.print_md("Collecting model data...")
    baskets = adapters.collect_baskets(doc)
    walls = adapters.collect_walls(doc)
    rooms = adapters.collect_rooms(doc)
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level).WhereElementIsNotElementType())
    
    output.print_md("- Baskets found: {}".format(len(baskets)))
    output.print_md("- Walls found: {}".format(len(walls)))
    output.print_md("- Rooms found: {}".format(len(rooms)))
    output.print_md("---")
    
    # 3. Process
    stats = {
        'created': 0,
        'skipped_no_level': 0,
        'skipped_no_facade': 0,
        'skipped_no_perp': 0,
        'skipped_balcony': 0,
        'skipped_error': 0
    }
    
    created_ids = []
    last_socket_z = None
    last_level = None
    
    with DB.Transaction(doc, "Place AC Sockets") as t:
        t.Start()
        
        for i, basket in enumerate(baskets):
            pt = basket['point']
            
            # A. Find Level for Basket
            basket_level = None
            max_z = -1e9
            for l in levels:
                if l.Elevation <= pt.Z + 1.0 and l.Elevation > max_z:
                    max_z = l.Elevation
                    basket_level = l
            
            if not basket_level:
                stats['skipped_no_level'] += 1
                continue
                
            level_z = basket_level.Elevation
            
            # B. Filter Walls relevant to this level (intersecting vertical range)
            level_walls = []
            range_min = level_z - 1.0
            range_max = level_z + domain.mm2ft(4000) # Assumed floor height
            
            for w in walls:
                # Check vertical intersection
                if w['z_max'] > range_min and w['z_min'] < range_max:
                    level_walls.append(w)
                    
            if not level_walls:
                stats['skipped_no_facade'] += 1
                continue

            # C. Find Facade Wall (Closest exterior wall)
            facade_wall = None
            min_dist = constants.SEARCH_RADIUS_MM / 304.8 # Convert to feet
            
            # Pass 1: Strict check (Must be Exterior)
            for w in level_walls:
                if not w['is_exterior']: continue
                
                # Check distance
                proj_pt, dist = domain.project_to_segment_xy(pt, w['p0'], w['p1'])
                if dist < min_dist:
                    min_dist = dist
                    facade_wall = w
            
            # Pass 2: Fallback (Any wall close to basket, e.g. < 1 meter)
            # Use this if Pass 1 failed
            if not facade_wall:
                fallback_dist = domain.mm2ft(1000) # 1 meter max for strict fallback
                min_dist_fallback = fallback_dist
                
                for w in level_walls:
                    # Skip if we already checked it and it failed distance
                    
                    proj_pt, dist = domain.project_to_segment_xy(pt, w['p0'], w['p1'])
                    if dist < min_dist_fallback:
                        min_dist_fallback = dist
                        facade_wall = w
            
            if not facade_wall:
                stats['skipped_no_facade'] += 1
                continue
                
            # D. Find Perpendicular Partition (Intersecting Facade near Basket)
            perp_wall = None
            min_perp_dist = 1e9
            
            facade_dir = facade_wall['direction']
            
            for w in level_walls:
                if w['is_exterior']: continue # Skip other exterior walls
                
                # Check geometric perpendicularity
                if not domain.are_walls_perpendicular(w['direction'], facade_dir):
                    continue
                
                # Check if it touches/intersects the facade wall (within search radius of basket)
                # Distance from basket to this wall
                proj_pt, dist = domain.project_to_segment_xy(pt, w['p0'], w['p1'])
                if dist > min_dist * 2.0 and dist > constants.SEARCH_RADIUS_MM / 304.8: # Too far from basket?
                     continue
                     
                if dist < min_perp_dist:
                    min_perp_dist = dist
                    perp_wall = w
            
            if not perp_wall:
                stats['skipped_no_perp'] += 1
                continue
                
            # E. Calculate Placement Point
            # 1. Intersection of Facade Axis and Perp Axis
            intersection = domain.intersect_lines_xy(
                facade_wall['p0'], facade_wall['direction'],
                perp_wall['p0'], perp_wall['direction']
            )
            
            if not intersection:
                stats['skipped_error'] += 1
                continue
                
            # 2. Determine direction along Perp Wall (Away from Facade)
            # Center of perp wall
            perp_mid = DB.XYZ((perp_wall['p0'].X+perp_wall['p1'].X)/2, (perp_wall['p0'].Y+perp_wall['p1'].Y)/2, 0)
            
            # Vector from Intersection to Perp Mid
            vec_to_room = DB.XYZ(perp_mid.X - intersection.X, perp_mid.Y - intersection.Y, 0)
            length = vec_to_room.GetLength()
            if length < 1e-9: continue
            
            dir_along_perp = DB.XYZ(vec_to_room.X/length, vec_to_room.Y/length, 0)
            
            # 3. Base point on Perp Axis
            # OFFSET LOGIC: Start from intersection (axis), move past Facade Half Width, then add Corner Offset
            facade_half_width = facade_wall['width'] / 2.0
            total_offset = facade_half_width + domain.mm2ft(constants.OFFSET_FROM_CORNER_MM)
            
            base_pt = DB.XYZ(
                intersection.X + dir_along_perp.X * total_offset,
                intersection.Y + dir_along_perp.Y * total_offset,
                0 # Z will be set later
            )
            
            # 4. Offset to surfaces (Left and Right)
            perp_normal = DB.XYZ(-dir_along_perp.Y, dir_along_perp.X, 0)
            perp_width = perp_wall['width']
            surface_offset = perp_width / 2.0
            
            # Calculate Z
            # Height = Top of Wall - Offset
            # If wall is tall, cap it at Level + 2.7m
            wall_top = perp_wall['z_max']
            socket_z = wall_top - domain.mm2ft(constants.OFFSET_FROM_CEILING_MM)
            
            if socket_z > level_z + domain.mm2ft(4000):
                socket_z = level_z + domain.mm2ft(2700) # Standard height fallback
            
            candidates = []
            
            # Side 1
            candidates.append({
                'pt': DB.XYZ(base_pt.X + perp_normal.X * surface_offset, base_pt.Y + perp_normal.Y * surface_offset, socket_z),
                'normal': perp_normal 
            })
            
            # Side 2
            candidates.append({
                'pt': DB.XYZ(base_pt.X - perp_normal.X * surface_offset, base_pt.Y - perp_normal.Y * surface_offset, socket_z),
                'normal': DB.XYZ(-perp_normal.X, -perp_normal.Y, 0)
            })
            
            # F. Validate and Create
            placed_for_this_basket = False
            
            for cand in candidates:
                cand_pt = cand['pt']
                cand_norm = cand['normal']
                
                # Check Room
                room_data = adapters.get_room_at_point(cand_pt, rooms)
                
                if room_data and not room_data['is_balcony']:
                    # Create Socket!
                    inst = adapters.create_socket(doc, cand_pt, symbol, basket_level, cand_norm)
                    if inst:
                        created_ids.append(inst.Id)
                        placed_for_this_basket = True
                        
                        # Store for debug view
                        last_socket_z = socket_z
                        last_level = basket_level
            
            if placed_for_this_basket:
                stats['created'] += 1
            else:
                stats['skipped_balcony'] += 1
        
        t.Commit()
        
    output.print_md("### Statistics")
    output.print_md("- Created Sockets: **{}**".format(len(created_ids)))
    output.print_md("- Skipped (No Level): {}".format(stats['skipped_no_level']))
    output.print_md("- Skipped (No Facade Wall): {}".format(stats['skipped_no_facade']))
    output.print_md("- Skipped (No Partition Wall): {}".format(stats['skipped_no_perp']))
    output.print_md("- Skipped (Balcony/No Room): {}".format(stats['skipped_balcony']))

    if created_ids:
        # Ask to view
        options = ["Open Plan", "Close"]
        if last_level:
            options.insert(1, "Create Debug Plan")
            
        res = forms.alert("Created {} sockets. What next?".format(len(created_ids)), options=options)
        
        if res == "Open Plan":
            uidoc.Selection.SetElementIds(System.Collections.Generic.List[DB.ElementId](created_ids))
            
        elif res == "Create Debug Plan" and last_level:
            output.print_md("Creating debug view...")
            debug_view = None
            
            with DB.Transaction(doc, "Create Debug View") as t2:
                t2.Start()
                debug_view = adapters.create_debug_view(doc, uidoc, last_level, created_ids, last_socket_z)
                t2.Commit()
                
            if debug_view:
                uidoc.ActiveView = debug_view
                uidoc.Selection.SetElementIds(System.Collections.Generic.List[DB.ElementId](created_ids))
                output.print_md("Debug view created: **{}**".format(debug_view.Name))
    else:
        forms.alert("No sockets were created.\nCheck the output window for skipped reasons.", title="Done")
