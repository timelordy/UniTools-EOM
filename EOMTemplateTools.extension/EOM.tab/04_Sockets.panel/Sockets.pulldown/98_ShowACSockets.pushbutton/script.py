# -*- coding: utf-8 -*-
"""
Show AC Sockets (Modeless)
"""

__persistentengine__ = True

import clr
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent

from pyrevit import DB, revit, forms, script

class SocketItem(object):
    def __init__(self, elem, doc):
        self.Id = elem.Id
        self.Name = "ID: {}".format(elem.Id.IntegerValue)
        
        # Level
        lvl_name = "?"
        try:
            lid = elem.LevelId
            l = doc.GetElement(lid)
            if l: lvl_name = l.Name
        except: pass
        
        # Location
        loc_str = ""
        try:
            loc = elem.Location
            if loc and hasattr(loc, "Point"):
                pt = loc.Point
                loc_str = "({:.1f}, {:.1f}, {:.1f})".format(pt.X, pt.Y, pt.Z)
        except: pass
        
        self.Desc = "Lvl: {} | {}".format(lvl_name, loc_str)

class ZoomHandler(IExternalEventHandler):
    def __init__(self):
        self.target_id = None
        self.mode = "3d" # "3d" or "plan"
        self.view_name = "3D_Check_AC_Sockets"
        
    def Execute(self, app):
        if not self.target_id: return
        
        uidoc = app.ActiveUIDocument
        doc = uidoc.Document
        
        try:
            t = DB.Transaction(doc, "Zoom AC Socket")
            t.Start()
            
            # 1. Find Element
            try:
                elem = doc.GetElement(self.target_id)
            except:
                t.RollBack()
                forms.alert("Элемент не найден.")
                return
                
            if not elem:
                t.RollBack()
                forms.alert("Элемент не найден (null).")
                return

            view_to_activate = None

            if self.mode == "plan":
                # Find Plan View
                lid = elem.LevelId
                if lid == DB.ElementId.InvalidElementId:
                    t.RollBack()
                    forms.alert("У элемента не задан уровень.")
                    return
                
                # Search for a Floor Plan associated with this level
                plans = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan).WhereElementIsNotElementType().ToElements()
                candidate_plans = []
                for v in plans:
                    if v.ViewType == DB.ViewType.FloorPlan and not v.IsTemplate and v.GenLevel and v.GenLevel.Id == lid:
                        candidate_plans.append(v)
                
                if not candidate_plans:
                    t.RollBack()
                    forms.alert("Не найден план этажа для уровня элемента.")
                    return
                
                # Prefer one that is not dependent? or just first
                view_to_activate = candidate_plans[0]
                # No transaction needed to just switch view, but if we want to isolate/box? No, plans are usually static.
                t.RollBack() # Cancel transaction as we are not modifying model for plan view switch
                
            else:
                # 3D Mode
                # 2. Find/Create 3D View
                view3d = None
                col_views = DB.FilteredElementCollector(doc).OfClass(DB.View3D)
                for v in col_views:
                    if v.Name == self.view_name and not v.IsTemplate:
                        view3d = v
                        break
                
                if not view3d:
                    # Create
                    v_type = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType().ToElements()
                    v_type_3d = [vt for vt in v_type if vt.ViewFamily == DB.ViewFamily.ThreeDimensional]
                    if v_type_3d:
                        try:
                            view3d = DB.View3D.CreateIsometric(doc, v_type_3d[0].Id)
                            view3d.Name = self.view_name
                        except: 
                            # Name conflict?
                            pass
                
                if not view3d:
                    t.RollBack()
                    forms.alert("Не удалось создать 3D вид '3D_Check_AC_Sockets'.")
                    return

                # 3. Set Section Box
                bb = elem.get_BoundingBox(None)
                if not bb:
                    pt = elem.Location.Point
                    d = 2.0
                    min_pt = DB.XYZ(pt.X - d, pt.Y - d, pt.Z - d)
                    max_pt = DB.XYZ(pt.X + d, pt.Y + d, pt.Z + d)
                    bb = DB.BoundingBoxXYZ()
                    bb.Min = min_pt
                    bb.Max = max_pt
                else:
                    margin = 3.0
                    bb.Min = DB.XYZ(bb.Min.X - margin, bb.Min.Y - margin, bb.Min.Z - margin)
                    bb.Max = DB.XYZ(bb.Max.X + margin, bb.Max.Y + margin, bb.Max.Z + margin)
                
                try:
                    view3d.SetSectionBox(bb)
                    p_box = view3d.get_Parameter(DB.BuiltInParameter.VIEWER_MODEL_CLIP_BOX_ACTIVE)
                    if p_box: p_box.Set(1)
                except: pass
                
                t.Commit()
                view_to_activate = view3d
            
            # 4. Activate & Select
            if view_to_activate:
                if uidoc.ActiveView.Id != view_to_activate.Id:
                    uidoc.ActiveView = view_to_activate
                
                uidoc.Selection.SetElementIds([self.target_id])
                
                if self.mode == "plan":
                    uidoc.ShowElements(self.target_id)
            
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
        
        # Manual Event Binding
        self.btnShow3D.Click += self.button_show_3d_click
        self.btnShowPlan.Click += self.button_show_plan_click
        self.btnClose.Click += self.button_close_click

    def selection_changed(self, sender, args):
        # Optional: Auto-trigger on selection?
        # Let's keep it manual via button to avoid accidental jumps, 
        # or enable it if user prefers. For now, let's rely on Button.
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

def main():
    doc = revit.doc
    target_comment = "SOCKET_AC"
    
    col_ef = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalFixtures).WhereElementIsNotElementType()
    col_ee = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType()
    
    found = []
    for col in (col_ef, col_ee):
        for e in col:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() and target_comment in p.AsString():
                found.append(e)
    
    if not found:
        forms.alert("Розетки с меткой '{}' не найдены.".format(target_comment))
        return

    items = [SocketItem(e, doc) for e in found]
    items.sort(key=lambda x: x.Name)
    
    win = MainWindow(items, doc)
    win.Show()

if __name__ == '__main__':
    main()
