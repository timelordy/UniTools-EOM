# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    TextNote,
    TextNoteType,
    Transaction,
)
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogCommandLinkId, TaskDialogIcon  # noqa: E402
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402

from unibim.tt_utils import compute_tt_results  # noqa: E402


NAME_FAMILY_COUNTER = u"TSL_ANY_Счётчик электроэнергии"
NAME_FAMILY_CURRENT_1 = u"TSL_Таблица_Расчетная для схемы"
NAME_FAMILY_CURRENT_2 = u"TSL_Таблица_Расчетная для щитов"
NAME_FAMILY_CURRENT_3 = u"TSL_Таблица_Фазировка"
NAME_FAMILY_RESULT = u"TSL_Таблица_Проверка коэффициентов трансформации"
NAME_FAMILY_TT = u"TSL_ANY_Трансформатор тока"

PARAM_PHASE_A = u"Ток фазы А"
PARAM_PHASE_B = u"Ток фазы В"
PARAM_PHASE_C = u"Ток фазы С"
PARAM_IP = u"Ip"
PARAM_ACCESSORY = u"Принадлежность щиту"

PARAM_ADSK_MARK = u"ADSK_Марка"
PARAM_ADSK_DESIGNATION = u"ADSK_Обозначение"
PARAM_ADSK_POWER = u"Полная мощность"
PARAM_WIRE_SECTION = u"Сечение проводника"
PARAM_WIRE_LENGTH = u"Длина проводника"
PARAM_ID_QFS = u"Id расчётных аппаратов"

CAPTION = u"Проверить трансформатор тока"


class _NameFilter(ISelectionFilter):
    def __init__(self, allowed_names):
        self._allowed = set(allowed_names)

    def AllowElement(self, element):
        try:
            return element.Name in self._allowed
        except Exception:
            return False

    def AllowReference(self, reference, position):
        return False


def _element_id_from_string(value):
    try:
        return ElementId(int(value))
    except Exception:
        try:
            return ElementId(long(value))  # noqa: F821
        except Exception:
            return None


def _get_current(element, mode):
    if element is None:
        return 0.0
    if element.Name == NAME_FAMILY_CURRENT_3:
        values = [
            element.LookupParameter(PARAM_PHASE_A).AsDouble(),
            element.LookupParameter(PARAM_PHASE_B).AsDouble(),
            element.LookupParameter(PARAM_PHASE_C).AsDouble(),
        ]
        values.sort()
        return values[-1] if mode == "max" else values[0]
    return element.LookupParameter(PARAM_IP).AsDouble()


def _format_tt_info(tt):
    if tt is None:
        return ""
    text = ""
    try:
        text = (tt.LookupParameter(PARAM_ACCESSORY).AsString() or "")
    except Exception:
        text = ""
    try:
        text = text + "\n" + (tt.LookupParameter(PARAM_ADSK_DESIGNATION).AsString() or "")
    except Exception:
        pass
    try:
        text = text + " " + (tt.LookupParameter(PARAM_ADSK_MARK).AsString() or "")
    except Exception:
        pass
    return text.strip()


def _parse_ratio(tt):
    mark = ""
    try:
        mark = tt.LookupParameter(PARAM_ADSK_MARK).AsString()
    except Exception:
        return 0.0, 0.0
    if not mark or "/" not in mark:
        return 0.0, 0.0
    parts = [p.strip() for p in mark.split("/") if p.strip()]
    if len(parts) < 2:
        return 0.0, 0.0
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return 0.0, 0.0


def _build_update_columns(tt, norm, max_el):
    col1 = _format_tt_info(tt)
    col2 = ""
    col3 = ""
    col4 = ""
    col5 = u"Не производится"
    col6 = ""
    col7 = u"Не производится"
    col8 = ""

    max_val = 0.0
    if max_el is not None:
        max_val = _get_current(max_el, "max")
        col2 = str(max_val)

    min_val = 0.0
    if norm is not None:
        min_val = _get_current(norm, "min")
        col3 = str(min_val)

    i1, i2 = _parse_ratio(tt)
    ratio = i1 / i2 if i2 else 0.0
    if i1 and i2:
        col4 = u"{}/{}={}".format(i1, i2, ratio)

    if col2 and col2 != "0" and ratio:
        try:
            num5 = round(float(col2) / ratio, 3)
            value = round(i2 * 0.4, 2)
            values = [round(num5, 3), round(value, 3), i2]
            values.sort()
            col5 = u"{}/{}={}А; {}>{}>{}".format(col2, round(ratio, 3), num5, values[2], values[1], values[0])
        except Exception:
            pass

    if ratio and col3:
        try:
            num7 = float(col3) / ratio
            if num7 > 0.1:
                col6 = u"{}/{}={}А; {}>0.1".format(col3, ratio, round(num7, 3), round(num7, 3))
            elif num7 < 0.1:
                col6 = u"{}/{}={}А; {}<0.1".format(col3, ratio, round(num7, 3), round(num7, 3))
        except Exception:
            pass

    if col2 and col2 != "0" and i1:
        try:
            if i1 * 1.2 >= float(col2):
                col7 = u"{}x1,2={}А > {}А\n".format(i1, i1 * 1.2, col2)
            else:
                col7 = u"{}x1,2={}А < {}А\n".format(i1, i1 * 1.2, col2)
            col7 += col6
        except Exception:
            pass

    if i1 and min_val:
        if i1 > min_val:
            col8 = u"{} > {}\nВыполняется".format(i1, min_val)
        else:
            col8 = u"{} > {}\nНе выполняется".format(min_val, i1)

    return [col1, col2, col3, col4, col5, col6, col7, col8]


def _build_new_columns(tt, results, current1, current2, current_min_line, i1, i2):
    col1 = _format_tt_info(tt)
    col2 = str(current2) if current2 else ""
    col3 = str(current_min_line) if current_min_line else ""
    ratio = i1 / i2 if i2 else 0.0
    col4 = u"{}/{}={}".format(i1, i2, ratio) if i1 and i2 else ""
    col5 = u"Не производится"
    col6 = u""
    col7 = u"Не производится"
    col8 = u""

    if current2 and ratio:
        values = [results["CurrentMax2"], results["Current40"], i2]
        values.sort()
        col5 = u"{}/{}={}А; {}>{}>{}".format(
            col2,
            round(ratio, 3),
            results["CurrentMax2"],
            values[2],
            values[1],
            values[0],
        )

    if current1 and ratio:
        if results["CurrentMin2"] > 0.1:
            col6 = u"{}/{}={}А; {}>0.1".format(
                current1,
                ratio,
                results["CurrentMin2"],
                results["CurrentMin2"],
            )
        elif results["CurrentMin2"] < 0.1:
            col6 = u"{}/{}={}А; {}<0.1".format(
                current1,
                ratio,
                results["CurrentMin2"],
                results["CurrentMin2"],
            )

    if current2:
        if results["CurrentTT20"] >= current2:
            col7 = u"{}x1,2={}А > {}А".format(i1, results["CurrentTT20"], current2)
        else:
            col7 = u"{}x1,2={}А < {}А".format(i1, results["CurrentTT20"], current2)
        col7 = col7 + "\n" + col6

    if i1 and current1:
        if i1 > current1:
            col8 = u"{} > {}\nВыполняется".format(i1, current1)
        else:
            col8 = u"{} > {}\nНе выполняется".format(current1, i1)

    return [col1, col2, col3, col4, col5, col6, col7, col8]


def _write_columns(element, columns):
    for idx, value in enumerate(columns, start=1):
        try:
            param = element.LookupParameter(u"Столбец {}".format(idx))
            if param:
                param.Set(value)
        except Exception:
            pass


def _update_result(doc, result_element, tt, norm, max_el, counter):
    columns = _build_update_columns(tt, norm, max_el)
    _write_columns(result_element, columns)


def _pick_with_filter(uidoc, filter_obj, prompt):
    ref = uidoc.Selection.PickObject(ObjectType.Element, filter_obj, prompt)
    return uidoc.Document.GetElement(ref)


def _find_result_symbol(doc):
    symbols = (
        FilteredElementCollector(doc)
        .WhereElementIsElementType()
        .OfCategory(BuiltInCategory.OST_GenericAnnotation)
        .ToElements()
    )
    for symbol in symbols:
        if symbol.Name == NAME_FAMILY_RESULT:
            return symbol
    return None


def _write_result(doc, uidoc, tt, norm, max_el, counter, columns):
    symbol = _find_result_symbol(doc)
    if symbol is None:
        TaskDialog.Show(CAPTION, u"Загрузите в модель семейство {}".format(NAME_FAMILY_RESULT))
        return False
    t = Transaction(doc, u"Вывод проверки ТТ")
    try:
        t.Start()
        point = uidoc.Selection.PickPoint(u"Выберите точку вставки расчета")
        inst = doc.Create.NewFamilyInstance(point, symbol, doc.ActiveView)
        doc.Regenerate()
        _write_columns(inst, columns)
        id_param = inst.LookupParameter(PARAM_ID_QFS)
        if id_param:
            ids = []
            ids.append(str(tt.Id) if tt else "0")
            ids.append(str(norm.Id) if norm else "0")
            ids.append(str(max_el.Id) if max_el else "0")
            ids.append(str(counter.Id) if counter else "0")
            id_param.Set("; ".join(ids))
        doc.Regenerate()
        t.Commit()
        return inst
    finally:
        t.Dispose()


def _update_reports(doc, uidoc, elements):
    updated = []
    failed = []
    t = Transaction(doc, u"Вывод проверки ТТ")
    try:
        t.Start()
        for element in elements:
            try:
                id_param = element.LookupParameter(PARAM_ID_QFS)
                if id_param is None or not id_param.AsString():
                    failed.append(element)
                    continue
                ids = [part.strip() for part in id_param.AsString().split(";")]
                tt = norm = max_el = counter = None
                if len(ids) > 0:
                    eid = _element_id_from_string(ids[0])
                    tt = doc.GetElement(eid) if eid else None
                if len(ids) > 1:
                    eid = _element_id_from_string(ids[1])
                    norm = doc.GetElement(eid) if eid else None
                if len(ids) > 2:
                    eid = _element_id_from_string(ids[2])
                    max_el = doc.GetElement(eid) if eid else None
                if len(ids) > 3:
                    eid = _element_id_from_string(ids[3])
                    counter = doc.GetElement(eid) if eid else None
                _update_result(doc, element, tt, norm, max_el, counter)
                updated.append(element)
            except Exception:
                failed.append(element)
        t.Commit()
    finally:
        t.Dispose()
    return updated, failed


def _prompt_mode():
    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = CAPTION
    dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Проверить ТТ", u"Будет произведена проверка выбранного ТТ")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Обновить все отчёты о проверке ТТ", u"Все ранее выполняемые отчёты будут обновлены")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, u"Обновить выбранные отчёты о проверке ТТ", u"Выбранные отчёты будут обновлены")
    return dlg.Show()


def _prompt_pick_current(uidoc, prompt):
    return _pick_with_filter(uidoc, _NameFilter([NAME_FAMILY_CURRENT_1, NAME_FAMILY_CURRENT_2, NAME_FAMILY_CURRENT_3]), prompt)


def _prompt_pick_tt(uidoc):
    return _pick_with_filter(uidoc, _NameFilter([NAME_FAMILY_TT]), u"Выберите трансформатор тока")


def _prompt_pick_counter(uidoc):
    return _pick_with_filter(uidoc, _NameFilter([NAME_FAMILY_COUNTER]), u"Выберите счётчик")


def _check_tt(doc, uidoc):
    try:
        tt = _prompt_pick_tt(uidoc)
    except Exception:
        return

    mark = tt.LookupParameter(PARAM_ADSK_MARK)
    power_param = tt.LookupParameter(PARAM_ADSK_POWER)
    if mark is None or power_param is None:
        TaskDialog.Show(CAPTION, u"Обновите семейство {}".format(NAME_FAMILY_TT))
        return

    i1, i2 = _parse_ratio(tt)
    if not i1 or not i2:
        TaskDialog.Show(
            CAPTION,
            u"Заполните параметр ADSK_Марка в следующей форме:\nПервичный номинальный ток, А / Вторичный номинальный ток, А"
        )
        return

    tt_power = power_param.AsDouble()

    try:
        norm = _prompt_pick_current(uidoc, u"Выберите расчётный ток в нормальном режиме")
    except Exception:
        return
    current1 = _get_current(norm, "min")
    current_min_line = current1

    current2 = 0.0
    max_el = None
    dlg_max = TaskDialog(CAPTION)
    dlg_max.MainInstruction = CAPTION
    dlg_max.MainContent = u"Выберите расчётный ток в максимальном режиме"
    dlg_max.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg_max.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg_max.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Выбрать", u"Выберите расчётный ток в максимальном режиме")
    dlg_max.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Схема не резервируемая", u"Проверка будет только по нормальному режиму")
    choice_max = dlg_max.Show()
    if choice_max == TaskDialogCommandLinkId.CommandLink1:
        try:
            max_el = _prompt_pick_current(uidoc, u"Выберите расчётный ток в максимальном режиме")
            current2 = _get_current(max_el, "max")
        except Exception:
            max_el = None
            current2 = 0.0
    elif choice_max == TaskDialogCommandLinkId.CommandLink3 or choice_max == TaskDialogCommandLinkId.CommandLink2:
        pass
    else:
        return

    counter = None
    counter_length = 0.0
    counter_power = 0.0
    dlg_counter = TaskDialog(CAPTION)
    dlg_counter.MainInstruction = CAPTION
    dlg_counter.MainContent = u"Выберите счётчик"
    dlg_counter.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg_counter.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg_counter.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Выбрать", u"Выберите семейство {}".format(NAME_FAMILY_COUNTER))
    dlg_counter.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Не выбирать", u"Проверка по расчётной вторичной нагрузке не будет выполнена")
    choice_counter = dlg_counter.Show()
    if choice_counter == TaskDialogCommandLinkId.CommandLink1:
        try:
            counter = _prompt_pick_counter(uidoc)
            counter_length = counter.LookupParameter(PARAM_WIRE_LENGTH).AsDouble()
            counter_power = counter.LookupParameter(PARAM_ADSK_POWER).AsDouble()
        except Exception:
            TaskDialog.Show(CAPTION, u"Обновите семейство {}".format(NAME_FAMILY_COUNTER))
            return
    elif choice_counter != TaskDialogCommandLinkId.CommandLink2:
        return

    try:
        wire_section = tt.LookupParameter(PARAM_WIRE_SECTION).AsDouble()
    except Exception:
        wire_section = 2.5

    form = forms.FlexForm(
        CAPTION,
        [
            forms.Label(u"I1, А"),
            forms.TextBox("i1", str(i1)),
            forms.Label(u"I2, А"),
            forms.TextBox("i2", str(i2)),
            forms.Label(u"Ток норм., А"),
            forms.TextBox("current1", str(current1)),
            forms.Label(u"Ток макс., А"),
            forms.TextBox("current2", str(current2)),
            forms.Label(u"Ток мин. линии, А"),
            forms.TextBox("current_min_line", str(current_min_line)),
            forms.Label(u"Полная мощность ТТ"),
            forms.TextBox("tt_power", str(tt_power)),
            forms.Label(u"Длина проводника"),
            forms.TextBox("counter_length", str(counter_length)),
            forms.Label(u"Полная мощность счётчика"),
            forms.TextBox("counter_power", str(counter_power)),
            forms.Label(u"Сечение проводника"),
            forms.TextBox("wire_section", str(wire_section)),
            forms.Label(u"Rконт, Ом"),
            forms.TextBox("zcontacts", "0.015"),
            forms.Separator(),
            forms.Button(u"Рассчитать"),
        ],
    )
    if not form.show():
        return

    try:
        i1 = float(form.values["i1"])
        i2 = float(form.values["i2"])
        current1 = float(form.values["current1"])
        current2 = float(form.values["current2"])
        current_min_line = float(form.values["current_min_line"])
        tt_power = float(form.values["tt_power"])
        counter_length = float(form.values["counter_length"])
        counter_power = float(form.values["counter_power"])
        wire_section = float(form.values["wire_section"])
        zcontacts = float(form.values["zcontacts"])
    except Exception:
        forms.alert(u"Неверный формат чисел", title=CAPTION)
        return

    results = compute_tt_results(
        i1=i1,
        i2=i2,
        current1=current1,
        current2=current2,
        current_min_line=current_min_line,
        zcontacts=zcontacts,
        tt_power=tt_power,
        counter_length=counter_length,
        counter_power=counter_power,
        wire_section=wire_section,
    )

    summary = (
        u"I1/I2={:.3f}\n"
        u"Перегрузка: {}\n"
        u"40% I2: {}\n"
        u"Нормальный режим: {}\n"
        u"Мин. ток 0.1А: {}\n"
        u"Мин. ток 5%: {}\n"
        u"Вторичная нагрузка: {}"
    ).format(
        results["Ratio"] if results["Ratio"] else 0.0,
        results["CheckPeregruzka"],
        results["Check40"],
        results["CheckNorm"],
        results["CheckMin"],
        results["Check5"],
        results["CheckZ"],
    )

    dlg_write = TaskDialog(CAPTION)
    dlg_write.MainInstruction = CAPTION
    dlg_write.MainContent = summary
    dlg_write.MainIcon = TaskDialogIcon.TaskDialogIconInformation
    dlg_write.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg_write.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Записать результат")
    dlg_write.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Не записывать")
    choice_write = dlg_write.Show()
    if choice_write != TaskDialogCommandLinkId.CommandLink1:
        return

    columns = _build_new_columns(tt, results, current1, current2, current_min_line, i1, i2)
    inst = _write_result(doc, uidoc, tt, norm, max_el, counter, columns)
    if not inst:
        return

    if results["CheckZ"] != u"Не производится":
        dlg_z = TaskDialog(CAPTION)
        dlg_z.MainInstruction = CAPTION
        dlg_z.MainIcon = TaskDialogIcon.TaskDialogIconInformation
        dlg_z.CommonButtons = TaskDialogCommonButtons.Cancel
        dlg_z.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Вывести проверку вторичной нагрузки ТТ")
        dlg_z.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Не выводить результат проверки вторичной нагрузки ТТ")
        choice_z = dlg_z.Show()
        if choice_z == TaskDialogCommandLinkId.CommandLink1:
            section_val = wire_section or 2.5
            text = (
                u"В соответствии с п.6.4.1, п.6.4.2 ГОСТ 7746-2015 и п.6.7 РМ-2559, "
                u"проводится проверка расчётной вторичной нагрузки трансформатора тока:\n"
                u"Zнагр.ном. ⩾ Zнагр ⩾ Zmin,\n"
                u"где Zнагр.ном. - номинальное сопротивления сети для ТТ;\n"
                u"    Zнагр - расчётная вторичная нагрузка ТТ;\n"
                u"    Zmin - минимальный предел вторичной нагрузки ТТ\n"
                u"Расчётная вторичная нагрузка равна:\n"
                u"Zнагр = Rприб. +  Rпров. + Rконт. = {z_counter} + {z_prov} + {z_cont} = {z_sum} Ом,\n"
                u"где Rприб.= {z_counter} Ом - сопротивление подключенных приборов вторичной обмотке ТТ;\n"
                u"    Rпров. = L/(YxS) = {length}/(57x{section}) = {z_prov} Ом - сопротивление проводов от ТТ до счётчика;\n"
                u"    Rконт. = {z_cont} Ом - сопротивление контактных соединений.\n"
            ).format(
                z_counter=results["ZCounter"],
                z_prov=results["ZProvodov"],
                z_cont=zcontacts,
                z_sum=results["Znagruzka"],
                length=counter_length,
                section=section_val,
            )
            values = {
                u"Zнагр.ном.": results["TTZ"],
                u"Zнагр.": results["Znagruzka"],
                u"Zmin.": results["TTZ"] * 0.25,
            }
            ordered = sorted(values.items(), key=lambda item: item[1])
            text += u"{0} ⩾ {1} ⩾ {2};\n{3} ⩾ {4} ⩾ {5}\n".format(
                ordered[2][0], ordered[1][0], ordered[0][0], ordered[2][1], ordered[1][1], ordered[0][1]
            )
            if ordered[1][0] == u"Zнагр.":
                text += u"Вывод: Измерительные ТТ работают в заданном классе точности"
            else:
                text += u"Вывод: Измерительные ТТ не работают в заданном классе точности"
            point = uidoc.Selection.PickPoint(u"Выберите точку вставки")
            t = Transaction(doc, u"Вывод проверки ТТ")
            try:
                t.Start()
                text_type = (
                    FilteredElementCollector(doc)
                    .OfClass(TextNoteType)
                    .WhereElementIsElementType()
                    .FirstElement()
                )
                type_id = text_type.Id if text_type else ElementId.InvalidElementId
                TextNote.Create(doc, doc.ActiveView.Id, point, text, type_id)
                t.Commit()
            finally:
                t.Dispose()


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    choice = _prompt_mode()
    if choice == TaskDialogCommandLinkId.CommandLink1:
        _check_tt(doc, uidoc)
        return
    if choice == TaskDialogCommandLinkId.CommandLink2:
        elements = (
            FilteredElementCollector(doc)
            .WhereElementIsNotElementType()
            .OfCategory(BuiltInCategory.OST_GenericAnnotation)
            .ToElements()
        )
        result_elems = [e for e in elements if e.Name == NAME_FAMILY_RESULT]
        if not result_elems:
            TaskDialog.Show(
                CAPTION,
                u"В модели отсутствуют семейства {} с записанными Id элементов".format(NAME_FAMILY_RESULT)
            )
            return
        updated, failed = _update_reports(doc, uidoc, result_elems)
    elif choice == TaskDialogCommandLinkId.CommandLink3:
        try:
            refs = uidoc.Selection.PickObjects(ObjectType.Element, _NameFilter([NAME_FAMILY_RESULT]), u"Выберите отчёты ТТ")
        except Exception:
            return
        result_elems = [doc.GetElement(r) for r in refs]
        if not result_elems:
            return
        updated, failed = _update_reports(doc, uidoc, result_elems)
    else:
        return

    if updated:
        message = u"Результаты обновлены в {} отчёте(-ах)".format(len(updated))
        if failed:
            message += u"\n\nВ следующих элементах результаты проверки не обновлены:\n{}".format(
                "; ".join(str(e.Id) for e in failed)
            )
        TaskDialog.Show(CAPTION, message)
    elif failed:
        TaskDialog.Show(
            CAPTION,
            u"В следующих элементах результаты проверки не обновлены:\n{}".format(
                "; ".join(str(e.Id) for e in failed)
            )
        )


if __name__ == "__main__":
    main()
