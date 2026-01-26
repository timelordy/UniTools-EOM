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
from Autodesk.Revit.DB.ExtensibleStorage import Schema  # noqa: E402
from Autodesk.Revit.UI import TaskDialog  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402
from System import Guid  # noqa: E402
from System.Collections.Generic import IList, List  # noqa: E402

from unibim.load_collection_utils import compute_load_collection  # noqa: E402


CAPTION = u"Собрать нагрузки"

TABLE_NAMES = [
    u"TSL_Таблица_Расчетная для схемы",
    u"TSL_Таблица_Расчетная для щитов",
]

PARAM_PY = "Py"
PARAM_PP = "Pp"
PARAM_KC = "Kc"
PARAM_COS = "Cosf"
PARAM_IP = "Ip"
PARAM_SP = "Sp"
PARAM_U = u"Напряжение"
PARAM_ACCESSORY = u"Принадлежность щиту"

SCHEMA_VOLTAGE_GUID = "c96a640d-7cf1-47dd-bd1d-1a938122227f"
SCHEMA_SETTINGS_GUID = "c94ca2e5-771e-407d-9c09-f62feb4448b6"
FIELD_VOLTAGE = "Voltage_CR"
FIELD_SETTINGS = "Tesla_settings_list"


class _TableFilter(ISelectionFilter):
    def AllowElement(self, element):
        try:
            return element.Name in TABLE_NAMES
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
    value = None
    try:
        value = entity.Get[IList[str]](field)
    except Exception:
        try:
            value = entity.Get[List[str]](field)
        except Exception:
            try:
                value = entity.Get[str](field)
            except Exception:
                value = None
    if value is None:
        return []
    try:
        return list(value)
    except Exception:
        return [value]


def _get_voltage_kv(doc):
    proj_info = _get_project_info(doc)
    values = _read_storage_list(proj_info, SCHEMA_VOLTAGE_GUID, FIELD_VOLTAGE)
    if not values:
        return None, []
    voltage = None
    for item in values:
        if item == "380":
            voltage = 0.38
        elif item == "400":
            voltage = 0.4
    return voltage, values


def _get_round_value(doc):
    proj_info = _get_project_info(doc)
    values = _read_storage_list(proj_info, SCHEMA_SETTINGS_GUID, FIELD_SETTINGS)
    if "Round_value_ts" in values:
        idx = values.index("Round_value_ts")
        if idx + 1 < len(values):
            try:
                return int(values[idx + 1])
            except Exception:
                pass
    return 1


def _get_tables(doc, uidoc):
    tables = []
    sel_ids = uidoc.Selection.GetElementIds()
    if sel_ids:
        for eid in sel_ids:
            elem = doc.GetElement(eid)
            if elem and elem.Name in TABLE_NAMES:
                tables.append(elem)
    if tables:
        return tables
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, _TableFilter(), u"Выберите расчетные таблицы на схеме")
    except Exception:
        return []
    return [doc.GetElement(r) for r in refs]


def _warn_and_return(message):
    TaskDialog.Show(CAPTION, message)


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    tables = _get_tables(doc, uidoc)
    if not tables:
        _warn_and_return(u"Необходимо выбрать расчетные таблицы.")
        return

    try:
        uidoc.Selection.SetElementIds(List[ElementId]([t.Id for t in tables]))
    except Exception:
        pass

    voltage_kv, _voltage_values = _get_voltage_kv(doc)
    if not _voltage_values:
        _warn_and_return(
            u"В данном файле не сохранены настройки программы.\n"
            u"Нажмите кнопку «Настройки» на ленте «Teslabim»."
        )
        return

    py_list = []
    pp_list = []
    kc_list = []
    cos_list = []
    sp_list = []
    voltage_list = []

    for table in tables:
        if table.Name not in TABLE_NAMES:
            continue
        py_param = table.LookupParameter(PARAM_PY)
        pp_param = table.LookupParameter(PARAM_PP)
        kc_param = table.LookupParameter(PARAM_KC)
        cos_param = table.LookupParameter(PARAM_COS)
        sp_param = table.LookupParameter(PARAM_SP)
        u_param = table.LookupParameter(PARAM_U)

        if py_param:
            py_list.append(py_param.AsDouble())
        if pp_param:
            pp_list.append(pp_param.AsDouble())
        if sp_param:
            sp_list.append(sp_param.AsDouble())
        if kc_param:
            kc_val = kc_param.AsDouble()
            kc_list.append(kc_val)
            if kc_val <= 0.0:
                _warn_and_return(u"Kc=\"{}\" <= 0".format(kc_val))
                return
        if cos_param:
            cos_val = cos_param.AsDouble()
            cos_list.append(cos_val)
            if cos_val <= 0.0:
                _warn_and_return(u"Cosf <= 0")
                return
        if u_param:
            voltage_list.append(u_param.AsDouble())

    if not py_list:
        _warn_and_return(u"Не найден параметр <Py>")
        return
    if not kc_list:
        _warn_and_return(u"Не найден параметр <Kc>")
        return
    if not cos_list:
        _warn_and_return(u"Не найден параметр <Cosf>")
        return
    if not sp_list:
        _warn_and_return(u"Не найден параметр <Sp>")
        return
    if not voltage_list:
        _warn_and_return(u"Не найден параметр <{}>".format(PARAM_U))
        return

    voltage_unique = sorted(set(voltage_list))
    if len(voltage_unique) > 1:
        values = [str(v) for v in voltage_unique]
        text = u"В выборе {} разных напряжения: {}".format(len(values), u"; ".join(values) + u";")
        _warn_and_return(text)
        return

    voltage_param = voltage_unique[0] / 1000.0
    if voltage_kv is None or voltage_param != voltage_kv:
        _warn_and_return(
            u"В выбранных элементах значение параметра «Напряжение» отличается от настроек.\n"
            u"В настройках установлено {} В".format(voltage_kv * 1000.0 if voltage_kv else 0)
        )
        return

    py_sum = sum(py_list)
    pp_sum = sum(pp_list)
    sp_sum = sum(sp_list)
    round_value = _get_round_value(doc)

    try:
        result = compute_load_collection(py_sum, pp_sum, sp_sum, voltage_kv, round_value)
    except Exception:
        _warn_and_return(u"Проверьте значения Py, Pp, Sp и напряжение.")
        return

    kc_exist = result["kc_exist"]

    form = forms.FlexForm(
        CAPTION,
        [
            forms.Label(u"Py (кВт): {}".format(round(py_sum, round_value))),
            forms.Label(u"Kc (существ.): {}".format(round(kc_exist, 4))),
            forms.Label(u"Pp (кВт): {}".format(round(pp_sum, round_value))),
            forms.Label(u"Cosf: {}".format(round(result["cosf"], 2))),
            forms.Label(u"Ip (А): {}".format(round(result["ip"], round_value))),
            forms.Label(u"Sp (кВА): {}".format(round(sp_sum, round_value))),
            forms.Separator(),
            forms.CheckBox("use_kc", u"Использовать Kc расч."),
            forms.TextBox("kc_calc", str(round(kc_exist, 4))),
            forms.Button(u"Записать"),
        ],
    )
    if not form.show():
        return

    kc_override = None
    if form.values.get("use_kc"):
        try:
            kc_override = float(form.values.get("kc_calc"))
        except Exception:
            forms.alert(u"Неверный формат Kc", title=CAPTION)
            return

    try:
        result = compute_load_collection(py_sum, pp_sum, sp_sum, voltage_kv, round_value, kc_override=kc_override)
    except Exception:
        _warn_and_return(u"Проверьте значение Kc.")
        return

    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, u"Выберите расчетную таблицу или аппарат для записи результата")
    except Exception:
        return

    target = doc.GetElement(ref.ElementId)
    if target is None:
        return

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        for name in [PARAM_PY, PARAM_KC, PARAM_PP, PARAM_COS, PARAM_IP, PARAM_SP, PARAM_U, PARAM_ACCESSORY]:
            param = target.LookupParameter(name)
            if param is None:
                continue
            if name == PARAM_U:
                param.Set(voltage_unique[0])
            elif name == PARAM_PY:
                param.Set(round(py_sum, round_value))
            elif name == PARAM_KC:
                param.Set(round(result["kc_used"], 2))
            elif name == PARAM_PP:
                param.Set(round(result["pp"], round_value))
            elif name == PARAM_COS:
                param.Set(round(result["cosf"], 2))
            elif name == PARAM_IP:
                param.Set(round(result["ip"], round_value))
            elif name == PARAM_SP:
                param.Set(round(result["sp"], round_value))
        t.Commit()
    finally:
        t.Dispose()

    TaskDialog.Show(CAPTION, u"Выполнение завершено!")


if __name__ == "__main__":
    main()
