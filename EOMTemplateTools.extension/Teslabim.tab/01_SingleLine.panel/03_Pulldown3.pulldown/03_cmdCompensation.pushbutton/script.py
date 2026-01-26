# -*- coding: utf-8 -*-

import math

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    ElementId,
    ElementTransformUtils,
    ElementTypeGroup,
    FilteredElementCollector,
    LocationPoint,
    TextNote,
    TextNoteOptions,
    Transaction,
    XYZ,
)
from Autodesk.Revit.UI import (  # noqa: E402
    TaskDialog,
    TaskDialogCommandLinkId,
    TaskDialogCommonButtons,
    TaskDialogIcon,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402

from unibim.compensation_utils import compute_compensation, compute_table_values  # noqa: E402


CAPTION = u"Компенсация реактивной мощности"
TABLE_NAME_PART = u"TSL_Таблица_Расчетная для"

PARAM_P = "Pp"
PARAM_COS = "Cosf"
PARAM_IP = "Ip"
PARAM_SP = "Sp"
PARAM_U = u"Напряжение"


class _TableFilter(ISelectionFilter):
    def AllowElement(self, element):
        try:
            return TABLE_NAME_PART in element.Name
        except Exception:
            return False

    def AllowReference(self, reference, position):
        return False


def _pick_table(uidoc):
    try:
        ref = uidoc.Selection.PickObject(ObjectType.Element, _TableFilter(), u"Выберите расчетную таблицу")
    except Exception:
        return None
    return uidoc.Document.GetElement(ref)


def _get_table_from_selection(doc, uidoc):
    sel_ids = uidoc.Selection.GetElementIds()
    if not sel_ids:
        return None
    elem = doc.GetElement(list(sel_ids)[0])
    if elem and TABLE_NAME_PART in elem.Name:
        return elem
    return "INVALID"


def _get_location_point(element):
    loc = element.Location
    if isinstance(loc, LocationPoint):
        return loc.Point
    bbox = element.get_BoundingBox(None)
    if bbox:
        return (bbox.Min + bbox.Max) * 0.5
    return XYZ(0, 0, 0)


def _copy_table(doc, table_elem, new_point):
    origin = _get_location_point(table_elem)
    move = new_point - origin
    new_id = ElementTransformUtils.CopyElement(doc, table_elem.Id, move)[0]
    doc.Regenerate()
    return doc.GetElement(new_id)


def _write_table(doc, table_elem, cos_new):
    p_param = table_elem.LookupParameter(PARAM_P)
    u_param = table_elem.LookupParameter(PARAM_U)
    ip_param = table_elem.LookupParameter(PARAM_IP)
    cos_param = table_elem.LookupParameter(PARAM_COS)
    sp_param = table_elem.LookupParameter(PARAM_SP)
    if not (p_param and u_param and ip_param and cos_param and sp_param):
        return
    p_val = p_param.AsDouble()
    u_val = u_param.AsDouble()
    ip_val, sp_val = compute_table_values(p_val, u_val, cos_new)
    cos_param.Set(cos_new)
    ip_param.Set(ip_val)
    sp_param.Set(sp_val)


def _build_calc_text(P, tg1, tg2, qr, q_text, cos2, aukrm, step):
    if q_text and q_text != u"Не требуется":
        if aukrm:
            install = u"АУКРМ мощностью {0}кВАр, ступень регулирования {1}кВАр".format(q_text, step)
        else:
            install = u"УКРМ мощностью {0}кВАр".format(q_text)
    else:
        install = u""
    return (
        u"Расчет компенсации реактивной мощности:\n"
        u"Qc = Pp x (tgφ1-tgφ2) = {P} x ({tg1}-{tg2}) = {qr} кВАр"
        u"\nгде Pp - расчетная активная мощность, кВт;"
        u"\n    Qc - необходимая мощность реактивной мощности, кВАр;"
        u"\n    tgφ1 - tgφ потребителя до установки компенсирующих устройств;"
        u"\n    tgφ2 - tgφ потребителя после установки компенсирующих устройств."
        u"\nДля достижения необходимого коэффициента реактивной мощности {cos2}"
        u"\nнеобходима установка {install}"
    ).format(P=P, tg1=tg1, tg2=tg2, qr=qr, cos2=cos2, install=install)


def _prompt_output():
    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = CAPTION
    dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Вывести расчет")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Вывести обновленную расчетную таблицу")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, u"Вывести расчет и таблицу")
    return dlg.Show()


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    table = _get_table_from_selection(doc, uidoc)
    if table == "INVALID":
        TaskDialog.Show(
            CAPTION,
            u"Выбранный элемент не является TSL_Таблица_Расчетная для щитов или TSL_Таблица_Расчетная для схемы",
        )
        return
    if table is None:
        table = _pick_table(uidoc)
        if table is None:
            return
        if TABLE_NAME_PART not in table.Name:
            TaskDialog.Show(
                CAPTION,
                u"Выбранный элемент не является TSL_Таблица_Расчетная для щитов или TSL_Таблица_Расчетная для схемы",
            )
            return

    try:
        P = table.LookupParameter(PARAM_P).AsDouble()
        cos1 = table.LookupParameter(PARAM_COS).AsDouble()
    except Exception:
        return

    if P == 0.0:
        TaskDialog.Show(CAPTION, u"Параметр Pp должен быть больше 0")
        return
    if cos1 == 0.0 or cos1 > 1.0:
        TaskDialog.Show(CAPTION, u"Параметр Cosf должен быть больше 0 и не может быть больше 1")
        return

    default_cos2 = 0.9439
    form = forms.FlexForm(
        CAPTION,
        [
            forms.Label(u"Pp (кВт)"),
            forms.TextBox("P", str(P)),
            forms.Label(u"Cosφ1"),
            forms.TextBox("cos1", str(cos1)),
            forms.Label(u"Cosφ2 (цель)"),
            forms.TextBox("cos2", str(default_cos2)),
            forms.CheckBox("auk", u"АУКРМ (регулируемая установка)"),
            forms.Label(u"Шаг регулирования, кВАр"),
            forms.TextBox("step", "2.5"),
            forms.Separator(),
            forms.Button(u"Рассчитать"),
        ],
    )
    if not form.show():
        return
    try:
        P = float(form.values["P"])
        cos1 = float(form.values["cos1"])
        cos2 = float(form.values["cos2"])
        aukrm = bool(form.values.get("auk", False))
        step = float(form.values.get("step", 2.5))
    except Exception:
        forms.alert(u"Неверный формат чисел", title=CAPTION)
        return

    try:
        result = compute_compensation(P, cos1, cos2, aukrm, step)
    except Exception:
        TaskDialog.Show(CAPTION, u"Проверьте значения Pp и Cosφ")
        return

    if result.get("Error") == "STEP_MISMATCH":
        TaskDialog.Show(
            CAPTION,
            u"Скорректируйте шаг регулирования. Итоговая мощность должна делиться без остатка на шаг регулирования.",
        )
        return

    calc_text = _build_calc_text(
        P=P,
        tg1=result["Tg1"],
        tg2=result["Tg2"],
        qr=result["Qr"],
        q_text=result["Q"],
        cos2=cos2,
        aukrm=aukrm,
        step=step,
    )

    choice = _prompt_output()
    if choice == TaskDialogCommandLinkId.CommandLink1:
        t = Transaction(doc, CAPTION)
        try:
            t.Start()
            point = uidoc.Selection.PickPoint(u"Выберите точку вставки расчета")
            text_opts = TextNoteOptions(doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType))
            TextNote.Create(doc, doc.ActiveView.Id, point, calc_text, text_opts)
            t.Commit()
        finally:
            t.Dispose()
        return
    if choice == TaskDialogCommandLinkId.CommandLink2:
        t = Transaction(doc, CAPTION)
        try:
            t.Start()
            point = uidoc.Selection.PickPoint(u"Выберите точку вставки таблицы")
            new_table = _copy_table(doc, table, point)
            _write_table(doc, new_table, result["CosNew"])
            t.Commit()
        finally:
            t.Dispose()
        return
    if choice == TaskDialogCommandLinkId.CommandLink3:
        t = Transaction(doc, CAPTION)
        try:
            t.Start()
            point = uidoc.Selection.PickPoint(u"Выберите точку вставки расчета")
            text_opts = TextNoteOptions(doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType))
            TextNote.Create(doc, doc.ActiveView.Id, point, calc_text, text_opts)
            doc.Regenerate()
            point2 = uidoc.Selection.PickPoint(u"Выберите точку вставки таблицы")
            new_table = _copy_table(doc, table, point2)
            _write_table(doc, new_table, result["CosNew"])
            t.Commit()
        finally:
            t.Dispose()


if __name__ == "__main__":
    main()
