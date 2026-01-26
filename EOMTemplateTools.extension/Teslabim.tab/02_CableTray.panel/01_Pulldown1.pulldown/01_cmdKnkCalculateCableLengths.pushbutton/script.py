# -*- coding: utf-8 -*-

import json

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    AnnotationSymbol,
    BuiltInCategory,
    BuiltInParameter,
    CableTray,
    Conduit,
    ElementId,
    FilteredElementCollector,
    StorageType,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem  # noqa: E402
from Autodesk.Revit.DB.ExtensibleStorage import (  # noqa: E402
    AccessLevel,
    Entity,
    Schema,
    SchemaBuilder,
)
from Autodesk.Revit.UI import (  # noqa: E402
    TaskDialog,
    TaskDialogCommandLinkId,
    TaskDialogCommonButtons,
    TaskDialogResult,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList  # noqa: E402

from unibim import knk_core  # noqa: E402
from unibim.cable_length_utils import summarize_lengths  # noqa: E402
from unibim.cable_param_utils import get_cable_param_names  # noqa: E402


TITLE = u"Рассчитать длины кабелей"

SCHEMA_GUID = "a46b718b-2f69-473b-8f4f-de0e4137593c"
SCHEMA_NAME = "TslSettings_KnkCalculateCableLengths"
FIELD_NAME = "JSON"

PARAM_SCHEMA_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
PARAM_SCHEMA_FIELD = "Param_Names_Storage_list"

DEFAULT_SETTINGS = {
    "IsDiameterConduit": False,
    "ReserveElectricalEquipment": 0.0,
    "ReserveElectricalDevise": 0.0,
    "CableTrayLaying": u"лоток",
    "IsChangeElectricalCircuit": False,
}


class _FamilySelectionByElectricalSystemFilter(ISelectionFilter):
    def AllowElement(self, element):
        fam = element if hasattr(element, "MEPModel") else None
        if fam is not None and fam.MEPModel:
            try:
                systems = list(fam.MEPModel.GetElectricalSystems())
            except Exception:
                systems = []
            if systems:
                return True
        name = element.Name or ""
        if u"TSL_2D автоматический выключатель_ВРУ" in name:
            return True
        if u"TSL_2D автоматический выключатель_Щит" in name:
            return True
        return False

    def AllowReference(self, reference, position):
        return False


def _get_project_info(doc):
    return (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ProjectInformation)
        .WhereElementIsNotElementType()
        .FirstElement()
    )


def _get_or_create_schema():
    schema = Schema.Lookup(Guid(SCHEMA_GUID))
    if schema:
        return schema
    builder = SchemaBuilder(Guid(SCHEMA_GUID))
    builder.SetSchemaName(SCHEMA_NAME)
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    builder.AddSimpleField(FIELD_NAME, str)
    return builder.Finish()


def _read_settings(doc):
    schema = Schema.Lookup(Guid(SCHEMA_GUID))
    if not schema:
        return DEFAULT_SETTINGS.copy()
    project_info = _get_project_info(doc)
    entity = project_info.GetEntity(schema)
    if not entity.IsValid():
        return DEFAULT_SETTINGS.copy()
    field = schema.GetField(FIELD_NAME)
    json_text = entity.Get[str](field)
    if not json_text:
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(json_text)
    except Exception:
        return DEFAULT_SETTINGS.copy()
    for key, value in DEFAULT_SETTINGS.items():
        data.setdefault(key, value)
    return data


def _write_settings(doc, settings):
    schema = _get_or_create_schema()
    field = schema.GetField(FIELD_NAME)
    project_info = _get_project_info(doc)
    entity = Entity(schema)
    entity.Set(field, json.dumps(settings, ensure_ascii=False))
    project_info.SetEntity(entity)


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


def _show_settings_dialog(settings):
    components = [
        forms.Label(u"Настройки"),
        forms.CheckBox("IsDiameterConduit", u"Учитывать диаметр гофры", default=settings["IsDiameterConduit"]),
        forms.CheckBox("IsChangeElectricalCircuit", u"Изменять номера цепей", default=settings["IsChangeElectricalCircuit"]),
        forms.Label(u"Запас на оборудование (%)"),
        forms.TextBox("ReserveElectricalEquipment", default=str(settings["ReserveElectricalEquipment"])),
        forms.Label(u"Запас на устройства (%)"),
        forms.TextBox("ReserveElectricalDevise", default=str(settings["ReserveElectricalDevise"])),
        forms.Label(u"Кабельная трасса"),
        forms.TextBox("CableTrayLaying", default=settings["CableTrayLaying"]),
        forms.Separator(),
        forms.Button(u"OK"),
    ]
    form = forms.FlexForm(TITLE, components)
    form.show()
    if not form.values:
        return None
    try:
        settings["IsDiameterConduit"] = bool(form.values.get("IsDiameterConduit"))
        settings["IsChangeElectricalCircuit"] = bool(form.values.get("IsChangeElectricalCircuit"))
        settings["ReserveElectricalEquipment"] = float(str(form.values.get("ReserveElectricalEquipment")).replace(",", "."))
        settings["ReserveElectricalDevise"] = float(str(form.values.get("ReserveElectricalDevise")).replace(",", "."))
        settings["CableTrayLaying"] = form.values.get("CableTrayLaying") or u"лоток"
    except Exception:
        forms.alert(u"Некорректные значения в настройках.", title=TITLE, warn_icon=True)
        return None
    return settings


def _collect_path_edges(doc):
    edges = []
    for el in FilteredElementCollector(doc).OfClass(Conduit).ToElements():
        try:
            conns = list(el.ConnectorManager.Connectors)
        except Exception:
            conns = []
        if len(conns) >= 2:
            edges.append((_xyz_to_tuple(conns[0].Origin), _xyz_to_tuple(conns[1].Origin), el.Id.IntegerValue))
    for el in FilteredElementCollector(doc).OfClass(CableTray).ToElements():
        try:
            conns = list(el.ConnectorManager.Connectors)
        except Exception:
            conns = []
        if len(conns) >= 2:
            edges.append((_xyz_to_tuple(conns[0].Origin), _xyz_to_tuple(conns[1].Origin), el.Id.IntegerValue))
    for bic in (BuiltInCategory.OST_ConduitFitting, BuiltInCategory.OST_CableTrayFitting):
        for el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements():
            try:
                conns = list(el.MEPModel.ConnectorManager.Connectors) if hasattr(el, "MEPModel") else list(el.ConnectorManager.Connectors)
            except Exception:
                conns = []
            if len(conns) >= 2:
                for i in range(len(conns)):
                    for j in range(i + 1, len(conns)):
                        edges.append((_xyz_to_tuple(conns[i].Origin), _xyz_to_tuple(conns[j].Origin), el.Id.IntegerValue))
    return edges


def _xyz_to_tuple(pt):
    return (float(pt.X), float(pt.Y), float(pt.Z))


def _set_param_value(param, value):
    if param is None:
        return False
    try:
        if param.StorageType == StorageType.Double:
            param.Set(float(value))
            return True
        if param.StorageType == StorageType.Integer:
            param.Set(int(value))
            return True
        param.Set(str(value))
        return True
    except Exception:
        return False


def _get_selected_systems(doc, uidoc, all_systems):
    sel_ids = uidoc.Selection.GetElementIds()
    if not sel_ids or sel_ids.Count == 0:
        return []
    by_name = {s.Name: s for s in all_systems}
    picked = []
    for eid in sel_ids:
        elem = doc.GetElement(eid)
        if isinstance(elem, ElectricalSystem):
            picked.append(elem)
            continue
        if isinstance(elem, AnnotationSymbol):
            param = elem.LookupParameter(u"Номер цепи")
            if param:
                name = param.AsString()
                if name in by_name:
                    picked.append(by_name[name])
            continue
        if hasattr(elem, "MEPModel") and elem.MEPModel:
            try:
                systems = list(elem.MEPModel.GetElectricalSystems())
            except Exception:
                systems = []
            picked.extend(systems)
    uniq = {}
    for s in picked:
        try:
            uniq[int(s.Id.IntegerValue)] = s
        except Exception:
            uniq[s] = s
    return list(uniq.values())


def _show_mode_dialog():
    dlg = TaskDialog(TITLE)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Обработать все элементы",
        u"Будет рассчитана длина для всех электрических цепей в модели.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Выбрать элементы",
        u"Будет рассчитана длина для выбранных цепей.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink3,
        u"Настройки",
        u"Настройки расчёта длин кабелей",
    )
    return dlg.Show()


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    all_systems = list(FilteredElementCollector(doc).OfClass(ElectricalSystem).ToElements())
    if not all_systems:
        forms.alert(u"В данном файле отсутствуют электрические цепи.", title=TITLE, warn_icon=True)
        return

    settings = _read_settings(doc)

    selected = _get_selected_systems(doc, uidoc, all_systems)
    if not selected:
        choice = _show_mode_dialog()
        if choice == TaskDialogResult.Cancel:
            return
        if choice == TaskDialogCommandLinkId.CommandLink3:
            settings = _show_settings_dialog(settings)
            if settings is None:
                return
            _write_settings(doc, settings)
            choice = _show_mode_dialog()
            if choice == TaskDialogResult.Cancel:
                return
        if choice == TaskDialogCommandLinkId.CommandLink2:
            try:
                refs = uidoc.Selection.PickObjects(
                    ObjectType.Element,
                    _FamilySelectionByElectricalSystemFilter(),
                    u"Выберите элементы электрической цепи.",
                )
            except Exception:
                return
            uidoc.Selection.SetElementIds([r.ElementId for r in refs])
            selected = _get_selected_systems(doc, uidoc, all_systems)
        else:
            selected = all_systems

    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, PARAM_SCHEMA_GUID, PARAM_SCHEMA_FIELD)
    param_names = get_cable_param_names(settings_list)

    edges = _collect_path_edges(doc)
    graph = knk_core.build_graph(edges)
    edge_elements = {eid: doc.GetElement(ElementId(eid)) for (_, _, eid) in edges}

    total_systems = 0
    total_length_ft = 0.0
    total_remote_ft = 0.0

    with revit.Transaction(TITLE):
        for system in selected:
            base = system.BaseEquipment
            if base is None:
                continue
            try:
                base_pt = base.Location.Point
            except Exception:
                base_pt = None
            if base_pt is None:
                continue

            lengths = []
            used_edge_ids = set()
            for elem in system.Elements:
                if elem.Id == base.Id:
                    continue
                try:
                    pt = elem.Location.Point
                except Exception:
                    pt = None
                if pt is None:
                    continue
                length, used = knk_core.shortest_path(graph, _xyz_to_tuple(base_pt), _xyz_to_tuple(pt))
                if length == 0.0:
                    try:
                        length = base_pt.DistanceTo(pt)
                    except Exception:
                        length = 0.0
                if length > 0.0:
                    lengths.append(length)
                used_edge_ids.update(used or [])

            total_len, max_len = summarize_lengths(lengths)
            if total_len == 0.0 and max_len == 0.0:
                continue

            reserve_eq = settings.get("ReserveElectricalEquipment", 0.0) / 100.0
            reserve_dev = settings.get("ReserveElectricalDevise", 0.0) / 100.0
            cable_length = total_len * (1.0 + reserve_eq)
            cable_length_remote = max_len * (1.0 + reserve_eq + reserve_dev)
            cable_length_adjusted = cable_length_remote

            param_len = system.LookupParameter(param_names["CableLength"])
            _set_param_value(param_len, cable_length)
            param_remote = system.LookupParameter(param_names["CableLengthToRemoteDevice"])
            _set_param_value(param_remote, cable_length_remote)
            param_adj = system.LookupParameter(param_names["CableLengthAdjusted"])
            _set_param_value(param_adj, cable_length_adjusted)

            if used_edge_ids:
                laying = settings.get("CableTrayLaying", u"лоток")
                used_tray = False
                for eid in used_edge_ids:
                    el = edge_elements.get(eid)
                    if isinstance(el, CableTray):
                        used_tray = True
                        break
                param_laying = system.LookupParameter(param_names["CableLayingMethod"])
                _set_param_value(param_laying, laying if used_tray else u"труба")

            total_systems += 1
            total_length_ft += cable_length
            total_remote_ft += cable_length_remote

    forms.alert(
        u"Готово.\n"
        u"Цепей обработано: {0}\n"
        u"Суммарная длина (м): {1:.2f}\n"
        u"Макс. длина (м): {2:.2f}".format(
            total_systems,
            total_length_ft * 0.3048,
            total_remote_ft * 0.3048,
        ),
        title=TITLE,
    )


if __name__ == "__main__":
    main()
