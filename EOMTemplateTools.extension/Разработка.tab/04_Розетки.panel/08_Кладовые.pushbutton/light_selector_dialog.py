# -*- coding: utf-8 -*-

from pyrevit import DB, forms

def show_storage_light_selector_dialog(doc, cfg, rules):
    """Показывает быстрый список выбора светильника."""
    if doc is None:
        return None, None

    # ОПТИМИЗАЦИЯ: Используем итератор, а не список
    # Это не загружает все элементы в память сразу
    col = (DB.FilteredElementCollector(doc)
           .OfCategory(DB.BuiltInCategory.OST_LightingFixtures)
           .WhereElementIsElementType())

    # Словарь для уникальных имен
    options_dict = {}
    
    # Лимит (жесткий) - чтобы точно не висло
    LIMIT = 500
    count = 0

    # Получаем рекомендуемые имена из конфига
    preferred_names = set()
    try:
        preferred = (rules or {}).get('family_type_names', {}).get('light_ceiling_point')
        if isinstance(preferred, list):
            preferred_names = set([p.lower() for p in preferred if p])
        elif isinstance(preferred, str):
            preferred_names = {preferred.lower()}
    except:
        pass

    # Итерируемся (Revit отдает элементы по одному)
    for sym in col:
        if count >= LIMIT:
            break
            
        try:
            # Сначала берем FamilyName (самое быстрое)
            fam_name = sym.FamilyName
            if not fam_name: 
                continue
                
            # Фильтр на уровне имен (чтобы не показывать мусор)
            # Если нужно, можно добавить здесь проверку на ключевые слова
            
            name = "{} : {}".format(fam_name, sym.Name)
            
            # Маркер
            is_pref = False
            if preferred_names and any(p in name.lower() for p in preferred_names):
                display_name = "⭐ " + name
            else:
                display_name = name
            
            options_dict[display_name] = sym
            count += 1
        except Exception:
            continue

    if not options_dict:
        forms.alert("Не удалось найти светильники (или список пуст).")
        return None, None

    # Сортировка (только уже отобранных строк)
    sorted_options = sorted(options_dict.keys())

    selected_name = forms.SelectFromList.show(
        sorted_options,
        title="Выберите светильник (показано первые {})".format(count),
        button_name="Выбрать",
        multiselect=False
    )

    if selected_name:
        symbol = options_dict[selected_name]
        clean_label = selected_name.replace("⭐ ", "").split(" (")[0]
        return symbol, clean_label
    
    return None, None
