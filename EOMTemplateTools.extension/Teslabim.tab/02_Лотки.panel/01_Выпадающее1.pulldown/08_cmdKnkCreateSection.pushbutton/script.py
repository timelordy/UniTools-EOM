# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    Line,
    TextNote,
    TextNoteOptions,
    ElementTypeGroup,
    Group,
    Transaction,
    UnitUtils,
    UnitTypeId,
    XYZ,
)
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId, TaskDialogCommonButtons  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.knk_param_utils import get_knk_param_names  # noqa: E402
from unibim.knk_circuit_utils import parse_circuit_numbers  # noqa: E402
from unibim.knk_occupancy_utils import (  # noqa: E402
    compute_occupancy_percent,
    match_cable_db,
    parse_cable_db,
)


CAPTION = u"Создать сечение лотка"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"

GUIDSTR_MANUF_NAMES = "fc725aed-20ed-4d44-984c-522c476e3abc"
FIELD_MANUF_NAMES = "ManufNames_ManufacturerSelect_listCable"

GUIDSTR_CABLE_DB = "895e7aef-18fd-4e6c-b8f2-73af53f04aba"
FIELD_CABLE_DB = "Cable_ListDB_ManufacturerSelect_list"

DEFAULT_BUNDLE_PARAM = u"ADSK_Комплект"

KNS_OCCUPANCY_PARAM = u"TSL_КНС_Заполняемость лотка (%)"
KNS_VOLUME_PARAM = u"TSL_КНС_Объём горючей массы (л/км)"

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


def _get_section_group(doc, elem_id):
    groups = (
        FilteredElementCollector(doc, doc.ActiveView.Id)
        .OfClass(Group)
        .ToElements()
    )
    for grp in groups:
        if grp.Name and "TSL_КНК_" in grp.Name and str(elem_id) in grp.Name:
            return grp
    return None


def _origin_from_group(doc, group):
    try:
        ids = list(group.GetMemberIds())
        for gid in ids:
            elem = doc.GetElement(gid)
            if elem and elem.GetType().Name == "DetailLine":
                curve = elem.GeometryCurve
                if curve:
                    return curve.GetEndPoint(0)
    except Exception:
        return None
    return None


def _create_section(doc, elem, origin, height_mm, width_mm, occupancy, cables):
    scale = 10
    h = UnitUtils.ConvertToInternalUnits(height_mm, UnitTypeId.Millimeters) * scale
    w = UnitUtils.ConvertToInternalUnits(width_mm, UnitTypeId.Millimeters) * scale

    p0 = origin
    p1 = XYZ(p0.X, p0.Y + h, p0.Z)
    p2 = XYZ(p0.X + w, p0.Y, p0.Z)
    p3 = XYZ(p0.X + w, p0.Y + h, p0.Z)

    ids = []
    for line in (Line.CreateBound(p0, p1), Line.CreateBound(p0, p2), Line.CreateBound(p2, p3)):
        ids.append(doc.Create.NewDetailCurve(doc.ActiveView, line).Id)

    text_note_type = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)
    opts = TextNoteOptions(text_note_type)
    label = u"{0:.0f}×{1:.0f} ВхШ, {2}%".format(height_mm, width_mm, occupancy)
    ids.append(TextNote.Create(doc, doc.ActiveView.Id, p0, label, opts).Id)

    counts = {}
    for cable in cables:
        label_key = u"{0} {1}×{2}".format(
            cable.get("mark", ""),
            cable.get("count_of_veins", 0),
            cable.get("cross_section", 0.0),
        )
        circuit = cable.get("circuit_number", "")
        key = (circuit, label_key)
        counts[key] = counts.get(key, 0) + 1
    lines = []
    for (circuit, label_key), cnt in sorted(counts.items()):
        lines.append(u"{0}; {1} - {2} шт.".format(circuit, label_key, cnt))
    if lines:
        offset = UnitUtils.ConvertToInternalUnits(417.0, UnitTypeId.Millimeters) * scale
        p_text = XYZ(p0.X, p0.Y - offset, p0.Z)
        ids.append(TextNote.Create(doc, doc.ActiveView.Id, p_text, "\n".join(lines), opts).Id)

    group = doc.Create.NewGroup(List[ElementId](ids))
    group.GroupType.Name = u"TSL_КНК_М{0}_{1:.0f}x{2:.0f} ВхШ, {3}%_{4}".format(
        scale, height_mm, width_mm, occupancy, elem.Id.IntegerValue
    )


def _collect_elements(doc, uidoc, param_name, mode):
    elements = []
    if mode == "all":
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
    if mode == "pick":
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
    return []


def main():
    doc = revit.doc
    uidoc = revit.uidoc
    project_info = _get_project_info(doc)
    settings_list = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    knk_names = get_knk_param_names(settings_list)
    bundle_param_name = _get_bundle_param_name(settings_list)

    manuf_list = _read_storage_list(project_info, GUIDSTR_MANUF_NAMES, FIELD_MANUF_NAMES)
    if not manuf_list or (manuf_list[0] and u"нет производителя" in manuf_list[0]):
        forms.alert(
            u"Не выбран производитель кабельной продукции. Создать сечение невозможно.",
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

    dlg = TaskDialog(CAPTION)
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Создать сечение лотка",
        u"Создать/обновить сечение для выбранного элемента.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Обновить сечения у всех лотков",
        u"Обновить только существующие сечения (если нет группы, элемент будет пропущен).",
    )
    res = dlg.Show()
    if res == TaskDialogCommandLinkId.CommandLink1:
        mode = "pick"
    elif res == TaskDialogCommandLinkId.CommandLink2:
        mode = "all"
    else:
        return

    elements = _collect_elements(doc, uidoc, knk_names["KnkCircuitNumber"], mode)
    if not elements:
        forms.alert(u"Не найдены элементы КНК.", title=CAPTION)
        return

    errors = []
    skipped = []
    ok_count = 0

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for elem in elements:
            circuits = parse_circuit_numbers(
                (elem.LookupParameter(knk_names["KnkCircuitNumber"]).AsString() or "")
            )
            if not circuits:
                continue
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

            group = _get_section_group(doc, elem.Id.IntegerValue)
            origin = None
            if group is not None:
                origin = _origin_from_group(doc, group)
                doc.Delete(group.Id)
            if origin is None:
                if mode == "all":
                    skipped.append(str(elem.Id.IntegerValue))
                    continue
                try:
                    origin = uidoc.Selection.PickPoint(u"Укажите точку вставки сечения лотка")
                except Exception:
                    continue
            _create_section(doc, elem, origin, height_mm, width_mm, occupancy, elem_cables)
            ok_count += 1
        t.Commit()
    finally:
        t.Dispose()

    warn_lines = []
    if missing_circuits:
        warn_lines.append(u"Нет данных кабеля для цепей:\n{0}".format(
            "\n".join(sorted([c for c in missing_circuits if c]))
        ))
    if errors:
        warn_lines.append(u"Ошибки параметров/габаритов у элементов:\n{0}".format("\n".join(errors)))
    if skipped:
        warn_lines.append(u"Пропущены без существующего сечения:\n{0}".format("\n".join(skipped)))

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
