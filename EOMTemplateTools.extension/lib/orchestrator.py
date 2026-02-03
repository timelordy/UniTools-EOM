# -*- coding: utf-8 -*-
"""Orchestrator for EOM Template Tools.

Dispatches execution to specific placement logic based on tool ID.
"""
import os
import sys
import traceback
import io
import time
from pyrevit import script, revit, DB
from config_loader import load_rules
from placement_engine import get_or_load_family_symbol, place_point_family_instance

# DEBUG LOGGING setup
DEBUG_LOG_FILE = os.path.join(os.environ.get("TEMP"), "eom_orchestrator.log")

def log_debug(msg):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with io.open(DEBUG_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(u"[{0}] {1}\n".format(timestamp, msg))
    except:
        pass

def get_room_center(room):
    """Calculate room center point."""
    try:
        # Try BoundingBox first
        bbox = room.get_BoundingBox(None)
        if bbox:
            center = (bbox.Min + bbox.Max) / 2.0
            return center
            
        # Fallback to LocationPoint
        loc = room.Location
        if loc and isinstance(loc, DB.LocationPoint):
            return loc.Point
    except Exception as e:
        log_debug("get_room_center error: " + str(e))
    return None

def run_lights_center(doc, uidoc, output, rules):
    """Run Light in Center placement."""
    log_debug("run_lights_center started")
    
    # 1. Get family name from rules
    fam_names = rules.get('family_type_names', {})
    fam_name = fam_names.get('lights_center') or fam_names.get('light_ceiling_point', "TSL_LF_э_ПЛ_Патрон (нагрузка)")
    
    log_debug("Family name: " + str(fam_name))
    
    if not fam_name:
        msg = "ERROR: No family name configured for 'light_ceiling_point'"
        log_debug(msg)
        if output: output.print_md(msg)
        return {'placed': 0, 'skipped': 0, 'error': 'Configuration error'}

    # 2. Load symbol
    try:
        # Avoid using UI alerts in orchestrator if possible, or wrap them safely
        # We manually check find_family_symbol first to avoid the alert in get_or_load_family_symbol
        from placement_engine import find_family_symbol
        symbol = find_family_symbol(doc, fam_name)
        
        if not symbol:
            msg = "ERROR: Family '{}' not found in project. Please load it first.".format(fam_name)
            log_debug(msg)
            if output: output.print_md(msg)
            return {'placed': 0, 'skipped': 0, 'error': 'Family not found'}
            
        # Activate if found
        if not symbol.IsActive:
            symbol.Activate()
            doc.Regenerate()
            
    except Exception as e:
        log_debug("Symbol loading error: " + str(e))
        log_debug(traceback.format_exc())
        return {'placed': 0, 'skipped': 0, 'error': str(e)}

    log_debug("Symbol found: " + str(symbol.Name))

    # 3. Get rooms
    try:
        rooms = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
        log_debug("Rooms found: " + str(len(rooms)))
    except Exception as e:
        log_debug("Room collection error: " + str(e))
        return {'placed': 0, 'skipped': 0, 'error': str(e)}
    
    placed = 0
    skipped = 0
    
    try:
        active_view = doc.ActiveView
        if not active_view:
            log_debug("No active view")
            return {'placed': 0, 'skipped': 0, 'error': 'No active view'}
            
        p_view_phase = active_view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE)
        active_phase_id = p_view_phase.AsElementId() if p_view_phase else DB.ElementId.InvalidElementId
    except Exception as e:
        log_debug("View/Phase error: " + str(e))
        return {'placed': 0, 'skipped': 0, 'error': str(e)}
    
    try:
        with revit.Transaction("Свет по центру"):
            for room in rooms:
                try:
                    # Filter by phase
                    p_room_phase = room.get_Parameter(DB.BuiltInParameter.ROOM_PHASE)
                    if p_room_phase and p_room_phase.AsElementId() != active_phase_id:
                        continue
                        
                    if room.Area <= 0: 
                        continue
                        
                    if not room.Location:
                        continue

                    center = get_room_center(room)
                    if center:
                        # Height offset
                        height_mm = rules.get('light_center_room_height_mm', 2700)
                        height_ft = height_mm / 304.8
                        
                        level_id = room.LevelId
                        level = doc.GetElement(level_id)
                        z_base = level.Elevation if level else 0
                        
                        target = DB.XYZ(center.X, center.Y, z_base + height_ft)
                        
                        # Place
                        inst = place_point_family_instance(doc, symbol, target, prefer_level=level)
                        if inst:
                            placed += 1
                            
                            # Set comment
                            tag = rules.get('comment_tag', 'AUTO_EOM')
                            p_comment = inst.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                            if p_comment:
                                p_comment.Set(tag)
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                except Exception as inner_e:
                    # Log individual room error but continue
                    # log_debug("Room processing error: " + str(inner_e))
                    skipped += 1
                    
        log_debug("Transaction committed. Placed: {}, Skipped: {}".format(placed, skipped))
        
    except Exception as e:
        log_debug("Transaction error: " + str(e))
        log_debug(traceback.format_exc())
        return {'placed': placed, 'skipped': skipped, 'error': str(e)}
                
    if output:
        output.print_md("Размещено: **{}**, Пропущено: **{}**".format(placed, skipped))
        output.print_md("Сэкономлено времени: **~{:.1f} минут**".format(placed * 15.0))

    return {'placed': placed, 'skipped': skipped}

def run_placement(doc, uidoc, output, script_obj):
    """Main entry point called by scripts."""
    log_debug("run_placement called")
    try:
        # Determine tool ID
        tool_id = os.environ.get('EOM_HUB_TOOL_ID')
        log_debug("Tool ID from env: " + str(tool_id))
        
        # Fallback: infer from script path
        if not tool_id and script_obj:
            try:
                path = script_obj.get_bundle_files()[0]
                log_debug("Script path: " + str(path))
                if 'СветПоЦентру' in path:
                    tool_id = 'lights_center'
                elif 'СветВЛифтах' in path:
                    tool_id = 'lights_elevator'
            except Exception as e:
                log_debug("Error inferring tool id: " + str(e))

        if output:
            output.print_md("Запуск инструмента: **{}**".format(tool_id or 'Unknown'))

        try:
            rules = load_rules()
            log_debug("Rules loaded")
        except Exception as e:
            log_debug("Error loading rules: " + str(e))
            rules = {}
        
        if tool_id == 'lights_center':
            return run_lights_center(doc, uidoc, output, rules)
        
        msg = "Инструмент '{}' пока не реализован в Orchestrator".format(tool_id)
        log_debug(msg)
        if output:
            output.print_md(msg)
            
        return {'placed': 0, 'skipped': 0, 'status': 'not_implemented'}

    except Exception as e:
        log_debug("CRITICAL ERROR in orchestrator: " + str(e))
        log_debug(traceback.format_exc())
        if output:
            output.print_md("ERROR in orchestrator: {}".format(str(e)))
            output.print_md(traceback.format_exc())
        return {'placed': 0, 'skipped': 0, 'error': str(e)}
