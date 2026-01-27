# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    FilteredElementCollector,
    Transaction,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem  # noqa: E402
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId, TaskDialogCommonButtons  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.knk_param_utils import get_knk_param_names  # noqa: E402
from unibim.knk_circuit_utils import parse_circuit_numbers  # noqa: E402
from unibim.knk_split_utils import split_by_flag, split_by_name  # noqa: E402


CAPTION = u"Разделить номера цепей в лотках и коробах"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

KNK_CATEGORIES = [
    BuiltInCategory.OST_CableTray,
    BuiltInCategory.OST_Conduit,
    BuiltInCategory.OST_CableTrayFitting,
    BuiltInCategory.OST_ConduitFitting,
]


class _CategoryFilter(ISelectionFilter):
    def __init__(self, categories):
        self._cat_ids = set(int(c) for c in categories)

    def AllowElement(self, element):
        try:
            return element.Category and element.Category.Id.IntegerValue in self._cat_ids
        except Exception:
            return False

    def AllowReference(self, reference, position):
        return False


def _read_storage_list(element, schema_guid, field_name):
    if element is None:
        return []
    schema = Schema.Lookup(Guid(schema_guid))
    if schema is None:
        return []
    field = schema.GetField(field_name)
    if field is None:
        return []
    entity = element.GetEntity(schema)
    if not entity or not entity.IsValid():
        return []
    try:
        return list(entity.Get[IList[str]](field))
    except Exception:
        return []


def _get_project_info(doc):
    return (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ProjectInformation)
        .WhereElementIsNotElementType()
        .FirstElement()
    )


def _collect_elements(doc, uidoc, param_name):
    elements = []
    if uidoc.Selection.GetElementIds():
        for eid in uidoc.Selection.GetElementIds():
            elem = doc.GetElement(eid)
            if elem is None:
                continue
            param = elem.LookupParameter(param_name)
            if param is None or not (param.AsString() or ""):
                continue
            elements.append(elem)
        return elements

    dlg = TaskDialog(CAPTION)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Обработать все элементы",
        u"Разделить номера цепей во всех лотках и коробах.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Выбрать элементы",
        u"Разделить номера цепей только у выбранных элементов.",
    )
    res = dlg.Show()
    if res == TaskDialogCommandLinkId.CommandLink1:
        for cat in KNK_CATEGORIES:
            elems = (
                FilteredElementCollector(doc)
                .OfCategory(cat)
                .WhereElementIsNotElementType()
                .ToElements()
            )
            for elem in elems:
                param = elem.LookupParameter(param_name)
                if param is None or not (param.AsString() or ""):
                    continue
                elements.append(elem)
        return elements
    if res == TaskDialogCommandLinkId.CommandLink2:
        try:
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element,
                _CategoryFilter(KNK_CATEGORIES),
                u"Выберите участки КНК",
            )
        except Exception:
            return []
        for r in refs:
            elem = doc.GetElement(r.ElementId)
            if elem is None:
                continue
            param = elem.LookupParameter(param_name)
            if param is None or not (param.AsString() or ""):
                continue
            elements.append(elem)
    return elements


def _build_circuit_maps(doc):
    load_map = {}
    flag_map = {}
    systems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ElectricalCircuit)
        .OfClass(ElectricalSystem)
        .ToElements()
    )
    for sys in systems:
        name = sys.Name
        load_map[name] = sys.LoadName or ""
        is_lighting = False
        try:
            for elem in sys.Elements:
                if elem.Category and elem.Category.Id.IntegerValue in (
                    int(BuiltInCategory.OST_LightingFixtures),
                    int(BuiltInCategory.OST_LightingDevices),
                ):
                    is_lighting = True
                    break
        except Exception:
            pass
        flag_map[name] = is_lighting
    return load_map, flag_map


def _prompt_mode():
    action = forms.CommandSwitchWindow.show(
        [u"Авто по названию нагрузки", u"Авто по составу цепи", u"Ручной выбор"],
        message=CAPTION,
    )
    return action


def main():
    doc = revit.doc
    uidoc = revit.uidoc
    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)

    elem_list = _collect_elements(doc, uidoc, knk_names["KnkCircuitNumber"])
    if not elem_list:
        forms.alert(u"Нет элементов для обработки.", title=CAPTION)
        return

    if not (knk_names["KnkCircuitNumberEO"] and knk_names["KnkCircuitNumberEM"] and knk_names["KnkCircuitNumberES"]):
        forms.alert(
            u"Добавьте параметры: {0}, {1}, {2}".format(
                knk_names["KnkCircuitNumberEO"],
                knk_names["KnkCircuitNumberEM"],
                knk_names["KnkCircuitNumberES"],
            ),
            title=CAPTION,
        )
        return

    circuits = sorted(set(sum([parse_circuit_numbers(e.LookupParameter(knk_names["KnkCircuitNumber"]).AsString() or "") for e in elem_list], [])))
    if not circuits:
        forms.alert(u"Не найдены номера цепей для разделения.", title=CAPTION)
        return

    load_map, flag_map = _build_circuit_maps(doc)
    mode = _prompt_mode()
    if not mode:
        return

    eo = []
    em = []
    es = []
    if mode == u"Авто по названию нагрузки":
        keywords = [u"освещ", u"свет", u"указател"]
        eo, em, es = split_by_name(circuits, load_map, [k.lower() for k in keywords])
    elif mode == u"Авто по составу цепи":
        eo, em, es = split_by_flag(circuits, flag_map)
    else:
        display = []
        label_to_circuit = {}
        for c in circuits:
            label = c
            load = load_map.get(c, "")
            if load:
                label = u"{0} - {1}".format(c, load)
            display.append(label)
            label_to_circuit[label] = c
        eo_sel = forms.SelectFromList.show(display, multiselect=True, title=CAPTION, button_name=u"Выбрать ЭО")
        if eo_sel is None:
            return
        eo = [label_to_circuit[i] for i in eo_sel]
        remaining = [i for i in display if label_to_circuit[i] not in eo]
        em_sel = forms.SelectFromList.show(remaining, multiselect=True, title=CAPTION, button_name=u"Выбрать ЭМ")
        if em_sel is None:
            return
        em = [label_to_circuit[i] for i in em_sel]
        es = [label_to_circuit[i] for i in remaining if label_to_circuit[i] not in em]

    eo_set = set(eo)
    em_set = set(em)
    es_set = set(es)

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for elem in elem_list:
            circuits_elem = parse_circuit_numbers(elem.LookupParameter(knk_names["KnkCircuitNumber"]).AsString() or "")
            eo_vals = [c for c in circuits_elem if c in eo_set]
            em_vals = [c for c in circuits_elem if c in em_set]
            es_vals = [c for c in circuits_elem if c in es_set]
            p_eo = elem.LookupParameter(knk_names["KnkCircuitNumberEO"])
            p_em = elem.LookupParameter(knk_names["KnkCircuitNumberEM"])
            p_es = elem.LookupParameter(knk_names["KnkCircuitNumberES"])
            if p_eo is not None:
                p_eo.Set("\n".join(eo_vals))
            if p_em is not None:
                p_em.Set("\n".join(em_vals))
            if p_es is not None:
                p_es.Set("\n".join(es_vals))
        t.Commit()
    finally:
        t.Dispose()

    forms.alert(u"Разделение выполнено.", title=CAPTION)


if __name__ == "__main__":
    main()
