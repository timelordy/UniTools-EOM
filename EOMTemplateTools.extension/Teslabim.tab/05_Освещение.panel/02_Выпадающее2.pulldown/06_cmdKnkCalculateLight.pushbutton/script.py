# -*- coding: utf-8 -*-

import json
import os

from pyrevit import revit, forms, script
from Autodesk.Revit.DB import (
    BuiltInCategory,
    FilteredElementCollector,
    AnnotationSymbol,
    ViewPlan,
    XYZ,
    Conduit,
    CableTray,
    FamilyInstance,
    BuiltInParameter,
    ElementId,
    StorageType,
    IndependentTag,
    TagOrientation,
    Reference,
    FamilySymbol,
)
from Autodesk.Revit.DB.Electrical import ElectricalSystem
from Autodesk.Revit.DB.ExtensibleStorage import (
    AccessLevel,
    Entity,
    Schema,
    SchemaBuilder,
)
from System import Guid

from unibim import knk_core, knk_switch


TITLE = u"Р РµС€РµРЅРёСЏ РїРѕ СЌР»РµРєС‚СЂРѕРѕСЃРІРµС‰РµРЅРёСЋ"
SCHEMA_GUID = "a46b718b-2f69-473b-8f4f-de0e4137593c"
SCHEMA_NAME = "TslSettings_KnkCalculateCableLengths"
FIELD_NAME = "JSON"


DEFAULT_SETTINGS = {
    "IsSpace": False,
    "IsLevel": False,
    "IsRevitLink": False,
    "IsCheckConnector": False,
    "IsDiameterConduit": False,
    "ReserveElectricalEquipment": 0.0,
    "ReserveElectricalDevise": 0.0,
    "DiameterConduit": 16.0,
    "IsChangeElectricalCircuit": False,
    "CableTrayLaying": u"Р»РѕС‚РѕРє",
    "LayingMethods": [
        u"РІ Р»РѕС‚РєРµ",
        u"Р»РѕС‚РѕРє",
        u"РѕС‚РєСЂС‹С‚Рѕ",
        u"РІ С€С‚СЂР°Р±Рµ",
        u"С€С‚СЂР°Р±Р°",
        u"Рє/Рє",
        u"РєРє",
        u"РєР°Р±РµР»СЊРЅР°СЏ С‚СЂР°СЃСЃР°",
    ],
}


ADVANCED_DEFAULTS = {
    "UseConduit": True,
    "UseCableTray": True,
    "SnapToleranceMm": 50.0,
    "FallbackDirect": True,
    "WriteCommSystem": True,
    "WriteCoreCount": True,
    "WriteSection": True,
    "WriteSwitchCodes": True,
    "MarkSwitchCodes": False,
}


SNAP_TOL_FT = None


def _get_project_info(doc):
    return (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_ProjectInformation)
        .WhereElementIsNotElementType()
        .FirstElement()
    )


def _get_or_create_schema():
    schema = Schema.Lookup(Guid(SCHEMA_GUID))
    if schema:
        return schema
    builder = SchemaBuilder(Guid(SCHEMA_GUID))
    builder.SetSchemaName(SCHEMA_NAME)
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    builder.AddSimpleField(FIELD_NAME, str)
    return builder.Finish()


def _read_settings(doc):
    schema = Schema.Lookup(Guid(SCHEMA_GUID))
    if not schema:
        return DEFAULT_SETTINGS.copy()
    project_info = _get_project_info(doc)
    entity = project_info.GetEntity(schema)
    if not entity.IsValid():
        return DEFAULT_SETTINGS.copy()
    field = schema.GetField(FIELD_NAME)
    json_text = entity.Get[str](field)
    if not json_text:
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(json_text)
    except Exception:
        return DEFAULT_SETTINGS.copy()
    for key, value in DEFAULT_SETTINGS.items():
        data.setdefault(key, value)
    return data


def _write_settings(doc, settings):
    schema = _get_or_create_schema()
    field = schema.GetField(FIELD_NAME)
    project_info = _get_project_info(doc)
    entity = Entity(schema)
    entity.Set(field, json.dumps(settings, ensure_ascii=False))
    project_info.SetEntity(entity)


def _parse_float(value, label):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        raise ValueError(label)


def _collect_floor_plans(doc):
    plans = (
        FilteredElementCollector(doc)
        .OfClass(ViewPlan)
        .ToElements()
    )
    return [vp for vp in plans if not vp.IsTemplate]


def _select_floor_plans(doc):
    plans = _collect_floor_plans(doc)
    if not plans:
        forms.alert(u"Планы этажей не найдены.", title=TITLE, warn_icon=True)
        return []
    return plans


def _show_settings_dialog(settings):
    components = [
        forms.Label(u"РќР°СЃС‚СЂРѕР№РєРё"),
        forms.CheckBox("IsRevitLink", u"РСЃРїРѕР»СЊР·РѕРІР°С‚СЊ СЃРІСЏР·СЊ Revit", default=settings["IsRevitLink"]),
        forms.CheckBox("IsDiameterConduit", u"РЈС‡РёС‚С‹РІР°С‚СЊ РґРёР°РјРµС‚СЂ РіРѕС„СЂС‹", default=settings["IsDiameterConduit"]),
        forms.CheckBox("IsChangeElectricalCircuit", u"РР·РјРµРЅСЏС‚СЊ РЅРѕРјРµСЂР° С†РµРїРµР№", default=settings["IsChangeElectricalCircuit"]),
        forms.Label(u"Р—Р°РїР°СЃ РЅР° РѕР±РѕСЂСѓРґРѕРІР°РЅРёРµ (%)"),
        forms.TextBox("ReserveElectricalEquipment", default=str(settings["ReserveElectricalEquipment"])),
        forms.Label(u"Р—Р°РїР°СЃ РЅР° СѓСЃС‚СЂРѕР№СЃС‚РІР° (%)"),
        forms.TextBox("ReserveElectricalDevise", default=str(settings["ReserveElectricalDevise"])),
        forms.Label(u"Р”РёР°РјРµС‚СЂ РіРѕС„СЂС‹ (РјРј)"),
        forms.TextBox("DiameterConduit", default=str(settings["DiameterConduit"])),
        forms.Label(u"РЎРїРѕСЃРѕР±С‹ РїСЂРѕРєР»Р°РґРєРё (РїРѕ РѕРґРЅРѕРјСѓ РЅР° СЃС‚СЂРѕРєСѓ)"),
        forms.TextBox("LayingMethods", default="\n".join(settings["LayingMethods"]), multiline=True),
        forms.Separator(),
        forms.Button(u"OK"),
    ]
    form = forms.FlexForm(TITLE, components)
    form.show()
    if not form.values:
        return None
    try:
        settings["IsRevitLink"] = bool(form.values.get("IsRevitLink"))
        settings["IsDiameterConduit"] = bool(form.values.get("IsDiameterConduit"))
        settings["IsChangeElectricalCircuit"] = bool(form.values.get("IsChangeElectricalCircuit"))
        settings["ReserveElectricalEquipment"] = _parse_float(
            form.values.get("ReserveElectricalEquipment"), u"Р—Р°РїР°СЃ РЅР° РѕР±РѕСЂСѓРґРѕРІР°РЅРёРµ"
        )
        settings["ReserveElectricalDevise"] = _parse_float(
            form.values.get("ReserveElectricalDevise"), u"Р—Р°РїР°СЃ РЅР° СѓСЃС‚СЂРѕР№СЃС‚РІР°"
        )
        settings["DiameterConduit"] = _parse_float(
            form.values.get("DiameterConduit"), u"Р”РёР°РјРµС‚СЂ РіРѕС„СЂС‹"
        )
        methods_raw = form.values.get("LayingMethods") or ""
        settings["LayingMethods"] = [m.strip() for m in methods_raw.splitlines() if m.strip()]
        if not settings["LayingMethods"]:
            settings["LayingMethods"] = list(DEFAULT_SETTINGS["LayingMethods"])
    except ValueError as err:
        forms.alert(u"РќРµРєРѕСЂСЂРµРєС‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ: {0}".format(err), title=TITLE, warn_icon=True)
        return None
    return settings


def _show_advanced_dialog(advanced):
    components = [
        forms.Label(u"Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё"),
        forms.CheckBox("UseConduit", u"РЈС‡РёС‚С‹РІР°С‚СЊ С‚СЂСѓР±С‹", default=advanced["UseConduit"]),
        forms.CheckBox("UseCableTray", u"РЈС‡РёС‚С‹РІР°С‚СЊ Р»РѕС‚РєРё", default=advanced["UseCableTray"]),
        forms.CheckBox("FallbackDirect", u"Р•СЃР»Рё РїСѓС‚СЊ РЅРµ РЅР°Р№РґРµРЅ вЂ” СЃС‡РёС‚Р°С‚СЊ РїРѕ РїСЂСЏРјРѕР№", default=advanced["FallbackDirect"]),
        forms.CheckBox("WriteCommSystem", u"Р—Р°РїРёСЃС‹РІР°С‚СЊ TSL_РЎРёСЃС‚РµРјР° РєРѕРјРјСѓС‚Р°С†РёРё", default=advanced["WriteCommSystem"]),
        forms.CheckBox("WriteCoreCount", u"Р—Р°РїРёСЃС‹РІР°С‚СЊ TSL_РљРѕР»РёС‡РµСЃС‚РІРѕ Р¶РёР» РїСЂРѕРІРѕРґРЅРёРєР° РЅР° С‚СЂР°СЃСЃРµ", default=advanced["WriteCoreCount"]),
        forms.CheckBox("WriteSection", u"Р—Р°РїРёСЃС‹РІР°С‚СЊ TSL_РЎРµС‡РµРЅРёРµ Р¶РёР» РїСЂРѕРІРѕРґРЅРёРєР°", default=advanced["WriteSection"]),
        forms.CheckBox("WriteSwitchCodes", u"Р—Р°РїРёСЃС‹РІР°С‚СЊ TSL_РљРѕРґ РїРµСЂРµРєР»СЋС‡Р°С‚РµР»СЏ", default=advanced["WriteSwitchCodes"]),
        forms.CheckBox("MarkSwitchCodes", u"РњР°СЂРєРёСЂРѕРІР°С‚СЊ РєРѕРґ РїРµСЂРµРєР»СЋС‡Р°С‚РµР»СЏ РЅР° РїР»Р°РЅРµ", default=advanced["MarkSwitchCodes"]),
        forms.Label(u"РўРѕР»РµСЂР°РЅСЃ СЃС‚С‹РєРѕРІРєРё, РјРј"),
        forms.TextBox("SnapToleranceMm", default=str(advanced["SnapToleranceMm"])),
        forms.Separator(),
        forms.Button(u"OK"),
    ]
    form = forms.FlexForm(TITLE + u" вЂ” РґРѕРї. РЅР°СЃС‚СЂРѕР№РєРё", components)
    form.show()
    if not form.values:
        return None
    try:
        advanced["UseConduit"] = bool(form.values.get("UseConduit"))
        advanced["UseCableTray"] = bool(form.values.get("UseCableTray"))
        advanced["FallbackDirect"] = bool(form.values.get("FallbackDirect"))
        advanced["WriteCommSystem"] = bool(form.values.get("WriteCommSystem"))
        advanced["WriteCoreCount"] = bool(form.values.get("WriteCoreCount"))
        advanced["WriteSection"] = bool(form.values.get("WriteSection"))
        advanced["WriteSwitchCodes"] = bool(form.values.get("WriteSwitchCodes"))
        advanced["MarkSwitchCodes"] = bool(form.values.get("MarkSwitchCodes"))
        advanced["SnapToleranceMm"] = _parse_float(form.values.get("SnapToleranceMm"), u"РўРѕР»РµСЂР°РЅСЃ СЃС‚С‹РєРѕРІРєРё, РјРј")
    except ValueError as err:
        forms.alert(u"РќРµРєРѕСЂСЂРµРєС‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ: {0}".format(err), title=TITLE, warn_icon=True)
        return None
    return advanced


def _select_systems_ui(all_systems):
    picked = forms.SelectFromList.show(
        all_systems,
        name_attr="Name",
        multiselect=True,
        title=u"Р’С‹Р±РµСЂРёС‚Рµ С†РµРїРё (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)",
        button_name=u"РџСЂРѕРґРѕР»Р¶РёС‚СЊ",
    )
    return picked or []


def _collect_electrical_systems(doc):
    try:
        return list(FilteredElementCollector(doc).OfClass(ElectricalSystem).ToElements())
    except Exception:
        return []


def _get_selected_systems(doc, uidoc, all_systems):
    sel_ids = uidoc.Selection.GetElementIds()
    if not sel_ids or sel_ids.Count == 0:
        return []
    by_name = {s.Name: s for s in all_systems}
    picked = []
    for eid in sel_ids:
        elem = doc.GetElement(eid)
        if isinstance(elem, ElectricalSystem):
            picked.append(elem)
            continue
        if isinstance(elem, AnnotationSymbol):
            try:
                param = elem.LookupParameter(u"РќРѕРјРµСЂ С†РµРїРё")
            except Exception:
                param = None
            if param:
                name = param.AsString()
                if name in by_name:
                    picked.append(by_name[name])
    # unique by id
    uniq = {}
    for s in picked:
        try:
            uniq[int(s.Id.IntegerValue)] = s
        except Exception:
            uniq[s] = s
    return list(uniq.values())


def _xyz_to_tuple(pt):
    x = float(pt.X)
    y = float(pt.Y)
    z = float(pt.Z)
    if SNAP_TOL_FT and SNAP_TOL_FT > 0:
        x = round(x / SNAP_TOL_FT) * SNAP_TOL_FT
        y = round(y / SNAP_TOL_FT) * SNAP_TOL_FT
        z = round(z / SNAP_TOL_FT) * SNAP_TOL_FT
    return (x, y, z)


def _iter_connectors(element):
    try:
        if isinstance(element, (Conduit, CableTray)):
            return list(element.ConnectorManager.Connectors)
    except Exception:
        pass
    try:
        if isinstance(element, FamilyInstance) and element.MEPModel:
            return list(element.MEPModel.ConnectorManager.Connectors)
    except Exception:
        pass
    return []


def _collect_path_edges(doc, use_conduit=True, use_tray=True):
    edges = []
    if use_conduit:
        for el in FilteredElementCollector(doc).OfClass(Conduit).ToElements():
            conns = _iter_connectors(el)
            if len(conns) >= 2:
                p1 = _xyz_to_tuple(conns[0].Origin)
                p2 = _xyz_to_tuple(conns[1].Origin)
                edges.append((p1, p2, el.Id.IntegerValue))
    if use_tray:
        for el in FilteredElementCollector(doc).OfClass(CableTray).ToElements():
            conns = _iter_connectors(el)
            if len(conns) >= 2:
                p1 = _xyz_to_tuple(conns[0].Origin)
                p2 = _xyz_to_tuple(conns[1].Origin)
                edges.append((p1, p2, el.Id.IntegerValue))

    for bic in (BuiltInCategory.OST_ConduitFitting, BuiltInCategory.OST_CableTrayFitting):
        for el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements():
            conns = _iter_connectors(el)
            if len(conns) >= 2:
                for i in range(len(conns)):
                    for j in range(i + 1, len(conns)):
                        p1 = _xyz_to_tuple(conns[i].Origin)
                        p2 = _xyz_to_tuple(conns[j].Origin)
                        edges.append((p1, p2, el.Id.IntegerValue))
    return edges


def _get_system_line_count(system):
    try:
        p1 = system.get_Parameter(BuiltInParameter.RBS_ELEC_NUM_UNGROUNDED_CONDUCTORS)
    except Exception:
        p1 = None
    if p1:
        return p1.AsInteger()
    total = 0
    for pid in (-1140100, -1140099, -1140098):
        try:
            val = system.get_Parameter(BuiltInParameter(pid))
            if val:
                total += val.AsInteger()
        except Exception:
            continue
    return total


def _append_param_value(param, text):
    if param is None:
        return
    try:
        cur = param.AsString() or ""
        values = [v.strip() for v in cur.split("\n") if v.strip()]
        if text not in values:
            values.append(text)
            param.Set("\n".join(values))
    except Exception:
        pass


def _get_param_value(elem, name):
    if elem is None:
        return None
    try:
        param = elem.LookupParameter(name)
    except Exception:
        param = None
    if param is None or not param.HasValue:
        return None
    try:
        if param.StorageType == StorageType.String:
            return param.AsString()
        if param.StorageType == StorageType.Double:
            return param.AsDouble()
        if param.StorageType == StorageType.Integer:
            return param.AsInteger()
    except Exception:
        return None
    return None


def _set_param_value(param, value):
    if param is None:
        return False
    try:
        if param.StorageType == StorageType.String:
            param.Set(str(value))
            return True
        if param.StorageType == StorageType.Double:
            param.Set(float(value))
            return True
        if param.StorageType == StorageType.Integer:
            param.Set(int(value))
            return True
    except Exception:
        return False
    try:
        param.Set(str(value))
        return True
    except Exception:
        return False


def _get_name_blob(elem):
    parts = []
    try:
        if elem.Name:
            parts.append(elem.Name)
    except Exception:
        pass
    try:
        if elem.Symbol and elem.Symbol.FamilyName:
            parts.append(elem.Symbol.FamilyName)
    except Exception:
        pass
    try:
        if elem.Symbol and elem.Symbol.Name:
            parts.append(elem.Symbol.Name)
    except Exception:
        pass
    return " ".join(parts).lower()


def _is_light_elem(elem):
    try:
        return elem.Category and elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_LightingFixtures)
    except Exception:
        return False


def _is_switch_elem(elem):
    try:
        if elem.Category:
            cat_id = elem.Category.Id.IntegerValue
            if cat_id in (
                int(BuiltInCategory.OST_ElectricalFixtures),
                int(BuiltInCategory.OST_LightingDevices),
            ):
                return True
    except Exception:
        pass
    name_blob = _get_name_blob(elem)
    for key in ("выключ", "переключ", "кноп", "switch", "toggle", "button"):
        if key in name_blob:
            return True
    return False


def _is_commutation_family(elem):
    try:
        return elem.Symbol.FamilyName == u"TSL_LD_э_КР (коммутация)"
    except Exception:
        return False


def _get_location_point(elem):
    try:
        loc = elem.Location
    except Exception:
        loc = None
    if loc is None:
        return None
    try:
        return loc.Point
    except Exception:
        pass
    try:
        return loc.Curve.Evaluate(0.5, True)
    except Exception:
        return None


def _parse_commutation_groups(text):
    groups = []
    if not text:
        return groups
    for chunk in text.split(')'):
        chunk = chunk.strip()
        if not chunk or '=' not in chunk:
            continue
        parts = chunk.split('=')
        if len(parts) != 2:
            continue
        left = parts[0].replace('(', '').replace(' ', '')
        right = parts[1].replace('>', '').replace(' ', '')
        left_ids = [int(x) for x in left.split(';') if x]
        right_ids = [int(x) for x in right.split(';') if x]
        if left_ids or right_ids:
            groups.append((left_ids, right_ids))
    return groups


def _build_switch_segments(system, lights, switches):
    light_ids = [l.Id.IntegerValue for l in lights]
    switch_ids = [s.Id.IntegerValue for s in switches]
    light_set = set(light_ids)
    switch_set = set(switch_ids)

    groups = []
    for elem in system.Elements:
        try:
            text = elem.LookupParameter(u"TSL_Система коммутации").AsString()
        except Exception:
            text = None
        if text and "(" in text and "=" in text:
            groups = _parse_commutation_groups(text)
            if groups:
                break

    segments = []
    if groups:
        for left_ids, right_ids in groups:
            l_ids = [i for i in left_ids if i in light_set]
            d_ids = [i for i in left_ids if i in switch_set]
            for rid in right_ids:
                if rid in switch_set and rid not in d_ids:
                    d_ids.append(rid)
                if rid in light_set and rid not in l_ids:
                    l_ids.append(rid)
            base_id = d_ids[0] if d_ids else (right_ids[0] if right_ids else None)
            if base_id is None:
                continue
            segments.append({
                "base_id": base_id,
                "light_ids": l_ids,
                "device_ids": d_ids,
            })
    else:
        if light_ids:
            base_id = switch_ids[0] if switch_ids else light_ids[0]
            segments.append({
                "base_id": base_id,
                "light_ids": light_ids,
                "device_ids": switch_ids,
            })
    return segments


def _get_section_value(system, base):
    for name in (u"TSL_Сечение жил проводника", u"Сечение проводника"):
        val = _get_param_value(system, name)
        if val not in (None, "", 0):
            return val
    for name in (u"Сечение проводника",):
        val = _get_param_value(base, name)
        if val not in (None, "", 0):
            return val
    return None


def _get_tag_symbol(doc, category, name_mark):
    symbols = (
        FilteredElementCollector(doc)
        .OfCategory(category)
        .WhereElementIsElementType()
        .OfClass(FamilySymbol)
        .ToElements()
    )
    for sym in symbols:
        try:
            if name_mark in sym.Name:
                return sym
        except Exception:
            continue
    return None


def _tag_elements(doc, view, light_tag, switch_tag, element_ids):
    for eid in element_ids:
        elem = doc.GetElement(ElementId(eid))
        if elem is None:
            continue
        pt = _get_location_point(elem)
        if pt is None:
            continue
        if _is_light_elem(elem) and light_tag is not None:
            tag_type = light_tag.Id
            offset = XYZ(0.2, 0.2, 0.0)
        elif switch_tag is not None:
            tag_type = switch_tag.Id
            offset = XYZ(0.7, 0.7, 0.0)
        else:
            continue
        try:
            IndependentTag.Create(doc, tag_type, view.Id, Reference(elem), False, TagOrientation.Horizontal, pt + offset)
        except Exception:
            continue


doc = revit.doc

selected_plans = _select_floor_plans(doc)
if not selected_plans:
    script.exit()

settings = _read_settings(doc)
settings = _show_settings_dialog(settings)
if settings is None:
    script.exit()

advanced = ADVANCED_DEFAULTS.copy()
advanced = _show_advanced_dialog(advanced)
if advanced is None:
    script.exit()

SNAP_TOL_FT = advanced["SnapToleranceMm"] / 304.8

with revit.Transaction(TITLE + u" - РЅР°СЃС‚СЂРѕР№РєРё"):
    _write_settings(doc, settings)

all_systems = _collect_electrical_systems(doc)
if not all_systems:
    forms.alert(
        u"Р’ РґР°РЅРЅРѕРј С„Р°Р№Р»Рµ РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚ СЌР»РµРєС‚СЂРёС‡РµСЃРєРёРµ С†РµРїРё.",
        title=TITLE,
        warn_icon=True,
    )
    script.exit()

selected_systems = _get_selected_systems(doc, revit.uidoc, all_systems)
if not selected_systems:
    selected_systems = _select_systems_ui(all_systems)
systems_to_process = selected_systems if selected_systems else all_systems

edges = _collect_path_edges(doc, advanced["UseConduit"], advanced["UseCableTray"])
graph = knk_core.build_graph(edges)
edge_element_ids = set([eid for (_, _, eid) in edges])
edge_elements = {eid: doc.GetElement(ElementId(eid)) for eid in edge_element_ids}

total_paths = 0
total_length = 0.0
path_data = {}
updated_devices = 0
updated_light_codes = 0
updated_switch_codes = 0
core_written = 0
section_written = 0
tag_targets = set()

with revit.Transaction(TITLE + u" - расчет"):
    for system in systems_to_process:
        base = system.BaseEquipment
        if base is None:
            continue
        try:
            base_pt = base.Location.Point
        except Exception:
            base_pt = None
        if base_pt is None:
            continue

        line_count = _get_system_line_count(system)
        section_value = _get_section_value(system, base)

        if advanced["WriteSwitchCodes"]:
            lights = [e for e in system.Elements if _is_light_elem(e)]
            switches = [e for e in system.Elements if _is_switch_elem(e)]
            segments = _build_switch_segments(system, lights, switches)
            codes = knk_switch.assign_switch_codes(segments)
            for lid, code in codes.get("light_codes", {}).items():
                elem = doc.GetElement(ElementId(lid))
                if elem is None or not _is_light_elem(elem):
                    continue
                if _set_param_value(elem.LookupParameter(u"TSL_Код переключателя"), code):
                    updated_light_codes += 1
                    tag_targets.add(lid)
            for sid, codestr in codes.get("switch_codes", {}).items():
                elem = doc.GetElement(ElementId(sid))
                if elem is None or not _is_switch_elem(elem):
                    continue
                if _is_commutation_family(elem):
                    continue
                if _set_param_value(elem.LookupParameter(u"TSL_Код переключателя"), codestr):
                    updated_switch_codes += 1
                    tag_targets.add(sid)
        for elem in system.Elements:
            if elem.Id == base.Id:
                continue
            try:
                loc = elem.Location
                pt = loc.Point if loc else None
            except Exception:
                pt = None
            if pt is None:
                continue

            length, used = knk_core.shortest_path(graph, _xyz_to_tuple(base_pt), _xyz_to_tuple(pt))
            if length == 0.0 and advanced["FallbackDirect"]:
                try:
                    length = base_pt.DistanceTo(pt)
                except Exception:
                    length = 0.0
            if length > 0.0:
                total_paths += 1
                total_length += length

            for eid in used:
                data = path_data.setdefault(eid, {"systems": set(), "core_counts": [], "sections": []})
                data["systems"].add(system.Name)
                if line_count > 0:
                    data["core_counts"].append(line_count)
                if section_value is not None:
                    data["sections"].append(section_value)

            if advanced["WriteCommSystem"]:
                try:
                    param = elem.LookupParameter(u"TSL_Система коммутации")
                    _append_param_value(param, system.Name)
                    updated_devices += 1
                except Exception:
                    pass

    for eid, data in path_data.items():
        el = edge_elements.get(eid)
        if el is None:
            continue
        if advanced["WriteCoreCount"] and data.get("core_counts"):
            param = el.LookupParameter(u"TSL_Количество жил проводника")
            if param is not None:
                if param.StorageType == StorageType.String:
                    uniq = []
                    for v in data["core_counts"]:
                        sv = str(v)
                        if sv not in uniq:
                            uniq.append(sv)
                    value = "/".join(uniq)
                else:
                    value = max(data["core_counts"])
                if _set_param_value(param, value):
                    core_written += 1
        if advanced["WriteSection"] and data.get("sections"):
            param = el.LookupParameter(u"TSL_Сечение жил проводника")
            if param is not None:
                if param.StorageType == StorageType.String:
                    uniq = []
                    for v in data["sections"]:
                        sv = str(v)
                        if sv not in uniq:
                            uniq.append(sv)
                    value = "/".join(uniq)
                else:
                    value = data["sections"][0]
                if _set_param_value(param, value):
                    section_written += 1

    if advanced["WriteSwitchCodes"] and advanced["MarkSwitchCodes"]:
        if isinstance(doc.ActiveView, ViewPlan) and tag_targets:
            name_mark = u"Код переключателя"
            light_tag = _get_tag_symbol(doc, BuiltInCategory.OST_LightingFixtureTags, name_mark)
            switch_tag = _get_tag_symbol(doc, BuiltInCategory.OST_ElectricalFixtureTags, name_mark)
            if light_tag is not None and not light_tag.IsActive:
                light_tag.Activate()
            if switch_tag is not None and not switch_tag.IsActive:
                switch_tag.Activate()
            if light_tag is not None or switch_tag is not None:
                _tag_elements(doc, doc.ActiveView, light_tag, switch_tag, tag_targets)
            else:
                forms.alert(
                    u"Не найдены типы марок с именем \"Код переключателя\".",
                    title=TITLE,
                    warn_icon=True,
                )

forms.alert(
    u"Готово.\n"
    u"Планов этажей: {0}\n"
    u"Цепей обработано: {1}\n"
    u"Путей найдено: {2}\n"
    u"Суммарная длина (м): {3:.2f}\n"
    u"Обновлено приборов (система коммутации): {4}\n"
    u"Код переключателя: светильников {5}, выключателей {6}\n"
    u"Участков трасс с записью жил: {7}, сечений: {8}".format(
        len(selected_plans),
        len(systems_to_process),
        total_paths,
        total_length * 0.3048,
        updated_devices,
        updated_light_codes,
        updated_switch_codes,
        core_written,
        section_written,
    ),
    title=TITLE,
)



