# -*- coding: utf-8 -*-

import clr
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
from pyrevit import DB, forms

import adapters
import constants
import domain

class ZoomHandler(IExternalEventHandler):
    def __init__(self):
        self.target_id = None
        self.mode = "3d" # "3d" or "plan"
        self.view_name = constants.VIEW_NAME_3D
        
    def Execute(self, app):
        if not self.target_id: return
        
        uidoc = app.ActiveUIDocument
        doc = uidoc.Document
        
        try:
            t = DB.Transaction(doc, "Zoom AC Socket")
            t.Start()
            
            elem = adapters.get_element(doc, self.target_id)
            if not elem:
                t.RollBack()
                forms.alert("Элемент не найден.")
                return

            view_to_activate = None

            if self.mode == "plan":
                lid = elem.LevelId
                if lid == DB.ElementId.InvalidElementId:
                    t.RollBack()
                    forms.alert("У элемента не задан уровень.")
                    return
                
                candidate_plans = adapters.get_floor_plans(doc, lid)
                if not candidate_plans:
                    t.RollBack()
                    forms.alert("Не найден план этажа для уровня элемента.")
                    return
                
                view_to_activate = candidate_plans[0]
                t.RollBack()
                
            else:
                view3d = adapters.get_3d_view(doc, self.view_name)
                if not view3d:
                    view3d = adapters.create_3d_view(doc, self.view_name)
                
                if not view3d:
                    t.RollBack()
                    forms.alert("Не удалось создать 3D вид '{}'.".format(self.view_name))
                    return

                bb = domain.calculate_bbox(elem)
                adapters.set_section_box(view3d, bb)
                
                t.Commit()
                view_to_activate = view3d
            
            if view_to_activate:
                adapters.activate_view(uidoc, view_to_activate)
                adapters.select_element(uidoc, self.target_id)
            
        except Exception as e:
            forms.alert("Ошибка при переходе: {}".format(e))

    def GetName(self):
        return "ZoomHandler"

class MainWindow(forms.WPFWindow):
    def __init__(self, items, doc):
        forms.WPFWindow.__init__(self, 'UserInterface.xaml')
        self.doc = doc
        self.handler = ZoomHandler()
        self.ext_event = ExternalEvent.Create(self.handler)
        
        self.socket_list.ItemsSource = items
        
        self.btnShow3D.Click += self.button_show_3d_click
        self.btnShowPlan.Click += self.button_show_plan_click
        self.btnClose.Click += self.button_close_click

    def selection_changed(self, sender, args):
        pass

    def button_show_3d_click(self, sender, args):
        item = self.socket_list.SelectedItem
        if item:
            self.handler.target_id = item.Id
            self.handler.mode = "3d"
            self.ext_event.Raise()
        else:
            forms.alert("Выберите элемент из списка.")

    def button_show_plan_click(self, sender, args):
        item = self.socket_list.SelectedItem
        if item:
            self.handler.target_id = item.Id
            self.handler.mode = "plan"
            self.ext_event.Raise()
        else:
            forms.alert("Выберите элемент из списка.")

    def button_close_click(self, sender, args):
        self.Close()