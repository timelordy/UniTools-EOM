# -*- coding: utf-8 -*-

from pyrevit import revit, script, DB

import link_reader

doc = revit.doc
output = script.get_output()

def main():
    output.print_md('# Список дверей в связи (AR)')

    link_inst = link_reader.select_link_instance(doc, title='Выберите связь АР')
    if not link_inst:
        script.exit()

    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        output.print_md('❌ Связь не загружена.')
        return

    doors = link_reader.get_doors(link_doc)
    
    if not doors:
        output.print_md('❌ Двери в связи не найдены.')
        return

    output.print_md('Найдено экземпляров дверей: **{}**'.format(len(doors)))

    # Group by Family and Type
    types = {}
    for d in doors:
        try:
            fam_name = d.Symbol.FamilyName
            type_name = d.Name
            key = (fam_name, type_name)
            types[key] = types.get(key, 0) + 1
        except Exception:
            pass

    output.print_md('---')
    output.print_md('## Типы дверей:')
    
    # Sort by Family Name then Type Name
    sorted_keys = sorted(types.keys(), key=lambda x: (x[0], x[1]))

    for fam, typ in sorted_keys:
        count = types[(fam, typ)]
        output.print_md('- **{0}** : {1} (экземпляров: {2})'.format(fam, typ, count))

if __name__ == '__main__':
    main()
