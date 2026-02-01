# -*- coding: utf-8 -*-

from pyrevit import DB, forms

def show_storage_switch_selector_dialog(doc, cfg, rules):
    """Показывает быстрый список выбора выключателя."""
    if doc is None:
        return None, None

    # ОПТИМИЗАЦИЯ: Используем итератор, а не список
    # Это не загружает все элементы в память сразу
    col = (DB.FilteredElementCollector(doc)
           .OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment)
           .WhereElementIsElementType())

    # Словарь для уникальных имен
    options_dict = {}
    
    # Лимит (жесткий) - чтобы точно не висло
    LIMIT = 500
    count = 0

    # Получаем рекомендуемые имена из конфига
    preferred_names = set()
    try:
        preferred = (rules or {}).get('family_type_names', {}).get('switch')
        if isinstance(preferred, list):
            preferred_names = set([p.lower() for p in preferred if p])
        elif isinstance(preferred, str):
            preferred_names = {preferred.lower()}
        
        preferred_names.add("ip44")
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
                
            name = "{} : {}".format(fam_name, sym.Name)
            name_lower = name.lower()
            
            # Маркер
            is_pref = False
            if preferred_names and any(p in name_lower for p in preferred_names):
                is_pref = True
                
            # Доп. фильтр: выделять выключатели, но не удалять остальное
            if not is_pref and any(k in name_lower for k in ['вкл', 'switch', 'перекл']):
                is_pref = False 

            if is_pref:
                display_name = "⭐ " + name
            else:
                display_name = name
            
            options_dict[display_name] = sym
            count += 1
        except Exception:
            continue

    if not options_dict:
        forms.alert("Не удалось найти электрооборудование (или список пуст).")
        return None, None

    # Сортировка (только уже отобранных строк)
    sorted_options = sorted(options_dict.keys())

    selected_name = forms.SelectFromList.show(
        sorted_options,
        title="Выберите выключатель (показано первые {})".format(count),
        button_name="Выбрать",
        multiselect=False
    )

    if selected_name:
        symbol = options_dict[selected_name]
        clean_label = selected_name.replace("⭐ ", "").split(" (")[0]
        return symbol, clean_label
    
    return None, None
