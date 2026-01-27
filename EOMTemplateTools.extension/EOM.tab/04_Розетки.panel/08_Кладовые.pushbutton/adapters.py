# -*- coding: utf-8 -*-

from pyrevit import DB, forms
import json
import os


def get_config():
    """Загружает конфиг из файла"""
    try:
        # Ищем config в директории extension
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'config',
            'rules.default.json'
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config():
    """Сохраняет конфиг (пока не используется)"""
    pass


def get_rules():
    """Получает правила из конфига"""
    return get_config()


def get_link_doc(link_instance):
    """Получает документ линка"""
    try:
        return link_instance.GetLinkDocument()
    except Exception:
        return None


def get_total_transform(link_instance):
    """Получает полную трансформацию линка"""
    try:
        return link_instance.GetTotalTransform()
    except Exception:
        return None


def pick_storage_light_symbol(doc, cfg, rules):
    """Выбирает семейство светильника для кладовых"""
    try:
        # Получаем список типов из правил
        light_type_names = rules.get('family_type_names', {}).get('light_ceiling_point')
        if not light_type_names:
            if isinstance(light_type_names, str):
                light_type_names = [light_type_names]
            else:
                light_type_names = []

        if not light_type_names:
            light_type_names = rules.get('family_type_names', {}).get('light_wall_bath')
            if isinstance(light_type_names, str):
                light_type_names = [light_type_names]

        # Ищем типы в документе
        for type_name in light_type_names:
            try:
                sym = find_family_symbol(doc, type_name)
                if sym:
                    return sym, type_name
            except Exception:
                continue

        # Если не найдено, предлагаем выбрать вручную
        msg = "Не найден тип светильника для кладовых.\n\n"
        msg += "Выберите тип семейства из списка:"
        sym = forms.SelectFamilySymbol(title=msg,
                                      category=DB.BuiltInCategory.OST_LightingFixtures,
                                      filterfunc=lambda x: True)
        if sym:
            try:
                return sym, str(sym.Family.Name + " : " + sym.Name)
            except Exception:
                return sym, str(sym)

    except Exception:
        pass

    return None, None


def pick_switch_symbol(doc, cfg, rules):
    """Выбирает семейство выключателя"""
    try:
        # Получаем список типов из правил
        switch_type_names = rules.get('family_type_names', {}).get('switch')
        if not switch_type_names:
            if isinstance(switch_type_names, str):
                switch_type_names = [switch_type_names]
            else:
                switch_type_names = []

        # Ищем типы в документе
        for type_name in switch_type_names:
            try:
                sym = find_family_symbol(doc, type_name)
                if sym:
                    return sym, type_name
            except Exception:
                continue

        # Если не найдено, предлагаем выбрать вручную
        msg = "Не найден тип выключателя.\n\n"
        msg += "Выберите тип семейства из списка:"
        sym = forms.SelectFamilySymbol(title=msg,
                                      category=DB.BuiltInCategory.OST_ElectricalEquipment,
                                      filterfunc=lambda x: True)
        if sym:
            try:
                return sym, str(sym.Family.Name + " : " + sym.Name)
            except Exception:
                return sym, str(sym)

    except Exception:
        pass

    return None, None


def pick_panel_symbol(doc, cfg, rules):
    """Выбирает семейство щитка"""
    try:
        # Получаем список типов из правил
        panel_type_names = rules.get('family_type_names', {}).get('panel_shk')
        if not panel_type_names:
            panel_type_names = rules.get('panel_shk_variant_param')
            if panel_type_names:
                panel_type_names = [panel_type_names]

        # Ищем типы в документе
        if panel_type_names:
            for type_name in panel_type_names:
                try:
                    sym = find_family_symbol(doc, type_name)
                    if sym:
                        return sym, type_name
                except Exception:
                    continue

        # Если не найдено, предлагаем выбрать вручную
        msg = "Не найден тип щитка для кладовых.\n\n"
        msg += "Выберите тип семейства из списка:"
        sym = forms.SelectFamilySymbol(title=msg,
                                      category=DB.BuiltInCategory.OST_ElectricalEquipment,
                                      filterfunc=lambda x: True)
        if sym:
            try:
                return sym, str(sym.Family.Name + " : " + sym.Name)
            except Exception:
                return sym, str(sym)

    except Exception:
        pass

    return None, None


def find_family_symbol(doc, name_with_type):
    """Находит FamilySymbol по строке 'Family : Type' или просто имени типа"""
    try:
        # Разделяем имя family и type
        if ':' in name_with_type:
            parts = name_with_type.split(':')
            family_name = parts[0].strip()
            type_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            family_name = name_with_type.strip()
            type_name = ''

        # Сбор всех FamilySymbol
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
        symbols = collector.ToElements()

        for sym in symbols:
            try:
                # Проверяем полное имя
                full_name = str(sym.Family.Name) + " : " + str(sym.Name)
                if full_name == name_with_type.strip():
                    return sym

                # Проверяем по частям
                if family_name and family_name.lower() in str(sym.Family.Name).lower():
                    if not type_name or type_name.lower() in str(sym.Name).lower():
                        return sym
            except Exception:
                continue

    except Exception:
        pass

    return None


def get_all_linked_rooms(link_doc, limit=5000):
    """Получает все помещения из линка"""
    try:
        collector = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Rooms)
        rooms = collector.ToElements()

        if limit and len(rooms) > limit:
            rooms = rooms[:limit]

        return rooms
    except Exception:
        return []


def collect_tagged_instances(doc, comment_value, symbol_id=None):
    """Собирает уже размещенные элементы с тегом"""
    try:
        ids = set()
        elems = []
        pts = []

        # Сбор всех элементов с параметром Comments
        collector = DB.FilteredElementCollector(doc).WhereElementIsNotElementType()
        all_elems = collector.ToElements()

        for elem in all_elems:
            try:
                # Проверяем параметр Comments
                param = elem.LookupParameter("Comments")
                if param and param.HasValue:
                    val = param.AsString()
                    if val and comment_value in val:
                        ids.add(int(elem.Id.IntegerValue))
                        elems.append(elem)

                        # Получаем точку расположения
                        pt = get_element_center_point(elem)
                        if pt:
                            pts.append(pt)
            except Exception:
                continue

        return ids, elems, pts
    except Exception:
        return set(), [], []


def get_element_center_point(elem):
    """Получает центральную точку элемента"""
    try:
        loc = elem.Location
        if hasattr(loc, 'Point'):
            return loc.Point
        elif hasattr(loc, 'Curve'):
            curve = loc.Curve
            return curve.Evaluate(0.5, True)
        else:
            # Проверяем BoundingBox
            bbox = elem.get_BoundingBox(None)
            if bbox:
                cx = (bbox.Min.X + bbox.Max.X) / 2
                cy = (bbox.Min.Y + bbox.Max.Y) / 2
                cz = (bbox.Min.Z + bbox.Max.Z) / 2
                return DB.XYZ(cx, cy, cz)
    except Exception:
        pass
    return None
