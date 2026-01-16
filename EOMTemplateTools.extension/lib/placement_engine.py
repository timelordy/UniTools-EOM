# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms

from utils_revit import ensure_symbol_active, find_nearest_level, set_comments


def format_family_type(symbol):
    """Return 'Family : Type' label."""
    if symbol is None:
        return ''

    fam_name = ''
    # Prefer FamilyName (string) over Family.Name (can be heavier / less stable in some sessions).
    try:
        fam_name = getattr(symbol, 'FamilyName', None) or ''
    except Exception:
        fam_name = ''
    if not fam_name:
        try:
            fam = getattr(symbol, 'Family', None)
            fam_name = fam.Name if fam else ''
        except Exception:
            fam_name = ''
    try:
        type_name = symbol.Name
    except Exception:
        type_name = ''
    return u'{0} : {1}'.format(fam_name, type_name).strip()


def list_family_symbols(doc, category_bic=None):
    """List FamilySymbol in doc. If category_bic is set, filter by category."""
    # Deprecated for large projects (can be heavy). Kept for backward compat.
    return list(iter_family_symbols(doc, category_bic=category_bic, limit=None))


def iter_family_symbols(doc, category_bic=None, limit=None):
    """Yield FamilySymbol, optionally filtered by category, with optional limit.

    Avoids materializing all symbols into memory (reduces UI freeze risk).
    """
    if doc is None:
        return

    lim = None
    try:
        if limit is not None:
            lim = int(limit)
    except Exception:
        lim = None

    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
        if category_bic is not None:
            # This should be safe for FamilySymbol; do not swallow silently.
            col = col.OfCategory(category_bic)

        i = 0
        for s in col:
            yield s
            i += 1
            if lim is not None and i >= lim:
                break
    except Exception:
        return


def get_symbol_placement_type(symbol):
    """Return (enum_value, enum_name) for FamilyPlacementType, best-effort."""
    try:
        f = symbol.Family if symbol else None
        pt = f.FamilyPlacementType if f else None
        return pt, str(pt)
    except Exception:
        return None, 'Unknown'


def is_supported_point_placement(symbol):
    """We only support simple point placement families.

    In practice: OneLevelBased (or WorkPlaneBased if active view supports it).
    Hosted (ceiling/face) families are intentionally NOT supported in this demo.
    """
    pt, _ = get_symbol_placement_type(symbol)
    if pt is None:
        return False

    try:
        if pt == DB.FamilyPlacementType.OneLevelBased:
            return True
    except Exception:
        pass

    try:
        if pt == DB.FamilyPlacementType.WorkPlaneBased:
            return True
    except Exception:
        pass

    return False


def select_family_symbol(doc,
                         title='Select family type',
                         category_bic=None,
                         only_supported=True,
                         allow_none=True,
                         button_name='Select',
                         search_text=None,
                         limit=200,
                         scan_cap=5000):
    """Pick a FamilySymbol from loaded types with optional substring filter and cap.

    `search_text` filters by "Family : Type" contains (case-insensitive).
    `limit` caps number of items shown to avoid huge UI lists.
    """
    sfilter = _norm(search_text)
    lim = 200
    try:
        lim = int(limit or 200)
    except Exception:
        lim = 200
    lim = max(lim, 20)

    items = []
    scanned = 0
    scan_lim = 5000
    try:
        scan_lim = int(scan_cap or 5000)
    except Exception:
        scan_lim = 5000
    scan_lim = max(scan_lim, lim)

    for s in iter_family_symbols(doc, category_bic=category_bic, limit=None):
        scanned += 1
        try:
            if only_supported and (not is_supported_point_placement(s)):
                continue
            label = format_family_type(s)
            if not label:
                continue
            if sfilter and (sfilter not in _norm(label)):
                continue
            _, pt_name = get_symbol_placement_type(s)
            items.append((u'{0}   [{1}]'.format(label, pt_name), s))
            if len(items) >= lim:
                break
        except Exception:
            continue

        if scanned >= scan_lim:
            break

    if not items:
        return None

    # Sorting small lists is fine
    items = sorted(items, key=lambda x: x[0].lower())
    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False,
        button_name=button_name,
        allow_none=allow_none
    )

    if not picked:
        return None
    for lbl, sym in items:
        if lbl == picked:
            return sym
    return None


def _norm(s):
    try:
        return (s or '').strip().lower()
    except Exception:
        return ''


def _parse_family_type(fullname):
    """Parse 'Family : Type' -> (family, type)"""
    if not fullname:
        return None, None
    parts = [p.strip() for p in fullname.split(':')]
    if len(parts) == 1:
        # maybe "Family - Type" or just Type
        return None, parts[0]
    family = parts[0]
    type_name = ':'.join(parts[1:]).strip()
    return family, type_name


def find_family_symbol(doc, fullname, category_bic=None, limit=5000):
    """Find FamilySymbol by 'Family : Type' string.

    If category_bic is set, search within that category first.
    """
    fam_name, type_name = _parse_family_type(fullname)
    n_fam = _norm(fam_name)
    n_type = _norm(type_name)
    if not n_type:
        return None

    def _iter_symbols(collector):
        for s in collector:
            try:
                sym_type = _norm(getattr(s, 'Name', None))

                sym_fam = ''
                try:
                    sym_fam = _norm(getattr(s, 'FamilyName', None))
                except Exception:
                    sym_fam = ''
                if not sym_fam:
                    try:
                        fam = getattr(s, 'Family', None)
                        sym_fam = _norm(fam.Name) if fam else ''
                    except Exception:
                        sym_fam = ''

                if sym_type == n_type and ((not n_fam) or (sym_fam == n_fam)):
                    return s
            except Exception:
                continue
        return None

    try:
        found = _iter_symbols(iter_family_symbols(doc, category_bic=category_bic, limit=limit))
        if found:
            return found
        if category_bic is not None:
            return _iter_symbols(iter_family_symbols(doc, category_bic=None, limit=limit))
        return None
    except Exception:
        return None


def get_or_load_family_symbol(doc, fullname, category_bic=None, title='EOM Template Tools'):
    """Return FamilySymbol if present; otherwise instruct user to load it manually."""
    sym = find_family_symbol(doc, fullname, category_bic=category_bic)
    if sym:
        return sym

    forms.alert(
        'Family type not found in current project:\n\n  {0}\n\n'
        'Please load the family into the active EOM document (Insert -> Load Family), '
        'then run the tool again.'.format(fullname),
        title=title,
        warn_icon=True
    )
    return None


def place_point_family_instance(doc, symbol, point_xyz, prefer_level=None, view=None):
    """Place point-based family instance at XYZ. Returns created instance or None."""
    if doc is None or symbol is None or point_xyz is None:
        return None

    pt_enum, pt_name = get_symbol_placement_type(symbol)
    if not is_supported_point_placement(symbol):
        raise Exception('Unsupported family placement type for demo placement: {0}'.format(pt_name))

    ensure_symbol_active(doc, symbol)

    # WorkPlaneBased families are placed in a view context
    try:
        if pt_enum == DB.FamilyPlacementType.WorkPlaneBased:
            v = view or doc.ActiveView
            # If view has no sketch plane, placement can fail unpredictably.
            try:
                sp = getattr(v, 'SketchPlane', None)
                if sp is None:
                    raise Exception('Active view has no work plane (SketchPlane is None).')
            except Exception:
                # still try; some views don't expose SketchPlane
                pass

            return doc.Create.NewFamilyInstance(point_xyz, symbol, v)
    except Exception:
        # Do NOT fall back to level-based placement for WorkPlaneBased families.
        raise

    # OneLevelBased families: place by nearest level
    lvl = prefer_level or find_nearest_level(doc, point_xyz.Z)
    if lvl is None:
        raise Exception('No Level found in host doc to place instance.')

    return doc.Create.NewFamilyInstance(
        point_xyz,
        symbol,
        lvl,
        DB.Structure.StructuralType.NonStructural
    )


def place_lights_at_points(doc, symbol, points_xyz, comment_value=None, view=None, prefer_level=None, continue_on_error=True):
    created = []
    for pt in points_xyz or []:
        try:
            inst = place_point_family_instance(doc, symbol, pt, prefer_level=prefer_level, view=view)
        except Exception:
            if continue_on_error:
                continue
            raise
        if inst and comment_value is not None:
            set_comments(inst, comment_value)
        if inst:
            created.append(inst)
    return created
