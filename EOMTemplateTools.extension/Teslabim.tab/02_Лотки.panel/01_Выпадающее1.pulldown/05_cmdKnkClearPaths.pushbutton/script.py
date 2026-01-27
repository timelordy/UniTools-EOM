# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    GroupType,
    Transaction,
)
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId, TaskDialogCommonButtons  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.knk_param_utils import get_knk_param_names  # noqa: E402


CAPTION = u"Очистить трассы"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

KNS_GROUP_PARAM = u"TSL_КНС_Номер группы"
KNS_OCCUPANCY_PARAM = u"TSL_КНС_Заполняемость лотка (%)"
KNS_VOLUME_PARAM = u"TSL_КНС_Объём горючей массы (л/км)"

KNN_GROUP_NAME = u"TSL_КНК_"

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


def _collect_knk_elements(doc):
    elements = []
    for cat in KNK_CATEGORIES:
        elems = (
            FilteredElementCollector(doc)
            .OfCategory(cat)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        elements.extend(elems)
    return elements


def _delete_sections(doc):
    types = (
        FilteredElementCollector(doc)
        .OfClass(GroupType)
        .ToElements()
    )
    ids = [t.Id for t in types if t.Name and KNN_GROUP_NAME in t.Name and t.Groups.IsEmpty]
    if ids:
        doc.Delete(List[ElementId](ids))


def _clear_param_string(element, name):
    param = element.LookupParameter(name)
    if param is not None:
        param.Set("")


def _clear_param_number(element, name):
    param = element.LookupParameter(name)
    if param is not None:
        param.Set(0)


def _clear_knk_params(element, names, flags, include_kns=False):
    if flags.get("knk_circuit_number"):
        _clear_param_string(element, names["KnkCircuitNumber"])
    if flags.get("knk_cable_tray_occupancy"):
        _clear_param_number(element, names["KnkCableTrayOccupancy"])
    if flags.get("knk_volume"):
        _clear_param_number(element, names["KnkVolumeOfCombustibleMass"])
    if flags.get("knk_weight"):
        _clear_param_number(element, names["KnkWeightSectionMass"])
    if flags.get("knk_em"):
        _clear_param_string(element, names["KnkCircuitNumberEM"])
    if flags.get("knk_eo"):
        _clear_param_string(element, names["KnkCircuitNumberEO"])
    if flags.get("knk_es"):
        _clear_param_string(element, names["KnkCircuitNumberES"])
    if include_kns and flags.get("knk_circuit_number"):
        _clear_param_string(element, KNS_GROUP_PARAM)
    if include_kns and flags.get("knk_cable_tray_occupancy"):
        _clear_param_number(element, KNS_OCCUPANCY_PARAM)
    if include_kns and flags.get("knk_volume"):
        _clear_param_number(element, KNS_VOLUME_PARAM)


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


def _prompt_mode():
    dlg = TaskDialog(CAPTION)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Выбрать участки",
        u"Выбрать участки для удаления значений параметров",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Очистить всю модель",
        u"Удалить всю информацию из кабеленесущих конструкций и все созданные сечения",
    )
    return dlg.Show()


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)

    elements = []
    sel_ids = uidoc.Selection.GetElementIds()
    if not sel_ids:
        choice = _prompt_mode()
        if choice == TaskDialogCommandLinkId.CommandLink2:
            elements = _collect_knk_elements(doc)
            t = Transaction(doc, CAPTION)
            try:
                t.Start()
                flags = {
                    "knk_circuit_number": True,
                    "knk_cable_tray_occupancy": True,
                    "knk_volume": True,
                    "knk_weight": True,
                    "knk_em": True,
                    "knk_eo": True,
                    "knk_es": True,
                }
                for elem in elements:
                    _clear_knk_params(elem, knk_names, flags, include_kns=True)
                _delete_sections(doc)
                t.Commit()
            finally:
                t.Dispose()
            TaskDialog.Show(CAPTION, u"Выполнение завершено!")
            return
        if choice != TaskDialogCommandLinkId.CommandLink1:
            return
        elements = _pick_elements(uidoc, doc)
    else:
        elements = [doc.GetElement(eid) for eid in sel_ids if doc.GetElement(eid) is not None]

    if not elements:
        return

    form = forms.FlexForm(
        CAPTION,
        [
            forms.CheckBox("select_all", u"Выбрать всё", default=True),
            forms.Separator(),
            forms.CheckBox("knk_circuit_number", u"TSL_КНК_Номер цепи", default=True),
            forms.CheckBox("knk_cable_tray_occupancy", u"TSL_КНК_Заполняемость лотка (%)", default=True),
            forms.CheckBox("knk_volume", u"TSL_КНК_Объём горючей массы (л/м)", default=True),
            forms.CheckBox("knk_weight", u"TSL_КНК_Масса участка (кг/м)", default=True),
            forms.CheckBox("knk_em", u"TSL_КНК_Номер цепи ЭМ", default=True),
            forms.CheckBox("knk_eo", u"TSL_КНК_Номер цепи ЭО", default=True),
            forms.CheckBox("knk_es", u"TSL_КНК_Номер цепи ЭС", default=True),
            forms.Button(u"ОК"),
        ],
    )
    if not form.show():
        return

    if form.values.get("select_all"):
        flags = {
            "knk_circuit_number": True,
            "knk_cable_tray_occupancy": True,
            "knk_volume": True,
            "knk_weight": True,
            "knk_em": True,
            "knk_eo": True,
            "knk_es": True,
        }
    else:
        flags = {
            "knk_circuit_number": bool(form.values.get("knk_circuit_number")),
            "knk_cable_tray_occupancy": bool(form.values.get("knk_cable_tray_occupancy")),
            "knk_volume": bool(form.values.get("knk_volume")),
            "knk_weight": bool(form.values.get("knk_weight")),
            "knk_em": bool(form.values.get("knk_em")),
            "knk_eo": bool(form.values.get("knk_eo")),
            "knk_es": bool(form.values.get("knk_es")),
        }

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for elem in elements:
            _clear_knk_params(elem, knk_names, flags, include_kns=False)
        t.Commit()
    finally:
        t.Dispose()

    try:
        uidoc.Selection.SetElementIds(List[ElementId]([elem.Id for elem in elements]))
    except Exception:
        pass

    TaskDialog.Show(CAPTION, u"Выполнение завершено!")


if __name__ == "__main__":
    main()
