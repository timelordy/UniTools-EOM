# -*- coding: utf-8 -*-
import clr
import System

clr.AddReference("System.Drawing")
clr.AddReference("System.Windows.Forms")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from System.Drawing import Point, Size, Font
from System.Windows.Forms import Form, TextBox, Button, Label, DialogResult, FormStartPosition, FormBorderStyle
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import revit, forms


class ShowLinkElemIdForm(Form):
	def __init__(self, elem_id):
		Form.__init__(self)
		self.Text = u"Tesla - ID элемента"
		self.FormBorderStyle = FormBorderStyle.FixedDialog
		self.StartPosition = FormStartPosition.CenterScreen
		self.MaximizeBox = False
		self.MinimizeBox = False
		self.ClientSize = Size(300, 140)

		label = Label()
		label.Text = u"ID элемента"
		label.AutoSize = True
		label.Location = Point(10, 10)

		textbox = TextBox()
		textbox.Text = elem_id
		textbox.ReadOnly = True
		textbox.Location = Point(10, 35)
		textbox.Size = Size(270, 26)
		textbox.Font = Font("Arial Narrow", 12)

		ok_btn = Button()
		ok_btn.Text = "OK"
		ok_btn.DialogResult = DialogResult.OK
		ok_btn.Location = Point(210, 90)
		ok_btn.Size = Size(70, 30)

		self.AcceptButton = ok_btn
		self.Controls.Add(label)
		self.Controls.Add(textbox)
		self.Controls.Add(ok_btn)


def _pick_linked_element_id(uidoc):
	try:
		ref = uidoc.Selection.PickObject(ObjectType.LinkedElement, u"Выберите элемент в связи")
	except OperationCanceledException:
		return None
	except Exception:
		return None
	if ref is None:
		return None
	try:
		return str(ref.LinkedElementId.IntegerValue)
	except Exception:
		return None


def main():
	uidoc = revit.uidoc
	if uidoc is None:
		forms.alert("No active document.", exitscript=True)
		return
	elem_id = _pick_linked_element_id(uidoc)
	if not elem_id:
		return
	form = ShowLinkElemIdForm(elem_id)
	form.ShowDialog()


if __name__ == "__main__":
	main()
