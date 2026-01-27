# -*- coding: utf-8 -*-

from pyrevit import revit, forms

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInParameter,
    FamilyInstance,
    FilteredElementCollector,
    PanelScheduleView,
    SectionType,
    Transaction,
)
from Autodesk.Revit.UI import TaskDialog  # noqa: E402


CAPTION = u"Удаление пустых строк в схеме щита"
ALL_LABEL = u"Все"


def _get_selected_panel_name(uidoc, doc):
    sel_ids = uidoc.Selection.GetElementIds()
    if len(sel_ids) != 1:
        return ""
    elem = doc.GetElement(list(sel_ids)[0])
    if not isinstance(elem, FamilyInstance):
        return ""
    try:
        if elem.MEPModel is None:
            return ""
    except Exception:
        return ""
    try:
        param = elem.get_Parameter(BuiltInParameter(-1140078))
        return param.AsString() if param and param.AsString() else ""
    except Exception:
        return ""


def _get_panel_schedules(doc):
    return (
        FilteredElementCollector(doc)
        .OfClass(PanelScheduleView)
        .ToElements()
    )


def _delete_empty_lines(panel_view):
    try:
        number_of_slots = panel_view.GetTableData().NumberOfSlots
    except Exception:
        return
    shift = 0
    for slot in range(2, number_of_slots):
        try:
            value = panel_view.GetCellText(SectionType.Body, slot, 2)
        except Exception:
            value = ""
        if value == "":
            shift += 1
            continue
        if shift:
            try:
                if panel_view.CanMoveSlotTo(slot, 2, slot - shift, 2):
                    panel_view.MoveSlotTo(slot, 2, slot - shift, 2)
            except Exception:
                continue


def main():
    doc = revit.doc
    uidoc = revit.uidoc

    schedules = _get_panel_schedules(doc)
    if not schedules:
        TaskDialog.Show(
            CAPTION,
            u"В данном файле отсутствуют виды в группе «Принципиальная схема щита/панели» диспетчера проекта.",
        )
        return

    names = sorted([s.Name for s in schedules])
    names.insert(0, ALL_LABEL)

    selected_panel_name = _get_selected_panel_name(uidoc, doc)
    default_name = selected_panel_name if selected_panel_name in names else ALL_LABEL

    form = forms.FlexForm(
        CAPTION,
        [
            forms.ComboBox("panel_name", names, default=default_name),
            forms.Button(u"ОК"),
        ],
    )
    if not form.show():
        return

    panel_name = form.values.get("panel_name") or ALL_LABEL
    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        if panel_name == ALL_LABEL:
            for panel_view in schedules:
                _delete_empty_lines(panel_view)
        else:
            panel_view = next((s for s in schedules if s.Name == panel_name), None)
            if panel_view:
                _delete_empty_lines(panel_view)
        t.Commit()
    finally:
        t.Dispose()

    TaskDialog.Show(CAPTION, u"Выполнение завершено!")


if __name__ == "__main__":
    main()
