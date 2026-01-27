# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    FilteredElementCollector,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem  # noqa: E402
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import (  # noqa: E402
    TaskDialog,
    TaskDialogCommandLinkId,
    TaskDialogCommonButtons,
    TaskDialogResult,
)
from System import Guid  # noqa: E402
from System.Collections.Generic import IList  # noqa: E402

from unibim.knk_laying_methods_utils import (  # noqa: E402
    aggregate_by_bundle,
    parse_laying_methods,
)


CAPTION = u"Рассчитать материалы"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"


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


def _get_param_from_settings(settings_list, key, default):
    if not settings_list:
        return default
    for idx, item in enumerate(settings_list):
        if item == key and idx + 1 < len(settings_list):
            return settings_list[idx + 1]
    return default


def _prompt_source():
    dlg = TaskDialog(CAPTION)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Отчет из схем (TSL_Кабель)",
        u"Считать длины из параметра <Способ прокладки> на схемах.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Отчет из электрических цепей",
        u"Считать длины из параметра <Способ прокладки> электрических цепей.",
    )
    return dlg.Show()


def _collect_from_annotations(doc, bundle_param_name):
    entries = []
    annotations = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_GenericAnnotation)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    for ann in annotations:
        family_name = ""
        try:
            if getattr(ann, "Symbol", None) and ann.Symbol and ann.Symbol.Family:
                family_name = ann.Symbol.Family.Name or ""
        except Exception:
            family_name = ""
        if u"TSL_Кабель" not in family_name:
            continue
        method_param = ann.LookupParameter(u"Способ прокладки")
        if method_param is None:
            continue
        method_text = method_param.AsString() or ""
        if not method_text:
            continue
        bundle_val = ""
        bundle_param = ann.LookupParameter(bundle_param_name)
        if bundle_param is not None:
            bundle_val = bundle_param.AsString() or ""
        for method, length in parse_laying_methods(method_text):
            entries.append({"bundle": bundle_val, "method": method, "length": length})
    return entries


def _collect_from_systems(doc, bundle_param_name, laying_param_name):
    entries = []
    systems = (
        FilteredElementCollector(doc)
        .OfClass(ElectricalSystem)
        .ToElements()
    )
    for sys in systems:
        method_param = sys.LookupParameter(laying_param_name)
        if method_param is None:
            continue
        method_text = method_param.AsString() or ""
        if not method_text:
            continue
        bundle_val = ""
        bundle_param = sys.LookupParameter(bundle_param_name)
        if bundle_param is not None:
            bundle_val = bundle_param.AsString() or ""
        for method, length in parse_laying_methods(method_text):
            entries.append({"bundle": bundle_val, "method": method, "length": length})
    return entries


def _format_report(aggregate):
    lines = []
    for bundle in sorted(aggregate.keys()):
        lines.append(u"\n<{}>".format(bundle))
        methods = aggregate[bundle]
        for method in sorted(methods.keys()):
            lines.append(u"{0} - {1} м".format(method.ljust(6), methods[method]))
    return "\n".join(lines).strip()


def main():
    doc = revit.doc
    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    bundle_param = _get_param_from_settings(settings_list, "Param_name_40_for_Param_Names_Storage", u"ADSK_Комплект")
    laying_param = _get_param_from_settings(settings_list, "Param_name_30_for_Param_Names_Storage", u"TSL_Способ прокладки")

    choice = _prompt_source()
    if choice == TaskDialogCommandLinkId.CommandLink1:
        entries = _collect_from_annotations(doc, bundle_param)
    elif choice == TaskDialogCommandLinkId.CommandLink2:
        entries = _collect_from_systems(doc, bundle_param, laying_param)
    else:
        return

    if not entries:
        forms.alert(u"Нет элементов для обработки.", title=CAPTION)
        return

    aggregated = aggregate_by_bundle(entries)
    report = _format_report(aggregated)
    if not report:
        forms.alert(u"Нет данных для отчета.", title=CAPTION)
        return

    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = u"Отчет длин по способам прокладки"
    dlg.MainContent = report + u"\n\nСохранить отчет в файл?"
    dlg.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
    res = dlg.Show()
    if res == TaskDialogResult.Yes:  # noqa: F821
        path = forms.save_file(file_ext='txt', title=CAPTION)
        if path:
            with open(path, 'w') as f:
                f.write(report)


if __name__ == "__main__":
    main()
