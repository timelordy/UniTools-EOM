# -*- coding: utf-8 -*-

from pyrevit import DB

def get_links(doc):
    return DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()

def collect_elements(doc, bic):
    return DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements()

def get_link_doc(link_inst):
    return link_inst.GetLinkDocument()

def get_categories():
    return [
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_Furniture
    ]

def get_element_names(element):
    e_name = element.Name
    try: sym = element.Symbol
    except: sym = None
    sym_name = sym.Name if sym else ""
    fam_name = sym.Family.Name if sym and sym.Family else ""
    return e_name, sym_name, fam_name

def get_category_name(doc, bic):
    try:
        return doc.Settings.Categories.get_Item(bic).Name
    except:
        return str(bic)