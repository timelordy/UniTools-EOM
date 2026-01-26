# -*- coding: utf-8 -*-
import clr
import System

clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from System.Drawing import Point, Size, Font
from System.Windows.Forms import (
	Form,
	TextBox,
	Label,
	Button,
	CheckedListBox,
	DialogResult,
	FormStartPosition,
	FormBorderStyle,
	AnchorStyles,
)
from Autodesk.Revit.DB import (
	FilteredElementCollector,
	RevitLinkInstance,
	View3D,
	ViewFamilyType,
	ViewFamily,
	ViewDetailLevel,
	ElementId,
	XYZ,
	BoundingBoxXYZ,
	BuiltInParameter,
)
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, forms


def _get_link_display_name(link_inst):
	try:
		param = link_inst.get_Parameter(BuiltInParameter.RVT_LINK_INSTANCE_NAME)
		if param:
			name = param.AsString()
			if name:
				return name
	except Exception:
		pass
	return link_inst.Name


def _expand_bbox(bbox, pad=1.0, origin=None):
	if bbox is None:
		return None
	min_pt = XYZ(bbox.Min.X - pad, bbox.Min.Y - pad, bbox.Min.Z - pad)
	max_pt = XYZ(bbox.Max.X + pad, bbox.Max.Y + pad, bbox.Max.Z + pad)
	if origin is not None:
		min_pt = XYZ(min_pt.X + origin.X, min_pt.Y + origin.Y, min_pt.Z + origin.Z)
		max_pt = XYZ(max_pt.X + origin.X, max_pt.Y + origin.Y, max_pt.Z + origin.Z)
	new_bbox = BoundingBoxXYZ()
	new_bbox.Min = min_pt
	new_bbox.Max = max_pt
	return new_bbox


def _find_element_bbox(doc, id_text):
	try:
		elem_id = ElementId(int(id_text))
	except Exception:
		return None
	elem = doc.GetElement(elem_id)
	if elem is None:
		return None
	view = doc.ActiveView
	bbox = None
	try:
		if view:
			bbox = elem.get_BoundingBox(view)
	except Exception:
		bbox = None
	if bbox is None:
		try:
			bbox = elem.get_BoundingBox(None)
		except Exception:
			bbox = None
	return bbox


def _get_or_create_tsl_3d_view(doc):
	view = None
	for v in FilteredElementCollector(doc).OfClass(View3D):
		if v.IsTemplate:
			continue
		if v.Name == "TSL_3D":
			view = v
			break
	if view is not None:
		return view
	vft = None
	for vt in FilteredElementCollector(doc).OfClass(ViewFamilyType):
		if vt.ViewFamily == ViewFamily.ThreeDimensional:
			vft = vt
			break
	if vft is None:
		return None
	view = View3D.CreateIsometric(doc, vft.Id)
	if view is not None:
		name_param = view.get_Parameter(BuiltInParameter.VIEW_NAME)
		if name_param:
			name_param.Set("TSL_3D")
	return view


def _view_link_element(uidoc, link_inst, id_text):
	doc = uidoc.Document
	if not id_text:
		forms.alert(u"Введите ID элемента.", title=u"Tesla", warn_icon=True)
		return
	with revit.Transaction(u"Показать элемент в связи"):
		view3d = _get_or_create_tsl_3d_view(doc)
		if view3d is None:
			TaskDialog.Show(u"Ошибка", u"Не удалось создать 3D вид.")
			return
		origin = None
		target_doc = doc
		if link_inst is not None:
			target_doc = link_inst.GetLinkDocument()
			if target_doc is None:
				TaskDialog.Show(u"Ошибка", u"Связь не загружена.")
				return
			try:
				origin = link_inst.GetTotalTransform().Origin
			except Exception:
				origin = None
		bbox = _find_element_bbox(target_doc, id_text)
		if bbox is None:
			TaskDialog.Show(u"Ошибка", u"Элемент не может быть показан.")
			return
		view_bbox = _expand_bbox(bbox, pad=1.0, origin=origin)
		if view_bbox is None:
			TaskDialog.Show(u"Ошибка", u"Элемент не может быть показан.")
			return
		view3d.SetSectionBox(view_bbox)
		template_param = view3d.get_Parameter(BuiltInParameter.VIEW_TEMPLATE)
		if template_param:
			template_param.Set(ElementId.InvalidElementId)
		view3d.IsSectionBoxActive = True
		view3d.DetailLevel = ViewDetailLevel.Fine
	uidoc.ActiveView = view3d


class ViewLinkElementForm(Form):
	def __init__(self, uidoc):
		Form.__init__(self)
		self.uidoc = uidoc
		self.links = []

		self.Text = u"Tesla - Поиск элемента в связанном файле"
		self.FormBorderStyle = FormBorderStyle.FixedDialog
		self.StartPosition = FormStartPosition.CenterScreen
		self.MaximizeBox = False
		self.MinimizeBox = False
		self.ClientSize = Size(440, 340)

		self.label_title = Label()
		self.label_title.Text = u"Tesla - Поиск элемента в связанном файле"
		self.label_title.AutoSize = True
		self.label_title.Location = Point(10, 10)

		self.label_link = Label()
		self.label_link.Text = u"Выберите связь"
		self.label_link.AutoSize = True
		self.label_link.Location = Point(10, 40)

		self.links_list = CheckedListBox()
		self.links_list.Location = Point(10, 65)
		self.links_list.Size = Size(410, 140)
		self.links_list.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
		self.links_list.CheckOnClick = True
		self.links_list.ItemCheck += self._on_item_check

		self.label_id = Label()
		self.label_id.Text = u"Введите ID элемента"
		self.label_id.AutoSize = True
		self.label_id.Location = Point(10, 215)

		self.id_text = TextBox()
		self.id_text.Location = Point(10, 240)
		self.id_text.Size = Size(300, 26)
		self.id_text.Font = Font("Arial Narrow", 12)

		self.ok_btn = Button()
		self.ok_btn.Text = u"Показать элемент"
		self.ok_btn.Location = Point(295, 280)
		self.ok_btn.Size = Size(125, 40)
		self.ok_btn.Anchor = AnchorStyles.Bottom | AnchorStyles.Right
		self.ok_btn.Click += self._on_ok

		self.close_btn = Button()
		self.close_btn.Text = "X"
		self.close_btn.Location = Point(400, 10)
		self.close_btn.Size = Size(30, 25)
		self.close_btn.Anchor = AnchorStyles.Top | AnchorStyles.Right
		self.close_btn.Click += self._on_close

		self.Controls.Add(self.label_title)
		self.Controls.Add(self.label_link)
		self.Controls.Add(self.links_list)
		self.Controls.Add(self.label_id)
		self.Controls.Add(self.id_text)
		self.Controls.Add(self.ok_btn)
		self.Controls.Add(self.close_btn)

		self.Load += self._on_load

	def _on_load(self, sender, args):
		doc = self.uidoc.Document
		self.links = [
			l
			for l in FilteredElementCollector(doc).OfClass(RevitLinkInstance)
			if l.GetLinkDocument() is not None
		]
		for link in self.links:
			self.links_list.Items.Add(_get_link_display_name(link))

	def _on_item_check(self, sender, args):
		for i in range(self.links_list.Items.Count):
			if i != args.Index:
				self.links_list.SetItemChecked(i, False)

	def _on_ok(self, sender, args):
		selected_link = None
		for i in range(self.links_list.Items.Count):
			if self.links_list.GetItemChecked(i):
				selected_link = self.links[i]
				break
		id_text = self.id_text.Text.strip()
		_view_link_element(self.uidoc, selected_link, id_text)
		self.DialogResult = DialogResult.OK
		self.Close()

	def _on_close(self, sender, args):
		self.DialogResult = DialogResult.Cancel
		self.Close()


def main():
	uidoc = revit.uidoc
	if uidoc is None:
		forms.alert("No active document.", exitscript=True)
		return
	form = ViewLinkElementForm(uidoc)
	form.ShowDialog()


if __name__ == "__main__":
	main()
