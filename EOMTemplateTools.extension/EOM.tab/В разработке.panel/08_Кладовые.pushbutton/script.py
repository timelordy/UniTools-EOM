# -*- coding: utf-8 -*-

import math
from pyrevit import DB, revit, script, forms
import config_loader
import link_reader
import placement_engine
from utils_revit import set_comments, tx
from utils_units import mm_to_ft

doc = revit.doc
output = script.get_output()

# --- Configuration ---

STORAGE_PATTERNS = [u'клад', u'хранил', u'кладов', u'storage']

HEIGHT_SWITCH_MM = 900
HEIGHT_PANEL_MM = 1700
HEIGHT_LIGHT_MM = 2500 

OFFSET_IN_MM = 200 
OFFSET_SIDE_MM = 150 

COMMENT_TAG = 'AUTO_EOM:STORAGE'

# --- Helpers ---

def norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''

def text_has_any(text, patterns):
    t = norm(text)
    if not t:
        return False
    for p in patterns or []:
        np = norm(p)
        if np and (np in t):
            return True
    return False

def room_name(room):
    if room is None:
        return u''
    try:
        name = getattr(room, 'Name', u'')
        if name:
            return norm(name)
    except Exception:
        pass
    try:
        p = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        if p:
            return norm(p.AsString())
    except Exception:
        pass
    return u''

def get_from_to_rooms(door, link_doc):
    if door is None or link_doc is None:
        return None, None
    try:
        phases = list(link_doc.Phases)
        ph = phases[-1] if phases else None
    except Exception:
        ph = None
        
    fr = None
    tr = None
    
    if ph:
        try:
            m = getattr(door, 'get_FromRoom', None)
            if m: fr = m(ph)
        except: pass
        try:
            m = getattr(door, 'get_ToRoom', None)
            if m: tr = m(ph)
        except: pass
            
    if not fr and not tr:
        # Fallback
        try:
            fr = getattr(door, 'FromRoom', None)
            tr = getattr(door, 'ToRoom', None)
        except: pass
        
    return fr, tr

def get_wall_thickness(door):
    try:
        host = getattr(door, 'Host', None)
        if host:
            w = getattr(host, 'Width', 0.0)
            if w > 0: return w
            wt = getattr(host, 'WallType', None)
            if wt:
                w = getattr(wt, 'Width', 0.0)
                if w > 0: return w
    except: pass
    return mm_to_ft(200)

def simple_select_family(doc, category_bic, title):
    """Robust fallback selection without placement filters."""
    from pyrevit import forms
    
    # Debug: Count items
    col = DB.FilteredElementCollector(doc).OfCategory(category_bic).OfClass(DB.FamilySymbol)
    items = []
    count = 0
    for s in col:
        count += 1
        try:
            fam_name = s.FamilyName if hasattr(s, 'FamilyName') else s.Family.Name
            typ_name = s.Name
            name = u'{}: {}'.format(fam_name, typ_name)
            items.append((name, s))
        except:
            continue
            
    # output.print_md('Found {} symbols in category {}.'.format(count, category_bic))
            
    if not items:
        # forms.alert('В категории {} не найдено ни одного типоразмера.'.format(category_bic))
        return None
        
    items = sorted(items, key=lambda x: x[0])
    
    res = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False
    )
    
    if res:
        for name, sym in items:
            if name == res:
                return sym
    return None

def find_or_select(doc, key_names, title, category_bic, fallback_names=None):
    # 1. Try config names
    search_list = []
    if key_names:
        if isinstance(key_names, (list, tuple)):
            search_list.extend(key_names)
        else:
            search_list.append(key_names)
            
    if fallback_names:
        search_list.extend(fallback_names)

    # output.print_md('Searching for: {}'.format(search_list))

    for n in search_list:
        sym = placement_engine.find_family_symbol(doc, n, category_bic=category_bic)
        if sym:
            return sym
            
    # 2. Manual select (Robust)
    # Use simple_select_family directly as fallback to ensure we see everything
    return simple_select_family(doc, category_bic, title)

def main():
    output.print_md('# Расстановка в кладовых')

    # Load Config
    rules = config_loader.load_rules()
    ft_names = rules.get('family_type_names', {})

    # Debug: Check Categories
    # count_light = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).OfClass(DB.FamilySymbol).GetElementCount()
    # output.print_md('Lighting Fixtures in project: {}'.format(count_light))

    # 1. Link
    link_inst = link_reader.select_link_instance_auto(doc)
    if not link_inst:
        forms.alert('Связь АР не найдена.')
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        forms.alert('Не удалось прочитать документ связи.')
        return
    
    xf = link_inst.GetTotalTransform()

    # 2. Levels
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        return
    level_ids = [l.Id.IntegerValue for l in selected_levels]

    # 3. Families
    
    # Switch
    fam_switch = find_or_select(
        doc, 
        ft_names.get('switch_1g'), 
        'Выберите семейство: ВЫКЛЮЧАТЕЛЬ', 
        DB.BuiltInCategory.OST_ElectricalFixtures,
        fallback_names=['TSL_LD_т_СТ_в_IP20_Вкл_1P_1кл', 'Выключатель 1-кл']
    )
    if not fam_switch:
        fam_switch = find_or_select(
            doc, 
            ft_names.get('switch_1g'), 
            'Выберите семейство: ВЫКЛЮЧАТЕЛЬ (Lighting Devices)', 
            DB.BuiltInCategory.OST_LightingDevices
        )
        
    if not fam_switch:
        forms.alert('Не найден тип выключателя. Загрузите семейство/тип в проект и повторите.')
        return

    # Panel
    fam_panel = find_or_select(
        doc, 
        ft_names.get('panel_shk'), 
        'Выберите семейство: ЩИТОК', 
        DB.BuiltInCategory.OST_ElectricalEquipment,
        fallback_names=['TSL_EE_э_СТ_ЩРН', 'TSL_EE_э_ПЛ_ВРУ', 'ЩРН', 'ЩРВ']
    )
    if not fam_panel:
        fam_panel = find_or_select(
            doc, 
            ft_names.get('panel_shk'), 
            'Выберите семейство: ЩИТОК (Electrical Fixtures)', 
            DB.BuiltInCategory.OST_ElectricalFixtures,
            fallback_names=['TSL_EF_э_СТ_Щит (нагрузка)']
        )

    if not fam_panel:
        forms.alert('Не найден тип щитка. Загрузите семейство/тип в проект и повторите.')
        return

    # Light
    light_fallbacks = [
        'TSL_LF_э_ПЛ_Патрон (нагрузка)', 
        'Патрон', 
        'Светильник'
    ]
    
    fam_light = find_or_select(
        doc, 
        ft_names.get('light_ceiling_point'), 
        'Выберите семейство: СВЕТИЛЬНИК', 
        DB.BuiltInCategory.OST_LightingFixtures,
        fallback_names=light_fallbacks
    )
def simple_select_family(doc, category_bic, title):
    """Robust fallback selection without placement filters."""
    from pyrevit import forms
    
    # Debug: Count items
    col = DB.FilteredElementCollector(doc).OfCategory(category_bic).OfClass(DB.FamilySymbol)
    items = []
    count = 0
    
    # Collect all compatible elements
    # Using ElementType to be safe, though FamilySymbol is standard
    
    output.print_md('--- Debug: Searching in {}.'.format(category_bic))
    
    for s in col:
        count += 1
        try:
            # Try multiple ways to get name
            fam_name = '<Unknown>'
            if hasattr(s, 'FamilyName'):
                fam_name = s.FamilyName
            
            if fam_name == '<Unknown>':
                try:
                    fam = s.Family
                    if fam: fam_name = fam.Name
                except:
                    pass
            
            typ_name = s.Name
            name = u'{}: {}'.format(fam_name, typ_name)
            items.append((name, s))
            # output.print_md(u'Found: {}'.format(name)) 
        except Exception as e:
            output.print_md(u'Error reading symbol {}: {}'.format(s.Id, e))
            continue
            
    output.print_md('Total symbols found: {}'.format(len(items)))
            
    if not items:
        # forms.alert('В категории {} не найдено ни одного типоразмера.'.format(category_bic))
        return None
        
    items = sorted(items, key=lambda x: x[0])
    
    res = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False
    )
    
    if res:
        for name, sym in items:
            if name == res:
                return sym
    return None

def find_or_select(doc, key_names, title, category_bic, fallback_names=None):
    # 1. Try config names
    search_list = []
    if key_names:
        if isinstance(key_names, (list, tuple)):
            search_list.extend(key_names)
        else:
            search_list.append(key_names)
            
    if fallback_names:
        search_list.extend(fallback_names)

    # output.print_md('Searching for: {}'.format(search_list))

    for n in search_list:
        sym = placement_engine.find_family_symbol(doc, n, category_bic=category_bic)
        if sym:
            return sym
            
    # 2. Manual select (Robust)
    return simple_select_family(doc, category_bic, title)

def main():
    output.print_md('# Расстановка в кладовых')

    # Load Config
    rules = config_loader.load_rules()
    ft_names = rules.get('family_type_names', {})

    # Debug: Check Categories
    # count_light = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).OfClass(DB.FamilySymbol).GetElementCount()
    # output.print_md('Lighting Fixtures in project: {}'.format(count_light))

    # 1. Link
    link_inst = link_reader.select_link_instance_auto(doc)
    if not link_inst:
        forms.alert('Связь АР не найдена.')
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        forms.alert('Не удалось прочитать документ связи.')
        return
    
    xf = link_inst.GetTotalTransform()

    # 2. Levels
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        return
    level_ids = [l.Id.IntegerValue for l in selected_levels]

    # 3. Families
    
    # Switch
    fam_switch = find_or_select(
        doc, 
        ft_names.get('switch_1g'), 
        'Выберите семейство: ВЫКЛЮЧАТЕЛЬ', 
        DB.BuiltInCategory.OST_ElectricalFixtures,
        fallback_names=['TSL_LD_т_СТ_в_IP20_Вкл_1P_1кл', 'Выключатель 1-кл']
    )
    if not fam_switch:
        fam_switch = find_or_select(
            doc, 
            ft_names.get('switch_1g'), 
            'Выберите семейство: ВЫКЛЮЧАТЕЛЬ (Lighting Devices)', 
            DB.BuiltInCategory.OST_LightingDevices
        )
        
    if not fam_switch:
        forms.alert('Не найден тип выключателя. Загрузите семейство/тип в проект и повторите.')
        return

    # Panel
    fam_panel = find_or_select(
        doc, 
        ft_names.get('panel_shk'), 
        'Выберите семейство: ЩИТОК', 
        DB.BuiltInCategory.OST_ElectricalEquipment,
        fallback_names=['TSL_EE_э_СТ_ЩРН', 'TSL_EE_э_ПЛ_ВРУ', 'ЩРН', 'ЩРВ']
    )
    if not fam_panel:
        fam_panel = find_or_select(
            doc, 
            ft_names.get('panel_shk'), 
            'Выберите семейство: ЩИТОК (Electrical Fixtures)', 
            DB.BuiltInCategory.OST_ElectricalFixtures,
            fallback_names=['TSL_EF_э_СТ_Щит (нагрузка)']
        )

    if not fam_panel:
        forms.alert('Не найден тип щитка. Загрузите семейство/тип в проект и повторите.')
        return

    # Light
    light_fallbacks = [
        'TSL_LF_э_ПЛ_Патрон (нагрузка)', 
        'Патрон', 
        'Светильник'
    ]
    
    # Try Generic Models first? No, Lighting first.
    # Note: Using DB.BuiltInCategory.OST_LightingFixtures (-2001120)
    fam_light = find_or_select(
        doc, 
        ft_names.get('light_ceiling_point'), 
        'Выберите семейство: СВЕТИЛЬНИК', 
        DB.BuiltInCategory.OST_LightingFixtures,
        fallback_names=light_fallbacks
    )
    
    if not fam_light:
        # Fallback to Electrical Fixtures for lights (sometimes happens)
        fam_light = find_or_select(
            doc, 
            ft_names.get('light_ceiling_point'), 
            'Выберите семейство: СВЕТИЛЬНИК (Electrical Fixtures)', 
            DB.BuiltInCategory.OST_ElectricalFixtures,
            fallback_names=light_fallbacks
        )

    if not fam_light:
        # Fallback to Generic Models (rare but possible for simple symbols)
        fam_light = find_or_select(
            doc, 
            ft_names.get('light_ceiling_point'), 
            'Выберите семейство: СВЕТИЛЬНИК (Generic Models)', 
            DB.BuiltInCategory.OST_GenericModel,
            fallback_names=light_fallbacks
        )

    if not fam_light:
        forms.alert('Не найден тип светильника. Загрузите семейство/тип в проект и повторите.')
        return

    # 4. Process
    
    count_rooms = 0
    count_err = 0

    with tx('ЭОМ: Кладовые', doc=doc):
        # Gather doors in selected levels
        doors = []
        for lid in level_ids:
            try:
                ds = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, level_id=lid)
                doors.extend(list(ds))
            except: pass
            
        processed_rooms = set()
        
        for door in doors:
            fr, tr = get_from_to_rooms(door, link_doc)
            
            # Identify which side is Storage
            room_target = None
            room_other = None
            
            is_fr_storage = text_has_any(room_name(fr), STORAGE_PATTERNS)
            is_tr_storage = text_has_any(room_name(tr), STORAGE_PATTERNS)
            
            if is_fr_storage and not is_tr_storage:
                room_target = fr
            elif is_tr_storage and not is_fr_storage:
                room_target = tr
            elif is_fr_storage and is_tr_storage:
                # Both are storage? Rare. Skip or process both? 
                # Let's skip to avoid duplicates or complex logic for now.
                continue
            else:
                continue
                
            if not room_target: continue
            
            rid = room_target.Id.IntegerValue
            if rid in processed_rooms:
                continue
            processed_rooms.add(rid)

            # --- Calculation ---
            
            # 1. Door Geometry
            try:
                loc = door.Location
                center_pt = loc.Point
                facing = door.FacingOrientation # Vector perpendicular to wall usually
                hand = door.HandOrientation # Vector along wall
                
                # Normalize
                facing = facing.Normalize()
                hand = hand.Normalize()
            except:
                continue
                
            # Determine Inside Direction
            # Probe points
            pt_plus = center_pt + facing * mm_to_ft(500)
            pt_minus = center_pt - facing * mm_to_ft(500)
            
            in_dir = None
            if link_doc.GetRoomAtPoint(pt_plus) and link_doc.GetRoomAtPoint(pt_plus).Id == room_target.Id:
                in_dir = facing
            elif link_doc.GetRoomAtPoint(pt_minus) and link_doc.GetRoomAtPoint(pt_minus).Id == room_target.Id:
                in_dir = -facing
            else:
                # Fallback: check distance to room center
                try:
                    r_loc = room_target.Location.Point
                    d_plus = pt_plus.DistanceTo(r_loc)
                    d_minus = pt_minus.DistanceTo(r_loc)
                    if d_plus < d_minus: in_dir = facing
                    else: in_dir = -facing
                except:
                    in_dir = facing # Blind guess
            
            # 2. Switch & Panel Position
            # Move inside by wall thickness/2 + offset
            th = get_wall_thickness(door)
            dist_in = (th / 2.0) + mm_to_ft(OFFSET_IN_MM)
            
            # Move to side (latch side). 
            # How to find latch side? 
            # HandOrientation points to hinge or latch? 
            # Usually HandOrientation is parallel to wall.
            # We'll just pick one side: `hand`. 
            # If we want to be smarter, we could check which side has more space, but sticking to `hand` is standard.
            
            pos_base_xy = center_pt + (in_dir * dist_in) + (hand * mm_to_ft(OFFSET_SIDE_MM))
            
            # Transform to Host Coords
            p_switch = xf.OfPoint(DB.XYZ(pos_base_xy.X, pos_base_xy.Y, center_pt.Z + mm_to_ft(HEIGHT_SWITCH_MM)))
            p_panel = xf.OfPoint(DB.XYZ(pos_base_xy.X, pos_base_xy.Y, center_pt.Z + mm_to_ft(HEIGHT_PANEL_MM)))
            
            # 3. Light Position
            # Room Center
            try:
                r_center = room_target.Location.Point
                # Use room level + offset? Or fixed height?
                # Let's use Room Level Z + fixed height
                # Need to find Room's level in Link
                lvl_z = 0.0
                try:
                    lvl = link_doc.GetElement(room_target.LevelId)
                    lvl_z = lvl.Elevation
                except:
                    lvl_z = r_center.Z
                
                p_light_link = DB.XYZ(r_center.X, r_center.Y, lvl_z + mm_to_ft(HEIGHT_LIGHT_MM))
                p_light = xf.OfPoint(p_light_link)
            except:
                p_light = None

            # --- Placement ---
            
            try:
                # Switch
                s_inst = placement_engine.place_point_family_instance(doc, fam_switch, p_switch)
                set_comments(s_inst, COMMENT_TAG)
                
                # Panel
                p_inst = placement_engine.place_point_family_instance(doc, fam_panel, p_panel)
                set_comments(p_inst, COMMENT_TAG)
                
                # Light
                if p_light:
                    l_inst = placement_engine.place_point_family_instance(doc, fam_light, p_light)
                    set_comments(l_inst, COMMENT_TAG)
                
                count_rooms += 1
                output.print_md(u'Обработано: {}'.format(room_name(room_target)))
                
            except Exception as e:
                output.print_md(u'Ошибка {}: {}'.format(room_name(room_target), e))
                count_err += 1

    output.print_md(u'**Готово.** Комнат: {}, Ошибок: {}'.format(count_rooms, count_err))

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pass
