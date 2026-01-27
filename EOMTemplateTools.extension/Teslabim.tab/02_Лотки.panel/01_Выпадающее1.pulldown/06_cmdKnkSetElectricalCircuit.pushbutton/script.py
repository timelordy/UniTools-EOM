# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
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
from unibim.knk_set_circuit_utils import merge_circuits, normalize_circuits  # noqa: E402


CAPTION = u"Записать номера цепей из схем"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

KNS_GROUP_PARAM = u"TSL_КНС_Номер группы"

FAMILY_NAMES_AVT = [
    u"GA_SHM_2D автоматический выключатель_ВРУ",
    u"GA_SHM_2D автоматический выключатель_Щит",
    u"TSL_2D автоматический выключатель_ВРУ",
    u"TSL_2D автоматический выключатель_Щит",
]

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


def _prompt_source():
    dlg = TaskDialog(CAPTION)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Выбрать номера цепей из схем",
        u"Выбрать номера цепей из схем, расположенных на чертежных видах.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Выбрать номера цепей из электрических цепей",
        u"Выбрать номера цепей из электрических цепей в модели.",
    )
    return dlg.Show()


def _collect_scheme_circuits(doc):
    circuits = []
    annotations = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_GenericAnnotation)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    for ann in annotations:
        name = ""
        try:
            name = ann.Name or ""
        except Exception:
            pass
        if not name and getattr(ann, "Symbol", None) and ann.Symbol and ann.Symbol.Family:
            name = ann.Symbol.Family.Name or ""
        if name not in FAMILY_NAMES_AVT and u"TSL_Кабель" not in name:
            continue
        param = ann.LookupParameter(u"Номер цепи")
        if param is None:
            continue
        value = param.AsString()
        if value:
            circuits.append(value)
    return normalize_circuits(circuits)


def _collect_model_circuits(doc):
    systems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ElectricalCircuit)
        .OfClass(ElectricalSystem)
        .ToElements()
    )
    circuits = [s.Name for s in systems if getattr(s, "Name", None)]
    return normalize_circuits(circuits)


def _pick_elements(uidoc, doc):
    try:
        refs = uidoc.Selection.PickObjects(
            ObjectType.Element,
            _CategoryFilter(KNK_CATEGORIES),
            u"Выберите участки кабеленесущих конструкций",
        )
    except Exception:
        return []
    return [doc.GetElement(r.ElementId) for r in refs if doc.GetElement(r.ElementId) is not None]


def _get_elements(uidoc, doc):
    sel_ids = uidoc.Selection.GetElementIds()
    if sel_ids:
        return [doc.GetElement(eid) for eid in sel_ids if doc.GetElement(eid) is not None]
    return _pick_elements(uidoc, doc)


def _prompt_action():
    action = forms.CommandSwitchWindow.show(
        [u"Заменить цепи", u"Добавить цепи", u"Удалить цепи"],
        message=CAPTION,
    )
    if not action:
        return None
    return {
        u"Заменить цепи": "replace",
        u"Добавить цепи": "add",
        u"Удалить цепи": "remove",
    }.get(action)


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    choice = _prompt_source()
    if choice == TaskDialogCommandLinkId.CommandLink1:
        available = _collect_scheme_circuits(doc)
    elif choice == TaskDialogCommandLinkId.CommandLink2:
        available = _collect_model_circuits(doc)
    else:
        return

    if not available:
        forms.alert(u"Не найдены номера цепей для записи.", title=CAPTION)
        return

    elements = _get_elements(uidoc, doc)
    if not elements:
        return

    action = _prompt_action()
    if not action:
        return

    selected = forms.SelectFromList.show(
        available,
        multiselect=True,
        title=CAPTION,
        button_name=u"Выбрать цепи",
    )
    if not selected:
        return

    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)
    circuit_param_name = knk_names["KnkCircuitNumber"]

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for elem in elements:
            param = elem.LookupParameter(circuit_param_name)
            existing_raw = []
            if param is not None:
                text = param.AsString()
                if text:
                    existing_raw = [text]
            merged = merge_circuits(existing_raw, selected, action)
            if param is not None:
                param.Set("\n".join(merged))
            kns_param = elem.LookupParameter(KNS_GROUP_PARAM)
            if kns_param is not None:
                kns_param.Set("\n".join(merged))
        t.Commit()
    finally:
        t.Dispose()

    try:
        uidoc.Selection.SetElementIds(List[ElementId]([elem.Id for elem in elements]))
    except Exception:
        pass

    forms.alert(u"Выполнение завершено!", title=CAPTION)


if __name__ == "__main__":
    main()
