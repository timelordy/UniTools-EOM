# -*- coding: utf-8 -*-
"""Расстановка выключателей в квартирах.

Требования:
- Высота установки 900мм
- Со стороны дверной ручки
- Спальня/гостиная: 2-клавишный, остальное: 1-клавишный
- Санузлы/ванные: выключатель в прихожей (снаружи)
- Остальные комнаты: выключатель внутри комнаты
"""
import math

from pyrevit import DB, forms, revit, script

# ============================================================================
# НАСТРОЙКИ
# ============================================================================
SWITCH_HEIGHT_MM = 900      # Высота установки
JAMB_OFFSET_MM = 100        # Минимальный отступ от края дверного проёма
COMMENT_TAG = u"AUTO_EOM:SWITCH"

# ID типов выключателей из Revit (получено через MCP)
SWITCH_1G_TYPE_ID = 2010333  # TSL_LD_т_СТ_в_IP20_Вкл_1P_1кл
SWITCH_2G_TYPE_ID = 2015166  # TSL_LD_т_СТ_в_IP20_Вкл_1P_2кл

# Классификация комнат
WET_ROOMS = [u"сануз", u"ванн", u"душ", u"туал", u"с/у", u"wc"]
TWO_GANG_ROOMS = [u"спальн", u"гостин", u"жилая", u"комнат"]
CORRIDOR_ROOMS = [u"прихож", u"корид", u"холл", u"тамбур", u"вестиб"]
SKIP_ROOMS = [u"балкон", u"лодж", u"лестн", u"лифт", u"техн", u"кладов"]


# ============================================================================
# УТИЛИТЫ
# ============================================================================
def mm_to_ft(mm):
    return mm / 304.8


def ft_to_mm(ft):
    return ft * 304.8


def contains_any(text, patterns):
    """Проверить содержит ли текст любой из паттернов."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)


def get_room_name(room):
    """Получить имя комнаты."""
    try:
        param = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        return param.AsString() if param else u""
    except:
        return u""


def get_room_center(room):
    """Получить центр комнаты."""
    try:
        loc = room.Location
        return loc.Point if loc else None
    except:
        return None


# ============================================================================
# РАБОТА С ДВЕРЬМИ И СТЕНАМИ
# ============================================================================
def get_door_host_wall(door):
    """Получить стену-хост двери."""
    try:
        host = door.Host
        if host and isinstance(host, DB.Wall):
            return host
    except:
        pass
    return None


def get_wall_curve_and_width(wall):
    """Получить линию стены и её толщину."""
    try:
        loc = wall.Location
        if isinstance(loc, DB.LocationCurve):
            curve = loc.Curve
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            
            # Толщина стены
            width = mm_to_ft(200)  # default
            try:
                if hasattr(wall, 'Width'):
                    width = wall.Width
                elif hasattr(wall, 'WallType') and wall.WallType:
                    width = wall.WallType.Width
            except:
                pass
            
            return p0, p1, width
    except:
        pass
    return None, None, None


def get_door_info(door, link_doc, link_transform):
    """Получить информацию о двери."""
    info = {
        "center": None,
        "width": mm_to_ft(900),
        "hand": None,
        "facing": None,
        "from_room": None,
        "to_room": None,
        "wall": None,
        "wall_p0": None,
        "wall_p1": None,
        "wall_width": None,
        "door_bb_min": None,
        "door_bb_max": None
    }
    
    # Центр двери
    try:
        loc = door.Location
        if hasattr(loc, "Point"):
            info["center"] = loc.Point
    except:
        pass
    
    # BoundingBox двери для точных границ
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            info["door_bb_min"] = link_transform.OfPoint(bb.Min)
            info["door_bb_max"] = link_transform.OfPoint(bb.Max)
    except:
        pass
    
    if not info["center"]:
        try:
            bb = door.get_BoundingBox(None)
            if bb:
                info["center"] = DB.XYZ(
                    (bb.Min.X + bb.Max.X) / 2,
                    (bb.Min.Y + bb.Max.Y) / 2,
                    bb.Min.Z
                )
        except:
            pass
    
    # Ширина двери
    try:
        p = door.Symbol.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
        if p:
            info["width"] = p.AsDouble()
    except:
        pass
    
    # Направления
    try:
        info["hand"] = door.HandOrientation
        info["facing"] = door.FacingOrientation
    except:
        pass
    
    # Комнаты
    try:
        phases = list(link_doc.Phases)
        if phases:
            phase = phases[-1]
            info["from_room"] = door.get_FromRoom(phase)
            info["to_room"] = door.get_ToRoom(phase)
    except:
        pass
    
    # Стена-хост
    wall = get_door_host_wall(door)
    if wall:
        info["wall"] = wall
        p0, p1, width = get_wall_curve_and_width(wall)
        if p0 and p1:
            info["wall_p0"] = link_transform.OfPoint(p0)
            info["wall_p1"] = link_transform.OfPoint(p1)
            info["wall_width"] = width
    
    return info


def calc_switch_position(door_info, place_inside_room, target_room, link_transform, output=None):
    """Рассчитать позицию выключателя на стене рядом с дверью."""
    center = door_info["center"]
    hand = door_info["hand"]
    facing = door_info["facing"]
    wall_p0 = door_info["wall_p0"]
    wall_p1 = door_info["wall_p1"]
    wall_width = door_info["wall_width"]
    
    if not center:
        return None, None
    
    # Трансформируем центр двери в координаты хоста
    center_host = link_transform.OfPoint(center)
    
    # Если есть стена - размещаем на её поверхности
    if wall_p0 and wall_p1 and wall_width:
        # Направление стены
        dx = wall_p1.X - wall_p0.X
        dy = wall_p1.Y - wall_p0.Y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1e-9:
            return None, None
        
        wall_dir = DB.XYZ(dx/length, dy/length, 0)
        wall_normal = DB.XYZ(-wall_dir.Y, wall_dir.X, 0)
        
        # Определяем сторону ручки относительно стены
        # hand указывает направление от центра двери к ручке
        if hand:
            hand_host = link_transform.OfVector(hand)
        else:
            # Fallback: ручка перпендикулярна facing
            if facing:
                facing_host = link_transform.OfVector(facing)
                hand_host = DB.XYZ(-facing_host.Y, facing_host.X, 0)
            else:
                hand_host = wall_dir  # просто вдоль стены
        
        # Проекция hand на направление стены определяет сторону
        hand_dot = hand_host.X * wall_dir.X + hand_host.Y * wall_dir.Y
        if hand_dot >= 0:
            side_along_wall = 1  # в сторону p1
        else:
            side_along_wall = -1  # в сторону p0
        
        # Проецируем центр двери на линию стены
        to_center_x = center_host.X - wall_p0.X
        to_center_y = center_host.Y - wall_p0.Y
        t_door_center = (to_center_x * wall_dir.X + to_center_y * wall_dir.Y)
        
        # Ширина двери (половина)
        # HandOrientation указывает от петель к ручке
        # Ручка находится на расстоянии ~ширина_двери от петель
        # Петли на противоположной стороне от ручки
        door_width = door_info["width"]
        if door_width < mm_to_ft(600):
            door_width = mm_to_ft(800)  # минимум 800мм
        
        # Позиция выключателя:
        # - Со стороны ручки (side_along_wall)
        # - На расстоянии: ширина_двери + отступ 100мм от края проёма
        # 
        # Центр двери -> край двери со стороны ручки = door_width/2
        # + отступ от края = JAMB_OFFSET_MM
        half_door = door_width / 2.0
        jamb_offset = mm_to_ft(JAMB_OFFSET_MM)
        
        # Общее смещение от центра двери
        offset_from_center = half_door + jamb_offset
        
        # Позиция выключателя вдоль стены
        t_switch = t_door_center + side_along_wall * offset_from_center
        
        # Ограничиваем длиной стены
        t_switch = max(mm_to_ft(100), min(length - mm_to_ft(100), t_switch))
        
        # Точка на оси стены
        axis_x = wall_p0.X + wall_dir.X * t_switch
        axis_y = wall_p0.Y + wall_dir.Y * t_switch
        
        # Определяем на какой стороне стены размещать (внутрь/наружу комнаты)
        half_width = wall_width / 2.0
        
        if target_room:
            room_center = get_room_center(target_room)
            if room_center:
                room_center_host = link_transform.OfPoint(room_center)
                # Вектор от оси стены к центру целевой комнаты
                to_room_x = room_center_host.X - axis_x
                to_room_y = room_center_host.Y - axis_y
                # Проекция на нормаль стены
                room_dot = to_room_x * wall_normal.X + to_room_y * wall_normal.Y
                if room_dot >= 0:
                    surface_sign = 1
                else:
                    surface_sign = -1
            else:
                # Fallback: используем facing
                if facing:
                    facing_host = link_transform.OfVector(facing)
                    facing_dot = facing_host.X * wall_normal.X + facing_host.Y * wall_normal.Y
                    surface_sign = 1 if (facing_dot >= 0) == place_inside_room else -1
                else:
                    surface_sign = 1
        else:
            surface_sign = 1
        
        # Итоговая точка на поверхности стены
        surface_x = axis_x + wall_normal.X * half_width * surface_sign
        surface_y = axis_y + wall_normal.Y * half_width * surface_sign
        surface_z = center_host.Z + mm_to_ft(SWITCH_HEIGHT_MM)
        
        point = DB.XYZ(surface_x, surface_y, surface_z)
        
        # Угол поворота - нормаль к стене (наружу) + 90° по часовой (-π/2)
        rotation = math.atan2(wall_normal.Y * surface_sign, wall_normal.X * surface_sign) - math.pi / 2
        
        return point, rotation
    
    # Fallback если нет стены - старый метод
    return None, None


# ============================================================================
# РАЗМЕЩЕНИЕ
# ============================================================================
def get_switch_symbol(doc, two_gang=False):
    """Получить символ выключателя по ID."""
    type_id = SWITCH_2G_TYPE_ID if two_gang else SWITCH_1G_TYPE_ID
    try:
        elem = doc.GetElement(DB.ElementId(type_id))
        if elem and isinstance(elem, DB.FamilySymbol):
            if not elem.IsActive:
                elem.Activate()
            return elem
    except:
        pass
    return None


def place_switch(doc, symbol, point, rotation, level):
    """Разместить выключатель."""
    try:
        inst = doc.Create.NewFamilyInstance(
            point, symbol, level,
            DB.Structure.StructuralType.NonStructural
        )
        if rotation and inst:
            axis = DB.Line.CreateBound(point, DB.XYZ(point.X, point.Y, point.Z + 1))
            DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, rotation)
        # Пометить комментарием
        try:
            p = inst.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p:
                p.Set(COMMENT_TAG)
        except:
            pass
        return inst
    except:
        return None


def get_closest_level(doc, z):
    """Найти ближайший уровень."""
    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    closest = None
    min_dist = float("inf")
    for lvl in levels:
        dist = abs(lvl.Elevation - z)
        if dist < min_dist:
            min_dist = dist
            closest = lvl
    return closest


# ============================================================================
# ГЛАВНАЯ ЛОГИКА
# ============================================================================
def main():
    doc = revit.doc
    output = script.get_output()
    output.print_md(u"# Размещение выключателей")
    
    # Получить связь АР
    links = list(DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance))
    if not links:
        forms.alert(u"Связи АР не найдены", exitscript=True)
        return
    
    link_names = [l.Name for l in links]
    selected = forms.SelectFromList.show(link_names, title=u"Выберите связь АР")
    if not selected:
        return
    
    link_inst = links[link_names.index(selected)]
    link_doc = link_inst.GetLinkDocument()
    if not link_doc:
        forms.alert(u"Связь не загружена", exitscript=True)
        return
    
    link_transform = link_inst.GetTotalTransform()
    
    # Получить символы выключателей
    sym_1g = get_switch_symbol(doc, two_gang=False)
    sym_2g = get_switch_symbol(doc, two_gang=True)
    
    if not sym_1g:
        forms.alert(u"Не найден тип 1-кл выключателя (ID {})".format(SWITCH_1G_TYPE_ID), exitscript=True)
        return
    if not sym_2g:
        sym_2g = sym_1g
    
    try:
        name_1g = sym_1g.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except:
        name_1g = str(sym_1g.Id.IntegerValue)
    try:
        name_2g = sym_2g.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
    except:
        name_2g = str(sym_2g.Id.IntegerValue)
    
    output.print_md(u"- 1-кл: `{}`".format(name_1g))
    output.print_md(u"- 2-кл: `{}`".format(name_2g))
    
    # Собрать комнаты и двери из связи
    rooms = [r for r in DB.FilteredElementCollector(link_doc)
             .OfCategory(DB.BuiltInCategory.OST_Rooms)
             if r.Area > 0]
    
    doors = list(DB.FilteredElementCollector(link_doc)
                 .OfCategory(DB.BuiltInCategory.OST_Doors)
                 .WhereElementIsNotElementType())
    
    output.print_md(u"- Комнат: **{}**, дверей: **{}**".format(len(rooms), len(doors)))
    
    # Построить связь комната -> двери
    room_to_doors = {}
    for door in doors:
        info = get_door_info(door, link_doc, link_transform)
        for room in [info["from_room"], info["to_room"]]:
            if room and room.Id.IntegerValue not in room_to_doors:
                room_to_doors[room.Id.IntegerValue] = []
            if room:
                room_to_doors[room.Id.IntegerValue].append((door, info))
    
    # Размещение
    created = 0
    skipped = 0
    
    with DB.Transaction(doc, u"ЭОМ: Выключатели") as t:
        t.Start()
        
        for room in rooms:
            room_name = get_room_name(room)
            room_id = room.Id.IntegerValue
            
            # Пропустить технические/балконы
            if contains_any(room_name, SKIP_ROOMS):
                continue
            
            # Пропустить коридоры (туда будут выходить выключатели санузлов)
            if contains_any(room_name, CORRIDOR_ROOMS):
                continue
            
            # Найти дверь для этой комнаты
            if room_id not in room_to_doors:
                skipped += 1
                continue
            
            door_list = room_to_doors[room_id]
            if not door_list:
                skipped += 1
                continue
            
            # Выбрать дверь (приоритет: ведёт в коридор)
            best_door = None
            best_info = None
            other_room = None
            
            for door, info in door_list:
                # Определить другую комнату
                fr = info["from_room"]
                tr = info["to_room"]
                other = tr if (fr and fr.Id == room.Id) else fr
                other_name = get_room_name(other) if other else u""
                
                if contains_any(other_name, CORRIDOR_ROOMS):
                    best_door = door
                    best_info = info
                    other_room = other
                    break
            
            if not best_door:
                best_door, best_info = door_list[0]
                fr = best_info["from_room"]
                tr = best_info["to_room"]
                other_room = tr if (fr and fr.Id == room.Id) else fr
            
            # Определить параметры размещения
            is_wet = contains_any(room_name, WET_ROOMS)
            is_two_gang = contains_any(room_name, TWO_GANG_ROOMS)
            
            # Для санузлов - ставим снаружи (в коридоре), иначе внутри
            place_inside = not is_wet
            target_room = room if place_inside else other_room
            
            symbol = sym_2g if is_two_gang else sym_1g
            
            # Рассчитать позицию
            point, rotation = calc_switch_position(
                best_info, place_inside, target_room, link_transform
            )
            
            # Отладка первых 3 размещений
            if created < 3:
                output.print_md(u"")
                output.print_md(u"**{}** (wet={}, 2g={})".format(room_name, is_wet, is_two_gang))
                output.print_md(u"  wall: {}".format("YES" if best_info["wall"] else "NO"))
                if best_info["center"]:
                    c = link_transform.OfPoint(best_info["center"])
                    output.print_md(u"  door center: ({:.0f},{:.0f}), width={:.0f}mm".format(
                        ft_to_mm(c.X), ft_to_mm(c.Y), ft_to_mm(best_info["width"])))
                if best_info["hand"]:
                    h = link_transform.OfVector(best_info["hand"])
                    output.print_md(u"  hand direction: ({:.2f},{:.2f})".format(h.X, h.Y))
                if point:
                    output.print_md(u"  switch: ({:.0f}, {:.0f}, {:.0f}) mm".format(
                        ft_to_mm(point.X), ft_to_mm(point.Y), ft_to_mm(point.Z)))
                    # Расстояние от центра двери до выключателя
                    if best_info["center"]:
                        c = link_transform.OfPoint(best_info["center"])
                        dist = math.sqrt((point.X - c.X)**2 + (point.Y - c.Y)**2)
                        output.print_md(u"  distance from door center: {:.0f}mm".format(ft_to_mm(dist)))
                else:
                    output.print_md(u"  switch: NONE (no wall?)")
            
            if not point:
                skipped += 1
                continue
            
            # Найти уровень
            level = get_closest_level(doc, point.Z)
            if not level:
                skipped += 1
                continue
            
            # Разместить
            inst = place_switch(doc, symbol, point, rotation, level)
            if inst:
                created += 1
            else:
                skipped += 1
        
        t.Commit()
    
    output.print_md(u"---")
    output.print_md(u"## Результат")
    output.print_md(u"- Создано: **{}**".format(created))
    output.print_md(u"- Пропущено: {}".format(skipped))
    
    if created > 0:
        forms.alert(u"Создано {} выключателей".format(created))

if __name__ == "__main__":
    main()
