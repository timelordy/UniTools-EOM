# -*- coding: utf-8 -*-

from pyrevit import revit

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    ElementId,
    FilteredElementCollector,
    Transaction,
)
from Autodesk.Revit.UI import TaskDialog  # noqa: E402
from System.Collections.Generic import List  # noqa: E402

from unibim.knk_delete_paths_utils import is_knk_path_name  # noqa: E402


CAPTION = u"Удалить пути до трассы"


def _collect_paths(doc):
    elements = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_CableTrayFitting)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return [elem.Id for elem in elements if is_knk_path_name(getattr(elem, "Name", None))]


def main():
    doc = revit.doc
    ids = _collect_paths(doc)
    if not ids:
        TaskDialog.Show(CAPTION, u"Пути не найдены.")
        return

    t = Transaction(doc, CAPTION)
    try:
        t.Start()
        doc.Delete(List[ElementId](ids))
        t.Commit()
    finally:
        t.Dispose()

    TaskDialog.Show(CAPTION, u"Выполнение завершено!")


if __name__ == "__main__":
    main()
