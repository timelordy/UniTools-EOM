# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

from utils_revit import alert, log_exception, trace, tx
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


# Auto-pick heuristics (no UI)
LIGHT_STRONG_KEYWORDS = [u'свет', u'light', u'lighting', u'светиль', u'lamp', u'lum']
LIGHT_CEILING_KEYWORDS = [u'потол', u'ceiling']
LIGHT_POINT_KEYWORDS = [u'точеч', u'point', u'downlight', u'spot', u'dl']
LIGHT_NEGATIVE_KEYWORDS = [u'авар', u'emerg', u'emergency', u'exit', u'табло', u'указ', u'sign', u'эвак']


def _get_user_config():
    try:
        return script.get_config()
    except Exception:
        return None


def _save_user_config():
    try:
        script.save_config()
        return True
    except Exception:
        return False


def _load_symbol_from_saved_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        try:
            eid = DB.ElementId(int(val))
        except Exception:
            return None
        e = doc.GetElement(eid)
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def _load_symbol_from_saved_unique_id(doc, cfg, key):
    if doc is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc.GetElement(str(uid))
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


def _as_net_id_list(ids):
    """Convert python list[ElementId] to .NET List[ElementId] for Revit API calls."""
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


def _report_symbol_geometry(symbol):
    """Best-effort: report if chosen symbol has any visible geometry."""
    if symbol is None:
        return
    try:
        opts = DB.Options()
        try:
            opts.DetailLevel = DB.ViewDetailLevel.Fine
        except Exception:
            pass
        geom = symbol.get_Geometry(opts)
        if geom is None:
            output.print_md('Symbol geometry: **None** (may be invisible in 3D/plan)')
            return

        solids = 0
        meshes = 0
        curves = 0
        for g in geom:
            try:
                if isinstance(g, DB.Solid) and g.Volume > 0:
                    solids += 1
                elif isinstance(g, DB.Mesh):
                    meshes += 1
                elif isinstance(g, DB.Curve):
                    curves += 1
            except Exception:
                continue
        output.print_md('Symbol geometry summary: solids={0}, meshes={1}, curves={2}'.format(solids, meshes, curves))
        if solids == 0 and meshes == 0 and curves == 0:
            output.print_md('**Warning:** selected family type seems to have no geometry. It may place instances that are not visible.')
    except Exception:
        # do not break tool
        return


def _get_or_create_debug_3d_view(doc, name, aliases=None):
    try:
        aliases = list(aliases or [])

        # Reuse if exists (primary)
        for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    return v
            except Exception:
                continue

        # Reuse by alias and rename to primary
        if aliases:
            for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
                try:
                    if not v or v.IsTemplate:
                        continue
                    if v.Name in aliases:
                        try:
                            v.Name = name
                        except Exception:
                            pass
                        return v
                except Exception:
                    continue

        vft_id = None
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.ThreeDimensional:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
        if vft_id is None:
            return None

        v3d = DB.View3D.CreateIsometric(doc, vft_id)
        try:
            v3d.Name = name
        except Exception:
            pass
        return v3d
    except Exception:
        return None


def _bbox_from_points(points_xyz, pad_ft=20.0):
    pts = points_xyz or []
    if not pts:
        return None
    try:
        minx = pts[0].X
        miny = pts[0].Y
        minz = pts[0].Z
        maxx = pts[0].X
        maxy = pts[0].Y
        maxz = pts[0].Z
        for p in pts[1:]:
            if p.X < minx:
                minx = p.X
            if p.Y < miny:
                miny = p.Y
            if p.Z < minz:
                minz = p.Z
            if p.X > maxx:
                maxx = p.X
            if p.Y > maxy:
                maxy = p.Y
            if p.Z > maxz:
                maxz = p.Z

        pad = float(pad_ft or 0.0)
        bb = DB.BoundingBoxXYZ()
        bb.Min = DB.XYZ(minx - pad, miny - pad, minz - pad)
        bb.Max = DB.XYZ(maxx + pad, maxy + pad, maxz + pad)
        return bb
    except Exception:
        return None


def _points_debug_stats(points_xyz):
    pts = points_xyz or []
    if not pts:
        return None
    try:
        minx = pts[0].X
        miny = pts[0].Y
        minz = pts[0].Z
        maxx = pts[0].X
        maxy = pts[0].Y
        maxz = pts[0].Z
        for p in pts[1:]:
            if p.X < minx:
                minx = p.X
            if p.Y < miny:
                miny = p.Y
            if p.Z < minz:
                minz = p.Z
            if p.X > maxx:
                maxx = p.X
            if p.Y > maxy:
                maxy = p.Y
            if p.Z > maxz:
                maxz = p.Z

        return {
            'min': DB.XYZ(minx, miny, minz),
            'max': DB.XYZ(maxx, maxy, maxz),
            'range_x': float(maxx - minx),
            'range_y': float(maxy - miny),
            'range_z': float(maxz - minz),
        }
    except Exception:
        return None


def _adjust_bbox_z(bb, z_center, half_height_ft):
    if bb is None or z_center is None:
        return bb
    try:
        hh = float(half_height_ft or 0.0)
        if hh <= 0.0:
            return bb
        zc = float(z_center)
        bb.Min = DB.XYZ(bb.Min.X, bb.Min.Y, zc - hh)
        bb.Max = DB.XYZ(bb.Max.X, bb.Max.Y, zc + hh)
        return bb
    except Exception:
        return bb


def _pick_symbol_from_existing_instance(category_bic):
    """Ask user to click an existing instance in host doc and return its Symbol.

    This avoids scanning all FamilySymbols (can be unstable in some projects).
    """
    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    bic_int = int(category_bic)

    class InstFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                if elem is None:
                    return False
                if not isinstance(elem, DB.FamilyInstance):
                    return False
                cat = getattr(elem, 'Category', None)
                return bool(cat and cat.Id and int(cat.Id.IntegerValue) == bic_int)
            except Exception:
                return False

        def AllowReference(self, reference, position):
            return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.Element, InstFilter(), 'Pick an existing instance in EOM to define the family type')
    except Exception:
        return None

    try:
        inst = doc.GetElement(r.ElementId)
        return inst.Symbol if inst else None
    except Exception:
        return None


def _norm(s):
    try:
        return (s or '').strip().lower()
    except Exception:
        return ''


def _score_light_label(label):
    t = _norm(label)
    if not t:
        return -999

    score = 0
    if 'eom' in t:
        score += 40

    for kw in LIGHT_STRONG_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in t):
            score += 20

    for kw in LIGHT_CEILING_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in t):
            score += 30

    for kw in LIGHT_POINT_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in t):
            score += 25

    for kw in LIGHT_NEGATIVE_KEYWORDS:
        nkw = _norm(kw)
        if nkw and (nkw in t):
            score -= 80

    return score


def _collect_existing_light_type_counts(host_doc, limit=3000):
    counts = {}
    if host_doc is None:
        return counts

    lim = 3000
    try:
        lim = int(limit or 3000)
    except Exception:
        lim = 3000

    try:
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfCategory(DB.BuiltInCategory.OST_LightingFixtures))
        i = 0
        for e in col:
            i += 1
            if lim and i > lim:
                break
            try:
                tid = e.GetTypeId()
                if tid is None:
                    continue
                k = int(tid.IntegerValue)
                counts[k] = counts.get(k, 0) + 1
            except Exception:
                continue
    except Exception:
        return {}

    return counts


def _auto_pick_light_symbol(doc, prefer_fullname=None, scan_cap=2000):
    """Auto-pick best available Lighting Fixture FamilySymbol (no UI)."""
    # Keep this import inside the function: the script uses lazy imports inside main()
    # and we still want this helper to work without relying on a global.
    import placement_engine

    prefer = _norm(prefer_fullname)

    # Prefer types already used in the model
    type_counts = _collect_existing_light_type_counts(doc, limit=3000)
    if type_counts:
        try:
            best_tid = max(type_counts.items(), key=lambda kv: kv[1])[0]
            sym0 = doc.GetElement(DB.ElementId(int(best_tid)))
            if sym0 is not None and isinstance(sym0, DB.FamilySymbol):
                try:
                    if placement_engine.is_supported_point_placement(sym0):
                        return sym0, [placement_engine.format_family_type(sym0)]
                except Exception:
                    pass
        except Exception:
            pass

    ranked = []
    scanned = 0
    for s in placement_engine.iter_family_symbols(doc, category_bic=DB.BuiltInCategory.OST_LightingFixtures, limit=None):
        scanned += 1
        if scan_cap and scanned > int(scan_cap):
            break
        try:
            if not placement_engine.is_supported_point_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue

            sc = _score_light_label(lbl)
            if prefer and (_norm(lbl) == prefer):
                sc += 1000

            try:
                c = type_counts.get(int(s.Id.IntegerValue), 0)
                if c:
                    sc += min(80, c * 2)
            except Exception:
                pass

            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None, []

    ranked.sort(key=lambda x: (x[0], _norm(x[1])), reverse=True)
    best = ranked[0]
    return best[2], [r[1] for r in ranked[:10]]


def _get_param_as_string(elem, bip=None, name=None):
    if elem is None:
        return ''
    p = None
    try:
        if bip is not None:
            p = elem.get_Parameter(bip)
    except Exception:
        p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return ''
    try:
        s = p.AsString()
        return s if s is not None else ''
    except Exception:
        return ''


def _room_text(room):
    if room is None:
        return ''
    parts = []
    try:
        n = room.Name
        if n:
            parts.append(n)
    except Exception:
        pass

    try:
        parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME, name='Name'))
    except Exception:
        pass
    try:
        parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER, name='Number'))
    except Exception:
        pass
    try:
        parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT, name='Department'))
    except Exception:
        pass

    try:
        return u' '.join([p for p in parts if p])
    except Exception:
        try:
            return ' '.join([p for p in parts if p])
        except Exception:
            return ''


def _collect_existing_tagged_points(host_doc, tag):
    """Collect points for already tagged instances, using parameter filters (faster than scanning all instances)."""
    pts = []
    t = _norm(tag)
    if not t:
        return pts

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        # Revit API versions differ a bit; try both
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag)

        pfilter = DB.ElementParameterFilter(rule)

        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfCategory(DB.BuiltInCategory.OST_LightingFixtures)
               .WherePasses(pfilter)
               .ToElements())

        for e in col:
            try:
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
                if p:
                    pts.append(p)
            except Exception:
                continue
    except Exception:
        # Fallback: do nothing (avoid heavy scanning)
        return []

    return pts


def _count_tagged_instances(host_doc, tag):
    t = (tag or '').strip()
    if not t:
        return 0
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, t, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, t)
        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfCategory(DB.BuiltInCategory.OST_LightingFixtures)
               .WherePasses(pfilter))
        # Don't call ToElements() on big sets; just count
        c = 0
        for _ in col:
            c += 1
        return c
    except Exception:
        return 0


def _count_tagged_family_instances_any_category(host_doc, tag):
    t = (tag or '').strip()
    if not t:
        return 0
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, t, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, t)
        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(host_doc)
               .WhereElementIsNotElementType()
               .OfClass(DB.FamilyInstance)
               .WherePasses(pfilter))
        c = 0
        for _ in col:
            c += 1
        return c
    except Exception:
        return 0


def _bbox_from_element_ids(doc, ids, pad_ft=30.0, limit=500):
    if doc is None or not ids:
        return None
    try:
        pad = float(pad_ft or 0.0)
        minx = None
        miny = None
        minz = None
        maxx = None
        maxy = None
        maxz = None
        i = 0
        for eid in ids:
            i += 1
            if limit and i > int(limit):
                break
            e = None
            try:
                e = doc.GetElement(eid)
            except Exception:
                e = None
            if e is None:
                continue

            p = None
            try:
                loc = e.Location
                p = loc.Point if loc and hasattr(loc, 'Point') else None
            except Exception:
                p = None

            if p is None:
                try:
                    bb = e.get_BoundingBox(None)
                    if bb:
                        p = (bb.Min + bb.Max) * 0.5
                except Exception:
                    p = None

            if p is None:
                continue

            if minx is None:
                minx = p.X
                miny = p.Y
                minz = p.Z
                maxx = p.X
                maxy = p.Y
                maxz = p.Z
            else:
                if p.X < minx:
                    minx = p.X
                if p.Y < miny:
                    miny = p.Y
                if p.Z < minz:
                    minz = p.Z
                if p.X > maxx:
                    maxx = p.X
                if p.Y > maxy:
                    maxy = p.Y
                if p.Z > maxz:
                    maxz = p.Z

        if minx is None:
            return None

        bb2 = DB.BoundingBoxXYZ()
        bb2.Min = DB.XYZ(minx - pad, miny - pad, minz - pad)
        bb2.Max = DB.XYZ(maxx + pad, maxy + pad, maxz + pad)
        return bb2
    except Exception:
        return None


def _is_near_existing(pt, existing_pts, radius_ft):
    if pt is None or not existing_pts or radius_ft is None:
        return False
    r = float(radius_ft)
    for p in existing_pts:
        try:
            if pt.DistanceTo(p) <= r:
                return True
        except Exception:
            continue
    return False


def _pt_key_mm(pt, step_mm=5):
    """Hash point with mm grid to detect duplicates without expensive distance checks.

    step_mm=5 means points within ~5mm grid cell will be treated as same.
    """
    if pt is None:
        return None
    try:
        s = float(step_mm or 5)
        if s <= 0:
            s = 5.0
        # feet -> mm
        x = float(pt.X) * 304.8
        y = float(pt.Y) * 304.8
        z = float(pt.Z) * 304.8
        return (int(round(x / s)), int(round(y / s)), int(round(z / s)))
    except Exception:
        return None


def _dedupe_points(points, existing_pts, radius_ft, mode='radius', key_step_mm=5):
    """Return (filtered_points, skipped_count)."""
    pts = points or []
    ex = existing_pts or []
    if not pts:
        return [], 0

    if not ex:
        return list(pts), 0

    out = []
    skipped = 0

    if mode == 'exact':
        keys = set()
        for p in ex:
            k = _pt_key_mm(p, step_mm=key_step_mm)
            if k is not None:
                keys.add(k)
        for p in pts:
            k = _pt_key_mm(p, step_mm=key_step_mm)
            if k is not None and k in keys:
                skipped += 1
                continue
            out.append(p)
        return out, skipped

    # default: radius-based
    r = float(radius_ft or 0.0)
    for p in pts:
        if r > 0 and _is_near_existing(p, ex, r):
            skipped += 1
            continue
        out.append(p)
    return out, skipped


def _enforce_min_spacing(points_xyz, min_dist_ft):
    """Filter points so that no two accepted points are closer than min_dist_ft."""
    pts = points_xyz or []
    try:
        d = float(min_dist_ft or 0.0)
    except Exception:
        d = 0.0
    if d <= 0.0 or len(pts) < 2:
        return list(pts), 0

    cell = d
    grid = {}
    kept = []
    skipped = 0

    def _cell_key(p):
        return (int(p.X / cell), int(p.Y / cell))

    for p in pts:
        k = _cell_key(p)
        ok = True
        # check neighbor cells
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                kk = (k[0] + dx, k[1] + dy)
                arr = grid.get(kk)
                if not arr:
                    continue
                for q in arr:
                    try:
                        if p.DistanceTo(q) < d:
                            ok = False
                            break
                    except Exception:
                        continue
                if not ok:
                    break
            if not ok:
                break

        if not ok:
            skipped += 1
            continue

        kept.append(p)
        grid.setdefault(k, []).append(p)

    return kept, skipped


def _chunks(seq, n):
    if not seq:
        return
    n = max(int(n or 1), 1)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    trace('PlaceLightsFromRooms: start')
    output.print_md('# Place: Light at Linked Room Centers (demo)')
    output.print_md('Host (EOM) document: `{0}`'.format(doc.Title))

    # Lazy imports (so we can trace before potentially risky module import/collector calls)
    import config_loader
    import link_reader
    import placement_engine

    trace('Select link UI')
    link_inst = link_reader.select_link_instance(doc, title='Select AR Link')
    if link_inst is None:
        trace('Cancelled at link selection')
        output.print_md('**Cancelled.**')
        return

    trace('Selected link: {0}'.format(getattr(link_inst, 'Name', '<no name>')))
    if not link_reader.is_link_loaded(link_inst):
        alert('Selected link is not loaded. Load it in Manage Links and retry.')
        return

    trace('Get link_doc')
    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Could not access link document. Is the link loaded?')
        return

    output.print_md('Selected link: `{0}`'.format(link_inst.Name))

    trace('Load rules')
    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    height_mm = rules.get('light_center_room_height_mm', 2700)
    dedupe_mm = rules.get('dedupe_radius_mm', 500)
    max_place = int(rules.get('max_place_count', 200) or 200)
    batch_size = int(rules.get('batch_size', 25) or 25)
    scan_limit_rooms = int(rules.get('scan_limit_rooms', 500) or 500)
    enable_existing_dedupe = bool(rules.get('enable_existing_dedupe', False))
    debug_section_half_height_mm = rules.get('debug_section_half_height_mm', 1500)
    exclude_room_name_keywords = rules.get('exclude_room_name_keywords', []) or []
    min_light_spacing_mm = rules.get('min_light_spacing_mm', 0) or 0
    min_light_wall_clearance_mm = rules.get('min_light_wall_clearance_mm', 300) or 300
    fam_fullname = (rules.get('family_type_names', {}) or {}).get('light_ceiling_point') or ''

    trace('Rules loaded: fam_fullname="{0}" max_place={1}'.format(fam_fullname, max_place))

    if fam_fullname:
        output.print_md('Configured target type (optional): `{0}`'.format(fam_fullname))

    # Select family type WITHOUT picking elements (works even when other models are only underlays)
    cfg = _get_user_config()
    symbol = None

    # 0) Fast path: cached symbol (avoids scanning types; most stable)
    trace('Try load symbol from saved unique id')
    symbol = _load_symbol_from_saved_unique_id(doc, cfg, 'last_light_symbol_uid')
    if symbol is None:
        trace('Try load symbol from saved id')
        symbol = _load_symbol_from_saved_id(doc, cfg, 'last_light_symbol_id')
    if symbol is not None:
        try:
            output.print_md('Using cached light type: `{0}`'.format(placement_engine.format_family_type(symbol)))
        except Exception:
            pass

    # No user prompts: auto-pick a suitable light type if not cached.
    if symbol is None:
        trace('Auto-pick light symbol (no UI)')
        symbol, top10 = _auto_pick_light_symbol(doc, prefer_fullname=fam_fullname, scan_cap=2000)
        if symbol is not None:
            try:
                output.print_md('Auto-selected light type: `{0}`'.format(placement_engine.format_family_type(symbol)))
            except Exception:
                pass
            if top10:
                output.print_md('Top candidates (auto):')
                for x in top10:
                    output.print_md('- `{0}`'.format(x))

    if symbol is None:
        alert('Не удалось автоматически выбрать тип светильника.\n\nЗагрузите подходящее семейство (точечное/по рабочей плоскости) в активный документ ЭОМ и повторите.')
        return

    # Cache for next run
    try:
        _store_symbol_id(cfg, 'last_light_symbol_id', symbol)
        _store_symbol_unique_id(cfg, 'last_light_symbol_uid', symbol)
        _save_user_config()
    except Exception:
        pass

    trace('Symbol selected: {0}'.format(placement_engine.format_family_type(symbol)))

    # Validate placement type (safety)
    _, pt_name = placement_engine.get_symbol_placement_type(symbol)
    output.print_md('Family placement type: `{0}`'.format(pt_name))
    if not placement_engine.is_supported_point_placement(symbol):
        alert(
            'Selected family type is NOT supported by this demo placement.\n\n'
            'Family placement type: {0}\n\n'
            'Use a simple point-based or work-plane-based light family (NOT ceiling/face-hosted).'.format(pt_name)
        )
        return

    _report_symbol_geometry(symbol)

    trace('Collect rooms')
    # Optional level filter (major performance boost)
    lvl = None
    try:
        lvl_choice = forms.CommandSwitchWindow.show(
            ['Pick AR level (recommended)', 'All levels (slow)', 'Cancel'],
            message='Rooms can be very heavy. Filter by AR level?'
        )
    except Exception:
        lvl_choice = 'Pick AR level (recommended)'

    if not lvl_choice or lvl_choice == 'Cancel':
        return

    if lvl_choice.startswith('Pick'):
        lvl = link_reader.select_level(link_doc, title='Select AR Level (Rooms)', allow_none=True)

    level_id = lvl.Id if lvl else None

    # Pick / infer host level to avoid placing on the wrong story (common cause of "nothing appears")
    host_level = None
    if lvl is not None:
        try:
            # match by name
            lname = (lvl.Name or '').strip().lower()
            for hl in link_reader.list_levels(doc):
                try:
                    if (hl.Name or '').strip().lower() == lname:
                        host_level = hl
                        break
                except Exception:
                    continue
        except Exception:
            host_level = None

    if host_level is None:
        host_level = link_reader.select_level(doc, title='Select HOST Level (where to place lights)', allow_none=True)

    if host_level is not None:
        output.print_md('Host level for placement: `{0}`'.format(host_level.Name))

    t = link_reader.get_total_transform(link_inst)
    z_off = mm_to_ft(height_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0
    debug_hh_ft = mm_to_ft(debug_section_half_height_mm) or 0.0
    min_spacing_ft = mm_to_ft(min_light_spacing_mm) or 0.0
    min_wall_clear_ft = mm_to_ft(min_light_wall_clearance_mm) or 0.0

    trace('Compute points from rooms')
    points = []
    skipped_no_center = 0
    skipped_unplaced = 0
    skipped_excluded = 0
    c_boundary = 0
    c_location = 0
    c_bbox = 0
    processed = 0
    truncated = False
    pb_max = scan_limit_rooms if scan_limit_rooms > 0 else 500
    host_level_z = None
    try:
        host_level_z = float(host_level.Elevation) if host_level is not None else None
    except Exception:
        host_level_z = None

    placement_z = (host_level_z + z_off) if host_level_z is not None else None

    with forms.ProgressBar(title='EOM: Reading room centers', cancellable=True, step=1) as pb:
        pb.max_value = pb_max
        for r in link_reader.iter_rooms(link_doc, limit=scan_limit_rooms, level_id=level_id):
            processed += 1
            pb.update_progress(min(processed, pb_max), pb_max)
            if pb.cancelled:
                trace('Cancelled while computing room points')
                return

            # Skip unplaced / not-enclosed rooms
            try:
                if hasattr(r, 'Area') and float(r.Area) <= 0.0:
                    skipped_unplaced += 1
                    continue
            except Exception:
                pass

            # Skip niches/balconies/etc by room name keywords
            try:
                rt = _norm(_room_text(r))
                excluded = False
                for kw in exclude_room_name_keywords:
                    nkw = _norm(kw)
                    if nkw and (nkw in rt):
                        excluded = True
                        break
                if excluded:
                    skipped_excluded += 1
                    continue
            except Exception:
                pass

            c, m = link_reader.get_room_center_ex_safe(r, min_wall_clear_ft, return_method=True)
            if c is None:
                skipped_no_center += 1
                continue

            if m == 'boundary':
                c_boundary += 1
            elif m == 'location':
                c_location += 1
            elif m == 'bbox':
                c_bbox += 1

            host_c = t.OfPoint(c)
            z = (host_level_z + z_off) if host_level_z is not None else (host_c.Z + z_off)
            points.append(DB.XYZ(host_c.X, host_c.Y, z))

            # Hard cap to avoid freezing on huge models
            if max_place > 0 and len(points) >= max_place:
                truncated = True
                break

    if not points:
        alert('No valid room centers found.\n\nSkipped: unplaced={0}, no_center={1}'.format(skipped_unplaced, skipped_no_center))
        return

    comment_value = '{0}:LIGHT_FROM_LINK'.format(comment_tag)

    output.print_md('---')
    output.print_md('Rooms processed: **{0}**{1}'.format(processed, ' (level-filtered)' if lvl else ''))
    if skipped_unplaced:
        output.print_md('Skipped (unplaced/Area=0): **{0}**'.format(skipped_unplaced))
    if skipped_excluded:
        output.print_md('Skipped (excluded by name keywords): **{0}**'.format(skipped_excluded))
    if skipped_no_center:
        output.print_md('Skipped (no center): **{0}**'.format(skipped_no_center))
    output.print_md('Candidate placements: **{0}**'.format(len(points)))
    output.print_md('Center method counts: boundary={0}, location={1}, bbox={2}'.format(c_boundary, c_location, c_bbox))
    if truncated:
        output.print_md('**Note:** Reached max_place_count limit ({0}). Rerun tool for next batch or narrow the level.'.format(max_place))

    # No extra confirmation needed; max_place_count already caps the batch

    # Dedupe vs already placed AUTO_EOM lights
    # Repeat runs without dedupe create many identical instances and can destabilize Revit.
    existing_pts = []
    dedupe_mode = 'radius'

    try:
        existing_count = _count_tagged_instances(doc, comment_value)
    except Exception:
        existing_count = 0

    if existing_count and (not enable_existing_dedupe):
        # auto safety prompt
        try:
            go = forms.alert(
                'Detected {0} existing placed lights with tag `{1}`.\n\n'
                'If you run again without dedupe, Revit will create duplicates (often causes warnings and sometimes crashes).\n\n'
                'Enable safe dedupe for this run?'.format(existing_count, comment_value),
                title='EOM: Prevent duplicates',
                warn_icon=True,
                yes=True,
                no=True
            )
        except Exception:
            go = True

        if go:
            enable_existing_dedupe = True
            # Use exact dedupe (grid) to avoid skipping nearby valid points in adjacent rooms
            dedupe_mode = 'exact'
        else:
            dedupe_mode = 'radius'

    if enable_existing_dedupe:
        trace('Collect existing points for dedupe (count={0}, mode={1})'.format(existing_count, dedupe_mode))
        existing_pts = _collect_existing_tagged_points(doc, comment_value)

    filtered_points, skipped_dedupe = _dedupe_points(
        points,
        existing_pts,
        dedupe_ft,
        mode=dedupe_mode,
        key_step_mm=5
    )

    # Prevent clustering: enforce minimum distance between placed lights
    skipped_spacing = 0
    if min_spacing_ft > 0.0:
        filtered_points, skipped_spacing = _enforce_min_spacing(filtered_points, min_spacing_ft)

    output.print_md('After dedupe ({0}mm): **{1}** to place, skipped **{2}**'.format(
        dedupe_mm, len(filtered_points), skipped_dedupe
    ))
    if min_spacing_ft > 0.0:
        output.print_md('Min spacing filter ({0}mm): kept **{1}**, skipped **{2}**'.format(
            int(min_light_spacing_mm), len(filtered_points), skipped_spacing
        ))
    if not filtered_points:
        output.print_md('Nothing to place.')
        return

    # Debug: detect "all points stacked" or "far away" situations
    try:
        st = _points_debug_stats(filtered_points)
        if st:
            output.print_md('Points bbox(ft): min=({0:.2f},{1:.2f},{2:.2f}) max=({3:.2f},{4:.2f},{5:.2f}) range_xy=({6:.2f},{7:.2f})'.format(
                st['min'].X, st['min'].Y, st['min'].Z,
                st['max'].X, st['max'].Y, st['max'].Z,
                st['range_x'], st['range_y']
            ))
            if st['range_x'] < 1.0 and st['range_y'] < 1.0:
                output.print_md('**Warning:** placement points are almost identical in XY (lights may be stacked in one spot).')
    except Exception:
        pass

    # Batch transactions to reduce risk of Revit instability on large counts
    created_count = 0
    first_created_id = None
    created_ids = []
    batch_size = max(batch_size, 1)
    trace('Start placement batches: total={0}'.format(len(filtered_points)))
    batches = list(_chunks(filtered_points, batch_size))
    with forms.ProgressBar(title='EOM: Placing lights', cancellable=True, step=1) as pb2:
        pb2.max_value = len(batches)
        bi = 0
        for batch in batches:
            bi += 1
            pb2.update_progress(bi, pb2.max_value)
            if pb2.cancelled:
                trace('Cancelled during placement batches')
                break

            with tx('EOM: Place lights from linked rooms (demo)', doc=doc, swallow_warnings=True):
                created = placement_engine.place_lights_at_points(
                    doc,
                    symbol,
                    batch,
                    comment_value=comment_value,
                    view=doc.ActiveView,
                    prefer_level=host_level,
                    continue_on_error=True
                )
                created_count += len(created)
                if first_created_id is None and created:
                    try:
                        first_created_id = created[0].Id
                    except Exception:
                        first_created_id = None
                if created:
                    # keep a limited list for selection/zoom
                    try:
                        for ci in created:
                            if len(created_ids) >= 500:
                                break
                            created_ids.append(ci.Id)
                    except Exception:
                        pass

            trace('Batch done: placed={0}'.format(created_count))

    output.print_md('---')
    output.print_md('Placed **{0}** light(s).'.format(created_count))
    if skipped_dedupe:
        output.print_md('Skipped by dedupe: **{0}**'.format(skipped_dedupe))
    output.print_md('Comments tag set to: `{0}`'.format(comment_value))

    # Verify elements actually exist in the model (not just counted during creation)
    try:
        total_tagged_cat = _count_tagged_instances(doc, comment_value)
        total_tagged_any = _count_tagged_family_instances_any_category(doc, comment_value)
        output.print_md('Model now contains tagged lights (LightingFixtures): **{0}**'.format(total_tagged_cat))
        output.print_md('Model now contains tagged family instances (ANY category): **{0}**'.format(total_tagged_any))
    except Exception:
        pass

    # Help locate placed instances (common: user is on a sheet or plan that doesn't show fixtures)
    if created_count > 0:
        try:
            e0 = doc.GetElement(first_created_id) if first_created_id else None
            if e0:
                p0 = None
                try:
                    loc = e0.Location
                    p0 = loc.Point if loc and hasattr(loc, 'Point') else None
                except Exception:
                    p0 = None

                try:
                    lvl0 = doc.GetElement(e0.LevelId) if hasattr(e0, 'LevelId') else None
                    lvl0_name = lvl0.Name if lvl0 else ''
                except Exception:
                    lvl0_name = ''

                if p0:
                    output.print_md('First placed id: `{0}` level: `{1}` xyz(ft): ({2:.3f}, {3:.3f}, {4:.3f})'.format(
                        int(first_created_id.IntegerValue), lvl0_name, float(p0.X), float(p0.Y), float(p0.Z)
                    ))
        except Exception:
            pass

        # Debug bbox of created elements (helps detect "everything in one point" or "far away")
        try:
            bb_created = _bbox_from_element_ids(doc, created_ids, pad_ft=0.0, limit=500)
            if bb_created:
                rx = float(bb_created.Max.X - bb_created.Min.X)
                ry = float(bb_created.Max.Y - bb_created.Min.Y)
                rz = float(bb_created.Max.Z - bb_created.Min.Z)
                output.print_md('Created elements bbox(ft): min=({0:.2f},{1:.2f},{2:.2f}) max=({3:.2f},{4:.2f},{5:.2f}) range=({6:.2f},{7:.2f},{8:.2f})'.format(
                    float(bb_created.Min.X), float(bb_created.Min.Y), float(bb_created.Min.Z),
                    float(bb_created.Max.X), float(bb_created.Max.Y), float(bb_created.Max.Z),
                    rx, ry, rz
                ))
                if rx < 1.0 and ry < 1.0:
                    output.print_md('**Warning:** created instances are almost stacked in one XY location.')
        except Exception:
            pass

        # Offer to open a dedicated 3D view with a section box around placements
        try:
            go3d = forms.alert(
                'Элементы созданы, но их может быть не видно на текущем плане/листе (настройки вида, диапазон видимости, категория и т.д.).\n\nОткрыть отладочный 3D-вид и приблизить к размещённым светильникам?',
                title='ЭОМ: Найти размещённые светильники',
                warn_icon=False,
                yes=True,
                no=True
            )
        except Exception:
            go3d = False

        if go3d:
            try:
                # Prefer bbox from ACTUAL created instances; points-based bbox can miss them
                bb = _bbox_from_element_ids(doc, created_ids, pad_ft=60.0, limit=500)
                if bb is None:
                    bb = _bbox_from_points(filtered_points, pad_ft=60.0)

                # Make a proper "floor slice" section box around the actual placement Z
                bb = _adjust_bbox_z(bb, placement_z, debug_hh_ft)
                v3d = None
                with tx('ЭОМ: Открыть отладочный 3D-вид (светильники)', doc=doc, swallow_warnings=True):
                    v3d = _get_or_create_debug_3d_view(
                        doc,
                        'ЭОМ_ОТЛАДКА_Размещенные_Светильники',
                        aliases=['EOM_DEBUG_Placed_Lights']
                    )
                    if v3d and bb:
                        # ensure no template hides categories
                        try:
                            v3d.ViewTemplateId = DB.ElementId.InvalidElementId
                        except Exception:
                            pass

                        # maximize chance of seeing small families
                        try:
                            v3d.DetailLevel = DB.ViewDetailLevel.Fine
                        except Exception:
                            pass
                        try:
                            # Wireframe makes links very noisy; use shaded/hidden-line.
                            v3d.DisplayStyle = DB.DisplayStyle.Shading
                        except Exception:
                            pass

                        # Show Revit links in debug view (user wants to see underlay + placed lights)
                        try:
                            cat_links = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_RvtLinks)
                            if cat_links:
                                v3d.SetCategoryHidden(cat_links.Id, False)
                        except Exception:
                            pass

                        try:
                            cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_LightingFixtures)
                            if cat:
                                v3d.SetCategoryHidden(cat.Id, False)
                        except Exception:
                            pass

                        try:
                            v3d.IsSectionBoxActive = True
                        except Exception:
                            pass
                        try:
                            v3d.SetSectionBox(bb)
                        except Exception:
                            pass

                if v3d:
                    try:
                        ok = uidoc.RequestViewChange(v3d)
                    except Exception as ex:
                        pass

                    # After view switch: ensure NOT isolated (so link/underlay stays visible), select + zoom.
                    try:
                        av = uidoc.ActiveView
                        if av and created_ids:
                            try:
                                if av.IsTemporaryHideIsolateActive():
                                    av.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
                            except Exception:
                                pass

                            try:
                                uidoc.Selection.SetElementIds(_as_net_id_list(created_ids[:50]))
                            except Exception:
                                pass

                            try:
                                if first_created_id is not None:
                                    uidoc.ShowElements(first_created_id)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

    trace('Done: placed={0}'.format(created_count))
    logger.info('Placed %s light(s); skipped_unplaced=%s skipped_no_center=%s skipped_dedupe=%s',
                created_count, skipped_unplaced, skipped_no_center, skipped_dedupe)


try:
    main()
except Exception:
    log_exception('Place lights failed')
    alert('Tool failed. See pyRevit output for details.')
