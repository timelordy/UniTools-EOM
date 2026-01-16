# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

from utils_revit import alert, find_nearest_level, log_exception, set_comments, trace, tx
from utils_units import mm_to_ft

import config_loader
import link_reader
import placement_engine
import socket_utils


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


def _as_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [v for v in val if v]
    return [val]


def _load_symbol_from_saved_id(doc_, cfg, key):
    if doc_ is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        try:
            eid = DB.ElementId(int(val))
        except Exception:
            return None
        e = doc_.GetElement(eid)
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def _load_symbol_from_saved_unique_id(doc_, cfg, key):
    if doc_ is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc_.GetElement(str(uid))
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def _store_symbol_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, int(symbol.Id.IntegerValue))
    except Exception:
        pass


def _store_symbol_unique_id(cfg, key, symbol):
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


def _pick_light_symbol(doc_, cfg, type_names):
    sym = _load_symbol_from_saved_id(doc_, cfg, 'last_light_lift_shaft_symbol_id')
    if sym is None:
        sym = _load_symbol_from_saved_unique_id(doc_, cfg, 'last_light_lift_shaft_symbol_uid')
    if sym is not None:
        return sym

    for name in _as_list(type_names):
        try:
            found = placement_engine.find_family_symbol(doc_, name, category_bic=DB.BuiltInCategory.OST_LightingFixtures)
        except Exception:
            found = None
        if found and placement_engine.is_supported_point_placement(found):
            return found

    picked = placement_engine.select_family_symbol(
        doc_,
        title='Выберите тип светильника (шахта лифта)',
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=True,
        allow_none=True,
        button_name='Выбрать',
        search_text=None,
        limit=200,
        scan_cap=5000
    )
    return picked


def _is_wall_hosted(symbol):
    if symbol is None:
        return False
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.OneLevelBasedHosted:
            return True
    except Exception:
        pass
    try:
        if pt == DB.FamilyPlacementType.FaceBased:
            return True
    except Exception:
        pass
    try:
        if pt == DB.FamilyPlacementType.TwoLevelsBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and (u'host' in pt_name.lower() or u'face' in pt_name.lower() or u'wall' in pt_name.lower()):
            return True
    except Exception:
        pass
    return False


def _is_one_level_based(symbol):
    if symbol is None:
        return False
    pt, pt_name = placement_engine.get_symbol_placement_type(symbol)
    try:
        if pt == DB.FamilyPlacementType.OneLevelBased:
            return True
    except Exception:
        pass
    try:
        if pt_name and u'onelevelbased' in pt_name.lower():
            return True
    except Exception:
        pass
    return False


def _find_host_wall_in_bbox_near_point(doc_, pt, bbox_min, bbox_max, max_dist_ft):
    if doc_ is None or pt is None or bbox_min is None or bbox_max is None:
        return None, None, None

    best_wall = None
    best_curve = None
    best_pt = None
    best_d = None

    try:
        col = DB.FilteredElementCollector(doc_).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType()
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
                if not _bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue
            ir = curve.Project(pt)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not _bbox_contains_point(bbox_min, bbox_max, proj):
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


def _find_link_wall_in_bbox_near_point(link_doc, pt_link, bbox_min, bbox_max, max_dist_ft, limit=None):
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
                if not _bbox_intersects(bbox_min, bbox_max, wmin, wmax):
                    continue

            ir = curve.Project(pt_link)
            if not ir:
                continue
            proj = None
            try:
                proj = ir.XYZPoint
            except Exception:
                proj = None
            if proj is not None and not _bbox_contains_point(bbox_min, bbox_max, proj):
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


def _place_wall_hosted(doc_, symbol, wall, pt, level):
    if doc_ is None or symbol is None or wall is None or pt is None:
        return None

    placement_engine.ensure_symbol_active(doc_, symbol)

    try:
        inst = doc_.Create.NewFamilyInstance(
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
                return doc_.Create.NewFamilyInstance(best_ref, pt, DB.XYZ.BasisZ, symbol)
            except Exception:
                return None
    except Exception:
        return None

    return None


def _iter_solids(geom):
    if geom is None:
        return
    try:
        for go in geom:
            if isinstance(go, DB.Solid):
                try:
                    if float(go.Volume) > 1e-9:
                        yield go
                except Exception:
                    continue
            elif isinstance(go, DB.GeometryInstance):
                try:
                    inst_geom = go.GetInstanceGeometry()
                except Exception:
                    inst_geom = None
                if inst_geom is None:
                    continue
                for ig in inst_geom:
                    if isinstance(ig, DB.Solid):
                        try:
                            if float(ig.Volume) > 1e-9:
                                yield ig
                        except Exception:
                            continue
    except Exception:
        return


def _solid_centroid(elem):
    if elem is None:
        return None
    try:
        opt = DB.Options()
        try:
            opt.DetailLevel = DB.ViewDetailLevel.Fine
        except Exception:
            pass
        try:
            opt.IncludeNonVisibleObjects = True
        except Exception:
            pass
        geom = elem.get_Geometry(opt)
    except Exception:
        geom = None

    if geom is None:
        return None

    total_vol = 0.0
    sx = sy = sz = 0.0
    for solid in _iter_solids(geom):
        try:
            c = solid.ComputeCentroid()
            v = float(solid.Volume)
        except Exception:
            continue
        if c is None or v <= 1e-9:
            continue
        total_vol += v
        sx += float(c.X) * v
        sy += float(c.Y) * v
        sz += float(c.Z) * v
    if total_vol <= 1e-9:
        return None
    return DB.XYZ(sx / total_vol, sy / total_vol, sz / total_vol)


def _geom_center_and_z(elem):
    if elem is None:
        return None, None, None, None, None
    center = _solid_centroid(elem)
    try:
        bb = elem.get_BoundingBox(None)
    except Exception:
        bb = None
    if bb is None:
        return center, None, None, None, None
    try:
        minx = float(min(bb.Min.X, bb.Max.X))
        miny = float(min(bb.Min.Y, bb.Max.Y))
        minz = float(min(bb.Min.Z, bb.Max.Z))
        maxx = float(max(bb.Min.X, bb.Max.X))
        maxy = float(max(bb.Min.Y, bb.Max.Y))
        maxz = float(max(bb.Min.Z, bb.Max.Z))
        if center is None:
            center = DB.XYZ((minx + maxx) * 0.5, (miny + maxy) * 0.5, (minz + maxz) * 0.5)
        bmin = DB.XYZ(minx, miny, minz)
        bmax = DB.XYZ(maxx, maxy, maxz)
        return center, minz, maxz, bmin, bmax
    except Exception:
        return center, None, None, None, None


def _bbox_contains_point(bmin, bmax, pt, eps=1e-6):
    if bmin is None or bmax is None or pt is None:
        return False
    try:
        return (float(bmin.X) - eps <= float(pt.X) <= float(bmax.X) + eps and
                float(bmin.Y) - eps <= float(pt.Y) <= float(bmax.Y) + eps and
                float(bmin.Z) - eps <= float(pt.Z) <= float(bmax.Z) + eps)
    except Exception:
        return False


def _bbox_intersects(bmin, bmax, omin, omax, eps=1e-6):
    if bmin is None or bmax is None or omin is None or omax is None:
        return False
    try:
        return (float(bmin.X) - eps <= float(omax.X) and float(bmax.X) + eps >= float(omin.X) and
                float(bmin.Y) - eps <= float(omax.Y) and float(bmax.Y) + eps >= float(omin.Y) and
                float(bmin.Z) - eps <= float(omax.Z) and float(bmax.Z) + eps >= float(omin.Z))
    except Exception:
        return False


def _expand_bbox_xy(bmin, bmax, delta):
    if bmin is None or bmax is None or delta is None:
        return bmin, bmax
    try:
        d = float(delta)
        return (DB.XYZ(float(bmin.X) - d, float(bmin.Y) - d, float(bmin.Z)),
                DB.XYZ(float(bmax.X) + d, float(bmax.Y) + d, float(bmax.Z)))
    except Exception:
        return bmin, bmax


def _transform_bbox(t, bmin, bmax):
    if bmin is None or bmax is None:
        return None, None
    if t is None:
        return bmin, bmax
    try:
        xs = [float(bmin.X), float(bmax.X)]
        ys = [float(bmin.Y), float(bmax.Y)]
        zs = [float(bmin.Z), float(bmax.Z)]
        pts = []
        for x in xs:
            for y in ys:
                for z in zs:
                    pts.append(t.OfPoint(DB.XYZ(x, y, z)))
        minx = min([p.X for p in pts])
        miny = min([p.Y for p in pts])
        minz = min([p.Z for p in pts])
        maxx = max([p.X for p in pts])
        maxy = max([p.Y for p in pts])
        maxz = max([p.Z for p in pts])
        return DB.XYZ(minx, miny, minz), DB.XYZ(maxx, maxy, maxz)
    except Exception:
        return None, None


def _collect_shafts_from_openings_and_generic(link_doc, rx_inc, rx_exc, limit, min_height_ft=None):
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
        center, zmin, zmax, bmin, bmax = _geom_center_and_z(e)
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

            center, zmin, zmax, bmin, bmax = _geom_center_and_z(e)
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


def _norm_lift_name(s):
    try:
        t = socket_utils._norm(s)
    except Exception:
        t = (s or u'').strip().lower()
    try:
        # Normalize Cyrillic/Latin X to a single form for matching (use latin x)
        t = t.replace(u'\u0425', u'x').replace(u'\u0445', u'x')
    except Exception:
        pass
    return t


def _match_exact_names(txt, names):
    if not txt or not names:
        return False
    t = _norm_lift_name(txt)
    for nm in names:
        nn = _norm_lift_name(nm)
        if nn and (nn in t):
            return True
    return False


def _collect_shafts_from_families(link_doc, rx_inc, rx_exc, limit, min_height_ft=None, exact_names=None):
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
                if not _match_exact_names(txt, exact_names):
                    skipped_name += 1
                    continue
            else:
                if rx_inc and (not socket_utils._match_any(rx_inc, txt)):
                    skipped_name += 1
                    continue
                if rx_exc and socket_utils._match_any(rx_exc, txt):
                    skipped_name += 1
                    continue

            center, zmin, zmax, bmin, bmax = _geom_center_and_z(e)
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


def _find_link_with_families(host_doc, rx_inc, rx_exc, limit, min_height_ft, exact_names):
    """Find the first loaded link that contains any of the exact family/type names."""
    if host_doc is None or not exact_names:
        return None, None, None, 0, 0, 0, 0
    try:
        links = link_reader.list_link_instances(host_doc)
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
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = _collect_shafts_from_families(
            ld, rx_inc, rx_exc, limit, min_height_ft=min_height_ft, exact_names=exact_names
        )
        if shafts_fam:
            return ln, ld, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height
    return None, None, None, 0, 0, 0, 0


def _sorted_levels(doc_):
    lvls = link_reader.list_levels(doc_)
    try:
        return sorted([l for l in lvls if l], key=lambda x: float(x.Elevation))
    except Exception:
        return lvls


def _segment_ranges(levels, shaft_min_z, shaft_max_z):
    if shaft_min_z is None or shaft_max_z is None:
        return []
    if not levels:
        return [(shaft_min_z, shaft_max_z)]

    out = []
    for i, lvl in enumerate(levels):
        try:
            bottom = float(lvl.Elevation)
        except Exception:
            continue

        if i + 1 < len(levels):
            try:
                top = float(levels[i + 1].Elevation)
            except Exception:
                top = None
        else:
            top = None

        seg_min = max(bottom, shaft_min_z)
        seg_max = shaft_max_z if top is None else min(top, shaft_max_z)
        if seg_max <= seg_min:
            continue
        out.append((seg_min, seg_max))
    return out


def _chunks(seq, n):
    if not seq:
        return
    n = max(int(n or 1), 1)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _get_or_create_debug_plan_view(doc_, level, name, aliases=None):
    if doc_ is None or level is None:
        return None

    try:
        aliases = list(aliases or [])
    except Exception:
        aliases = []

    try:
        for v in DB.FilteredElementCollector(doc_).OfClass(DB.ViewPlan):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    return v
            except Exception:
                continue
    except Exception:
        pass

    if aliases:
        try:
            for v in DB.FilteredElementCollector(doc_).OfClass(DB.ViewPlan):
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
        for vft in DB.FilteredElementCollector(doc_).OfClass(DB.ViewFamilyType):
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
        vplan = DB.ViewPlan.Create(doc_, vft_id, level.Id)
    except Exception:
        return None

    try:
        vplan.Name = name
    except Exception:
        pass
    return vplan


def _set_plan_view_range(vplan, cut_mm=3000, top_mm=12000, bottom_mm=-2000, depth_mm=-4000):
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


def _as_net_id_list(ids):
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


def _open_debug_plans(uidoc_, doc_, created_elems):
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
                lvl = doc_.GetElement(lid)
        except Exception:
            lvl = None

        if lvl is None:
            try:
                loc = getattr(e, 'Location', None)
                pt = loc.Point if loc and hasattr(loc, 'Point') else None
                if pt is not None:
                    lvl = find_nearest_level(doc_, pt.Z)
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
    with tx('ЭОМ: Отладочные планы шахт лифта', doc=doc_, swallow_warnings=True):
        for _, (lvl, elems) in sorted(level_map.items(), key=lambda x: x[0]):
            name = u'ЭОМ_ОТЛАДКА_ШахтаЛифта_План_{0}'.format(lvl.Name)
            vplan = _get_or_create_debug_plan_view(doc_, lvl, name)
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

            _set_plan_view_range(vplan)

            ids = [e.Id for e in elems if e]
            id_list = _as_net_id_list(ids)
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
        uidoc_.ActiveView = first_view
        try:
            uidoc_.RefreshActiveView()
            views = uidoc_.GetOpenUIViews()
            if views:
                views[0].ZoomToFit()
        except Exception:
            pass
    except Exception:
        pass


def main():
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

    fams = rules.get('family_type_names', {}) or {}
    type_names = fams.get('light_lift_shaft') or fams.get('light_ceiling_point') or None

    rx_inc = socket_utils._compile_patterns(model_keywords)
    rx_exc = socket_utils._compile_patterns(exclude_patterns)

    cfg = script.get_config()
    symbol = _pick_light_symbol(doc, cfg, type_names)
    if symbol is None:
        alert('Не найден тип светильника для шахты лифта. Загрузите тип из rules.default.json (family_type_names.light_lift_shaft).')
        return

    try:
        _store_symbol_id(cfg, 'last_light_lift_shaft_symbol_id', symbol)
        _store_symbol_unique_id(cfg, 'last_light_lift_shaft_symbol_uid', symbol)
        script.save_config()
    except Exception:
        pass

    is_wall_hosted = _is_wall_hosted(symbol)
    is_one_level = _is_one_level_based(symbol)
    if not is_wall_hosted and not is_one_level:
        _, pt_name = placement_engine.get_symbol_placement_type(symbol)
        alert('Выбранный тип не поддерживает настенное размещение и не является уровневым (OneLevelBased).\n\nТип: {0}'.format(pt_name))
        return

    min_height_ft = mm_to_ft(min_height_mm) or 0.0
    edge_offset_ft = mm_to_ft(edge_offset_mm) or 0.0
    min_wall_clear_ft = mm_to_ft(min_wall_clear_mm) or 0.0
    wall_search_ft = mm_to_ft(wall_search_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0

    # Auto-detect link by exact family names if provided
    link_inst = None
    link_doc = None
    shafts_fam = None
    processed_fam = skipped_fam_name = skipped_fam_bbox = skipped_fam_height = 0
    if exact_family_names:
        # Scan all loaded links without limit to find the target lift families
        link_inst, link_doc, shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = _find_link_with_families(
            doc, rx_inc, rx_exc, None, min_height_ft, exact_family_names
        )
        # If not found in any link, try current (host) model
        if not shafts_fam:
            try:
                shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = _collect_shafts_from_families(
                    doc, rx_inc, rx_exc, None, min_height_ft=min_height_ft, exact_names=exact_family_names
                )
                if shafts_fam:
                    link_inst = None
                    link_doc = doc
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

    if link_inst is None:
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
        shafts_fam, processed_fam, skipped_fam_name, skipped_fam_bbox, skipped_fam_height = _collect_shafts_from_families(
            link_doc, rx_inc, rx_exc, scan_limit_rooms, min_height_ft=min_height_ft, exact_names=exact_family_names
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
         processed_generic, skipped_generic_name, skipped_generic_bbox, skipped_generic_height) = _collect_shafts_from_openings_and_generic(
            link_doc, rx_inc, rx_exc, scan_limit_rooms, min_height_ft=min_height_ft
        )

    if not shafts:
        alert('Не найдены шахты лифта в связи АР (ShaftOpening и Generic Model).')
        return

    levels = _sorted_levels(doc)

    comment_value = '{0}:LIGHT_LIFT_SHAFT'.format(comment_tag)
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
                host_bmin, host_bmax = _transform_bbox(t, bmin, bmax)
            except Exception:
                continue

            if host_bmin is None or host_bmax is None:
                continue
            host_bmin, host_bmax = _expand_bbox_xy(host_bmin, host_bmax, min_wall_clear_ft)

            link_bmin = bmin
            link_bmax = bmax
            if link_bmin is None or link_bmax is None:
                continue
            link_bmin, link_bmax = _expand_bbox_xy(link_bmin, link_bmax, min_wall_clear_ft)

            shaft_min = min(float(host_zmin), float(host_zmax))
            shaft_max = max(float(host_zmin), float(host_zmax))
            if shaft_max <= shaft_min:
                continue

            segments = _segment_ranges(levels, shaft_min, shaft_max)
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
    batches = list(_chunks(points, batch_size))
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

                    # Try linked wall hosting first
                    if link_inst is not None and link_bmin is not None and link_bmax is not None:
                        try:
                            pt_link = t_inv.OfPoint(pt) if t_inv is not None else pt
                        except Exception:
                            pt_link = pt
                        wall_link, proj_pt_link = _find_link_wall_in_bbox_near_point(
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

                            if is_wall_hosted and link_ref is not None:
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
                        wall, _, proj_pt = _find_host_wall_in_bbox_near_point(doc, pt, bbox_min, bbox_max, wall_search_ft)
                        if wall is not None:
                            try:
                                use_pt = proj_pt if proj_pt is not None else pt
                                use_pt = DB.XYZ(float(use_pt.X), float(use_pt.Y), float(pt.Z))
                            except Exception:
                                use_pt = pt

                            if is_wall_hosted:
                                inst = _place_wall_hosted(doc, symbol, wall, use_pt, lvl)

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
    logger.info('Placed %s lift shaft light(s)', created_count)

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
            _open_debug_plans(uidoc, doc, created_elems)


try:
    main()
except Exception:
    log_exception('Place lift shaft lights failed')
    alert('Инструмент завершился с ошибкой. Проверьте pyRevit Output.')

