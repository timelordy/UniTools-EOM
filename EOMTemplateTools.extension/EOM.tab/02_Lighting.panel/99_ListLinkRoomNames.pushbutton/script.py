# -*- coding: utf-8 -*-
from pyrevit import script
import link_reader

output = script.get_output()
doc = __revit__.ActiveUIDocument.Document

def main():
    link_inst = link_reader.select_link_instance(doc, title="Выберите связь АР")
    if not link_inst:
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        return

    rooms = link_reader.get_rooms(link_doc)
    names = set()
    for r in rooms:
        try:
            n = r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
            if n:
                names.add(n)
        except:
            pass
    
    output.print_md("### Имена помещений в связи:")
    for n in sorted(names):
        print(n)

if __name__ == "__main__":
    main()
