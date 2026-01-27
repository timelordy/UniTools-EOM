# -*- coding: utf-8 -*-

from pyrevit import revit

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    AnnotationSymbol,
    BuiltInCategory,
    Color,
    DisplayStyle,
    ElementId,
    FilteredElementCollector,
    OverrideGraphicSettings,
    Transaction,
    ViewDisplayBackground,
    ViewType,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem  # noqa: E402
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.Exceptions import OperationCanceledException  # noqa: E402
from Autodesk.Revit.UI import TaskDialog, TaskDialogIcon  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.knk_circuit_utils import parse_circuit_numbers  # noqa: E402
from unibim.knk_param_utils import get_knk_param_names  # noqa: E402


CAPTION = u"Показать кабельную трассу"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

SELECT_CATEGORY_IDS = set([
    -2000150,
    -2001040,
    -2001060,
    -2008087,
    -2001120,
    -2008083,
    -2008016,
    -2008055,
    -2001140,
    -2008079,
    -2008085,
    -2001160,
    -2008075,
    -2008077,
    -2008081,
    -2001046,
    -2001043,
])

KNK_CATEGORIES = [
    BuiltInCategory.OST_CableTray,
    BuiltInCategory.OST_Conduit,
    BuiltInCategory.OST_CableTrayFitting,
    BuiltInCategory.OST_ConduitFitting,
]


class _CategoryFilter(ISelectionFilter):
    def __init__(self, allowed_ids):
        self._allowed = set(int(x) for x in allowed_ids)

    def AllowElement(self, element):
        try:
            return element.Category and element.Category.Id.IntegerValue in self._allowed
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


def _get_active_views(uidoc):
    doc = uidoc.Document
    views = []
    for ui_view in uidoc.GetOpenUIViews():
        view = doc.GetElement(ui_view.ViewId)
        if view and view.ViewType in [ViewType.FloorPlan, ViewType.CeilingPlan, ViewType.ThreeD]:
            views.append(view)
    return views


def _apply_halftone_settings(uidoc, selected_ids):
    doc = uidoc.Document
    views = _get_active_views(uidoc)
    t = Transaction(doc, u"Установка настроек полутонов")
    try:
        t.Start()
        for view in views:
            try:
                view.EnableTemporaryViewPropertiesMode(view.Id)
            except Exception:
                pass
            if view.ViewType == ViewType.ThreeD:
                white = Color(255, 255, 255)
                view.SetBackground(ViewDisplayBackground.CreateGradient(white, white, white))
            view.DisplayStyle = DisplayStyle.Shading

            highlight = OverrideGraphicSettings()
            highlight.SetProjectionLineColor(Color(255, 0, 255))

            dim = OverrideGraphicSettings()
            dim.SetProjectionLineColor(Color(175, 175, 175))
            dim.SetProjectionLineWeight(1)
            dim.SetSurfaceTransparency(25)

            view_elements = (
                FilteredElementCollector(doc, view.Id)
                .WhereElementIsNotElementType()
                .WhereElementIsViewIndependent()
                .ToElements()
            )
            for elem in view_elements:
                try:
                    if elem.Id in selected_ids:
                        view.SetElementOverrides(elem.Id, highlight)
                    else:
                        view.SetElementOverrides(elem.Id, dim)
                except Exception:
                    pass
        t.Commit()
    finally:
        t.Dispose()


def _reset_halftone_settings(uidoc):
    doc = uidoc.Document
    views = _get_active_views(uidoc)
    t = Transaction(doc, u"Сброс настроек полутонов")
    try:
        t.Start()
        for view in views:
            view_elements = (
                FilteredElementCollector(doc, view.Id)
                .WhereElementIsNotElementType()
                .WhereElementIsViewIndependent()
                .ToElements()
            )
            for elem in view_elements:
                try:
                    view.SetElementOverrides(elem.Id, OverrideGraphicSettings())
                except Exception:
                    pass
            try:
                view.EnableTemporaryViewPropertiesMode(ElementId.InvalidElementId)
            except Exception:
                pass
        t.Commit()
    finally:
        t.Dispose()


def _find_electrical_system_by_name(doc, name):
    if not name:
        return None
    for system in FilteredElementCollector(doc).OfClass(ElectricalSystem).ToElements():
        if system and system.Name == name:
            return system
    return None


def _get_circuit_name_from_instance(instance):
    if not instance or not hasattr(instance, "MEPModel"):
        return None, None
    try:
        systems = list(instance.MEPModel.GetElectricalSystems())
    except Exception:
        systems = []
    if not systems:
        return None, None
    system = systems[0]
    return system.Name, system


def _collect_system_element_ids(system):
    ids = set()
    if system is None:
        return ids
    try:
        base = system.BaseEquipment
        if base is not None:
            ids.add(base.Id)
    except Exception:
        pass
    try:
        for elem in system.Elements:
            if elem is not None:
                ids.add(elem.Id)
    except Exception:
        pass
    return ids


def _get_circuit_name_from_tag(tag):
    if tag is None or not tag.ViewSpecific:
        return None
    param = tag.LookupParameter(u"Номер цепи")
    return param.AsString() if param else None


def _get_knk_match_ids(doc, circuit_name, knk_param_names):
    if not circuit_name:
        return None
    param_name = knk_param_names["KnkCircuitNumber"]
    ids = set()
    for elem in _collect_knk_elements(doc):
        param = elem.LookupParameter(param_name)
        if param is None:
            TaskDialog.Show(
                CAPTION,
                u"Не удалось найти параметр {0} у элемента КНК. "
                u"Проверьте наличие параметра у категорий: Кабельный лоток, Короб."
                .format(param_name),
            )
            return None
        numbers = parse_circuit_numbers(param.AsString())
        if circuit_name in numbers:
            ids.add(elem.Id)
    return ids


def main():
    uidoc = revit.uidoc
    doc = revit.doc
    selection = uidoc.Selection

    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)

    selected_ids = None
    filter_by_category = _CategoryFilter(SELECT_CATEGORY_IDS)
    while True:
        try:
            ref = selection.PickObject(
                ObjectType.Element,
                filter_by_category,
                u"Выберите элемент электрической цепи. Для выхода нажмите Esc.",
            )
        except OperationCanceledException:
            if selected_ids:
                _reset_halftone_settings(uidoc)
                try:
                    selection.SetElementIds(List[ElementId](selected_ids))
                except Exception:
                    pass
            return

        elem = doc.GetElement(ref.ElementId)
        if elem is None:
            continue

        circuit_name = None
        system = None
        ids = set()

        if isinstance(elem, AnnotationSymbol):
            circuit_name = _get_circuit_name_from_tag(elem)
            if not circuit_name:
                continue
            system = _find_electrical_system_by_name(doc, circuit_name)
        else:
            circuit_name, system = _get_circuit_name_from_instance(elem)
            if not circuit_name:
                TaskDialog.Show(CAPTION, u"Элемент не подключен к электрической цепи!")
                continue

        ids.update(_collect_system_element_ids(system))

        knk_ids = _get_knk_match_ids(doc, circuit_name, knk_names)
        if knk_ids is None:
            return
        ids.update(knk_ids)

        if not ids:
            dlg = TaskDialog(CAPTION)
            dlg.MainIcon = TaskDialogIcon.Warning
            dlg.MainInstruction = u"Номер цепи \"{0}\" не принадлежит кабеленесущей конструкции!".format(circuit_name)
            dlg.Show()
            continue

        _apply_halftone_settings(uidoc, ids)
        selected_ids = list(ids)


if __name__ == "__main__":
    main()
