# -*- coding: utf-8 -*-

from pyrevit import revit

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    AnnotationSymbol,
    BuiltInCategory,
    BuiltInParameter,
    ElementId,
    ElementTypeGroup,
    FamilyInstance,
    FilteredElementCollector,
    HorizontalTextAlignment,
    TextNote,
    TextNoteOptions,
    TextNoteType,
    Transaction,
    UnitTypeId,
    UnitUtils,
    VerticalTextAlignment,
)
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.panel_info_utils import build_param_names, count_module_stats  # noqa: E402


CAPTION = u"Информация о щите/панели"

PANEL_NAMES = [
    u"TSL_Панель распределительная",
    u"TSL_Щит распределительный",
]

FAMILY_NAMES_EQUIPMENTS = [
    u"GA_SHM_2D автоматический выключатель_ВРУ",
    u"GA_SHM_2D автоматический выключатель_Щит",
    u"GA_SHM_Вводной автомат для щитов",
    u"GA_SHM_Любой автомат для схем",
    u"GA_SHM_Резервный автомат для ВРУ",
    u"GA_SHM_Резервный автомат для щитов",
    u"TSL_2D автоматический выключатель_ВРУ",
    u"TSL_2D автоматический выключатель_Щит",
    u"TSL_Вводной автомат для щитов",
    u"TSL_Любой автомат для схем",
    u"TSL_Резервный автомат для ВРУ",
    u"TSL_Резервный автомат для щитов",
]

PARAM_PANEL_NAME = u"Имя панели"
PARAM_ACCESSORY = u"Принадлежность щиту"
PARAM_MODULES = u"Кол-во модулей"
PARAM_HEIGHT = u"Высота (мм)"
PARAM_DEPTH = u"Глубина (мм)"
PARAM_WIDTH = u"Ширина (мм)"

EXT_SCHEMA_PARAM_GUID = "44bf8d44-4a4a-4fde-ada8-cd7d802648c4"
EXT_SCHEMA_PARAM_FIELD = "Param_Names_Storage_list"
EXT_SCHEMA_VOLUME_GUID = "be501520-4a57-4ad3-a4df-6f11afe6e007"
EXT_SCHEMA_VOLUME_FIELD = "VolumeCapacityNKU_FieldName"


class _PanelFilter(ISelectionFilter):
    def AllowElement(self, element):
        try:
            return element.Name in PANEL_NAMES
        except Exception:
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


def _pick_panel(uidoc, doc):
    sel_ids = uidoc.Selection.GetElementIds()
    for eid in sel_ids:
        elem = doc.GetElement(eid)
        if elem and elem.Name in PANEL_NAMES:
            return elem
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, _PanelFilter(), u"Выберите щит/панель на схеме")
    except Exception:
        return None
    return doc.GetElement(ref.ElementId)


def _get_panel_name(element):
    try:
        param = element.LookupParameter(PARAM_PANEL_NAME)
        return param.AsString() if param else None
    except Exception:
        return None


def _missing_parameters(element, required):
    existing = []
    try:
        existing = [p.Definition.Name for p in element.Parameters]
    except Exception:
        existing = []
    missing = [name for name in required if name not in existing]
    return missing


def _collect_equipment_symbols(doc, panel_name):
    elems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_GenericAnnotation)
        .WhereElementIsNotElementType()
        .OfClass(AnnotationSymbol)
        .ToElements()
    )
    filtered = []
    for elem in elems:
        try:
            param = elem.LookupParameter(PARAM_ACCESSORY)
            if param and param.AsString() == panel_name:
                filtered.append(elem)
        except Exception:
            continue
    filtered.sort(key=lambda a: a.Symbol.Family.Name if a.Symbol and a.Symbol.Family else "")
    return filtered


def _collect_panel_instances(doc, panel_name):
    elems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ElectricalEquipment)
        .WhereElementIsNotElementType()
        .OfClass(FamilyInstance)
        .ToElements()
    )
    result = []
    for elem in elems:
        try:
            param = elem.get_Parameter(BuiltInParameter(-1140078))
            if param and param.AsString() == panel_name:
                result.append(elem)
        except Exception:
            continue
    return result


def _get_param_as_int(element, name):
    try:
        param = element.LookupParameter(name)
        return param.AsInteger() if param else 0
    except Exception:
        return 0


def _get_param_as_double_mm(element, name):
    try:
        param = element.LookupParameter(name)
        if not param:
            return 0.0
        return UnitUtils.ConvertFromInternalUnits(param.AsDouble(), UnitTypeId.Millimeters)
    except Exception:
        return 0.0


def _get_param_as_string(element, name):
    try:
        param = element.LookupParameter(name)
        return param.AsString() if param else None
    except Exception:
        return None


def _build_equipments(equipments, is_modular):
    result = []
    device_without_width = False
    for eq in equipments:
        name = eq.Name
        family_name = ""
        try:
            family_name = eq.Symbol.Family.Name
        except Exception:
            family_name = ""
        if name not in FAMILY_NAMES_EQUIPMENTS and "_ANY_" not in family_name:
            continue
        count_modules = _get_param_as_int(eq, PARAM_MODULES)
        width_mm = _get_param_as_double_mm(eq, PARAM_WIDTH)
        height_mm = _get_param_as_double_mm(eq, PARAM_HEIGHT)
        depth_mm = _get_param_as_double_mm(eq, PARAM_DEPTH)
        if count_modules == 0 and width_mm == 0.0:
            if is_modular:
                count_modules = 6
                width_mm = 108.0
            else:
                count_modules = 3
                width_mm = 54.0
            device_without_width = True
        elif count_modules > 0 and width_mm == 0.0:
            width_mm = 18.0 * count_modules
        result.append(
            {
                "CountModules": count_modules,
                "Width": width_mm,
                "Height": height_mm,
                "Depth": depth_mm,
                "Accessory": _get_param_as_string(eq, PARAM_ACCESSORY),
            }
        )
    result.sort(key=lambda x: (x["Height"], x["Width"], x["Depth"]))
    return result, device_without_width


def _find_text_type_id(doc):
    types = (
        FilteredElementCollector(doc)
        .OfClass(TextNoteType)
        .WhereElementIsElementType()
        .ToElements()
    )
    for t in types:
        if t.Name == "TSL_2.5":
            return t.Id
    return doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType)


def _insert_text(doc, point, text):
    type_id = _find_text_type_id(doc)
    opts = TextNoteOptions(type_id)
    opts.HorizontalAlignment = HorizontalTextAlignment.Left
    opts.VerticalAlignment = VerticalTextAlignment.Bottom
    TextNote.Create(doc, doc.ActiveView.Id, point, text, opts)


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    panel = _pick_panel(uidoc, doc)
    if panel is None:
        return

    try:
        uidoc.Selection.SetElementIds(List[ElementId]([panel.Id]))
    except Exception:
        pass

    panel_name = _get_panel_name(panel)
    if not panel_name:
        TaskDialog.Show(CAPTION, u"Не заполнен параметр «{}».".format(PARAM_PANEL_NAME))
        return

    project_info = _get_project_info(doc)
    _read_storage_list(project_info, EXT_SCHEMA_VOLUME_GUID, EXT_SCHEMA_VOLUME_FIELD)
    param_settings = _read_storage_list(project_info, EXT_SCHEMA_PARAM_GUID, EXT_SCHEMA_PARAM_FIELD)
    param_names = build_param_names(param_settings)

    panel_instances = _collect_panel_instances(doc, panel_name)
    if len(panel_instances) > 1:
        TaskDialog.Show(
            CAPTION,
            u"У щита/панели есть дубликат на плане этажа или 3D виде!\n{}".format(
                u"; ".join(str(i.Id) for i in panel_instances)
            ),
        )
        return

    is_modular = u"Панель" in panel.Name

    equipments = _collect_equipment_symbols(doc, panel_name)
    missing_report = u""
    last_name = None
    for eq in equipments:
        eq_name = eq.Name
        if eq_name == last_name:
            continue
        last_name = eq_name
        required = [
            PARAM_ACCESSORY,
            param_names["Units"],
            param_names["Manufacturer"],
            param_names["TypeMark"],
            PARAM_MODULES,
            PARAM_HEIGHT,
            PARAM_DEPTH,
            PARAM_WIDTH,
        ]
        missing = _missing_parameters(eq, required)
        if missing:
            try:
                fam_name = eq.Symbol.Family.Name
            except Exception:
                fam_name = eq_name
            missing_report += u"{}: {}\n".format(fam_name, u"; ".join(missing))

    if missing_report:
        TaskDialog.Show(
            CAPTION,
            u"Для корректной работы обновите семейства. Отсутствуют следующие параметры:\n{}".format(missing_report),
        )
        return

    equip_data, device_without_width = _build_equipments(equipments, is_modular)
    module_counts = [e["CountModules"] for e in equip_data if e["Accessory"] == panel_name]
    stats = count_module_stats(module_counts)

    text = ""
    if panel_instances:
        base_panel = panel_instances[0]
        systems = base_panel.MEPModel.GetElectricalSystems() if base_panel.MEPModel else None
        bad_names = []
        if systems:
            for system in systems:
                try:
                    if not system.CircuitNumber or panel_name not in system.CircuitNumber or system.BaseEquipment.Id != base_panel.Id:
                        bad_names.append(system.Name)
                except Exception:
                    continue
        text = u"\nНомер питающей цепи: " + u"; ".join(sorted(bad_names))
        try:
            if base_panel.Space:
                room_number = base_panel.Space.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
                room_name = base_panel.Space.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
                text += u"\nНомер помещения: {}".format(room_number or u"")
                text += u"\nИмя помещения: {}".format(room_name or u"")
        except Exception:
            pass

    if stats["all_modules"] > 0:
        text += u"\n\nЗанято модулей = {}".format(stats["all_modules"])
        if stats["count1p"]:
            text += u"\n1 модульных аппаратов = {}".format(stats["count1p"])
        if stats["count2p"]:
            text += u"\n2 модульных аппаратов = {}".format(stats["count2p"])
        if stats["count3p"]:
            text += u"\n3 модульных аппаратов = {}".format(stats["count3p"])
        if stats["count4p"]:
            text += u"\n4 модульных аппаратов = {}".format(stats["count4p"])
        if stats["count5p"]:
            text += u"\n5 модульных аппаратов = {}".format(stats["count5p"])
        if stats["count6p"]:
            text += u"\n6 модульных аппаратов = {}".format(stats["count6p"])
        if stats["count7p"]:
            text += u"\n7 модульных аппаратов = {}".format(stats["count7p"])
        if stats["count8p"]:
            text += u"\n8 модульных аппаратов = {}".format(stats["count8p"])
        if stats["count9p"]:
            text += u"\n9 модульных аппаратов = {}".format(stats["count9p"])
        if stats["count10p"]:
            text += u"\n10 модульных аппаратов = {}".format(stats["count10p"])
        if stats["count11p"]:
            text += u"\n11 модульных аппаратов = {}".format(stats["count11p"])
        if stats["count12p"]:
            text += u"\n12 модульных аппаратов = {}".format(stats["count12p"])
        if stats["count0p"]:
            text += u"\n\nНемодульных аппаратов = {}".format(stats["count0p"])
    else:
        text += u"\n\nК данному щиту не привязан ни один аппарат!"

    if device_without_width:
        _ = u"Примечание!\nВ панели присутствуют приборы с нулевыми значениями ширины и количества модулей."

    if not text.strip():
        TaskDialog.Show(
            CAPTION,
            u"В щите/панели нет приборов!\n\nВозможная причина: не указана принадлежность для оборудования к выбранной панели.",
        )
        return

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        point = uidoc.Selection.PickPoint(u"Укажите точку куда вставить текст.")
        full_text = u"Содержимое щита/панели \"{}\"\n{}".format(panel_name, text)
        _insert_text(doc, point, full_text)
        t.Commit()
    finally:
        t.Dispose()


if __name__ == "__main__":
    main()
