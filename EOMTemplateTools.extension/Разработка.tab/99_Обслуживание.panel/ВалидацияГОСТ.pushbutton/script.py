# -*- coding: utf-8 -*-
'''
Проверка размещения электрооборудования по ГОСТ/СП РФ.
'''

import math
import clr
import System
import sys

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from System.Windows.Forms import *
from System.Drawing import *
from System.Collections.Generic import *

from pyrevit import revit


# ----------------------------- Контекст Revit -----------------------------
doc = revit.doc
uidoc = revit.uidoc


# ----------------------------- Нормативы -----------------------------
NORM_SOCKET_HEIGHT = u'СП 256.1325800.2016, п. 15.30'
NORM_SWITCH_HEIGHT = u'СП 256.1325800.2016, п. 15.28'
NORM_SOCKET_COUNT_ROOM = u'СП 256.1325800.2016, п. 15.29'
NORM_SOCKET_COUNT_KITCHEN = u'СП 256.1325800.2016, п. 15.29'
NORM_GAS_DISTANCE = u'ПУЭ п. 7.1.50'
NORM_BATHROOM_ZONE = u'ГОСТ Р 50571.7.701-2013'
NORM_SINK_DISTANCE = u'СП 256.1325800.2016, п. 15.29'


# ----------------------------- Утилиты -----------------------------
def _to_mm(value_internal):
	try:
		return UnitUtils.ConvertFromInternalUnits(value_internal, DisplayUnitType.DUT_MILLIMETERS)
	except Exception:
		return UnitUtils.ConvertFromInternalUnits(value_internal, UnitTypeId.Millimeters)


def _to_internal_mm(value_mm):
	try:
		return UnitUtils.ConvertToInternalUnits(value_mm, DisplayUnitType.DUT_MILLIMETERS)
	except Exception:
		return UnitUtils.ConvertToInternalUnits(value_mm, UnitTypeId.Millimeters)


def _safe_str(val):
	try:
		if val is None:
			return ''
		return str(val)
	except Exception:
		return ''


def _safe_lower(val):
	return _safe_str(val).lower()


def _get_level_for_element(elem):
	try:
		if elem.LevelId and elem.LevelId.IntegerValue != -1:
			return doc.GetElement(elem.LevelId)
	except Exception:
			pass
	try:
		param = elem.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM)
		if param:
			lvl_id = param.AsElementId()
			if lvl_id and lvl_id.IntegerValue != -1:
				return doc.GetElement(lvl_id)
	except Exception:
		pass
	return None


def _get_element_point(elem):
	try:
		loc = elem.Location
		if isinstance(loc, LocationPoint):
			return loc.Point
		elif isinstance(loc, LocationCurve):
			return loc.Curve.Evaluate(0.5, True)
	except Exception:
		pass
	return None


def _get_height_from_level_mm(elem):
	try:
		pt = _get_element_point(elem)
		if not pt:
			return None
		lvl = _get_level_for_element(elem)
		if not lvl:
			return None
		z = pt.Z - lvl.Elevation
		return _to_mm(z)
	except Exception:
		return None


def _get_family_type_names(elem):
	try:
		if isinstance(elem, FamilyInstance):
			symbol = elem.Symbol
			fam_name = symbol.Family.Name if symbol and symbol.Family else ''
			type_name = symbol.Name if symbol else ''
			return fam_name, type_name, elem.Name
	except Exception:
		pass
	return '', '', elem.Name if elem else ''


def _is_socket(elem):
	name_parts = _get_family_type_names(elem)
	text = _safe_lower(u' '.join([n for n in name_parts if n]))
	return any(k in text for k in [u'розет', u'socket', u'recept', u'outlet'])


def _is_switch(elem):
	name_parts = _get_family_type_names(elem)
	text = _safe_lower(u' '.join([n for n in name_parts if n]))
	return any(k in text for k in [u'выключ', u'switch'])


def _is_kitchen(room):
	try:
		name = _safe_lower(room.Name)
		return u'кухн' in name
	except Exception:
		return False


def _is_bathroom(room):
	try:
		name = _safe_lower(room.Name)
		return any(k in name for k in [u'ванн', u'душ', u'сануз', u'туалет'])
	except Exception:
		return False


def _is_bath_fixture(elem):
	name_parts = _get_family_type_names(elem)
	text = _safe_lower(u' '.join([n for n in name_parts if n]))
	return any(k in text for k in [u'ванн', u'bath', u'душ', u'shower'])


def _is_sink_fixture(elem):
	name_parts = _get_family_type_names(elem)
	text = _safe_lower(u' '.join([n for n in name_parts if n]))
	return any(k in text for k in [u'раков', u'умыв', u'sink', u'wash'])


def _get_room_for_element(elem):
	try:
		if hasattr(elem, 'Room'):
			if elem.Room:
				return elem.Room
	except Exception:
		pass
	try:
		pt = _get_element_point(elem)
		if not pt:
			return None
		rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
		for room in rooms:
			try:
				if room.IsPointInRoom(pt):
					return room
			except Exception:
				pass
	except Exception:
		pass
	return None


def _collect_electrical_instances():
	result = []
	try:
		cats = [BuiltInCategory.OST_ElectricalFixtures, BuiltInCategory.OST_ElectricalDevices]
		for cat in cats:
			try:
				elems = FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType().ToElements()
				for e in elems:
					if isinstance(e, FamilyInstance):
						result.append(e)
			except Exception:
				continue
	except Exception:
		pass
	return result


def _collect_sockets():
	return [e for e in _collect_electrical_instances() if _is_socket(e)]


def _collect_switches():
	return [e for e in _collect_electrical_instances() if _is_switch(e)]


def _collect_rooms():
	try:
		return FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
	except Exception:
		return []


def _collect_pipes_gas():
	result = []
	try:
		pipes = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_PipeCurves).WhereElementIsNotElementType().ToElements()
		for p in pipes:
			try:
				param = p.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
				val = ''
				if param:
					val = param.AsValueString() or param.AsString() or ''
				if u'газ' in _safe_lower(val):
					result.append(p)
			except Exception:
				continue
	except Exception:
		pass
	return result


def _collect_plumbing_fixtures():
	try:
		return FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_PlumbingFixtures).WhereElementIsNotElementType().ToElements()
	except Exception:
		return []


def _make_violation(check_name, element, problem, norm):
	return {
		'check': check_name,
		'element': element,
		'problem': problem,
		'norm': norm
	}


def _element_display(elem):
	try:
		name = elem.Name
		eid = elem.Id.IntegerValue
		return u'Id: {0} | {1}'.format(eid, name)
	except Exception:
		return u'Id: ?'


# ----------------------------- Проверки -----------------------------
def check_socket_height():
	violations = []
	try:
		sockets = _collect_sockets()
		for s in sockets:
			h = _get_height_from_level_mm(s)
			if h is None:
				continue
			if h < 300 or h > 1000:
				problem = u'Высота розетки {0:.0f} мм (норма 300-1000 мм)'.format(h)
				violations.append(_make_violation(u'Высота розеток', s, problem, NORM_SOCKET_HEIGHT))
	except Exception:
		pass
	return violations


def check_switch_height():
	violations = []
	try:
		switches = _collect_switches()
		for s in switches:
			h = _get_height_from_level_mm(s)
			if h is None:
				continue
			if h < 800 or h > 1700:
				problem = u'Высота выключателя {0:.0f} мм (норма 800-1700 мм)'.format(h)
				violations.append(_make_violation(u'Высота выключателей', s, problem, NORM_SWITCH_HEIGHT))
	except Exception:
		pass
	return violations


def check_socket_count_per_perimeter():
	violations = []
	try:
		sockets = _collect_sockets()
		rooms = _collect_rooms()
		for room in rooms:
			try:
				perim_param = room.get_Parameter(BuiltInParameter.ROOM_PERIMETER)
				if not perim_param:
					continue
				perim_mm = _to_mm(perim_param.AsDouble())
				required = int(math.ceil(perim_mm / 3000.0))
				if required <= 0:
					continue
				count = 0
				for s in sockets:
					try:
						if s.Room and s.Room.Id == room.Id:
							count += 1
						else:
							pt = _get_element_point(s)
							if pt and room.IsPointInRoom(pt):
								count += 1
					except Exception:
						continue
				if count < required:
					problem = u'Розеток: {0}, требуется: {1} (периметр {2:.0f} мм)'.format(count, required, perim_mm)
					violations.append(_make_violation(u'Количество розеток по периметру', room, problem, NORM_SOCKET_COUNT_ROOM))
			except Exception:
				continue
	except Exception:
		pass
	return violations


def check_kitchen_sockets():
	violations = []
	try:
		sockets = _collect_sockets()
		rooms = _collect_rooms()
		for room in rooms:
			if not _is_kitchen(room):
				continue
			try:
				area_param = room.get_Parameter(BuiltInParameter.ROOM_AREA)
				if not area_param:
					continue
				area_m2 = UnitUtils.ConvertFromInternalUnits(area_param.AsDouble(), UnitTypeId.SquareMeters)
				required = 3 if area_m2 <= 8.0 else 4
				count = 0
				for s in sockets:
					try:
						if s.Room and s.Room.Id == room.Id:
							count += 1
						else:
							pt = _get_element_point(s)
							if pt and room.IsPointInRoom(pt):
								count += 1
					except Exception:
						continue
				if count < required:
					problem = u'Розеток: {0}, требуется: {1} (площадь {2:.2f} м²)'.format(count, required, area_m2)
					violations.append(_make_violation(u'Розетки на кухне', room, problem, NORM_SOCKET_COUNT_KITCHEN))
			except Exception:
				continue
	except Exception:
		pass
	return violations


def check_distance_from_gas():
	violations = []
	try:
		pipes = _collect_pipes_gas()
		if not pipes:
			return []
		sockets = _collect_sockets()
		min_dist_int = _to_internal_mm(500)
		for s in sockets:
			pt = _get_element_point(s)
			if not pt:
				continue
			min_found = None
			for p in pipes:
				try:
					loc = p.Location
					if not isinstance(loc, LocationCurve):
						continue
					dist = loc.Curve.Distance(pt)
					if min_found is None or dist < min_found:
						min_found = dist
				except Exception:
					continue
			if min_found is not None and min_found < min_dist_int:
				problem = u'Расстояние до газопровода {0:.0f} мм (норма ≥ 500 мм)'.format(_to_mm(min_found))
				violations.append(_make_violation(u'Расстояние до газопровода', s, problem, NORM_GAS_DISTANCE))
	except Exception:
		pass
	return violations


def check_bathroom_zones():
	violations = []
	try:
		sockets = _collect_sockets()
		rooms = [r for r in _collect_rooms() if _is_bathroom(r)]
		fixtures = [f for f in _collect_plumbing_fixtures() if _is_bath_fixture(f)]
		if not rooms or not fixtures:
			return []
		buffer_int = _to_internal_mm(600)
		for room in rooms:
			room_sockets = []
			for s in sockets:
				try:
					if s.Room and s.Room.Id == room.Id:
						room_sockets.append(s)
					else:
						pt = _get_element_point(s)
						if pt and room.IsPointInRoom(pt):
							room_sockets.append(s)
				except Exception:
					continue
			if not room_sockets:
				continue
			for fx in fixtures:
				try:
					fx_room = _get_room_for_element(fx)
					if not fx_room or fx_room.Id != room.Id:
						continue
					bbox = fx.get_BoundingBox(None)
					if not bbox:
						continue
					min_pt = XYZ(bbox.Min.X - buffer_int, bbox.Min.Y - buffer_int, bbox.Min.Z - buffer_int)
					max_pt = XYZ(bbox.Max.X + buffer_int, bbox.Max.Y + buffer_int, bbox.Max.Z + buffer_int)
					for s in room_sockets:
						pt = _get_element_point(s)
						if not pt:
							continue
						if (min_pt.X <= pt.X <= max_pt.X) and (min_pt.Y <= pt.Y <= max_pt.Y):
							problem = u'Розетка в зоне 600 мм от ванны/душа'
							violations.append(_make_violation(u'Запретная зона ванной', s, problem, NORM_BATHROOM_ZONE))
				except Exception:
					continue
	except Exception:
		pass
	return violations


def check_distance_from_sinks():
	violations = []
	try:
		sockets = _collect_sockets()
		sinks = [f for f in _collect_plumbing_fixtures() if _is_sink_fixture(f)]
		if not sinks:
			return []
		min_dist_int = _to_internal_mm(600)
		for s in sockets:
			pt = _get_element_point(s)
			if not pt:
				continue
			min_found = None
			for sink in sinks:
				try:
					bbox = sink.get_BoundingBox(None)
					if not bbox:
						continue
					# Минимальная дистанция по XYZ до bbox
					dx = 0 if bbox.Min.X <= pt.X <= bbox.Max.X else min(abs(pt.X - bbox.Min.X), abs(pt.X - bbox.Max.X))
					dy = 0 if bbox.Min.Y <= pt.Y <= bbox.Max.Y else min(abs(pt.Y - bbox.Min.Y), abs(pt.Y - bbox.Max.Y))
					dz = 0 if bbox.Min.Z <= pt.Z <= bbox.Max.Z else min(abs(pt.Z - bbox.Min.Z), abs(pt.Z - bbox.Max.Z))
					dist = math.sqrt(dx * dx + dy * dy + dz * dz)
					if min_found is None or dist < min_found:
						min_found = dist
				except Exception:
					continue
			if min_found is not None and min_found < min_dist_int:
				problem = u'Расстояние до раковины {0:.0f} мм (норма ≥ 600 мм)'.format(_to_mm(min_found))
				violations.append(_make_violation(u'Расстояние до раковин', s, problem, NORM_SINK_DISTANCE))
	except Exception:
		pass
	return violations


def run_all_checks():
	violations = []
	checks = [
		check_socket_height,
		check_switch_height,
		check_socket_count_per_perimeter,
		check_kitchen_sockets,
		check_distance_from_gas,
		check_bathroom_zones,
		check_distance_from_sinks
	]
	for ch in checks:
		try:
			violations.extend(ch())
		except Exception:
			continue
	return violations


# ----------------------------- UI -----------------------------
class ValidationWindow(Form):
	def __init__(self):
		self.TopMost = True
		self._violations = []
		self.InitializeComponent()

	def InitializeComponent(self):
		self._grid = System.Windows.Forms.DataGridView()
		self._btn_refresh = System.Windows.Forms.Button()
		self._btn_export = System.Windows.Forms.Button()
		self._btn_close = System.Windows.Forms.Button()
		self._col_check = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._col_element = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._col_problem = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._col_norm = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._col_show = System.Windows.Forms.DataGridViewButtonColumn()
		self._grid.BeginInit()
		self.SuspendLayout()

		# grid
		self._grid.AllowUserToAddRows = False
		self._grid.AllowUserToDeleteRows = False
		self._grid.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._grid.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._grid.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn]([
			self._col_check,
			self._col_element,
			self._col_problem,
			self._col_norm,
			self._col_show
		]))
		self._grid.Location = System.Drawing.Point(16, 16)
		self._grid.Name = "ValidationGrid"
		self._grid.ReadOnly = True
		self._grid.Size = System.Drawing.Size(920, 430)
		self._grid.TabIndex = 0
		self._grid.CellContentClick += self.GridCellContentClick

		# columns
		self._col_check.HeaderText = u"Тип проверки"
		self._col_check.Name = "col_check"
		self._col_check.ReadOnly = True

		self._col_element.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.Fill
		self._col_element.HeaderText = u"Элемент (ID + имя)"
		self._col_element.Name = "col_element"
		self._col_element.ReadOnly = True

		self._col_problem.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.Fill
		self._col_problem.HeaderText = u"Проблема"
		self._col_problem.Name = "col_problem"
		self._col_problem.ReadOnly = True

		self._col_norm.HeaderText = u"Норматив"
		self._col_norm.Name = "col_norm"
		self._col_norm.ReadOnly = True

		self._col_show.HeaderText = u"Показать"
		self._col_show.Name = "col_show"
		self._col_show.ReadOnly = True

		# buttons
		self._btn_refresh.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._btn_refresh.Location = System.Drawing.Point(16, 460)
		self._btn_refresh.Name = "btn_refresh"
		self._btn_refresh.Size = System.Drawing.Size(110, 26)
		self._btn_refresh.Text = u"Обновить"
		self._btn_refresh.UseVisualStyleBackColor = True
		self._btn_refresh.Click += self.RefreshClick

		self._btn_export.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._btn_export.Location = System.Drawing.Point(136, 460)
		self._btn_export.Name = "btn_export"
		self._btn_export.Size = System.Drawing.Size(110, 26)
		self._btn_export.Text = u"Экспорт"
		self._btn_export.UseVisualStyleBackColor = True
		self._btn_export.Click += self.ExportClick

		self._btn_close.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._btn_close.Location = System.Drawing.Point(826, 460)
		self._btn_close.Name = "btn_close"
		self._btn_close.Size = System.Drawing.Size(110, 26)
		self._btn_close.Text = u"Закрыть"
		self._btn_close.UseVisualStyleBackColor = True
		self._btn_close.Click += self.CloseClick

		# form
		self.ClientSize = System.Drawing.Size(952, 500)
		self.Controls.Add(self._grid)
		self.Controls.Add(self._btn_refresh)
		self.Controls.Add(self._btn_export)
		self.Controls.Add(self._btn_close)
		self.Name = "ValidationWindow"
		self.Text = u"Проверка по ГОСТ"
		self.Load += self.WindowLoad
		self._grid.EndInit()
		self.ResumeLayout(False)

	def _clear_grid(self):
		try:
			count = self._grid.Rows.Count
			while count > 0:
				self._grid.Rows.RemoveAt(0)
				count -= 1
		except Exception:
			pass

	def _fill_grid(self):
		self._clear_grid()
		for idx, v in enumerate(self._violations):
			elem = v.get('element')
			self._grid.Rows.Add(
				v.get('check', ''),
				_element_display(elem),
				v.get('problem', ''),
				v.get('norm', ''),
				u'Показать'
			)
			try:
				for col_idx in [0, 1, 2, 3]:
					self._grid.Rows[idx].Cells[col_idx].Style.ForeColor = Color.Red
			except Exception:
				pass

	def WindowLoad(self, sender, e):
		self._violations = run_all_checks()
		self._fill_grid()

	def RefreshClick(self, sender, e):
		self._violations = run_all_checks()
		self._fill_grid()

	def CloseClick(self, sender, e):
		self.Close()

	def ExportClick(self, sender, e):
		try:
			dialog = SaveFileDialog()
			dialog.Filter = u"CSV (*.csv)|*.csv"
			dialog.Title = u"Экспорт отчёта"
			dialog.FileName = u"gost_validation.csv"
			if dialog.ShowDialog() != DialogResult.OK:
				return
			path = dialog.FileName
			writer = System.IO.StreamWriter(path, False, System.Text.Encoding.UTF8)
			writer.WriteLine(u"Тип проверки;Элемент;Проблема;Норматив")
			for v in self._violations:
				elem = v.get('element')
				line = u"{0};{1};{2};{3}".format(
					_safe_str(v.get('check', '')),
					_safe_str(_element_display(elem)),
					_safe_str(v.get('problem', '')),
					_safe_str(v.get('norm', ''))
				)
				writer.WriteLine(line)
			writer.Close()
			TaskDialog.Show(u"Проверка по ГОСТ", u"Отчёт сохранён: {0}".format(path))
		except Exception:
			TaskDialog.Show(u"Проверка по ГОСТ", u"Не удалось сохранить отчёт.")

	def GridCellContentClick(self, sender, e):
		if self._grid.CurrentCell.ColumnIndex == 4 and self._grid.CurrentCell.RowIndex != -1:
			row_idx = self._grid.CurrentCell.RowIndex
			if row_idx < 0 or row_idx >= len(self._violations):
				return
			v = self._violations[row_idx]
			elem = v.get('element')
			if not elem:
				return
			try:
				elems = ElementSet()
				elems.Insert(elem)
				uidoc.ShowElements(elems)
			except Exception:
				pass
			try:
				ele_ids = List[ElementId]([elem.Id])
				uidoc.Selection.SetElementIds(ele_ids)
			except Exception:
				pass


# ----------------------------- Запуск -----------------------------
ValidationWindow().Show()
