# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

from unibim import reverse_lighting


TITLE = u"Перевернуть светильники"
PROMPT = u"Выберите семейства которые нужно перевернуть."
VIEW_WARN = (
    u"Выполнение прервано!\n"
    u"Активный вид не позволяет сделать выбор, перейдите на план этажа, "
    u"план потолка или 3D вид."
)


doc = revit.doc
uidoc = revit.uidoc
sel = uidoc.Selection


if not reverse_lighting.is_supported_view_type(doc.ActiveView.ViewType):
    forms.alert(VIEW_WARN, title=TITLE, warn_icon=True)
    script.exit()


element_ids = sel.GetElementIds()
elements = None

if element_ids and element_ids.Count > 0:
    elements = [doc.GetElement(eid) for eid in element_ids]
else:
    try:
        refs = sel.PickObjects(DB.Selection.ObjectType.Element, PROMPT)
    except Exception:
        script.exit()
    elements = [doc.GetElement(r) for r in refs]


instances = [e for e in elements if isinstance(e, DB.FamilyInstance)]
if not instances:
    forms.alert(u"Не выбрано ни одного семейства.", title=TITLE, warn_icon=True)
    script.exit()


with revit.Transaction(TITLE):
    reverse_lighting.flip_instances(instances)


forms.alert(u"Выполнение завершено!", title=TITLE)
try:
    sel.SetElementIds(element_ids)
except Exception:
    pass
