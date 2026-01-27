# -*- coding: utf-8 -*-
import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (
	FilteredElementCollector,
	Family,
	FamilySymbol,
	Line,
	DetailLine,
	LocationCurve,
	ViewType,
	StructuralType,
	ElementId,
	BuiltInParameter,
)
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import revit, forms


class _DetailLineFilter(ISelectionFilter):
	def AllowElement(self, elem):
		return isinstance(elem, DetailLine)

	def AllowReference(self, ref, point):
		return False


def _check_active_view(doc):
	vt = doc.ActiveView.ViewType
	allowed = {
		ViewType.FloorPlan,
		ViewType.CeilingPlan,
		ViewType.EngineeringPlan,
		ViewType.ThreeD,
	}
	if vt in allowed:
		return True
	forms.alert(
		u"Активный вид не позволяет выполнить команду, откройте план этажа или 3D вид.",
		title=u"Заменить линии детализации",
		warn_icon=True,
		exitscript=True,
	)
	return False


def _find_family_symbols(doc):
	families = [
		f
		for f in FilteredElementCollector(doc).OfClass(Family)
		if "Участок трассы_Горизонтальный" in f.Name or "Участок трассы_Вертикальный" in f.Name
	]
	symbols = []
	for fam in families:
		for sid in fam.GetFamilySymbolIds():
			sym = doc.GetElement(sid)
			if isinstance(sym, FamilySymbol):
				symbols.append(sym)
	return symbols


def _get_line_style_name(doc, detail_line):
	try:
		loc = detail_line.Location
		if isinstance(loc, LocationCurve):
			curve = loc.Curve
			if isinstance(curve, Line):
				gs_elem = doc.GetElement(curve.GraphicsStyleId)
				if gs_elem and gs_elem.Name:
					return gs_elem.Name
	except Exception:
		pass
	try:
		return detail_line.Name
	except Exception:
		return ""


def _create_family_instance(doc, location_curve, family_symbol):
	if family_symbol is None:
		return None
	if not family_symbol.IsActive:
		family_symbol.Activate()
	inst = doc.Create.NewFamilyInstance(
		location_curve.Curve,
		family_symbol,
		doc.ActiveView.GenLevel,
		StructuralType.NonStructural,
	)
	if inst:
		param = inst.LookupParameter(u"Тип линии")
		if param:
			param.Set(ElementId(2540227))
		param = inst.LookupParameter(u"TSL_Номер питающей цепи")
		if param:
			param.Set("")
		param = inst.LookupParameter(u"TSL_Номер питающей цепи (сгруппированный)")
		if param:
			param.Set("")
	return inst


def main():
	doc = revit.doc
	uidoc = revit.uidoc
	if doc is None:
		forms.alert("No active document.", exitscript=True)
		return

	if not _check_active_view(doc):
		return

	symbols = _find_family_symbols(doc)
	if not symbols:
		forms.alert(
			u'В файле отсутствует семейство "Участок трассы_Горизонтальный".',
			title=u"Заменить линии детализации",
			warn_icon=True,
			exitscript=True,
		)
		return

	detail_lines = []
	selected_ids = list(uidoc.Selection.GetElementIds())
	if not selected_ids:
		try:
			refs = uidoc.Selection.PickObjects(
				ObjectType.Element, _DetailLineFilter(), u"Выберите линии для обработки"
			)
		except OperationCanceledException:
			return
		for r in refs:
			elem = doc.GetElement(r.ElementId)
			if isinstance(elem, DetailLine):
				detail_lines.append(elem)
	else:
		for eid in selected_ids:
			elem = doc.GetElement(eid)
			if isinstance(elem, DetailLine):
				detail_lines.append(elem)

	if not detail_lines:
		forms.alert(
			u"На виде отсутствуют подходящие линии детализации.\n\n"
			u"Выберите линии которые в наименовании содержат \"Линия\" или \"Поток\".",
			title=u"Заменить линии детализации",
			warn_icon=True,
		)
		return

	name_map = {
		u"Линия 36 В": u"Линия 36 В",
		u"Линия 48 В": u"Линия 48 В",
		u"Линия в коробе": u"Линия в коробе",
		u"Линия в лотке": u"Линия в лотке",
		u"Линия в трубе": u"Линия в трубе",
		u"Линия в трубе_Открыто": u"Линия в трубе_Открыто",
	}

	created = 0
	with revit.Transaction(u"Заменить линии детализации"):
		for dl in detail_lines:
			loc = dl.Location
			if not isinstance(loc, LocationCurve):
				continue
			line_name = _get_line_style_name(doc, dl)
			symbol_name = None
			for key in name_map.keys():
				if key in line_name:
					symbol_name = name_map[key]
					break
			if symbol_name:
				symbol = next((s for s in symbols if s.Name == symbol_name), symbols[0])
			else:
				symbol = symbols[0]
			if _create_family_instance(doc, loc, symbol):
				created += 1

	if created > 0:
		td = TaskDialog(u"Заменить линии детализации")
		td.MainInstruction = u"Выполнение завершено!"
		td.MainContent = u"Обработано линий: {}\n\n\nУдалить исходные элементы?".format(created)
		td.CommonButtons = TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No
		res = td.Show()
		if res == TaskDialogResult.Yes:
			with revit.Transaction(u"Удалить исходные линии"):
				for dl in detail_lines:
					try:
						doc.Delete(dl.Id)
					except Exception:
						pass


if __name__ == "__main__":
	main()
