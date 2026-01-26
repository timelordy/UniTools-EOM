# -*- coding: utf-8 -*-

from pyrevit import DB, forms, revit
import config_loader
import link_reader
import placement_engine
import socket_utils
from utils_revit import alert, find_nearest_level, set_comments, trace, tx
from utils_units import mm_to_ft
from constants import LIGHT_LIFT_SHAFT_TAG
from domain import (
    geom_center_and_z,
    bbox_contains_point,
    bbox_intersects,
    expand_bbox_xy,
    transform_bbox,
    match_exact_names,
    segment_ranges,
    chunks,
    is_wall_hosted,
)
from adapters import (
    store_symbol_id,
    store_symbol_unique_id,
    pick_light_symbol,
    check_symbol_compatibility,
)


def find_host_wall_in_bbox_near_point(doc, pt, bbox_min, bbox_max, max_dist_ft):
    if doc is None or pt is None or bbox_min is None or bbox_max is None:
        return None, None, None

    best_wall = None
    best_curve = None
    best_pt = None
    best_d = None

    try:
        col = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
    except Exception:
        return None, None, None

    for w in col:
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue

            wbb = None
            try:
                wbb = w.get_BoundingBox(None)
            except Exception:
                wbb = None
            if wbb is not None:
                wmin = DB.XYZ(min(float(wbb.Min.X), float(wbb.Max.X)),
                              min(float(wbb.Min.Y), float(wbb.Max.Y)),
                              min(float(wbb.Min.Z), float(wbb.Max.Z)))
                wmax = DB.XYZ(max(float(wbb.Min.X), float(wbb.Max.X)),
                              max(float(wbb.Min.Y), float(wbb.Max.Y)),
                              max(float(wbb.Min.Z), float(wbb.Max.Z)))
                if not bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue
            ir = curve.Project(pt)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not bbox_contains_point(bbox_min, bbox_max, proj):
                continue
            d = float(ir.Distance)
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            if best_wall is None or d < best_d:
                best_wall = w
                best_curve = curve
                best_pt = proj
                best_d = d
        except Exception:
            continue

    return best_wall, best_curve, best_pt


def find_link_wall_in_bbox_near_point(link_doc, pt_link, bbox_min, bbox_max, max_dist_ft, limit=None):
    if link_doc is None or pt_link is None or bbox_min is None or bbox_max is None:
        return None, None

    best_wall = None
    best_pt = None
    best_d = None

    for w in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Walls, limit=limit, level_id=None):
        try:
            loc = getattr(w, 'Location', None)
            curve = loc.Curve if loc and hasattr(loc, 'Curve') else None
            if curve is None:
                continue

            wbb = None
            try:
                wbb = w.get_BoundingBox(None)
            except Exception:
                wbb = None
            if wbb is not None:
                wmin = DB.XYZ(min(float(wbb.Min.X), float(wbb.Max.X)),
                              min(float(wbb.Min.Y), float(wbb.Max.Y)),
                              min(float(wbb.Min.Z), float(wbb.Max.Z)))
                wmax = DB.XYZ(max(float(wbb.Min.X), float(wbb.Max.X)),
                              max(float(wbb.Min.Y), float(wbb.Max.Y)),
                              max(float(wbb.Min.Z), float(wbb.Max.Z)))
                if not bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue

            ir = curve.Project(pt_link)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not bbox_contains_point(bbox_min, bbox_max, proj):
                continue

            d = float(ir.Distance)
            if max_dist_ft is not None and d > float(max_dist_ft):
                continue
            if best_wall is None or d < best_d:
                best_wall = w
                best_pt = proj
                best_d = d
        except Exception:
            continue

    return best_wall, best_pt


def place_wall_hosted(doc, symbol, wall, pt, level):
    if doc is None or symbol is None or wall is None or pt is None:
        return None

    placement_engine.ensure_symbol_active(doc, symbol)

    try:
        inst = doc.Create.NewFamilyInstance(
            pt,
            symbol,
            wall,
            level,
            DB.Structure.StructuralType.NonStructural
        )
        return inst
    except Exception:
        pass

    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Interior))
        except Exception:
            pass
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Exterior))
        except Exception:
            pass

        best_ref = None
        best_d = None
        for r in refs:
            try:
                face = wall.GetGeometryObjectFromReference(r)
                if face is None:
                    continue
                ir = face.Project(pt)
                if not ir:
                    continue
                d = float(ir.Distance)
                if best_ref is None or d < best_d:
                    best_ref = r
                    best_d = d
            except Exception:
                continue

        if best_ref is not None:
            try:
                return doc.Create.NewFamilyInstance(best_ref, pt, DB.XYZ.BasisZ, symbol)
            except Exception:
                return None
    except Exception:
        return None

    return None


def collect_shafts_from_openings_and_generic(link_doc, rx_inc, rx_exc, limit, min_height_ft=None):
    shafts = []
    processed_openings = 0
    skipped_openings_bbox = 0
    skipped_openings_height = 0
    processed_generic = 0
    skipped_generic_name = 0
    skipped_generic_bbox = 0
    skipped_generic_height = 0

    for e in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_ShaftOpening, limit=limit, level_id=None):
        processed_openings += 1
        center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
        if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
            skipped_openings_bbox += 1
            continue
        if min_height_ft is not None:
            try:
                if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                    skipped_openings_height += 1
                    continue
            except Exception:
                pass
        shafts.append({'name': u'ShaftOpening', 'center': center, 'zmin': zmin, 'zmax': zmax,
                       'bbox_min': bmin, 'bbox_max': bmax})

    if rx_inc or rx_exc:
        for e in link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_GenericModel, limit=limit, level_id=None):
            processed_generic += 1
            txt = socket_utils._elem_text(e) or u''
            if rx_inc and (not socket_utils._match_any(rx_inc, txt)):
                skipped_generic_name += 1
                continue
            if rx_exc and socket_utils._match_any(rx_exc, txt):
                skipped_generic_name += 1
                continue

            center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
            if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
                skipped_generic_bbox += 1
                continue
            if min_height_ft is not None:
                try:
                    if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                        skipped_generic_height += 1
                        continue
                except Exception:
                    pass
            shafts.append({'name': txt or u'GenericModel', 'center': center, 'zmin': zmin, 'zmax': zmax,
                           'bbox_min': bmin, 'bbox_max': bmax})

    return (shafts, processed_openings, skipped_openings_bbox,
            skipped_openings_height, processed_generic, skipped_generic_name,
            skipped_generic_bbox, skipped_generic_height)


def collect_shafts_from_families(link_doc, rx_inc, rx_exc, limit, min_height_ft=None, exact_names=None):
    """Collect shaft volumes from family instances (GenericModel + Furniture) by name patterns."""
    shafts = []
    processed = 0
    skipped_name = 0
    skipped_bbox = 0
    skipped_height = 0

    for bic in (DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Furniture):
        for e in link_reader.iter_elements_by_category(link_doc, bic, limit=limit, level_id=None):
            processed += 1
            txt = socket_utils._elem_text(e) or u''
            if exact_names:
                if not match_exact_names(txt, exact_names):
                    skipped_name += 1
                    continue
            else:
                if rx_inc and (not socket_utils._match_any(rx_inc, txt)):
                    skipped_name += 1
                    continue
                if rx_exc and socket_utils._match_any(rx_exc, txt):
                    skipped_name += 1
                    continue

            center, zmin, zmax, bmin, bmax = geom_center_and_z(e)
            if center is None or zmin is None or zmax is None or bmin is None or bmax is None:
                skipped_bbox += 1
                continue
            if min_height_ft is not None:
                try:
                    if abs(float(zmax) - float(zmin)) < float(min_height_ft):
                        skipped_height += 1
                        continue
                except Exception:
                    pass
            shafts.append({'name': txt or u'Family', 'center': center, 'zmin': zmin, 'zmax': zmax,
                           'bbox_min': bmin, 'bbox_max': bmax})

    return shafts, processed, skipped_name, skipped_bbox, skipped_height


def iter_loaded_link_docs(doc, parent_transform=None, max_depth=2, visited=None, depth=0):
    """Yield (link_instance, link_doc, cumulative_transform, is_nested)."""
    if doc is None:
        return
    if visited is None:
        visited = set()

    try:
        key = doc.PathName or doc.Title
    except Exception:
        key = None
    if key:
        if key in visited:
            return
        visited.add(key)

    try:
        links = link_reader.list_link_instances(doc)
    except Exception:
        links = []

    for ln in links:
        try:
            if not link_reader.is_link_loaded(ln):
                continue
        except Exception:
            continue
        try:
            ld = link_reader.get_link_doc(ln)
        except Exception:
            ld = None
        if ld is None:
            continue
        try:
            t = link_reader.get_total_transform(ln)
        except Exception:
            t = DB.Transform.Identity
        if parent_transform is not None:
            try:
                t = parent_transform.Multiply(t)
            except Exception:
                pass
        yield ln, ld, t, (depth > 0)
        if max_depth and max_depth > 1:
            for sub in iter_loaded_link_docs(ld, parent_transform=t, max_depth=max_depth - 1, visited=visited, depth=depth + 1):
                yield sub


def find_link_with_families(host_doc, rx_inc, rx_exc, limit, min_height_ft, exact_names, max_depth=2):
    """Find the first loaded link (or nested link) that contains any of the exact family/type names."""
    if host_doc is None or not exact_names:
        return None, None, None, None, 0, 0, 0, 0

    for ln, ld, t, is_nested in iter_loaded_link_docs(host_doc, parent_transform=None, max_depth=max_depth):
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            ld, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
        )
        if shafts_fam:
            # If nested link, avoid linked-wall hosting (link_inst not valid in host doc)
            return (None if is_nested else ln), ld, t, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height
    return None, None, None, None, 0, 0, 0, 0


def find_link_doc_with_families(link_doc, base_transform, rx_inc, rx_exc, limit, min_height_ft, exact_names, max_depth=2):
    """Search selected link doc and its nested links for families; return doc + transform."""
    if link_doc is None or not exact_names:
        return None, None, None, 0, 0, 0, 0

    shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
        link_doc, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
    )
    if shafts_fam:
        return link_doc, base_transform, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height

    for ln, ld, t, _ in iter_loaded_link_docs(link_doc, parent_transform=base_transform, max_depth=max_depth):
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            ld, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
        )
        if shafts_fam:
            return ld, t, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height

    return None, None, None, 0, 0, 0, 0


def sorted_levels(doc):
    lvls = link_reader.list_levels(doc)
    try:
        return sorted([l for l in lvls if l], key=lambda x: float(x.Elevation))
    except Exception:
        return lvls


def get_or_create_debug_plan_view(doc, level, name, aliases=None):
    if doc is None or level is None:
        return None

    try:
        aliases = list(aliases or [])
    except Exception:
        aliases = []

    try:
        for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    return v
            except Exception:
                continue
    except Exception:
        pass

    if aliases:
        try:
            for v in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
                try:
                    if v and (not v.IsTemplate) and v.Name in aliases:
                        try:
                            v.Name = name
                        except Exception:
                            pass
                        return v
                except Exception:
                    continue
        except Exception:
            pass

    vft_id = None
    try:
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.FloorPlan:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
    except Exception:
        vft_id = None

    if vft_id is None:
        return None

    try:
        vplan = DB.ViewPlan.Create(doc, vft_id, level.Id)
    except Exception:
        return None

    try:
        vplan.Name = name
    except Exception:
        pass
    return vplan


def set_plan_view_range(vplan, cut_mm=3000, top_mm=12000, bottom_mm=-2000, depth_mm=-4000):
    if vplan is None:
        return
    try:
        vr = vplan.GetViewRange()
    except Exception:
        vr = None
    if vr is None:
        return

    try:
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, mm_to_ft(top_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.CutPlane, mm_to_ft(cut_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, mm_to_ft(bottom_mm) or 0.0)
    except Exception:
        pass
    try:
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, mm_to_ft(depth_mm) or 0.0)
    except Exception:
        pass

    try:
        vplan.SetViewRange(vr)
    except Exception:
        pass


def as_net_id_list(ids):
    try:
        from System.Collections.Generic import List
        lst = List[DB.ElementId]()
        for i in ids or []:
            try:
                if i is not None:
                    lst.Add(i)
            except Exception:
                continue
        return lst
    except Exception:
        return None


def open_debug_plans(uidoc, doc, created_elems):
    if not created_elems:
        return

    level_map = {}
    for e in created_elems:
        if e is None:
            continue
        lvl = None
        try:
            lid = e.LevelId
            if lid and lid != DB.ElementId.InvalidElementId:
                lvl = doc.GetElement(lid)
        except Exception:
            lvl = None

        if lvl is None:
            try:
                loc = getattr(e, 'Location', None)
                pt = loc.Point if loc and hasattr(loc, 'Point') else None
                if pt is not None:
                    lvl = find_nearest_level(doc, pt.Z)
            except Exception:
                lvl = None

        if lvl is None:
            continue

        key = int(lvl.Id.IntegerValue)
        level_map.setdefault(key, (lvl, []))
        level_map[key][1].append(e)

    if not level_map:
        return

    first_view = None
    with tx('ЭОМ: Отладочные планы шахт лифта', doc=doc, swallow_warnings=True):
        for _, (lvl, elems) in sorted(level_map.items(), key=lambda x: x[0]):
            name = u'ЭОМ_ОТЛАДКА_ШахтаЛифта_План_{0}'.format(lvl.Name)
            vplan = get_or_create_debug_plan_view(doc, lvl, name)
            if not vplan:
                continue

            try:
                vplan.ViewTemplateId = DB.ElementId.InvalidElementId
            except Exception:
                pass
            try:
                vplan.DetailLevel = DB.ViewDetailLevel.Fine
            except Exception:
                pass

            set_plan_view_range(vplan)

            ids = [e.Id for e in elems if e]
            id_list = as_net_id_list(ids)
            if id_list is not None:
                try:
                    vplan.IsolateElementsTemporary(id_list)
                except Exception:
                    pass

            if first_view is None:
                first_view = vplan

    if first_view is None:
        return

    try:
        uidoc.ActiveView = first_view
        try:
            uidoc.RefreshActiveView()
            views = uidoc.GetOpenUIViews()
            if views:
                views[0].ZoomToFit()
        except Exception:
            pass
    except Exception:
        pass


def run_placement(doc, output, script_module):
    trace('Place_Lights_LiftShaft: start')
    output.print_md('# Размещение светильников в шахтах лифта')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    scan_limit_rooms = int(rules.get('scan_limit_rooms', 500) or 500)
    max_place = int(rules.get('max_place_count', 200) or 200)
    batch_size = int(rules.get('batch_size', 25) or 25)

    model_keywords = rules.get('lift_shaft_generic_model_keywords', None)
    if not model_keywords:
        model_keywords = rules.get('lift_shaft_room_name_patterns', []) or []
    exact_family_names = rules.get('lift_shaft_family_names', []) or []
    exclude_patterns = rules.get('lift_shaft_generic_model_exclude_patterns', None)
    if exclude_patterns is None:
        exclude_patterns = rules.get('lift_shaft_room_exclude_patterns', []) or []
    min_height_mm = float(rules.get('lift_shaft_min_height_mm', 2000) or 2000)
    edge_offset_mm = float(rules.get('lift_shaft_edge_offset_mm', 500) or 500)
    # User rule: edge lights must be within 500mm from top/bottom of the shaft
    if edge_offset_mm > 500.0:
        edge_offset_mm = 500.0
    min_wall_clear_mm = float(rules.get('lift_shaft_min_wall_clearance_mm', 0) or 0)
    wall_search_mm = float(rules.get('lift_shaft_wall_search_mm', rules.get('host_wall_search_mm', 300)) or 300)
    dedupe_mm = rules.get('lift_shaft_dedupe_radius_mm', rules.get('dedupe_radius_mm', 500))
    enable_existing_dedupe = bool(rules.get('enable_existing_dedupe', False))
    link_search_depth = int(rules.get('lift_shaft_link_search_depth', 4) or 4)

    fams = rules.get('family_type_names', {}) or {}
    type_names = fams.get('light_lift_shaft') or fams.get('light_ceiling_point') or None

    rx_inc = socket_utils._compile_patterns(model_keywords)
    rx_exc = socket_utils._compile_patterns(exclude_patterns)

    cfg = script_module.get_config()
    symbol = pick_light_symbol(doc, cfg, type_names)
    if symbol is None:
        alert('Не найден тип светильника для шахты лифта. Загрузите тип из rules.default.json (family_type_names.light_lift_shaft).')
        return

    try:
        store_symbol_id(cfg, 'last_light_lift_shaft_symbol_id', symbol)
        store_symbol_unique_id(cfg, 'last_light_lift_shaft_symbol_uid', symbol)
        script_module.save_config()
    except Exception:
        pass

    if not check_symbol_compatibility(symbol):
        return

    min_height_ft = mm_to_ft(min_height_mm) or 0.0
    edge_offset_ft = mm_to_ft(edge_offset_mm) or 0.0
    min_wall_clear_ft = mm_to_ft(min_wall_clear_mm) or 0.0
    wall_search_ft = mm_to_ft(wall_search_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0
    fam_min_height_ft = None if exact_family_names else min_height_ft

    # Auto-detect link by exact family names if provided
    link_inst = None
    link_doc = None
    link_transform = None
    shafts_fam = None
    processed_fam = skipped_fam_name = skipped_fam_bbox = skipped_fam_height = 0
    if exact_family_names:
        # Scan all loaded links without limit to find the target lift families
        link_inst, link_doc, link_transform, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = find_link_with_families(
            doc, rx_inc, rx_exc, None, fam_min_height_ft, exact_family_names, max_depth=link_search_depth
        )
        # If not found in any link, try current (host) model
        if not shafts_fam:
            try:
                shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
                    doc, rx_inc, rx_exc, None, min_height_ft=fam_min_height_ft, exact_names=exact_family_names
                )
                if shafts_fam:
                    link_inst = None
                    link_doc = doc
                    link_transform = None
            except Exception:
                pass

    if link_inst is None and link_doc is None:
        link_inst = socket_utils._select_link_instance_ru(doc, 'Выберите связь АР')
        if link_inst is None:
            output.print_md('**Отменено.**')
            return

        if not link_reader.is_link_loaded(link_inst):
            alert('Связь не загружена. Загрузите её в Manage Links и повторите.')
            return

        link_doc = link_reader.get_link_doc(link_inst)
        if link_doc is None:
            alert('Не удалось получить документ связи. Проверьте загрузку связи.')
            return

        if exact_family_names:
            base_t = link_reader.get_total_transform(link_inst)
            # Do not limit when exact list provided; search selected link + nested
            selected_link_doc = link_doc
            link_doc_found, link_transform_found, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = find_link_doc_with_families(
                link_doc, base_t, rx_inc, rx_exc, None, fam_min_height_ft, exact_family_names, max_depth=link_search_depth
            )
            if link_doc_found is not None:
                link_doc = link_doc_found
                link_transform = link_transform_found
                # If family found in nested link, linked-wall hosting is unsafe; disable it
                try:
                    if selected_link_doc is not link_doc:
                        link_inst = None
                except Exception:
                    link_inst = None

    if link_transform is not None:
        t = link_transform
        try:
            t_inv = t.Inverse
        except Exception:
            t_inv = None
    elif link_inst is None:
        try:
            t = DB.Transform.Identity
            t_inv = DB.Transform.Identity
        except Exception:
            t = None
            t_inv = None
    else:
        t = link_reader.get_total_transform(link_inst)
        try:
            t_inv = t.Inverse
        except Exception:
            t_inv = None

    # Prefer family-based shaft volumes (GenericModel/Furniture). If found, ignore ShaftOpening.
    if shafts_fam is None:
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = collect_shafts_from_families(
            link_doc, rx_inc, rx_exc, (None if exact_family_names else scan_limit_rooms), min_height_ft=fam_min_height_ft, exact_names=exact_family_names
        )
    if exact_family_names:
        if not shafts_fam:
            alert(u'Не найдены семейства лифта по списку: {0}'.format(u', '.join(exact_family_names)))
            return
        shafts = shafts_fam
        processed_openings = skipped_openings = skipped_openings_height = 0
        processed_generic = skipped_generic_name = skipped_generic_bbox = skipped_generic_height = 0
        processed_families = processed_fam
        skipped_families_name = skipped_fam_name
        skipped_families_bbox = skipped_fam_bbox
        skipped_families_height = skipped_fam_height
    elif shafts_fam:
        shafts = shafts_fam
        processed_openings = skipped_openings = skipped_openings_height = 0
        processed_generic = skipped_generic_name = skipped_generic_bbox = skipped_generic_height = 0
        processed_families = processed_fam
        skipped_families_name = skipped_fam_name
        skipped_families_bbox = skipped_fam_bbox
        skipped_families_height = skipped_fam_height
    else:
        processed_families = skipped_families_name = skipped_families_bbox = skipped_families_height = 0
        (shafts, processed_openings, skipped_openings, skipped_openings_height,
         processed_generic, skipped_generic_name, skipped_generic_bbox, skipped_generic_height) = collect_shafts_from_openings_and_generic(
            link_doc, rx_inc, rx_exc, scan_limit_rooms, min_height_ft=min_height_ft
        )

    if not shafts:
        alert('Не найдены шахты лифта в связи АР (ShaftOpening и Generic Model).')
        return

    levels = sorted_levels(doc)

    comment_value = '{0}:{1}'.format(comment_tag, LIGHT_LIFT_SHAFT_TAG)
    idx = socket_utils._XYZIndex(cell_ft=5.0)
    if enable_existing_dedupe:
        try:
            for p in socket_utils._collect_existing_tagged_points(doc, comment_value):
                idx.add(p.X, p.Y, p.Z)
        except Exception:
            pass

    points = []
    truncated = False
    skipped_dedupe = 0
    skipped_no_wall = 0
    skipped_place = 0

    with forms.ProgressBar(title='ЭОМ: Поиск шахт лифта', cancellable=True, step=1) as pb:
        pb.max_value = len(shafts)
        for i, sh in enumerate(shafts):
            pb.update_progress(i + 1, pb.max_value)
            if pb.cancelled:
                return

            center = sh.get('center')
            zmin = sh.get('zmin')
            zmax = sh.get('zmax')
            bmin = sh.get('bbox_min')
            bmax = sh.get('bbox_max')
            if center is None or zmin is None or zmax is None:
                continue

            try:
                host_c = t.OfPoint(center)
                host_zmin = t.OfPoint(DB.XYZ(float(center.X), float(center.Y), float(zmin))).Z
                host_zmax = t.OfPoint(DB.XYZ(float(center.X), float(center.Y), float(zmax))).Z
                host_bmin, host_bmax = transform_bbox(t, bmin, bmax)
            except Exception:
                continue

            if host_bmin is None or host_bmax is None:
                continue
            host_bmin, host_bmax = expand_bbox_xy(host_bmin, host_bmax, min_wall_clear_ft)

            link_bmin = bmin
            link_bmax = bmax
            if link_bmin is None or link_bmax is None:
                continue
            link_bmin, link_bmax = expand_bbox_xy(link_bmin, link_bmax, min_wall_clear_ft)

            shaft_min = min(float(host_zmin), float(host_zmax))
            shaft_max = max(float(host_zmin), float(host_zmax))
            if shaft_max <= shaft_min + 1e-6:
                z_mid = shaft_min
                pt = DB.XYZ(float(host_c.X), float(host_c.Y), float(z_mid))
                if dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                else:
                    idx.add(pt.X, pt.Y, pt.Z)
                    points.append((pt, find_nearest_level(doc, z_mid), host_bmin, host_bmax, link_bmin, link_bmax))
                continue

            segments = segment_ranges(levels, shaft_min, shaft_max)
            if not segments:
                segments = [(shaft_min, shaft_max)]

            # One light per level (segment middle)
            for seg_min, seg_max in segments:
                seg_h = float(seg_max) - float(seg_min)
                if seg_h <= 1e-6:
                    continue
                z_mid = seg_min + seg_h * 0.5
                pt = DB.XYZ(float(host_c.X), float(host_c.Y), float(z_mid))
                if dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                else:
                    idx.add(pt.X, pt.Y, pt.Z)
                    points.append((pt, find_nearest_level(doc, z_mid), host_bmin, host_bmax, link_bmin, link_bmax))

                if max_place > 0 and len(points) >= max_place:
                    truncated = True
                    break
            if truncated:
                break

            # Extra lights near top and bottom of shaft
            if edge_offset_ft > 0.0:
                z_list = [shaft_min + edge_offset_ft, shaft_max - edge_offset_ft]
            else:
                z_list = [shaft_min, shaft_max]

            for z in z_list:
                if z <= shaft_min + 1e-6:
                    z = shaft_min + 1e-6
                if z >= shaft_max - 1e-6:
                    z = shaft_max - 1e-6
                pt = DB.XYZ(float(host_c.X), float(host_c.Y), float(z))
                if dedupe_ft > 0.0 and idx.has_near(pt.X, pt.Y, pt.Z, dedupe_ft):
                    skipped_dedupe += 1
                    continue
                idx.add(pt.X, pt.Y, pt.Z)
                points.append((pt, find_nearest_level(doc, z), host_bmin, host_bmax, link_bmin, link_bmax))

                if max_place > 0 and len(points) >= max_place:
                    truncated = True
                    break
            if truncated:
                break

    if not points:
        alert('Нет точек для размещения. Проверьте уровни и параметры offset.')
        return

    output.print_md('Шахты: **{0}**'.format(len(shafts)))
    if exact_family_names:
        output.print_md('Фильтр по семействам лифта: **{0}**'.format(u', '.join(exact_family_names)))
    if processed_families:
        output.print_md('Family (Generic/Furniture) обработано: **{0}**'.format(processed_families))
        if skipped_families_name:
            output.print_md('Пропущено (имя): **{0}**'.format(skipped_families_name))
        if skipped_families_bbox:
            output.print_md('Пропущено (bbox): **{0}**'.format(skipped_families_bbox))
        if skipped_families_height:
            output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_families_height))
    output.print_md('ShaftOpening обработано: **{0}**'.format(processed_openings))
    if skipped_openings:
        output.print_md('Пропущено (bbox): **{0}**'.format(skipped_openings))
    if skipped_openings_height:
        output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_openings_height))
    if rx_inc or rx_exc:
        output.print_md('Generic Model обработано: **{0}**'.format(processed_generic))
        if skipped_generic_name:
            output.print_md('Пропущено (фильтр имён): **{0}**'.format(skipped_generic_name))
        if skipped_generic_bbox:
            output.print_md('Пропущено (bbox): **{0}**'.format(skipped_generic_bbox))
        if skipped_generic_height:
            output.print_md('Пропущено (низкая высота): **{0}**'.format(skipped_generic_height))

    output.print_md('Кандидаты: **{0}**'.format(len(points)))
    if skipped_dedupe:
        output.print_md('Дедупликация: **{0}**'.format(skipped_dedupe))
    if truncated:
        output.print_md('**Внимание:** достигнут лимит max_place_count ({0}).'.format(max_place))

    created_count = 0
    created_elems = []
    batches = list(chunks(points, batch_size))
    with forms.ProgressBar(title='ЭОМ: Размещение светильников (шахта лифта)', cancellable=True, step=1) as pb2:
        pb2.max_value = len(batches)
        for i, batch in enumerate(batches):
            pb2.update_progress(i + 1, pb2.max_value)
            if pb2.cancelled:
                break

            with tx('ЭОМ: Светильники шахты лифта', doc=doc, swallow_warnings=True):
                for pt, lvl, bbox_min, bbox_max, link_bmin, link_bmax in batch:
                    if pt is None or lvl is None or bbox_min is None or bbox_max is None:
                        skipped_place += 1
                        continue

                    inst = None
                    use_pt = pt
                    is_wall_symbol = is_wall_hosted(symbol)

                    # Try linked wall hosting first
                    if link_inst is not None and link_bmin is not None and link_bmax is not None:
                        try:
                            pt_link = t_inv.OfPoint(pt) if t_inv is not None else pt
                        except Exception:
                            pt_link = pt
                        wall_link, proj_pt_link = find_link_wall_in_bbox_near_point(
                            link_doc, pt_link, link_bmin, link_bmax, wall_search_ft, limit=None
                        )
                        if wall_link is not None:
                            try:
                                link_ref, proj_pt_link, face_n_link = socket_utils._get_linked_wall_face_ref_and_point(
                                    wall_link, link_inst, pt_link
                                )
                            except Exception:
                                link_ref, proj_pt_link, face_n_link = None, None, None

                            if proj_pt_link is not None:
                                try:
                                    use_pt = t.OfPoint(proj_pt_link)
                                    use_pt = DB.XYZ(float(use_pt.X), float(use_pt.Y), float(pt.Z))
                                except Exception:
                                    use_pt = pt

                            if is_wall_symbol and link_ref is not None:
                                try:
                                    wall_dir_link = None
                                    try:
                                        wall_dir_link = wall_link.Location.Curve.Direction
                                    except Exception:
                                        wall_dir_link = None
                                    dir_host = t.OfVector(wall_dir_link) if wall_dir_link else DB.XYZ.BasisX
                                    if face_n_link and dir_host.GetLength() > 1e-9:
                                        n_host = t.OfVector(face_n_link)
                                        if n_host and n_host.GetLength() > 1e-9:
                                            n = n_host.Normalize()
                                            comp = n.Multiply(dir_host.DotProduct(n))
                                            dir_host = dir_host - comp
                                    dir_host = dir_host.Normalize() if dir_host.GetLength() > 1e-9 else DB.XYZ.BasisX
                                    try:
                                        inst = doc.Create.NewFamilyInstance(link_ref, use_pt, dir_host, symbol)
                                    except Exception:
                                        try:
                                            inst = doc.Create.NewFamilyInstance(link_ref, use_pt, symbol)
                                        except Exception:
                                            inst = None
                                except Exception:
                                    inst = None

                    # Fallback: host wall in model or point placement
                    if inst is None:
                        wall, _, proj_pt = find_host_wall_in_bbox_near_point(doc, pt, bbox_min, bbox_max, wall_search_ft)
                        if wall is not None:
                            try:
                                use_pt = proj_pt if proj_pt is not None else pt
                                use_pt = DB.XYZ(float(use_pt.X), float(use_pt.Y), float(pt.Z))
                            except Exception:
                                use_pt = pt

                            if is_wall_symbol:
                                inst = place_wall_hosted(doc, symbol, wall, use_pt, lvl)

                    if inst is None:
                        try:
                            inst = placement_engine.place_point_family_instance(doc, symbol, use_pt, prefer_level=lvl)
                        except Exception:
                            inst = None

                    if inst is None:
                        skipped_no_wall += 1
                    if inst is None:
                        skipped_place += 1
                        continue

                    try:
                        set_comments(inst, comment_value)
                    except Exception:
                        pass

                    created_count += 1
                    created_elems.append(inst)

    output.print_md('---')
    output.print_md('Размещено светильников: **{0}**'.format(created_count))
    if skipped_no_wall:
        output.print_md('Пропущено (не найдена стена): **{0}**'.format(skipped_no_wall))
    if skipped_place:
        output.print_md('Пропущено (ошибка размещения): **{0}**'.format(skipped_place))
    output.print_md('Тег Comments: `{0}`'.format(comment_value))
    # logger.info('Placed %s lift shaft light(s)', created_count)

    if created_elems:
        try:
            go_debug = forms.alert(
                'Создать отладочный план на уровне светильников и открыть его?',
                title='ЭОМ: Светильники в шахтах',
                warn_icon=False,
                yes=True,
                no=True
            )
        except Exception:
            go_debug = False

        if go_debug:
            open_debug_plans(revit.uidoc, doc, created_elems)
