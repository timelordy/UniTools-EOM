# -*- coding: utf-8 -*-
from Autodesk.Revit.UI import TaskDialog

def run(cmd_id):
    TaskDialog.Show("UniBIM", u"Команда '{0}' пока не реализована. Перенос в работе.".format(cmd_id))
