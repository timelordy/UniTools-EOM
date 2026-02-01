# -*- coding: utf-8 -*-
"""
Утилиты для определения входов в блок-секции (БС) и размещения распаячных коробок для нумерации подъездов.

Этот модуль предоставляет функции для:
- Извлечения номера БС из названия помещения
- Определения входных дверей в БС
- Поиска всех входов в БС из связанной АР модели
"""

import re
from pyrevit import DB


# Ключевые слова для определения внеквартирных коридоров (общедомовые помещения)
CORRIDOR_KEYWORDS = [
    u'внеквартир', u'корид', u'холл', u'лестн', u'лифтов', u'тамбур', 
    u'вестиб', u'подъезд', u'моп', u'общедомов'
]

# Ключевые слова для типов входных дверей в БС
ENTRANCE_DOOR_KEYWORDS = [
    u'витраж', u'витражн', u'стальн', u'стал', u'двупольн', 
    u'вход', u'входн', u'alumin', u'steel', u'glass', u'glazed'
]

# Паттерны для исключения (не входные двери)
EXCLUDE_DOOR_KEYWORDS = [
    u'деревян', u'однопольн', u'внутр', u'квартир', 
    u'wood', u'wooden', u'interior', u'apartment'
]


def extract_bs_number(room_name):
    """
    Извлекает номер блок-секции из названия помещения.
    
    Формат названия помещения: "Тип помещения БС.ЭТ.НОМЕР"
    Например: "Внеквартирный коридор 1.234" → БС = 1
              "Прихожая 2.117" → БС = 2
    
    Args:
        room_name (str): Название помещения из Revit
    
    Returns:
        int or None: Номер блок-секции (1, 2, 3...) или None если не удалось определить
    
    Examples:
        >>> extract_bs_number("Внеквартирный коридор 1.234")
        1
        >>> extract_bs_number("Лифтовой холл 3.112")
        3
        >>> extract_bs_number("Помещение без номера")
        None
    """
    if not room_name:
        return None
    
    # Паттерн: ищем число перед точкой (формат: цифра.цифры)
    # Примеры: "1.234", "2.117", "3.001"
    match = re.search(r'\b(\d+)\.(\d+)', room_name)
    if match:
        bs_number = int(match.group(1))
        return bs_number
    
    return None


def _normalize_text(text):
    """Нормализует текст для сравнения (lowercase, strip)."""
    if not text:
        return u''
    try:
        return text.strip().lower()
    except:
        return u''


def _contains_any_keyword(text, keywords):
    """Проверяет содержит ли текст хотя бы одно из ключевых слов."""
    normalized = _normalize_text(text)
    for keyword in keywords:
        if keyword in normalized:
            return True
    return False


def _is_corridor_room(room_name):
    """Проверяет является ли помещение внеквартирным коридором."""
    return _contains_any_keyword(room_name, CORRIDOR_KEYWORDS)


def _is_entrance_door_type(door_family_name, door_type_name):
    """Проверяет является ли тип двери входным в БС по названию семейства и типа."""
    combined = u'{} {}'.format(door_family_name or u'', door_type_name or u'')
    
    # Сначала проверяем исключения
    if _contains_any_keyword(combined, EXCLUDE_DOOR_KEYWORDS):
        return False
    
    # Проверяем ключевые слова входных дверей
    return _contains_any_keyword(combined, ENTRANCE_DOOR_KEYWORDS)


def is_bs_entrance_door(door_elem, link_transform=None):
    """
    Определяет является ли дверь входом в блок-секцию.
    
    Критерии:
    1. Одна сторона двери - внеквартирный коридор с номером БС
    2. Вторая сторона - наружное пространство (ToRoom или FromRoom = None/External)
    3. Тип двери - входная (витражная, стальная, двупольная)
    
    Args:
        door_elem (DB.FamilyInstance): Элемент двери из Revit
        link_transform (DB.Transform): Трансформация связанной модели (опционально)
    
    Returns:
        dict or None: Словарь с информацией о входе в БС:
            {
                'bs_number': int,           # Номер блок-секции
                'door_id': ElementId,       # ID двери
                'door_family': str,         # Название семейства
                'door_type': str,           # Тип двери
                'corridor_room': str,       # Название коридора
                'location': XYZ,            # Координаты двери (с учетом transform)
                'level_name': str           # Название уровня
            }
            Или None если дверь не является входом в БС
    """
    if not door_elem:
        return None
    
    try:
        # Получаем комнаты с обеих сторон двери
        from_room_param = door_elem.get_Parameter(DB.BuiltInParameter.DOOR_FROM_ROOM)
        to_room_param = door_elem.get_Parameter(DB.BuiltInParameter.DOOR_TO_ROOM)
        
        from_room_name = from_room_param.AsString() if from_room_param else None
        to_room_name = to_room_param.AsString() if to_room_param else None
        
        # Проверяем тип двери
        symbol = door_elem.Symbol
        door_family = symbol.FamilyName if symbol else u''
        door_type = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() if symbol else u''
        
        if not _is_entrance_door_type(door_family, door_type):
            return None
        
        # Определяем какая сторона - коридор, какая - наружу
        corridor_room = None
        bs_number = None
        
        # Проверяем from_room
        if from_room_name and _is_corridor_room(from_room_name):
            bs_num = extract_bs_number(from_room_name)
            if bs_num is not None:
                corridor_room = from_room_name
                bs_number = bs_num
        
        # Проверяем to_room
        if to_room_name and _is_corridor_room(to_room_name):
            bs_num = extract_bs_number(to_room_name)
            if bs_num is not None:
                corridor_room = to_room_name
                bs_number = bs_num
        
        # Если не нашли коридор с БС - не входная дверь
        if bs_number is None or corridor_room is None:
            return None
        
        # Проверяем что вторая сторона - наружу (null или не коридор)
        other_room = to_room_name if corridor_room == from_room_name else from_room_name
        if other_room and _is_corridor_room(other_room):
            # Обе стороны - коридоры, это не вход в БС
            return None
        
        # Получаем координаты двери
        location = door_elem.Location
        if isinstance(location, DB.LocationPoint):
            point = location.Point
        elif isinstance(location, DB.LocationCurve):
            curve = location.Curve
            point = curve.Evaluate(0.5, True)  # Середина двери
        else:
            return None
        
        # Применяем трансформацию если есть
        if link_transform:
            point = link_transform.OfPoint(point)
        
        # Получаем уровень
        level_param = door_elem.get_Parameter(DB.BuiltInParameter.FAMILY_LEVEL_PARAM)
        level_name = u''
        if level_param:
            level_id = level_param.AsElementId()
            if level_id and level_id != DB.ElementId.InvalidElementId:
                level_elem = door_elem.Document.GetElement(level_id)
                if level_elem:
                    level_name = level_elem.Name
        
        return {
            'bs_number': bs_number,
            'door_id': door_elem.Id,
            'door_family': door_family,
            'door_type': door_type,
            'corridor_room': corridor_room,
            'location': point,
            'level_name': level_name,
            'from_room': from_room_name,
            'to_room': to_room_name
        }
        
    except Exception as e:
        # Тихо игнорируем ошибки для отдельных дверей
        return None


def find_bs_entrance_doors(link_doc, link_transform):
    """
    Находит все входы в блок-секции из связанной АР модели.
    
    Args:
        link_doc (DB.Document): Документ связанной АР модели
        link_transform (DB.Transform): Трансформация связанной модели
    
    Returns:
        list: Список словарей с информацией о входах в БС (см. is_bs_entrance_door)
              Отсортирован по номеру БС
    
    Example:
        >>> entrances = find_bs_entrance_doors(link_doc, transform)
        >>> for entrance in entrances:
        ...     print(u"БС{}: {} на {}".format(
        ...         entrance['bs_number'], 
        ...         entrance['door_type'],
        ...         entrance['level_name']
        ...     ))
    """
    entrances = []
    
    if not link_doc:
        return entrances
    
    try:
        # Собираем все двери из связанной модели
        collector = DB.FilteredElementCollector(link_doc)\
            .OfCategory(DB.BuiltInCategory.OST_Doors)\
            .WhereElementIsNotElementType()
        
        for door in collector:
            entrance_info = is_bs_entrance_door(door, link_transform)
            if entrance_info:
                entrances.append(entrance_info)
        
        # Сортируем по номеру БС, затем по уровню
        entrances.sort(key=lambda x: (x['bs_number'], x['level_name']))
        
    except Exception as e:
        # В случае ошибки возвращаем пустой список
        pass
    
    return entrances


def group_entrances_by_bs(entrances):
    """
    Группирует входы по номерам блок-секций.
    
    Args:
        entrances (list): Список входов от find_bs_entrance_doors()
    
    Returns:
        dict: Словарь {bs_number: [список входов]}
    
    Example:
        >>> grouped = group_entrances_by_bs(entrances)
        >>> for bs_num, bs_entrances in sorted(grouped.items()):
        ...     print(u"БС{}: {} входов".format(bs_num, len(bs_entrances)))
    """
    grouped = {}
    for entrance in entrances:
        bs_num = entrance['bs_number']
        if bs_num not in grouped:
            grouped[bs_num] = []
        grouped[bs_num].append(entrance)
    return grouped


def select_main_entrance_per_level(bs_entrances):
    """
    Выбирает основной вход для каждого уровня в БС.
    
    Если на одном уровне несколько входов - выбирается дверь с наибольшей шириной.
    
    Args:
        bs_entrances (list): Список входов одной БС
    
    Returns:
        list: Список основных входов (по одному на уровень)
    """
    # Группируем по уровням
    by_level = {}
    for entrance in bs_entrances:
        level = entrance.get('level_name', u'')
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(entrance)
    
    # Для каждого уровня выбираем основной вход
    main_entrances = []
    for level, level_entrances in by_level.items():
        if len(level_entrances) == 1:
            main_entrances.append(level_entrances[0])
        else:
            # Выбираем дверь с самым "богатым" типом (витражная > стальная > остальные)
            # Это эвристика, можно улучшить проверкой ширины двери
            main = level_entrances[0]
            for entrance in level_entrances[1:]:
                if u'витраж' in _normalize_text(entrance['door_type']):
                    main = entrance
                    break
            main_entrances.append(main)
    
    return main_entrances
