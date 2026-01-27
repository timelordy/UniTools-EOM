# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit

from unibim.geometry_utils import midpoint
from utils_revit import tx


doc = revit.doc
uidoc = revit.uidoc


class _FamilyInstanceSelectionFilter(DB.ISelectionFilter):
    def AllowElement(self, element):
        try:
            return isinstance(element, DB.FamilyInstance)
        except Exception:
            return False

    def AllowReference(self, reference, position):
        return False


def _get_level_for_instance(inst):
    try:
        lvl_id = inst.LevelId
        if lvl_id and lvl_id != DB.ElementId.InvalidElementId:
            lvl = doc.GetElement(lvl_id)
            if isinstance(lvl, DB.Level):
                return lvl
    except Exception:
        pass
    try:
        v = doc.ActiveView
        return v.GenLevel if v else None
    except Exception:
        return None


def _copy_elevation_param(src, dst):
    try:
        src_p = src.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        dst_p = dst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if src_p and dst_p and not dst_p.IsReadOnly:
            dst_p.Set(src_p.AsDouble())
    except Exception:
        pass


def _place_instance(symbol, level, point):
    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()

    try:
        if level:
            return doc.Create.NewFamilyInstance(point, symbol, level, DB.Structure.StructuralType.NonStructural)
    except Exception:
        pass

    try:
        return doc.Create.NewFamilyInstance(point, symbol, DB.Structure.StructuralType.NonStructural)
    except Exception:
        return None


def main():
    try:
        ref = uidoc.Selection.PickObject(DB.Selection.ObjectType.Element, _FamilyInstanceSelectionFilter(), u'Выберите элемент‑образец')
    except Exception:
        return

    inst = doc.GetElement(ref.ElementId)
    if not isinstance(inst, DB.FamilyInstance):
        forms.alert(u'Выберите семейство экземпляра.', exitscript=True)

    symbol = inst.Symbol
    level = _get_level_for_instance(inst)

    placed = 0
    with tx(doc, u'UniBIM: Поставить по двум точкам'):
        while True:
            try:
                p1 = uidoc.Selection.PickPoint(u'Точка 1')
                p2 = uidoc.Selection.PickPoint(u'Точка 2')
            except Exception:
                break

            mx, my, mz = midpoint(p1, p2)
            pt = DB.XYZ(mx, my, mz)
            new_inst = _place_instance(symbol, level, pt)
            if new_inst:
                _copy_elevation_param(inst, new_inst)
                placed += 1

    if placed:
        forms.alert(u'Готово. Добавлено: {0}'.format(placed))


main()
