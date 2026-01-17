# -*- coding: utf-8 -*-
"""Find baskets in links."""
from pyrevit import DB, revit, script

def main():
    output = script.get_output()
    doc = revit.doc
    
    output.print_md('# Поиск корзин в связях')
    
    # 1. Get Links
    links = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    output.print_md('Найдено связей: **{}**'.format(len(links)))
    
    keywords = ["корзина", "basket", "external", "внешний", "блок", "кондиц"]
    categories = [
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_Furniture
    ]
    
    for ln in links:
        try:
            name = ln.Name
            link_doc = ln.GetLinkDocument()
            if not link_doc:
                output.print_md('- {}: **Не загружена**'.format(name))
                continue
                
            output.print_md('---')
            output.print_md('### Связь: {}'.format(name))
            
            found_count = 0
            
            for bic in categories:
                cat_name = str(bic)
                col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()
                
                for e in col:
                    # Get names
                    e_name = e.Name
                    try: sym = e.Symbol
                    except: sym = None
                    sym_name = sym.Name if sym else ""
                    fam_name = sym.Family.Name if sym and sym.Family else ""
                    
                    full_text = "{} {} {}".format(e_name, sym_name, fam_name).lower()
                    
                    matches = [k for k in keywords if k in full_text]
                    if matches:
                        output.print_md("- **Найдено**: [{}] {} / {} / {}".format(
                            link_doc.Settings.Categories.get_Item(bic).Name,
                            fam_name, sym_name, e_name
                        ))
                        found_count += 1
                        if found_count > 20:
                            output.print_md("... (слишком много результатов)")
                            break
                if found_count > 20: break
            
            if found_count == 0:
                output.print_md("Корзины не найдены по ключевым словам: " + ", ".join(keywords))
                
        except Exception as ex:
            output.print_md("Ошибка при обработке {}: {}".format(name, ex))

if __name__ == '__main__':
    main()
