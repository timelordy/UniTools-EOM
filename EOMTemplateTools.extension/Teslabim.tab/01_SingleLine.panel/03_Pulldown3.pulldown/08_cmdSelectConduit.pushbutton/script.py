# -*- coding: utf-8 -*-

import json
import os

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from System import Guid  # noqa: E402

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    Transaction,
    UnitUtils,
    UnitTypeId,
)
from Autodesk.Revit.DB.Electrical import ConduitSizeSettings  # noqa: E402
from Autodesk.Revit.DB.ExtensibleStorage import (  # noqa: E402
    Schema,
    SchemaBuilder,
    AccessLevel,
    Entity,
)
from Autodesk.Revit.UI import (  # noqa: E402
    TaskDialog,
    TaskDialogCommonButtons,
    TaskDialogCommandLinkId,
    TaskDialogIcon,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402

from unibim.select_conduit_utils import (  # noqa: E402
    find_cable_diameter,
    has_invalid_comma_separator,
    update_laying_method_text,
)


CAPTION = u"Подобрать диаметр трубы"
GUID = "3ca06558-b053-4270-b586-dc4a5a9223d3"
SCHEMA_NAME = "TslSettings_SelectConduit"
FIELD_NAME = "JSON"

PARAM_LAYING = u"Способ прокладки"
PARAM_VEINS = u"Количество жил"
PARAM_SECTION = u"Сечение проводника"
PARAM_MARK = u"Марка проводника"


class _LayingFilter(ISelectionFilter):
    def AllowElement(self, element):
        try:
            if element.LookupParameter(PARAM_LAYING) is None:
                return False
            if hasattr(element, "SuperComponent") and element.SuperComponent is not None:
                return False
            return True
        except Exception:
            return False

    def AllowReference(self, reference, position):
        return False


def _get_project_info(doc):
    elems = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).ToElements()
    return elems[0] if elems else None


def _get_schema():
    schema = Schema.Lookup(Guid(GUID))  # noqa: F821
    if schema is not None:
        return schema
    sb = SchemaBuilder(Guid(GUID))  # noqa: F821
    sb.SetSchemaName(SCHEMA_NAME)
    sb.AddSimpleField(FIELD_NAME, str)
    sb.SetReadAccessLevel(AccessLevel.Public)
    sb.SetWriteAccessLevel(AccessLevel.Public)
    return sb.Finish()


def _read_settings(doc):
    info = _get_project_info(doc)
    if info is None:
        return None
    schema = _get_schema()
    entity = info.GetEntity(schema)
    if entity is None or not entity.IsValid():
        return None
    try:
        data = entity.Get[str](FIELD_NAME)
    except Exception:
        data = None
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


def _write_settings(doc, payload):
    info = _get_project_info(doc)
    if info is None:
        return
    schema = _get_schema()
    entity = Entity(schema)
    entity.Set[str](FIELD_NAME, json.dumps(payload))
    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        info.SetEntity(entity)
        t.Commit()
    finally:
        t.Dispose()


def _get_conduit_size_types(doc):
    settings = ConduitSizeSettings.GetConduitSizeSettings(doc)
    if settings is None:
        return []
    result = []
    try:
        iterator = settings.GetEnumerator()
        items = []
        while iterator.MoveNext():
            items.append(iterator.Current)
    except Exception:
        items = list(settings)
    for kv in items:
        name = kv.Key
        sizes = kv.Value
        entry = {"Name": name, "Percent": 40.0, "ConduitModels": []}
        for size in sizes:
            entry["ConduitModels"].append(
                {
                    "NominalDiameter": UnitUtils.ConvertFromInternalUnits(size.NominalDiameter, UnitTypeId.Millimeters),
                    "InnerDiameter": UnitUtils.ConvertFromInternalUnits(size.InnerDiameter, UnitTypeId.Millimeters),
                    "OuterDiameter": UnitUtils.ConvertFromInternalUnits(size.OuterDiameter, UnitTypeId.Millimeters),
                }
            )
        result.append(entry)
    return result


def _apply_saved_percent(conduit_types, stored):
    if not stored:
        return conduit_types
    saved = {}
    for item in stored.get("ConduitSizeSettings", []):
        saved[item.get("Name")] = item.get("Percent", 40.0)
    for item in conduit_types:
        if item["Name"] in saved:
            item["Percent"] = saved[item["Name"]]
    return conduit_types


def _show_settings(conduit_types):
    components = []
    for item in conduit_types:
        components.append(forms.Label(u"{} (%)".format(item["Name"])))
        components.append(forms.TextBox(item["Name"], str(item.get("Percent", 40.0))))
    components.append(forms.Separator())
    components.append(forms.Button(u"Сохранить"))
    form = forms.FlexForm(u"Настройки", components)
    if not form.show():
        return None
    values = form.values
    for item in conduit_types:
        try:
            item["Percent"] = float(values.get(item["Name"], 40.0))
        except Exception:
            item["Percent"] = 40.0
    payload = {"ConduitSizeSettings": [{"Name": i["Name"], "Percent": i["Percent"]} for i in conduit_types]}
    return payload


def _pick_elements(uidoc):
    selection = uidoc.Selection
    try:
        refs = selection.PickObjects(ObjectType.Element, _LayingFilter(), u"Выберите линии для подбора диаметра трубы")
    except Exception:
        return []
    return [uidoc.Document.GetElement(r) for r in refs]


def _collect_family_instances(doc, view_only):
    if view_only:
        collector = FilteredElementCollector(doc, doc.ActiveView.Id)
    else:
        collector = FilteredElementCollector(doc)
    result = []
    for elem in collector.WhereElementIsNotElementType():
        try:
            if elem.LookupParameter(PARAM_LAYING) is None:
                continue
            if hasattr(elem, "SuperComponent") and elem.SuperComponent is not None:
                continue
            result.append(elem)
        except Exception:
            continue
    return result


def _prompt_scope():
    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = CAPTION
    dlg.MainContent = u"Выбрать линии для подбора диаметра трубы"
    dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Выбрать", u"Выберите линии для подбора диаметра трубы")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Обработать все элементы на активном виде")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, u"Обработать все элементы в модели")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink4, u"Настройки")
    return dlg.Show()


def _get_numeric(param, fallback=0.0):
    if param is None:
        return fallback
    try:
        return param.AsInteger()
    except Exception:
        try:
            return param.AsDouble()
        except Exception:
            return fallback


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    conduit_types = _get_conduit_size_types(doc)
    if not conduit_types:
        TaskDialog.Show(CAPTION, u"Не найдены типоразмеры труб.")
        return

    stored = _read_settings(doc)
    conduit_types = _apply_saved_percent(conduit_types, stored)

    selection_ids = uidoc.Selection.GetElementIds()
    if selection_ids:
        elems = []
        for eid in selection_ids:
            el = doc.GetElement(eid)
            if el.LookupParameter(PARAM_LAYING) is not None:
                elems.append(el)
        if not elems:
            TaskDialog.Show(CAPTION, u"Выберите элементы, содержащие параметр <Способ прокладки>")
            return
    else:
        choice = _prompt_scope()
        if choice == TaskDialogCommandLinkId.CommandLink1:
            elems = _pick_elements(uidoc)
            if not elems:
                return
        elif choice == TaskDialogCommandLinkId.CommandLink2:
            elems = _collect_family_instances(doc, True)
            if not elems:
                TaskDialog.Show(CAPTION, u"На активном виде отсутствуют элементы с параметром <Способ прокладки>")
                return
        elif choice == TaskDialogCommandLinkId.CommandLink3:
            elems = _collect_family_instances(doc, False)
            if not elems:
                TaskDialog.Show(CAPTION, u"В модели отсутствуют элементы с параметром <Способ прокладки>")
                return
        elif choice == TaskDialogCommandLinkId.CommandLink4:
            payload = _show_settings(conduit_types)
            if payload is not None:
                _write_settings(doc, payload)
            return
        else:
            return

    updated = 0
    no_diameter = []
    bad_separator = []
    fallback_used = []

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for el in elems:
            try:
                veins = int(_get_numeric(el.LookupParameter(PARAM_VEINS), 0))
                section = float(_get_numeric(el.LookupParameter(PARAM_SECTION), 0.0))
                mark = el.LookupParameter(PARAM_MARK).AsString() if el.LookupParameter(PARAM_MARK) else ""
                laying_param = el.LookupParameter(PARAM_LAYING)
                laying = laying_param.AsString() if laying_param else ""
                if not laying:
                    continue
                diameter, used_fallback = find_cable_diameter(mark, veins, section, None)
                if diameter == 0.0:
                    no_diameter.append(str(el.Id))
                    continue
                if used_fallback:
                    fallback_used.append(str(el.Id))
                new_text, had_unmatched, replaced = update_laying_method_text(laying, diameter, conduit_types)
                if not replaced:
                    no_diameter.append(str(el.Id))
                    continue
                laying_param.Set(new_text)
                updated += 1
                if has_invalid_comma_separator(laying):
                    bad_separator.append(str(el.Id))
                if had_unmatched:
                    no_diameter.append(str(el.Id))
            except Exception:
                continue
        t.Commit()
    finally:
        t.Dispose()

    if no_diameter:
        content = u"Диаметры подобраны для {0} кабелей\nДля следующих линий диаметр не подобран:\n{1}".format(
            updated, "; ".join(no_diameter)
        )
    elif bad_separator:
        content = (
            u"Диаметры подобраны для {0} кабелей\n"
            u"Для следующих линий диаметр не подобран, исправьте разделитель между способами прокладки на точку с запятой:\n{1}"
        ).format(updated, "; ".join(bad_separator))
    else:
        content = u"Диаметры подобраны для {0} кабелей".format(updated)

    if fallback_used:
        content += u"\nСледующие элементы не найдены в каталоге производителя, диаметры кабелей приняты усреднённые:\n{}".format(
            "; ".join(fallback_used)
        )

    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = u"Подбор диаметров труб завершен"
    dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg.MainContent = content
    dlg.Show()


if __name__ == "__main__":
    main()
