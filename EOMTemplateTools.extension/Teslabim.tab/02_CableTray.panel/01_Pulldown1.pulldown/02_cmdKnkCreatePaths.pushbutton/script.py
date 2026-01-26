# -*- coding: utf-8 -*-

from pyrevit import revit

import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (  # noqa: E402
    BuiltInCategory,
    BuiltInParameter,
    CableTray,
    Conduit,
    ConduitType,
    Curve,
    Domain,
    ElementId,
    FamilyInstance,
    FilteredElementCollector,
    Line,
    LocationCurve,
    LocationPoint,
    Transaction,
    Transform,
    XYZ,
)
from Autodesk.Revit.DB.Electrical import ElectricalEquipmentCircuitType  # noqa: E402
from Autodesk.Revit.UI import (  # noqa: E402
    TaskDialog,
    TaskDialogCommandLinkId,
    TaskDialogCommonButtons,
    TaskDialogIcon,
    TaskDialogResult,
)
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType  # noqa: E402

from unibim.knk_create_paths_utils import LINE_EPS, should_create_segment  # noqa: E402
from System import Guid  # noqa: E402


CAPTION = u"Создать пути до трассы"
CONDUIT_TYPE_NAME = u"CN_с_Трасса кабельной линии"
TRIPLE_FAMILY_NAME = u"CNF_с_Трасса кабельной линии_Тройник"


class _FamilySelectionByElectricalSystemFilter(ISelectionFilter):
    def AllowElement(self, element):
        family = element if isinstance(element, FamilyInstance) else None
        if family and family.MEPModel:
            try:
                systems = list(family.MEPModel.GetElectricalSystems())
            except Exception:
                systems = []
            if systems:
                return True
        name = element.Name or ""
        if u"TSL_2D автоматический выключатель_ВРУ" in name:
            return True
        if u"TSL_2D автоматический выключатель_Щит" in name:
            return True
        return False

    def AllowReference(self, reference, position):
        return False


def _get_electrical_system(family_instance):
    if family_instance is None or family_instance.MEPModel is None:
        return None
    try:
        systems = list(family_instance.MEPModel.GetElectricalSystems())
    except Exception:
        systems = []
    if not systems:
        return None
    for sys in systems:
        try:
            if sys.CircuitType == ElectricalEquipmentCircuitType.Incoming:
                return sys
        except Exception:
            pass
    return systems[0]


def _get_location_point(element):
    loc = element.Location
    return loc.Point if isinstance(loc, LocationPoint) else None


def _get_location_curve(element):
    loc = element.Location
    return loc.Curve if isinstance(loc, LocationCurve) else None


def _get_connector(xyz, element):
    connector_set = None
    if isinstance(element, Conduit):
        connector_set = element.ConnectorManager.Connectors
    elif isinstance(element, CableTray):
        connector_set = element.ConnectorManager.Connectors
    elif isinstance(element, FamilyInstance):
        connector_set = element.MEPModel.ConnectorManager.Connectors
    if connector_set is None:
        return None
    for conn in connector_set:
        try:
            if conn.Origin.IsAlmostEqualTo(xyz, 1E-05):
                return conn
        except Exception:
            continue
    return None


def _set_diameter(element, diameter):
    if element is None:
        return
    if isinstance(element, Conduit):
        try:
            param = element.get_Parameter(BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM)
            if param:
                param.Set(diameter)
        except Exception:
            pass
        return
    if isinstance(element, FamilyInstance):
        try:
            guid = Guid("9b679ab7-ea2e-49ce-90ab-0549d5aa36ff")
            param = element.get_Parameter(guid)
            if param:
                param.Set(diameter)
        except Exception:
            pass


def _create_perpendicular_point(line, element1, element2):
    point = _get_location_point(element1)
    if point is None:
        return None
    if line is None:
        point2 = _get_location_point(element2)
        if point2 is None:
            return None
        try:
            transform = element2.GetTransform()
        except Exception:
            transform = Transform.Identity
        basis = transform.BasisX
        line2 = Line.CreateBound(point2 + basis * 1000.0, point2 - basis * 1000.0)
        return line2.Project(point).XYZPoint
    if (
        round(line.Direction.X, 5) == 0.0
        and round(line.Direction.Y, 5) == 0.0
        and round(abs(line.Direction.Z), 5) == 1.0
    ):
        try:
            transform = element1.GetTransform()
        except Exception:
            transform = Transform.Identity
        basis = transform.BasisX
        line2 = Line.CreateBound(point + basis * 1000.0, point - basis * 1000.0)
        proj = line.Project(point).XYZPoint
        proj2 = line2.Project(proj).XYZPoint
        return XYZ(proj2.X, proj2.Y, proj.Z)
    direction = line.Direction.Normalize()
    proj = line.Project(point).XYZPoint
    line2 = Line.CreateBound(proj + direction * 1000.0, proj - direction * 1000.0)
    return line2.Project(point).XYZPoint


def _find_shortest_element(element, elements):
    point = _get_location_point(element)
    if point is None:
        return None
    trays = [e for e in elements if isinstance(e, (CableTray, Conduit))]
    if not trays:
        TaskDialog.Show(CAPTION, u"В модели отсутствуют лотки и короба")
        return None
    best = trays[0]
    try:
        best_dist = _get_location_curve(best).Distance(point)
    except Exception:
        best_dist = 1e30
    for item in trays:
        try:
            dist = _get_location_curve(item).Distance(point)
        except Exception:
            continue
        if dist < best_dist:
            best_dist = dist
            best = item
    return best


def _get_connected_elements(element):
    result = []
    connector_set = None
    if isinstance(element, Conduit):
        connector_set = element.ConnectorManager.Connectors
    elif isinstance(element, CableTray):
        connector_set = element.ConnectorManager.Connectors
    elif isinstance(element, FamilyInstance):
        connector_set = element.MEPModel.ConnectorManager.Connectors
    if connector_set is None:
        return result
    for conn in connector_set:
        try:
            if conn.Domain == Domain.DomainUndefined or not conn.IsConnected:
                continue
        except Exception:
            continue
        for ref in conn.AllRefs:
            try:
                if ref.Domain == Domain.DomainUndefined or not ref.IsConnected:
                    continue
            except Exception:
                continue
            if ref.Owner.Id != element.Id:
                result.append(ref.Owner)
    return result


def _build_graph(element, graph, graph_ids):
    graph.append(element)
    graph_ids.add(element.Id)
    for ref in _get_connected_elements(element):
        if ref.Id not in graph_ids:
            graph.append(ref)
            graph_ids.add(ref.Id)
            _build_graph(ref, graph, graph_ids)


def _create_conduit(doc, type_id, p1, p2, level_id, diameter, graph):
    if not should_create_segment(p1, p2):
        return None
    conduit = Conduit.Create(doc, type_id, p1, p2, level_id)
    _set_diameter(conduit, diameter)
    graph.append(conduit)
    return conduit


def _get_conduit_type_id(doc):
    conduit_types = (
        FilteredElementCollector(doc)
        .WhereElementIsElementType()
        .OfClass(ConduitType)
        .ToElements()
    )
    for ct in conduit_types:
        if CONDUIT_TYPE_NAME in ct.Name:
            return ct.Id
    return None


def _ensure_triple_family(doc):
    families = (
        FilteredElementCollector(doc)
        .WhereElementIsElementType()
        .ToElements()
    )
    for f in families:
        if TRIPLE_FAMILY_NAME in f.Name:
            return True
    return False


def _create_path_between(doc, element1, element2, graph):
    curve = _get_location_curve(element2)
    point = _get_location_point(element1)
    if point is None:
        return
    if curve is None:
        target_point = _get_location_point(element2)
    else:
        target_point = curve.Project(point).XYZPoint

    type_id = None
    diameter = 0.00328083989501312
    if isinstance(element2, Conduit):
        type_id = element2.GetTypeId()
        try:
            diameter = element2.get_Parameter(BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM).AsDouble()
        except Exception:
            pass
    else:
        type_id = _get_conduit_type_id(doc)
        if type_id is None:
            dlg = TaskDialog(CAPTION)
            dlg.MainInstruction = u"Предупреждение!"
            dlg.MainContent = u"Загрузите в модель короб \"TSL_CN_с_Трасса кабельной линии\""
            dlg.MainIcon = TaskDialogIcon.Warning
            dlg.Show()
            return

    if not _ensure_triple_family(doc):
        TaskDialog.Show(CAPTION, u"В данном файле отсутствует семейство {0}".format(TRIPLE_FAMILY_NAME))
        return

    level_id = element1.LevelId
    perp_point = _create_perpendicular_point(curve if isinstance(curve, Line) else None, element1, element2)
    if perp_point is None:
        return

    z_delta = target_point.Z - point.Z
    vertical_point = XYZ(point.X, point.Y, point.Z + z_delta)

    seg1 = _create_conduit(doc, type_id, point, vertical_point, level_id, diameter, graph)
    seg2 = _create_conduit(doc, type_id, vertical_point, perp_point, level_id, diameter, graph)
    seg3 = _create_conduit(doc, type_id, perp_point, target_point, level_id, diameter, graph)

    if seg1 and seg2:
        c1 = _get_connector(vertical_point, seg1)
        c2 = _get_connector(vertical_point, seg2)
        if c1 and c2:
            c1.ConnectTo(c2)
    if seg2 and seg3:
        c3 = _get_connector(perp_point, seg2)
        c4 = _get_connector(perp_point, seg3)
        if c3 and c4:
            c3.ConnectTo(c4)
    if seg3:
        c5 = _get_connector(target_point, seg3)
        c6 = _get_connector(target_point, element2)
        if c5 and c6 and (not c6.IsConnected) and (c5.Domain == c6.Domain):
            c5.ConnectTo(c6)


def main():
    uidoc = revit.uidoc
    doc = revit.doc
    sel = uidoc.Selection

    dlg = TaskDialog(CAPTION)
    dlg.MainInstruction = u"Выберите способ создания коробов"
    dlg.CommonButtons = TaskDialogCommonButtons.Cancel
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink1,
        u"Соединить все элементы в цепи",
        u"Будут созданы короба для всех потребителей в электрической цепи.",
    )
    dlg.AddCommandLink(
        TaskDialogCommandLinkId.CommandLink2,
        u"Соединить выбранный элемент",
        u"Будут созданы короба между двумя выбранными элементами.",
    )
    res = dlg.Show()
    if res == TaskDialogResult.Cancel:
        return

    graph = []
    graph_ids = set()

    if res == TaskDialogCommandLinkId.CommandLink2:
        try:
            ref1 = sel.PickObject(ObjectType.Element, _FamilySelectionByElectricalSystemFilter(), u"Выберите элемент в цепи")
            ref2 = sel.PickObject(ObjectType.Element, u"Выберите КНС")
        except Exception:
            return
        elem1 = doc.GetElement(ref1.ElementId)
        elem2 = doc.GetElement(ref2.ElementId)
        if elem1 is None or elem2 is None:
            return
        t = Transaction(doc, CAPTION)
        try:
            t.Start()
            _create_path_between(doc, elem1, elem2, graph)
            t.Commit()
        finally:
            t.Dispose()
        return

    try:
        ref = sel.PickObject(ObjectType.Element, _FamilySelectionByElectricalSystemFilter(), u"Выберите элемент.")
    except Exception:
        return

    element = doc.GetElement(ref.ElementId)
    if element is None:
        return
    family = element if isinstance(element, FamilyInstance) else None
    system = _get_electrical_system(family)
    if system is None or system.BaseEquipment is None:
        TaskDialog.Show(CAPTION, u"Элемент не присоединен к источнику питания")
        return

    consumers = []
    for item in system.Elements:
        if isinstance(item.Location, LocationPoint):
            consumers.append(item)

    source_point = _get_location_point(system.BaseEquipment)
    if source_point is None:
        return

    trays = list(FilteredElementCollector(doc).WhereElementIsNotElementType().OfClass(CableTray))
    conduits = list(FilteredElementCollector(doc).WhereElementIsNotElementType().OfClass(Conduit))
    graph_candidates = []
    graph_candidates.extend(trays)
    graph_candidates.extend(conduits)

    nearest = _find_shortest_element(system.BaseEquipment, graph_candidates)
    if nearest is None:
        return

    _build_graph(nearest, graph, graph_ids)

    consumers.sort(key=lambda x: _get_location_point(x).DistanceTo(source_point))

    t = Transaction(doc, CAPTION)
    t.Start()
    try:
        for item in consumers:
            nearest_path = _find_shortest_element(item, graph)
            if nearest_path is None:
                continue
            _create_path_between(doc, item, nearest_path, graph)
            doc.Regenerate()
    finally:
        t.Commit()
        t.Dispose()


if __name__ == "__main__":
    main()
