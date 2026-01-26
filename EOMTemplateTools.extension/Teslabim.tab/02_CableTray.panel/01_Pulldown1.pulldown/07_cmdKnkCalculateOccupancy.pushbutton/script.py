# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    FilteredElementCollector,
    Transaction,
    UnitUtils,
    UnitTypeId,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem  # noqa: F401,E402
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList  # noqa: E402

from unibim.knk_param_utils import get_knk_param_names  # noqa: E402
from unibim.knk_circuit_utils import parse_circuit_numbers  # noqa: E402
from unibim.knk_occupancy_utils import (  # noqa: E402
    compute_occupancy_percent,
    match_cable_db,
    parse_cable_db,
)


CAPTION = u"Рассчитать заполняемость лотков"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

GUIDSTR_MANUF_NAMES = "fc725aed-20ed-4d44-984c-522c476e3abc"
FIELD_MANUF_NAMES = "ManufNames_ManufacturerSelect_listCable"

GUIDSTR_CABLE_DB = "895e7aef-18fd-4e6c-b8f2-73af53f04aba"
FIELD_CABLE_DB = "Cable_ListDB_ManufacturerSelect_list"

DEFAULT_BUNDLE_PARAM = u"ADSK_Комплект"

KNS_OCCUPANCY_PARAM = u"TSL_КНС_Заполняемость лотка (%)"
KNS_VOLUME_PARAM = u"TSL_КНС_Объём горючей массы (л/км)"


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


def _read_storage_string(element, schema_guid, field_name):
    if element is None:
        return ""
    schema = Schema.Lookup(Guid(schema_guid))
    if schema is None:
        return ""
    field = schema.GetField(field_name)
    if field is None:
        return ""
    entity = element.GetEntity(schema)
    if not entity or not entity.IsValid():
        return ""
    try:
        return entity.Get[str](field)
    except Exception:
        return ""


def _get_project_info(doc):
    return (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ProjectInformation)
        .WhereElementIsNotElementType()
        .FirstElement()
    )


def _get_bundle_param_name(settings_list):
    if not settings_list:
        return DEFAULT_BUNDLE_PARAM
    for idx, key in enumerate(settings_list):
        if key == "Param_name_40_for_Param_Names_Storage" and idx + 1 < len(settings_list):
            return settings_list[idx + 1]
    return DEFAULT_BUNDLE_PARAM


def _get_int_param(elem, name, default=0):
    param = elem.LookupParameter(name)
    try:
        return param.AsInteger() if param is not None else default
    except Exception:
        return default


def _get_double_param(elem, name, default=0.0):
    param = elem.LookupParameter(name)
    try:
        return param.AsDouble() if param is not None else default
    except Exception:
        return default


def _collect_cable_groups(doc, bundle_param_name):
    cables = []
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
        circuit = ann.LookupParameter(u"Номер цепи")
        mark = ann.LookupParameter(u"Марка проводника")
        if circuit is None or mark is None:
            continue
        circuit_val = circuit.AsString()
        mark_val = mark.AsString()
        if not circuit_val or not mark_val:
            continue
        bundle = ""
        bundle_param = ann.LookupParameter(bundle_param_name)
        if bundle_param is not None:
            bundle = bundle_param.AsString() or ""

        count_beams = max(1, _get_int_param(ann, u"Количество лучей", 1))
        count_conductors = _get_int_param(ann, u"Количество проводников", 0)
        count_veins = _get_int_param(ann, u"Количество жил", 0)
        cross_section = _get_double_param(ann, u"Сечение проводника", 0.0)
        count_pe = _get_int_param(ann, u"Количество проводников PE", 0)
        cross_section_pe = _get_double_param(ann, u"Сечение проводника PE", 0.0)

        main_count = count_beams * (count_conductors if count_conductors > 0 else 1)
        for _ in range(max(1, main_count)):
            cables.append(
                {
                    "mark": mark_val,
                    "count_of_veins": count_veins,
                    "cross_section": cross_section,
                    "circuit_number": circuit_val,
                    "bundle": bundle,
                    "diameter": 0.0,
                    "weight": 0.0,
                    "volume": 0.0,
                }
            )
        for _ in range(max(0, count_pe)):
            cables.append(
                {
                    "mark": mark_val,
                    "count_of_veins": count_pe,
                    "cross_section": cross_section_pe,
                    "circuit_number": circuit_val,
                    "bundle": bundle,
                    "diameter": 0.0,
                    "weight": 0.0,
                    "volume": 0.0,
                }
            )
    return cables


def _attach_cable_db(cables, db_items):
    missing = set()
    for cable in cables:
        matched = match_cable_db(cable, db_items)
        if matched:
            cable["diameter"] = matched.get("diameter", 0.0)
            cable["weight"] = matched.get("weight", 0.0)
            cable["volume"] = matched.get("volume", 0.0)
        else:
            missing.add(cable.get("circuit_number") or "")
    return missing


def _get_tray_dims_mm(elem):
    height = 0.0
    width = 0.0
    if elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_CableTray):
        try:
            height = UnitUtils.ConvertFromInternalUnits(elem.Height, UnitTypeId.Millimeters)
            width = UnitUtils.ConvertFromInternalUnits(elem.Width, UnitTypeId.Millimeters)
        except Exception:
            return 0.0, 0.0
    else:
        params = list(elem.Parameters)
        height_param = None
        width_param = None
        for p in params:
            name = p.Definition.Name
            if "1_Высота" in name:
                height_param = p
            if "1_Ширина" in name:
                width_param = p
        if height_param is None:
            for p in params:
                if "Высота" in p.Definition.Name:
                    height_param = p
                    break
        if width_param is None:
            for p in params:
                if "Ширина" in p.Definition.Name:
                    width_param = p
                    break
        try:
            height = UnitUtils.ConvertFromInternalUnits(height_param.AsDouble(), UnitTypeId.Millimeters)
            width = UnitUtils.ConvertFromInternalUnits(width_param.AsDouble(), UnitTypeId.Millimeters)
        except Exception:
            return 0.0, 0.0
    return height, width


def _collect_knk_elements(doc, param_name):
    elements = []
    trays = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_CableTray)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    fittings = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_CableTrayFitting)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    for elem in list(trays) + list(fittings):
        param = elem.LookupParameter(param_name)
        if param is None:
            continue
        if (param.AsString() or "") == "":
            continue
        elements.append(elem)
    return elements


def main():
    doc = revit.doc

    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)
    bundle_param_name = _get_bundle_param_name(settings_list)

    manuf_list = _read_storage_list(project_info, GUIDSTR_MANUF_NAMES, FIELD_MANUF_NAMES)
    if not manuf_list or (manuf_list[0] and u"нет производителя" in manuf_list[0]):
        forms.alert(
            u"Не выбран производитель кабельной продукции. Рассчитать заполняемость лотков невозможно.",
            title=CAPTION,
        )
        return

    cable_db_raw = _read_storage_string(project_info, GUIDSTR_CABLE_DB, FIELD_CABLE_DB)
    if not cable_db_raw:
        forms.alert(
            u"Не найдены настройки базы кабелей. Откройте команду 'Подобрать кабели' и выберите производителя.",
            title=CAPTION,
        )
        return

    db_items = parse_cable_db(cable_db_raw)
    cables = _collect_cable_groups(doc, bundle_param_name)
    missing_circuits = _attach_cable_db(cables, db_items)

    elements = _collect_knk_elements(doc, knk_names["KnkCircuitNumber"])
    if not elements:
        forms.alert(u"Не найдены элементы КНК с номерами цепей.", title=CAPTION)
        return

    errors = []
    ok_count = 0

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for elem in elements:
            circuits = parse_circuit_numbers(
                (elem.LookupParameter(knk_names["KnkCircuitNumber"]).AsString() or "")
            )
            bundle_val = ""
            bundle_param = elem.LookupParameter(bundle_param_name)
            if bundle_param is not None:
                bundle_val = bundle_param.AsString() or ""

            elem_cables = [
                c for c in cables
                if c.get("circuit_number") in circuits
                and (not bundle_val or c.get("bundle") == bundle_val)
            ]

            height_mm, width_mm = _get_tray_dims_mm(elem)
            if height_mm <= 0 or width_mm <= 0:
                errors.append("id {0}".format(elem.Id.IntegerValue))
                continue

            diameters = [c.get("diameter", 0.0) for c in elem_cables if c.get("diameter", 0.0) > 0]
            occupancy = compute_occupancy_percent(diameters, height_mm, width_mm)
            volume = 0.0
            weight = 0.0
            if elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_CableTray):
                volume = sum(c.get("volume", 0.0) for c in elem_cables) / 1000.0
                weight = sum(c.get("weight", 0.0) for c in elem_cables) / 1000.0

            occ_param = elem.LookupParameter(knk_names["KnkCableTrayOccupancy"])
            if occ_param is not None:
                occ_param.Set(occupancy)
            kns_occ = elem.LookupParameter(KNS_OCCUPANCY_PARAM)
            if kns_occ is not None:
                kns_occ.Set(occupancy)
            vol_param = elem.LookupParameter(knk_names["KnkVolumeOfCombustibleMass"])
            if vol_param is not None:
                vol_param.Set(volume)
            kns_vol = elem.LookupParameter(KNS_VOLUME_PARAM)
            if kns_vol is not None:
                kns_vol.Set(volume)
            weight_param = elem.LookupParameter(knk_names["KnkWeightSectionMass"])
            if weight_param is not None:
                weight_param.Set(weight)

            ok_count += 1
        t.Commit()
    finally:
        t.Dispose()

    warn_lines = []
    if missing_circuits:
        warn_lines.append(u"Не найдены характеристики кабелей для цепей:\n{0}".format(
            "\n".join(sorted([c for c in missing_circuits if c]))
        ))
    if errors:
        warn_lines.append(u"Ошибки параметров/габаритов у элементов:\n{0}".format("\n".join(errors)))

    if warn_lines:
        TaskDialog.Show(
            CAPTION,
            u"Выполнение завершено!\nОшибок: {0} | Успешно: {1}\n\n{2}".format(
                len(errors), ok_count, "\n\n".join(warn_lines)
            ),
        )
    else:
        TaskDialog.Show(CAPTION, u"Выполнение завершено!\nУспешно: {0}".format(ok_count))


if __name__ == "__main__":
    main()
