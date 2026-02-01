# -*- coding: utf-8 -*-

from pyrevit import DB, forms

def collect_sockets(doc, target_comment):
    col_ef = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalFixtures).WhereElementIsNotElementType()
    col_ee = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType()
    
    found = []
    for col in (col_ef, col_ee):
        for e in col:
            p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if p and p.AsString() and target_comment in p.AsString():
                found.append(e)
    return found

def get_element(doc, elem_id):
    try:
        return doc.GetElement(elem_id)
    except:
        return None

def get_floor_plans(doc, level_id):
    plans = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan).WhereElementIsNotElementType().ToElements()
    candidate_plans = []
    for v in plans:
        if v.ViewType == DB.ViewType.FloorPlan and not v.IsTemplate and v.GenLevel and v.GenLevel.Id == level_id:
            candidate_plans.append(v)
    return candidate_plans

def get_3d_view(doc, view_name):
    col_views = DB.FilteredElementCollector(doc).OfClass(DB.View3D)
    for v in col_views:
        if v.Name == view_name and not v.IsTemplate:
            return v
    return None

def create_3d_view(doc, view_name):
    v_type = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType().ToElements()
    v_type_3d = [vt for vt in v_type if vt.ViewFamily == DB.ViewFamily.ThreeDimensional]
    if v_type_3d:
        try:
            view3d = DB.View3D.CreateIsometric(doc, v_type_3d[0].Id)
            view3d.Name = view_name
            return view3d
        except: 
            pass
    return None

def set_section_box(view3d, bbox):
    try:
        view3d.SetSectionBox(bbox)
        p_box = view3d.get_Parameter(DB.BuiltInParameter.VIEWER_MODEL_CLIP_BOX_ACTIVE)
        if p_box: p_box.Set(1)
    except: pass

def activate_view(uidoc, view):
    if uidoc.ActiveView.Id != view.Id:
        uidoc.ActiveView = view

def select_element(uidoc, elem_id):
    uidoc.Selection.SetElementIds([elem_id])
    uidoc.ShowElements(elem_id)