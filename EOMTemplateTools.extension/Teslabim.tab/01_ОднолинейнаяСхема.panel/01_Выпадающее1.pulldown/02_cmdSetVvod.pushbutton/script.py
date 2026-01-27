# -*- coding: utf-8 -*-

from pyrevit import revit

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    ElementId,
    FilteredElementCollector,
    FamilyInstance,
    Transaction,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId, TaskDialogCommonButtons
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

from unibim import setvvod_utils


TITLE = u"Обновить информацию о вводе"
NAME_VVOD = u"TSL_Вводной автомат для щитов"
NAME_PANEL = u"TSL_Щит распределительный"
NAME_AV_VRU = u"TSL_2D автоматический выключатель_ВРУ"
NAME_AV_SHIELD = u"TSL_2D автоматический выключатель_Щит"


class FilterFI(ISelectionFilter):
    def AllowElement(self, elem):
        try:
            name = elem.Name
        except Exception:
            name = ""
        return name in (NAME_VVOD, NAME_PANEL)

    def AllowReference(self, reference, position):
        return False


def _param_as_string(elem, name, default=""):
    try:
        p = elem.LookupParameter(name)
        if p is None:
            return default
        return p.AsString() or default
    except Exception:
        return default


def _param_as_int(elem, name, default=0):
    try:
        p = elem.LookupParameter(name)
        if p is None:
            return default
        return p.AsInteger()
    except Exception:
        return default


def _param_as_double(elem, name, default=0.0):
    try:
        p = elem.LookupParameter(name)
        if p is None:
            return default
        return p.AsDouble()
    except Exception:
        return default


class ElementWrapper(object):
    def __init__(self, element):
        self.element = element
        self.IntId = element.Id.IntegerValue
        self.markakabelya = _param_as_string(element, u"Марка проводника")
        self.kolvozhil = _param_as_int(element, u"Количество жил")
        self.kolvoluchey = _param_as_int(element, u"Количество лучей")
        self.kolvoprovodnikov = _param_as_int(element, u"Количество проводников")
        self.kolvoprovodnikovPE = _param_as_int(element, u"Количество проводников PE")
        self.sechenie = _param_as_double(element, u"Сечение проводника")
        self.secheniePE = _param_as_double(element, u"Сечение проводника PE")
        self.dlina = _param_as_double(element, u"Длина проводника")
        self.numberCircuit = _param_as_string(element, u"Номер цепи")
        self.naimenovanie = _param_as_string(element, u"Наименование электроприёмника")
        self.prinadlezhnost_AV = _param_as_string(element, u"Принадлежность щиту")
        self.kolvo_pol_AV = element.LookupParameter(u"3-фазный аппарат")


def _find_kabel(wrapper):
    return setvvod_utils.format_cable(
        mark=wrapper.markakabelya,
        kolvo_zhil=wrapper.kolvozhil,
        kolvo_luchey=wrapper.kolvoluchey,
        kolvo_provodnikov=wrapper.kolvoprovodnikov,
        kolvo_provodnikov_pe=wrapper.kolvoprovodnikovPE,
        sechenie=wrapper.sechenie,
        sechenie_pe=wrapper.secheniePE,
        dlina=wrapper.dlina,
    )


def _get_incoming_systems(doc, base_equipment):
    systems = []
    for sys in FilteredElementCollector(doc).OfClass(ElectricalSystem):
        try:
            if sys.BaseEquipment and sys.BaseEquipment.Id == base_equipment.Id:
                systems.append(sys)
        except Exception:
            continue
    return systems


def _get_poles_number(wrapper, system):
    if wrapper and wrapper.kolvo_pol_AV is not None:
        try:
            return wrapper.kolvo_pol_AV.AsInteger()
        except Exception:
            return 0
    try:
        return 1 if system.PolesNumber == 3 else 0
    except Exception:
        return 0


doc = revit.doc
uidoc = revit.uidoc
selection = uidoc.Selection

selected_ids = list(selection.GetElementIds())
targets = []
processed = []
not_processed = []
duplicates = []

if selected_ids:
    for eid in selected_ids:
        elem = doc.GetElement(eid)
        if isinstance(elem, FamilyInstance) and elem.Name in (NAME_VVOD, NAME_PANEL):
            targets.append(elem)
    if not targets:
        TaskDialog.Show(TITLE, u"Семейства \"{0}\" не выбраны".format(NAME_VVOD))
        raise SystemExit
else:
    dlg = TaskDialog(TITLE)
    dlg.TitleAutoPrefix = True
    dlg.AllowCancellation = True
    dlg.MainContent = u"Выберите элементы для которых синхронизировать ввод"
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Обработать все элементы")
    dlg.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Выбрать элементы вручную")
    res = dlg.Show()
    if res == TaskDialogCommandLinkId.CommandLink1:
        targets = [
            i for i in FilteredElementCollector(doc).OfClass(FamilyInstance)
            if i.Name == NAME_VVOD
        ]
    elif res == TaskDialogCommandLinkId.CommandLink2:
        try:
            refs = selection.PickObjects(ObjectType.Element, FilterFI())
        except Exception:
            raise SystemExit
        for r in refs:
            elem = doc.GetElement(r.ElementId)
            if isinstance(elem, FamilyInstance):
                targets.append(elem)
    if not targets:
        raise SystemExit

wrappers_vru = [
    ElementWrapper(e) for e in FilteredElementCollector(doc).OfClass(FamilyInstance)
    if e.Name == NAME_AV_VRU
]
wrappers_shield = [
    ElementWrapper(e) for e in FilteredElementCollector(doc).OfClass(FamilyInstance)
    if e.Name == NAME_AV_SHIELD
]
all_wrappers = list(wrappers_vru) + list(wrappers_shield)

td = TaskDialog(TITLE)
td.MainInstruction = u"Записать характеристики кабеля?"
td.CommonButtons = TaskDialogCommonButtons.Cancel
td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, u"Нет", u"Записать только источник и номер цепи питания")
td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, u"Да", u"Дополнительно записать марку, количество жил, сечение и длину")
choice = td.Show()
if choice == TaskDialogCommandLinkId.Cancel:
    raise SystemExit

with Transaction(doc, u"Переименовать ввод") as t:
    t.Start()
    for target in targets:
        p_text = target.LookupParameter(u"Ввод питания текст")
        p_panel = target.LookupParameter(u"Принадлежность щиту")
        p_3phase = target.LookupParameter(u"3-фазный аппарат")

        panel_name = p_panel.AsString() if p_panel else ""
        if not panel_name:
            not_processed.append(target)
            continue

        panel_elem = None
        for e in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType():
            try:
                pn = e.get_Parameter(BuiltInParameter(-1140078))
                if pn and pn.AsString() == panel_name:
                    panel_elem = e
                    break
            except Exception:
                continue

        if panel_elem is None:
            not_processed.append(target)
            continue

        systems = _get_incoming_systems(doc, panel_elem)
        text = ""
        for system in systems:
            matches = [w for w in all_wrappers if w.numberCircuit == system.Name]
            if len(matches) > 1:
                distinct_nums = sorted(set([w.numberCircuit for w in matches]))
                distinct_cables = sorted(set([_find_kabel(w) for w in matches]))
                if choice == TaskDialogCommandLinkId.CommandLink1 and len(distinct_nums) > 1:
                    duplicates.append((target, matches))
                    continue
                if choice == TaskDialogCommandLinkId.CommandLink2 and (len(distinct_nums) > 1 or len(distinct_cables) > 1):
                    duplicates.append((target, matches))
                    continue
            if len(matches) == 0:
                not_processed.append(target)
                continue
            wrapper = matches[0]

            try:
                src_name = system.get_Parameter(BuiltInParameter(-1140104)).AsString()
            except Exception:
                src_name = ""
            if not src_name:
                not_processed.append(target)
                continue
            try:
                circuit_num = system.get_Parameter(BuiltInParameter(-1140103)).AsString()
            except Exception:
                circuit_num = ""
            cable_text = ""
            if wrapper is not None and choice == TaskDialogCommandLinkId.CommandLink2:
                cable_text = u"; {0}м".format(_find_kabel(wrapper))
            text += u"Ввод питания от {0}\n{1}{2}".format(src_name, circuit_num, cable_text)
            try:
                poles = _get_poles_number(wrapper, system)
                if poles in (0, 1) and system.CircuitNumber == circuit_num:
                    p_3phase.Set(poles)
            except Exception:
                pass
            if target not in processed:
                processed.append(target)
            if target in not_processed:
                not_processed.remove(target)

        if text and p_text:
            p_text.Set(text)

    # fallback processing for remaining
    for target in list(not_processed):
        p_panelname = target.LookupParameter(u"Имя панели")
        p_phase = target.LookupParameter(u"Обозначение фаз")
        p_text = target.LookupParameter(u"Ввод питания текст")
        p_panel = target.LookupParameter(u"Принадлежность щиту")
        p_3phase = target.LookupParameter(u"3-фазный аппарат")

        try:
            if target.Name == NAME_VVOD and (p_panel is None or not p_panel.AsString()):
                continue
        except Exception:
            pass

        panel_name = p_panel.AsString() if p_panel else ""
        matches = [w for w in all_wrappers if panel_name and w.naimenovanie and panel_name in w.naimenovanie]
        if len(matches) > 1:
            distinct_nums = sorted(set([w.numberCircuit for w in matches]))
            distinct_cables = sorted(set([_find_kabel(w) for w in matches]))
            if choice == TaskDialogCommandLinkId.CommandLink1 and len(distinct_nums) > 1:
                duplicates.append((target, matches))
                continue
            if choice == TaskDialogCommandLinkId.CommandLink2 and (len(distinct_nums) > 1 or len(distinct_cables) > 1):
                duplicates.append((target, matches))
                continue
        if len(matches) == 0:
            continue
        wrapper = matches[0]
        cable_text = ""
        if choice == TaskDialogCommandLinkId.CommandLink2:
            cable_text = u"; {0}м".format(_find_kabel(wrapper))
        if p_text:
            p_text.Set(u"Ввод питания от {0}\n{1}{2}".format(wrapper.prinadlezhnost_AV, wrapper.numberCircuit, cable_text))
        try:
            if wrapper.kolvo_pol_AV.AsInteger() == 0:
                p_3phase.Set(0)
            elif wrapper.kolvo_pol_AV.AsInteger() == 1:
                p_3phase.Set(1)
        except Exception:
            pass
        if target not in processed:
            processed.append(target)
    t.Commit()

text6 = ""
if not_processed:
    text6 += (
        u"Элементы с представленными Id не обработаны. \n"
        u"Проверьте параметр принадлежность щиту семейства \"{0}\" "
        u"или в вашей модели отсутствует указанная позиция щита.\n\n{1}\n\n"
    ).format(NAME_VVOD, u"; ".join([str(e.Id.IntegerValue) for e in not_processed]))

if duplicates:
    text7 = ""
    for target, wrappers in duplicates:
        text7 += u"Вводной аппарат ({0}) - задублированные автоматы {1};\n".format(
            target.Id.IntegerValue,
            u"; ".join([str(w.IntId) for w in wrappers]),
        )
    text6 += (
        u"В следующие вводные аппараты не записана информация о линии питания, "
        u"так как присутствуют задублированные автоматы с одинаковым номером цепи:\n"
        + text7
    )

dlg = TaskDialog(TITLE)
dlg.TitleAutoPrefix = True
dlg.AllowCancellation = True
if not text6:
    if len(processed) == 1:
        dlg.MainContent = u"Обработан 1 элемент"
    elif 1 < len(processed) < 5:
        dlg.MainContent = u"Обработано {0} элемента".format(len(processed))
    else:
        dlg.MainContent = u"Обработано {0} элементов".format(len(processed))
else:
    if len(processed) == 1:
        dlg.MainContent = u"Обработан 1 элемент\n\n{0}".format(text6)
    elif 1 < len(processed) < 5:
        dlg.MainContent = u"Обработано {0} элемента\n\n{1}".format(len(processed), text6)
    else:
        dlg.MainContent = u"Обработано {0} элементов\n\n{1}".format(len(processed), text6)
dlg.Show()
