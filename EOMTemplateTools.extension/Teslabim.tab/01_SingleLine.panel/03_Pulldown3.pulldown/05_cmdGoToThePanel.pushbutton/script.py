# -*- coding: utf-8 -*-

from pyrevit import revit

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    BuiltInParameter,
    ElementId,
    FamilyInstance,
    FilteredElementCollector,
)
from Autodesk.Revit.UI import TaskDialog  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System.Collections.Generic import List  # noqa: E402


CAPTION = u"Перейти к щиту"
PARAM_PANEL_NAME = u"Имя панели"
FAMILY_NAMES_NKU = [
    u"GA_SHM_Панель распределительная",
    u"GA_SHM_Щит распределительный",
    u"TSL_Панель распределительная",
    u"TSL_Щит распределительный",
]


class _FamilySelectionByCategoryAndNameFilter(ISelectionFilter):
    def AllowElement(self, element):
        try:
            if element.Category and element.Category.Id.IntegerValue == int(BuiltInCategory.OST_ElectricalEquipment):
                return True
            if isinstance(element, FamilyInstance):
                fam = element.Symbol.Family if element.Symbol else None
                if fam and fam.Name in FAMILY_NAMES_NKU:
                    return True
        except Exception:
            return False
        return False

    def AllowReference(self, reference, position):
        return False


def _get_panel_name_from_equipment(element):
    try:
        param = element.get_Parameter(BuiltInParameter(-1140078))
        return param.AsString() if param else None
    except Exception:
        return None


def _get_panel_name_from_param(element):
    try:
        param = element.LookupParameter(PARAM_PANEL_NAME)
        return param.AsString() if param else None
    except Exception:
        return None


def _set_id_ee(elements):
    ids = []
    for elem in elements:
        name_val = _get_panel_name_from_equipment(elem)
        if name_val:
            ids.append(elem.Id)
    return ids


def _set_id_ga(elements):
    ids = []
    for elem in elements:
        name_val = _get_panel_name_from_param(elem)
        if name_val:
            ids.append(elem.Id)
    return ids


def _collect_electrical_equipments(doc, panel_name):
    elems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ElectricalEquipment)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return [e for e in elems if _get_panel_name_from_equipment(e) == panel_name]


def _collect_generic_annotations(doc, panel_name):
    elems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_GenericAnnotation)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return [e for e in elems if _get_panel_name_from_param(e) == panel_name]


def main():
    uidoc = revit.uidoc
    doc = revit.doc

    try:
        ref = uidoc.Selection.PickObject(
            ObjectType.Element,
            _FamilySelectionByCategoryAndNameFilter(),
            u"Выберите щит/панель на чертёжном виде, плане этажа или 3D виде",
        )
    except Exception:
        return

    picked = doc.GetElement(ref.ElementId)
    if picked is None:
        return

    panel_name = None
    target_ids = []
    mode = 0

    if picked.Category and picked.Category.Id.IntegerValue == int(BuiltInCategory.OST_ElectricalEquipment):
        eq_list = _collect_electrical_equipments(doc, _get_panel_name_from_equipment(picked))
        if eq_list:
            panel_name = _get_panel_name_from_equipment(eq_list[0])
        if len(eq_list) > 1:
            dup_ids = _set_id_ee(eq_list)
            TaskDialog.Show(
                CAPTION,
                u"У щита/панели <{}> есть дубликат на плане этажа или 3D виде!\n{}".format(
                    panel_name or u"", u"; ".join(str(i) for i in dup_ids)
                ),
            )
            return
        mode = 1
        ga_list = _collect_generic_annotations(doc, panel_name)
        for item in ga_list:
            if _get_panel_name_from_param(item):
                target_ids.append(item.Id)
        if len(target_ids) > 1:
            TaskDialog.Show(
                CAPTION,
                u"У щита/панели <{}> есть дубликат на чертёжном виде!\n{}".format(
                    panel_name or u"", u"; ".join(str(i) for i in target_ids)
                ),
            )
            return
    else:
        panel_name = _get_panel_name_from_param(picked)
        if panel_name:
            ga_list = _collect_generic_annotations(doc, panel_name)
            if ga_list:
                panel_name = _get_panel_name_from_param(ga_list[0])
            if len(ga_list) > 1:
                dup_ids = _set_id_ga(ga_list)
                TaskDialog.Show(
                    CAPTION,
                    u"У щита/панели <{}> есть дубликат на чертёжном виде!\n{}".format(
                        panel_name or u"", u"; ".join(str(i) for i in dup_ids)
                    ),
                )
                return
            mode = 2
            eq_list = _collect_electrical_equipments(doc, panel_name)
            for item in eq_list:
                if _get_panel_name_from_equipment(item):
                    target_ids.append(item.Id)
            if len(target_ids) > 1:
                TaskDialog.Show(
                    CAPTION,
                    u"У щита/панели <{}> есть дубликат на плане этажа или 3D виде!\n{}".format(
                        panel_name or u"", u"; ".join(str(i) for i in target_ids)
                    ),
                )
                return

    if len(target_ids) == 1:
        uidoc.ShowElements(target_ids[0])
        uidoc.Selection.SetElementIds(List[ElementId]([target_ids[0]]))
        return

    if len(target_ids) == 0:
        if mode == 1:
            TaskDialog.Show(
                CAPTION,
                u"У щита/панели <{}> нет схемы щита на чертёжном виде.".format(panel_name or u""),
            )
            return
        if mode == 2:
            TaskDialog.Show(
                CAPTION,
                u"У щита/панели <{}> нет экземпляра щита на плане этажа или 3D виде.".format(panel_name or u""),
            )
            return

    TaskDialog.Show(
        CAPTION,
        u"Упс! С этим элементом программа не работает :(\n"
        u"Выберите семейство щита/панели на чертёжном виде "
        u"или семейство категории «Электрооборудование» на плане этажа или 3D виде.",
    )


if __name__ == "__main__":
    main()
