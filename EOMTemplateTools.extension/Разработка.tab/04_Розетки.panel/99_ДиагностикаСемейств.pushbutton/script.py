# -*- coding: utf-8 -*-
"""
Диагностика семейств - показывает все FamilySymbol в проекте
"""
from pyrevit import DB, script

doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

output.print_md("# 🔍 Диагностика семейств в проекте")
output.print_md("---")

# Collect all FamilySymbols
collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).WhereElementIsElementType()

# Collect all into list with category info
all_families = []
for symbol in collector:
    try:
        cat = symbol.Category
        cat_name = cat.Name if cat else "NO CATEGORY"
        cat_id = cat.Id.IntegerValue if cat else 0
        
        family = symbol.Family
        family_name = family.Name if family else "NO FAMILY"
        type_name = symbol.Name if symbol.Name else "NO NAME"
        
        all_families.append({
            'family': family_name,
            'type': type_name,
            'category': cat_name,
            'cat_id': cat_id,
            'id': symbol.Id.IntegerValue,
            'active': symbol.IsActive
        })
    except Exception as ex:
        output.print_md("⚠️ Error reading symbol: {}".format(str(ex)))

output.print_md("\n## Всего семейств: {}\n".format(len(all_families)))

# Group by category
by_category = {}
for fam in all_families:
    cat = fam['category']
    if cat not in by_category:
        by_category[cat] = []
    by_category[cat].append(fam)

# Show categories
output.print_md("## Категории:\n")
for cat in sorted(by_category.keys()):
    count = len(by_category[cat])
    output.print_md("- **{}** (ID: {}) - {} типов".format(
        cat, 
        by_category[cat][0]['cat_id'] if by_category[cat] else 0,
        count
    ))

# Filter for potential sockets
output.print_md("\n---\n## 🔌 Потенциальные розетки (фильтр по ключевым словам):\n")

socket_keywords = ['tsl', 'розет', 'рзт', 'socket', 'outlet', 'p3t', 'ef', 'электр']
potential_sockets = []

for fam in all_families:
    combined = (fam['family'] + " " + fam['type'] + " " + fam['category']).lower()
    if any(kw in combined for kw in socket_keywords):
        potential_sockets.append(fam)

if potential_sockets:
    output.print_md("Найдено {} потенциальных розеток:\n".format(len(potential_sockets)))
    output.print_md("| № | Категория | Семейство | Тип | Cat ID | Active |")
    output.print_md("|---|-----------|-----------|-----|--------|--------|")
    
    for i, fam in enumerate(potential_sockets[:50], 1):
        active = "✅" if fam['active'] else "❌"
        output.print_md("| {} | {} | {} | {} | {} | {} |".format(
            i,
            fam['category'],
            fam['family'],
            fam['type'],
            fam['cat_id'],
            active
        ))
    
    output.print_md("\n---\n## Для конфигурации (только имена типов):\n")
    output.print_md("```json")
    for fam in potential_sockets:
        output.print_md('"{}",'.format(fam['type']))
    output.print_md("```")
else:
    output.print_md("⚠️ Не найдено ни одного семейства по ключевым словам!")
    
    # Show first 20 families from all
    output.print_md("\n---\n## Первые 20 семейств в проекте (для отладки):\n")
    output.print_md("| № | Категория | Семейство | Тип | Cat ID |")
    output.print_md("|---|-----------|-----------|-----|--------|")
    
    for i, fam in enumerate(all_families[:20], 1):
        output.print_md("| {} | {} | {} | {} | {} |".format(
            i,
            fam['category'],
            fam['family'],
            fam['type'],
            fam['cat_id']
        ))

output.print_md("\n---\n## ℹ️ Справка по категориям:\n")
output.print_md("- **OST_ElectricalFixtures** = -2001040 (Электроприборы)")
output.print_md("- **OST_ElectricalEquipment** = -2001100 (Электрооборудование)")
output.print_md("- **OST_LightingFixtures** = -2001120 (Осветительные приборы)")
