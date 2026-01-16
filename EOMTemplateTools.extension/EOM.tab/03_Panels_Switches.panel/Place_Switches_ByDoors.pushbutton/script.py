# -*- coding: utf-8 -*-

import math
import re
import difflib

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, ensure_symbol_active, log_exception, set_comments, tx
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()

ALLOW_POINT_SWITCH = False


# --- regex helpers ---


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _norm_type_key(s):
    """Normalize type/name strings to reduce Cyrillic/Latin look-alike mismatches.

    Common real-world issue: type names may contain Latin 'P' vs Cyrillic 'Р' (looks identical).
    """
    t = _norm(s)
    if not t:
        return t
    try:
        # Cyrillic -> Latin look-alikes (reduces copy/paste mismatches)
        repl = {
            u'а': u'a',
            u'в': u'b',
            u'е': u'e',
            u'к': u'k',
            u'м': u'm',
            u'н': u'h',
            u'о': u'o',
            u'р': u'p',
            u'с': u'c',
            u'т': u't',
            u'у': u'y',
            u'х': u'x',
        }
        for k, v in repl.items():
            t = t.replace(k, v)
    except Exception:
        pass

    # Normalize whitespace / separators (handles "Family:Type" vs "Family : Type")
    try:
        t = u' '.join(t.split())
    except Exception:
        pass
    try:
        t = t.replace(u' : ', u':').replace(u' :', u':').replace(u': ', u':')
    except Exception:
        pass
    return t


def _compile_patterns(patterns):
    out = []
    for p in (patterns or []):
        try:
            s = (p or u'').strip()
            if not s:
                continue
            out.append(re.compile(s, re.IGNORECASE))
        except Exception:
            # treat invalid regex as a plain substring
            try:
                s2 = (p or u'').strip()
                if s2:
                    out.append(re.compile(re.escape(s2), re.IGNORECASE))
            except Exception:
                continue
    return out


def _match_any(rx_list, text):
    t = text or u''
    for rx in rx_list or []:
        try:
            if rx.search(t):
                return True
        except Exception:
            continue
    return False


def _room_name(room):
    if room is None:
        return u''
    try:
        return room.Name or u''
    except Exception:
        return u''


def _room_area(room):
    if room is None:
        return None
    try:
        a = float(getattr(room, 'Area', None))
        return a if a > 1e-9 else None
    except Exception:
        return None


# --- selection ---


def _select_link_instance_ru(host_doc, title):
    links = link_reader.list_link_instances(host_doc)
    if not links:
        return None

    items = []
    for ln in links:
        try:
            name = ln.Name
        except Exception:
            name = u'<Связь>'
        status = u'Загружена' if link_reader.is_link_loaded(ln) else u'Не загружена'
        items.append((u'{0}  [{1}]'.format(name, status), ln))

    items = sorted(items, key=lambda x: _norm(x[0]))
    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False,
        button_name='Выбрать',
        allow_none=True
    )
    if not picked:
        return None

    for lbl, inst in items:
        if lbl == picked:
            return inst
    return None


def _auto_pick_link_instance_ru(host_doc, scan_limit_doors=200):
    links = link_reader.list_link_instances(host_doc)
    if not links:
        return None

    loaded = []
    for ln in links:
        try:
            if link_reader.is_link_loaded(ln):
                loaded.append(ln)
        except Exception:
            continue

    if not loaded:
        return None

    if len(loaded) == 1:
        return loaded[0]

    lim = None
    try:
        lim = int(scan_limit_doors)
    except Exception:
        lim = None
    if lim is None or lim <= 0:
        lim = 200

    def _score(name):
        n = name or u''
        n_norm = _norm(n)
        score = 0
        try:
            if re.search(r'(^|[^A-Za-zА-Яа-я])ар($|[^A-Za-zА-Яа-я])', n, re.IGNORECASE):
                score += 10
        except Exception:
            pass
        try:
            if re.search(r'(^|[^A-Za-zА-Яа-я])ar($|[^A-Za-zА-Яа-я])', n, re.IGNORECASE):
                score += 10
        except Exception:
            pass
        try:
            if u'арх' in n_norm or 'arch' in n_norm or 'architecture' in n_norm:
                score += 5
        except Exception:
            pass
        return score

    scored = []
    for ln in loaded:
        try:
            name = ln.Name
        except Exception:
            name = u''
        door_count = 0
        try:
            ldoc = link_reader.get_link_doc(ln)
            if ldoc is not None:
                for _ in link_reader.iter_doors(ldoc, limit=lim, level_id=None):
                    door_count += 1
        except Exception:
            door_count = 0
        scored.append((1 if door_count > 0 else 0, _score(name), door_count, _norm(name), ln))

    scored.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
    return scored[0][4]


def _pick_linked_doors(link_inst):
    """User picks doors in the selected link."""
    sel = uidoc.Selection

    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class _DoorFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return elem and elem.Id == link_inst.Id
            except Exception:
                return False

        def AllowReference(self, reference, position):
            try:
                if reference is None:
                    return False
                if reference.ElementId != link_inst.Id:
                    return False
                if reference.LinkedElementId is None or reference.LinkedElementId == DB.ElementId.InvalidElementId:
                    return False
                ldoc = link_inst.GetLinkDocument()
                if ldoc is None:
                    return False
                le = ldoc.GetElement(reference.LinkedElementId)
                if le is None:
                    return False
                cat = le.Category
                return cat and cat.Id.IntegerValue == int(DB.BuiltInCategory.OST_Doors)
            except Exception:
                return False

    try:
        refs = sel.PickObjects(ObjectType.LinkedElement, _DoorFilter(), 'Выберите двери в связанном файле АР')
    except Exception:
        return []

    picked = []
    ldoc = link_inst.GetLinkDocument()
    for r in refs or []:
        try:
            if r.ElementId != link_inst.Id:
                continue
            de = ldoc.GetElement(r.LinkedElementId)
            if de:
                picked.append(de)
        except Exception:
            continue
    return picked


# --- geometry / room side ---


def _xy_unit(vec):
    if vec is None:
        return None
    try:
        v = DB.XYZ(float(vec.X), float(vec.Y), 0.0)
        if v.GetLength() < 1e-9:
            return None
        return v.Normalize()
    except Exception:
        return None


def _xy_perp(v):
    v = _xy_unit(v)
    if v is None:
        return None
    try:
        return DB.XYZ(-float(v.Y), float(v.X), 0.0)
    except Exception:
        return None


def _door_center_point_link(door):
    if door is None:
        return None
    try:
        loc = getattr(door, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is not None:
            return pt
    except Exception:
        pass
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return (bb.Min + bb.Max) * 0.5
    except Exception:
        pass
    return None


def _get_last_phase(doc_):
    try:
        phases = list(doc_.Phases)
        return phases[-1] if phases else None
    except Exception:
        return None


def _get_preferred_phases(door, link_doc, phase_hint=None):
    """Return a best-effort ordered list of phases to try for room lookups."""
    phases = []

    def _add(ph):
        if ph is None:
            return
        try:
            pid = int(ph.Id.IntegerValue)
        except Exception:
            pid = None
        for e in phases:
            try:
                if pid is not None and int(e.Id.IntegerValue) == pid:
                    return
            except Exception:
                pass
            try:
                if e == ph:
                    return
            except Exception:
                pass
        phases.append(ph)

    _add(phase_hint)

    # Prefer door's created phase if available
    if door is not None and link_doc is not None:
        try:
            pid = getattr(door, 'CreatedPhaseId', None)
            if pid and pid != DB.ElementId.InvalidElementId:
                _add(link_doc.GetElement(pid))
        except Exception:
            pass

        try:
            p = door.get_Parameter(DB.BuiltInParameter.PHASE_CREATED)
            if p:
                pid = p.AsElementId()
                if pid and pid != DB.ElementId.InvalidElementId:
                    _add(link_doc.GetElement(pid))
        except Exception:
            pass

    # Last phase + all phases (fallback)
    try:
        all_ph = list(link_doc.Phases) if link_doc is not None else []
    except Exception:
        all_ph = []

    if all_ph:
        _add(all_ph[-1])
        for ph in all_ph:
            _add(ph)

    return phases


def _collect_host_walls(doc_):
    if doc_ is None:
        return []
    walls = []
    try:
        col = (DB.FilteredElementCollector(doc_)
               .OfClass(DB.Wall)
               .WhereElementIsNotElementType())
        for w in col:
            try:
                bb = w.get_BoundingBox(None)
            except Exception:
                bb = None
            walls.append((w, bb))
    except Exception:
        return []
    return walls


def _nearest_host_wall(walls_with_bb, pt, max_dist_ft):
    if not walls_with_bb or pt is None:
        return None
    try:
        max_d = float(max_dist_ft or 0.0)
    except Exception:
        max_d = 0.0
    if max_d <= 1e-6:
        return None

    best_w = None
    best_d = None
    for w, bb in walls_with_bb:
        if w is None:
            continue
        if bb is not None:
            try:
                if (
                    pt.X < bb.Min.X - max_d or pt.X > bb.Max.X + max_d or
                    pt.Y < bb.Min.Y - max_d or pt.Y > bb.Max.Y + max_d
                ):
                    continue
            except Exception:
                pass

        c = None
        try:
            loc = getattr(w, 'Location', None)
            if isinstance(loc, DB.LocationCurve):
                c = loc.Curve
        except Exception:
            c = None
        if c is None:
            continue

        try:
            p = DB.XYZ(float(pt.X), float(pt.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p)
            proj = ir.XYZPoint if ir else None
        except Exception:
            proj = None
        if proj is None:
            continue

        try:
            dx = float(proj.X) - float(pt.X)
            dy = float(proj.Y) - float(pt.Y)
            d = (dx * dx + dy * dy) ** 0.5
        except Exception:
            continue

        if best_d is None or d < best_d:
            best_d = d
            best_w = w

    if best_w is None or best_d is None:
        return None
    try:
        if float(best_d) > float(max_d):
            return None
    except Exception:
        return None

    return best_w


def _wall_tangent_xy(wall):
    if wall is None:
        return None
    try:
        loc = getattr(wall, 'Location', None)
        if isinstance(loc, DB.LocationCurve):
            c = loc.Curve
            d = c.GetEndPoint(1) - c.GetEndPoint(0)
            return _xy_unit(d)
    except Exception:
        pass
    try:
        o = getattr(wall, 'Orientation', None)
        return _xy_perp(o)
    except Exception:
        return None


def _get_host_wall_face_ref_and_point(wall, point_host):
    """Return (face_ref, projected_point_host) or (None, None)."""
    if wall is None or point_host is None:
        return None, None
    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Interior))
        except Exception:
            refs += []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Exterior))
        except Exception:
            refs += []
        if not refs:
            return None, None

        best_ref = None
        best_d = None
        best_pt = None
        for r in refs:
            try:
                face = wall.GetGeometryObjectFromReference(r)
            except Exception:
                face = None
            if face is None:
                continue
            try:
                ir = face.Project(point_host)
            except Exception:
                ir = None
            if ir is None:
                continue
            try:
                d = float(ir.Distance)
            except Exception:
                d = None
            if d is None:
                continue
            try:
                pt = getattr(ir, 'XYZPoint', None)
                if pt is None:
                    pt = getattr(ir, 'Point', None)
            except Exception:
                pt = None
            if pt is None:
                continue

            if best_d is None or d < best_d:
                best_ref = r
                best_d = d
                best_pt = pt

        if best_ref is None or best_pt is None:
            return None, None

        return best_ref, best_pt
    except Exception:
        return None, None


def _host_has_walls(doc_):
    if doc_ is None:
        return False
    try:
        col = (DB.FilteredElementCollector(doc_)
               .OfClass(DB.Wall)
               .WhereElementIsNotElementType())
        for _ in col:
            return True
    except Exception:
        pass
    return False


def _get_from_to_rooms_with_phase(door, link_doc):
    if door is None or link_doc is None:
        return None, None, None

    phases = _get_preferred_phases(door, link_doc)
    if not phases:
        return None, None, None

    fr = None
    tr = None
    used_ph = None

    for ph in phases:
        # Try indexed properties first (IronPython compatibility)
        if fr is None:
            try:
                rr = getattr(door, 'FromRoom', None)
                if rr is not None:
                    fr = rr[ph]
            except Exception:
                fr = None
        if tr is None:
            try:
                rr = getattr(door, 'ToRoom', None)
                if rr is not None:
                    tr = rr[ph]
            except Exception:
                tr = None

        # Fallback to API methods
        if fr is None:
            try:
                m = getattr(door, 'get_FromRoom', None)
                if m is not None:
                    fr = m(ph)
            except Exception:
                fr = None
        if tr is None:
            try:
                m = getattr(door, 'get_ToRoom', None)
                if m is not None:
                    tr = m(ph)
            except Exception:
                tr = None

        if fr is not None or tr is not None:
            used_ph = ph
            break

    return fr, tr, used_ph


def _try_get_room_at_point(doc_, pt, phase=None):
    if doc_ is None or pt is None:
        return None
    try:
        if phase is not None:
            return doc_.GetRoomAtPoint(pt, phase)
    except Exception:
        pass
    try:
        return doc_.GetRoomAtPoint(pt)
    except Exception:
        return None


def _get_from_to_rooms(door, link_doc):
    fr, tr, _ = _get_from_to_rooms_with_phase(door, link_doc)
    return fr, tr


def _try_get_wall_thickness_ft(door):
    if door is None:
        return None
    try:
        host = getattr(door, 'Host', None)
        if host is None:
            return None
        try:
            w = float(getattr(host, 'Width', None))
            if w > 0:
                return w
        except Exception:
            pass
        try:
            wt = getattr(host, 'WallType', None)
            w = float(getattr(wt, 'Width', None)) if wt is not None else None
            if w and w > 0:
                return w
        except Exception:
            pass
    except Exception:
        return None
    return None


def _try_get_door_facing_xy(door):
    if door is None:
        return None
    try:
        fo = getattr(door, 'FacingOrientation', None)
        v = _xy_unit(fo)
        if v is not None:
            return v
    except Exception:
        pass
    try:
        host = getattr(door, 'Host', None)
        o = getattr(host, 'Orientation', None) if host is not None else None
        v = _xy_unit(o)
        if v is not None:
            return v
    except Exception:
        pass
    return None


def _try_get_door_hand_xy(door):
    if door is None:
        return None
    try:
        ho = getattr(door, 'HandOrientation', None)
        v = _xy_unit(ho)
        if v is not None:
            return v
    except Exception:
        pass
    try:
        facing = _try_get_door_facing_xy(door)
        side = _xy_perp(facing)
        if side is None:
            return None
        hf = False
        try:
            hf = bool(getattr(door, 'HandFlipped', False))
        except Exception:
            hf = False
        if hf:
            side = DB.XYZ(-float(side.X), -float(side.Y), 0.0)
        return _xy_unit(side)
    except Exception:
        pass
    return None


def _get_door_width_ft(door):
    if door is None:
        return None
    # Try instance param first
    try:
        p = door.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
        if p:
            w = p.AsDouble()
            if w and float(w) > 1e-6:
                return float(w)
    except Exception:
        pass

    # Try type param
    try:
        sym = getattr(door, 'Symbol', None)
        if sym is not None:
            p = sym.get_Parameter(DB.BuiltInParameter.DOOR_WIDTH)
            if p:
                w = p.AsDouble()
                if w and float(w) > 1e-6:
                    return float(w)
    except Exception:
        pass

    return None


def _door_level_elevation_ft(door, link_doc, center_pt):
    # Prefer LevelId -> Level.Elevation
    try:
        lid = getattr(door, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId and link_doc is not None:
            lvl = link_doc.GetElement(lid)
            if lvl is not None and hasattr(lvl, 'Elevation'):
                return float(lvl.Elevation)
    except Exception:
        pass

    # Fallback: location Z
    try:
        if center_pt is not None:
            return float(center_pt.Z)
    except Exception:
        pass

    return 0.0


def _door_matches_level(door, level, z_tol_ft):
    if door is None or level is None:
        return True
    try:
        lid = getattr(door, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId:
            try:
                if int(lid.IntegerValue) == int(level.Id.IntegerValue):
                    return True
            except Exception:
                pass
    except Exception:
        pass

    try:
        target_z = float(getattr(level, 'Elevation', None))
    except Exception:
        target_z = None
    if target_z is None:
        return True

    try:
        c = _door_center_point_link(door)
        if c is not None and abs(float(c.Z) - float(target_z)) <= float(z_tol_ft or 0.0):
            return True
    except Exception:
        pass

    return False


def _room_id_int(room):
    try:
        return int(room.Id.IntegerValue) if room is not None else None
    except Exception:
        return None


def _dir_to_target_room_by_probe(door, link_doc, target_room, center_pt, facing_xy, phase_hint=None):
    """Return unit XY vector pointing towards target_room side. Uses GetRoomAtPoint probes."""
    if link_doc is None or target_room is None or center_pt is None or facing_xy is None:
        return None

    n = _xy_unit(facing_xy)
    if n is None:
        return None

    tid = _room_id_int(target_room)
    if tid is None:
        return None

    phases = _get_preferred_phases(door, link_doc, phase_hint=phase_hint)
    if not phases:
        phases = [None]
    th = _try_get_wall_thickness_ft(door)

    base_eps = mm_to_ft(500) or 0.0
    try:
        if th is not None:
            extra = (float(th) * 0.5) + (mm_to_ft(200) or 0.0)
            if extra > base_eps:
                base_eps = extra
    except Exception:
        pass

    try:
        zprobe = float(center_pt.Z) + (mm_to_ft(1000) or 0.0)
        base = DB.XYZ(float(center_pt.X), float(center_pt.Y), float(zprobe))
        for ph in phases:
            for eps in (base_eps, base_eps * 1.5, base_eps * 2.0):
                if eps <= 1e-9:
                    continue
                p_plus = base + (n * float(eps))
                p_minus = base + (n * float(-eps))
                r_plus = _try_get_room_at_point(link_doc, p_plus, phase=ph)
                r_minus = _try_get_room_at_point(link_doc, p_minus, phase=ph)
                if _room_id_int(r_plus) == tid:
                    return n
                if _room_id_int(r_minus) == tid:
                    return DB.XYZ(-n.X, -n.Y, 0.0)

            # Fallback: if one side has any room and the other doesn't
            r_plus = _try_get_room_at_point(link_doc, base + (n * float(base_eps)), phase=ph)
            r_minus = _try_get_room_at_point(link_doc, base + (n * float(-base_eps)), phase=ph)
            if r_plus is None and r_minus is not None:
                return DB.XYZ(-n.X, -n.Y, 0.0)
            if r_plus is not None and r_minus is None:
                return n
    except Exception:
        pass

    # Very last fallback: ToRoom side is often facing side
    try:
        fr, tr = _get_from_to_rooms(door, link_doc)
        if _room_id_int(tr) == tid:
            return n
        if _room_id_int(fr) == tid:
            return DB.XYZ(-n.X, -n.Y, 0.0)
    except Exception:
        pass

    return None


def _score_room_for_inside(room, corridor_rx):
    if room is None:
        return -999
    name = _room_name(room)
    if not name:
        return 0
    if _match_any(corridor_rx, name):
        return -50
    return 10


def _is_corridor_room(room, corridor_rx):
    return _match_any(corridor_rx, _room_name(room))


def _try_get_room_yesno_param(room, param_names):
    """Try read a room yes/no flag from parameters.

    Returns True/False when a matching parameter is found and parsed, otherwise None.
    """
    if room is None:
        return None

    names = list(param_names or [])
    if not names:
        return None

    truthy = set([u'1', u'да', u'yes', u'true', u'y', u'истина'])
    falsy = set([u'0', u'нет', u'no', u'false', u'n', u'ложь'])

    for nm in names:
        try:
            key = (nm or u'').strip()
        except Exception:
            key = u''
        if not key:
            continue

        p = None
        try:
            p = room.LookupParameter(key)
        except Exception:
            p = None
        if p is None:
            continue

        try:
            st = p.StorageType
        except Exception:
            st = None

        # Yes/No parameters are commonly integer 0/1
        try:
            if st == DB.StorageType.Integer:
                v = p.AsInteger()
                if v is None:
                    continue
                try:
                    return bool(int(v))
                except Exception:
                    return bool(v)
        except Exception:
            pass

        # Some parameters store strings like "Да"/"Нет"
        s = u''
        try:
            s = p.AsString()
        except Exception:
            s = u''
        if not s:
            try:
                s = p.AsValueString()
            except Exception:
                s = u''

        try:
            t = _norm(s)
        except Exception:
            t = u''
        if not t:
            continue
        if t in truthy:
            return True
        if t in falsy:
            return False

    return None


def _collect_room_ids_with_windows(link_doc, limit=0, level_id=None):
    """Return (room_ids_with_windows, windows_scanned, windows_with_room_binding)."""
    ids = set()
    scanned = 0
    bound = 0

    lim = None
    try:
        lim = None if int(limit or 0) <= 0 else int(limit)
    except Exception:
        lim = None

    try:
        it = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Windows, limit=lim, level_id=level_id)
    except Exception:
        it = []

    for w in it:
        scanned += 1
        fr, tr, _ = _get_from_to_rooms_with_phase(w, link_doc)
        if fr is not None or tr is not None:
            bound += 1
        rid = _room_id_int(fr)
        if rid is not None:
            ids.add(rid)
        rid = _room_id_int(tr)
        if rid is not None:
            ids.add(rid)

    return ids, scanned, bound


def _room_has_natural_light(room, rooms_with_windows, param_names=None, cache=None, default_when_unknown=True):
    """Return True when room has natural light, False otherwise.

    Natural light is detected by:
      1) optional Yes/No room parameter names
      2) presence of at least one Window bound to the room (FromRoom/ToRoom)

    If unknown, returns `default_when_unknown`.
    """
    if room is None:
        return bool(default_when_unknown)

    rid = _room_id_int(room)
    if cache is not None and rid is not None:
        try:
            if rid in cache:
                return bool(cache[rid])
        except Exception:
            pass

    v = _try_get_room_yesno_param(room, param_names)
    if v is None:
        try:
            if rooms_with_windows is not None and rid is not None:
                v = bool(rid in rooms_with_windows)
        except Exception:
            v = None

    if v is None:
        v = bool(default_when_unknown)

    if cache is not None and rid is not None:
        try:
            cache[rid] = bool(v)
        except Exception:
            pass

    return bool(v)


def _choose_rooms_for_switch(fr, tr, wet_rx, corridor_rx, has_natural_light_fn):
    """Return (placement_room, controlled_room, placed_outside).

    - controlled_room: the room whose lighting this switch is assumed to control
    - placement_room: the room where the switch should be placed (inside or outside)
    - placed_outside: True if switch is outside the controlled_room
    """
    if fr is None and tr is None:
        return None, None, False

    fr_wet = _match_any(wet_rx, _room_name(fr))
    tr_wet = _match_any(wet_rx, _room_name(tr))
    fr_corr = _match_any(corridor_rx, _room_name(fr))
    tr_corr = _match_any(corridor_rx, _room_name(tr))

    # 1) Wet rooms: always place outside; prefer corridor/hallway when possible.
    if fr_wet and (not tr_wet):
        controlled = fr
        placement = tr
        return placement, controlled, True
    if tr_wet and (not fr_wet):
        controlled = tr
        placement = fr
        return placement, controlled, True
    if fr_wet and tr_wet:
        controlled = fr or tr
        # Place on corridor side if one side looks like corridor.
        if fr_corr and (not tr_corr) and tr is not None:
            return tr, controlled, True
        if tr_corr and (not fr_corr) and fr is not None:
            return fr, controlled, True
        return (fr or tr), controlled, True

    # 2) Choose controlled room (prefer non-corridor).
    controlled = None
    other = None

    if fr_corr and (not tr_corr) and tr is not None:
        controlled = tr
        other = fr
    elif tr_corr and (not fr_corr) and fr is not None:
        controlled = fr
        other = tr
    else:
        # If both are non-corridor and exactly one has natural light: treat the dark room as controlled.
        if (fr is not None) and (tr is not None) and (not fr_corr) and (not tr_corr):
            try:
                fr_light = bool(has_natural_light_fn(fr))
            except Exception:
                fr_light = True
            try:
                tr_light = bool(has_natural_light_fn(tr))
            except Exception:
                tr_light = True

            if (not fr_light) and tr_light:
                controlled = fr
                other = tr
            elif (not tr_light) and fr_light:
                controlled = tr
                other = fr

        # Fallback: current heuristic (prefer non-corridor, then larger area, then ToRoom).
        if controlled is None:
            s_fr = _score_room_for_inside(fr, corridor_rx)
            s_tr = _score_room_for_inside(tr, corridor_rx)
            if s_fr == s_tr:
                a_fr = _room_area(fr)
                a_tr = _room_area(tr)
                if (a_fr is not None) and (a_tr is not None):
                    try:
                        if abs(float(a_fr) - float(a_tr)) > 1e-6:
                            if float(a_fr) > float(a_tr):
                                controlled = fr
                                other = tr
                            else:
                                controlled = tr
                                other = fr
                    except Exception:
                        pass
                if controlled is None:
                    controlled = tr or fr
                    other = fr if controlled == tr else tr
            else:
                controlled = fr if s_fr > s_tr else tr
                other = tr if controlled == fr else fr

    if controlled is None:
        return None, None, False

    # 3) Decide placement: inside for rooms with natural light; outside for rooms without.
    try:
        has_light = bool(has_natural_light_fn(controlled))
    except Exception:
        has_light = True

    if has_light:
        return controlled, controlled, False

    # outside
    if other is not None:
        return other, controlled, True
    return controlled, controlled, True


def _make_linked_door_key(link_inst, door):
    """Return stable key for a linked door within a specific link instance."""
    if link_inst is None or door is None:
        return None
    try:
        li_uid = str(getattr(link_inst, 'UniqueId', '') or '')
    except Exception:
        li_uid = ''
    try:
        d_uid = str(getattr(door, 'UniqueId', '') or '')
    except Exception:
        d_uid = ''

    if li_uid and d_uid:
        return u'{0}::{1}'.format(li_uid, d_uid)

    # Fallback: numeric ids (less stable across file changes but better than nothing)
    try:
        li_id = int(link_inst.Id.IntegerValue)
    except Exception:
        li_id = None
    try:
        d_id = int(door.Id.IntegerValue)
    except Exception:
        d_id = None
    if li_id is not None and d_id is not None:
        return u'{0}::{1}'.format(li_id, d_id)
    return None


def _comment_with_door_key(comment_prefix, door_key):
    if not comment_prefix:
        return comment_prefix
    if not door_key:
        return comment_prefix
    return u'{0}|door={1}'.format(comment_prefix, door_key)


def _collect_existing_switch_door_keys(host_doc, comment_prefix):
    """Return a set of door keys already present in Comments."""
    keys = set()
    if host_doc is None or not comment_prefix:
        return keys

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, comment_prefix, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, comment_prefix)
        pfilter = DB.ElementParameterFilter(rule)

        col = (DB.FilteredElementCollector(host_doc)
               .OfClass(DB.FamilyInstance)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))

        for e in col:
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                txt = p.AsString() if p else None
                txt = txt or ''
            except Exception:
                txt = ''
            if not txt:
                continue
            t = _norm(txt)
            i = t.find('door=')
            if i < 0:
                continue
            try:
                k = txt[i + 5:]
                # trim trailing separators/spaces
                k = k.split('|')[0].strip()
                if k:
                    keys.add(k)
            except Exception:
                continue
    except Exception:
        return keys

    return keys


def _collect_existing_switch_instances_by_door_key(host_doc, comment_prefix):
    """Return dict door_key -> list[FamilyInstance] for already placed switches."""
    mp = {}
    if host_doc is None or not comment_prefix:
        return mp

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, comment_prefix, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, comment_prefix)
        pfilter = DB.ElementParameterFilter(rule)

        col = (DB.FilteredElementCollector(host_doc)
               .OfClass(DB.FamilyInstance)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))

        for e in col:
            txt = ''
            try:
                p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                txt = p.AsString() if p else ''
                txt = txt or ''
            except Exception:
                txt = ''
            if not txt:
                continue
            lo = ''
            try:
                lo = (txt or '').lower()
            except Exception:
                lo = ''
            i = lo.find('door=')
            if i < 0:
                continue
            try:
                k = (txt[i + 5:]).split('|')[0].strip()
            except Exception:
                k = ''
            if not k:
                continue
            mp.setdefault(k, []).append(e)
    except Exception:
        return mp

    return mp


def _desired_facing_host_from_link_wall_face(door_link, link_inst, pt_link, total_transform):
    """Best-effort facing direction so that the button points to the room side.

    Prefers vector (wall face -> point inside room) projected onto XY and transformed to host.
    """
    if door_link is None or link_inst is None or pt_link is None:
        return None

    # Face-based direction (most reliable)
    try:
        wall_link = getattr(door_link, 'Host', None)
    except Exception:
        wall_link = None
    if wall_link is not None and isinstance(wall_link, DB.Wall):
        try:
            _, proj_pt_link = _get_linked_wall_face_ref_and_point(wall_link, link_inst, pt_link)
        except Exception:
            proj_pt_link = None
        if proj_pt_link is not None:
            try:
                v = DB.XYZ(float(pt_link.X) - float(proj_pt_link.X), float(pt_link.Y) - float(proj_pt_link.Y), 0.0)
                v = _xy_unit(v)
                if v is not None:
                    try:
                        return total_transform.OfVector(v) if total_transform is not None else v
                    except Exception:
                        return v
            except Exception:
                pass

    # Fallback: door facing
    try:
        n0 = _try_get_door_facing_xy(door_link)
        n0 = _xy_unit(n0)
        if n0 is not None:
            try:
                return total_transform.OfVector(n0) if total_transform is not None else n0
            except Exception:
                return n0
    except Exception:
        pass

    return None


def _probe_rooms_by_facing(door, link_doc, center_pt, facing_xy, phase_hint=None):
    """Fallback when FromRoom/ToRoom are missing: probe rooms on both sides of door."""
    if door is None or link_doc is None or center_pt is None or facing_xy is None:
        return None, None, None

    n = _xy_unit(facing_xy)
    if n is None:
        return None, None, None

    phases = _get_preferred_phases(door, link_doc, phase_hint=phase_hint)
    if not phases:
        phases = [None]

    th = _try_get_wall_thickness_ft(door)
    eps = mm_to_ft(500) or 0.0
    try:
        if th is not None:
            eps = max(float(eps), (float(th) * 0.5) + (mm_to_ft(200) or 0.0))
    except Exception:
        pass

    try:
        zprobe = float(center_pt.Z) + (mm_to_ft(1000) or 0.0)
        base = DB.XYZ(float(center_pt.X), float(center_pt.Y), float(zprobe))
    except Exception:
        return None, None, None

    for ph in phases:
        for e in (eps, eps * 1.5, eps * 2.0):
            if e <= 1e-9:
                continue
            try:
                p_plus = base + (n * float(e))
                p_minus = base + (n * float(-e))
            except Exception:
                continue

            r_plus = _try_get_room_at_point(link_doc, p_plus, phase=ph)
            r_minus = _try_get_room_at_point(link_doc, p_minus, phase=ph)
            if r_plus is not None or r_minus is not None:
                return r_minus, r_plus, ph

    return None, None, None


def _is_two_gang(room, two_gang_rx):
    return _match_any(two_gang_rx, _room_name(room))


def _room_level_name(room):
    if room is None:
        return u''
    # Prefer Room.Level if available
    try:
        lvl = getattr(room, 'Level', None)
        if lvl is not None and hasattr(lvl, 'Name'):
            return lvl.Name or u''
    except Exception:
        pass

    # Fallback: resolve Level by LevelId
    try:
        lid = getattr(room, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId:
            doc_ = getattr(room, 'Document', None)
            if doc_ is not None:
                lvl = doc_.GetElement(lid)
                if lvl is not None and hasattr(lvl, 'Name'):
                    return lvl.Name or u''
    except Exception:
        pass

    return u''


def _is_technical_room_or_level(room, room_rx, level_rx):
    """Detect technical rooms/floors by room name or level name patterns."""
    try:
        if _match_any(room_rx, _room_name(room)):
            return True
    except Exception:
        pass

    try:
        lvl_name = _room_level_name(room)
        if lvl_name and _match_any(level_rx, lvl_name):
            return True
    except Exception:
        pass

    return False


def _calc_switch_point_link(door, link_doc, target_room, height_ft, jamb_offset_ft, min_axis_ft, phase_hint=None):
    """Return XYZ point in LINK coords for switch placement, or None."""
    c = _door_center_point_link(door)
    if c is None or link_doc is None or target_room is None:
        return None

    def _is_point_in_target_room(pt):
        if pt is None:
            return False
        try:
            return bool(target_room.IsPointInRoom(pt))
        except Exception:
            # Fallback for cases when IsPointInRoom throws (phase/room issues)
            try:
                rr = _try_get_room_at_point(link_doc, pt, phase=phase_hint)
                return _room_id_int(rr) == _room_id_int(target_room)
            except Exception:
                return False

    base_z = _door_level_elevation_ft(door, link_doc, c)

    facing = _try_get_door_facing_xy(door)
    if facing is None:
        return None

    n = _xy_unit(facing)
    if n is None:
        return None

    h = _try_get_door_hand_xy(door)
    if h is None:
        h = _xy_perp(n)
    h = _xy_unit(h)
    if h is None:
        return None

    w = _get_door_width_ft(door)
    if w is None:
        w = mm_to_ft(900) or 0.0
    try:
        w = max(float(w), mm_to_ft(300) or 0.0)
    except Exception:
        w = mm_to_ft(900) or 0.0

    clear_ft = 0.0
    try:
        clear_ft = max(float(jamb_offset_ft or 0.0), float(min_axis_ft or 0.0))
    except Exception:
        clear_ft = float(jamb_offset_ft or 0.0)

    # Some doors are placed very close to wall ends/corners; allow reducing clearance to still place a switch.
    try:
        clear_candidates = [float(clear_ft), float(jamb_offset_ft or 0.0), float(min_axis_ft or 0.0), 0.0]
    except Exception:
        clear_candidates = [float(clear_ft), 0.0]
    # Deduplicate while keeping order
    _cc = []
    for x in clear_candidates:
        try:
            xf = float(x)
        except Exception:
            continue
        if xf < 0.0:
            continue
        if all(abs(xf - y) > 1e-6 for y in _cc):
            _cc.append(xf)
    clear_candidates = _cc

    base_half = float(w) * 0.5
    along_candidates = [base_half + float(cc) for cc in clear_candidates]

    th = _try_get_wall_thickness_ft(door)
    cross = mm_to_ft(100) or 0.0
    try:
        if th is not None and float(th) > 1e-6:
            cross = (float(th) * 0.5) + (mm_to_ft(30) or 0.0)
    except Exception:
        pass

    # Determine preferred side direction using room probe
    side_pref = _dir_to_target_room_by_probe(door, link_doc, target_room, c, n, phase_hint=phase_hint)
    # Always allow a fallback to the opposite side; accept only if point ends up inside target_room.
    if side_pref is not None:
        side_candidates = [side_pref, DB.XYZ(-side_pref.X, -side_pref.Y, 0.0)]
    else:
        side_candidates = [n, DB.XYZ(-n.X, -n.Y, 0.0)]

    # Use door location Z for room checks (more robust than level elevation on some models)
    ztest = float(c.Z) + (mm_to_ft(1000) or 0.0)

    for side in side_candidates:
        side = _xy_unit(side)
        if side is None:
            continue

        # Door.HandOrientation points to the HINGE side; place on the same (left/right) side.
        handle_base = DB.XYZ(float(h.X), float(h.Y), 0.0)
        handle = _xy_unit(handle_base)
        if handle is None:
            continue

        for along in along_candidates:
            try:
                x = float(c.X) + float(handle.X) * float(along) + float(side.X) * float(cross)
                y = float(c.Y) + float(handle.Y) * float(along) + float(side.Y) * float(cross)
                p_test = DB.XYZ(float(x), float(y), float(ztest))
                ok = _is_point_in_target_room(p_test)

                if not ok:
                    # push deeper inside the target room if needed (same side only)
                    for extra in (mm_to_ft(100) or 0.0, mm_to_ft(200) or 0.0, mm_to_ft(300) or 0.0):
                        if extra <= 1e-9:
                            continue
                        p2 = DB.XYZ(float(x) + float(side.X) * float(extra), float(y) + float(side.Y) * float(extra), float(ztest))
                        if _is_point_in_target_room(p2):
                            x = p2.X
                            y = p2.Y
                            ok = True
                            break

                if ok:
                    return DB.XYZ(float(x), float(y), float(base_z) + float(height_ft or 0.0))
            except Exception:
                continue

    return None


# --- symbol selection (no UI) ---


def _is_hosted_symbol(symbol):
    if symbol is None:
        return False
    try:
        _, pt_name = placement_engine.get_symbol_placement_type(symbol)
        n = _norm(pt_name)
        return ('host' in n) or ('hosted' in n) or ('wall' in n) or ('face' in n)
    except Exception:
        return False


def _is_supported_switch_placement(symbol):
    if symbol is None:
        return False
    if _is_hosted_symbol(symbol):
        return True
    if ALLOW_POINT_SWITCH:
        try:
            return placement_engine.is_supported_point_placement(symbol)
        except Exception:
            return False
    return False


def _has_hosted_switch_types(doc_):
    if doc_ is None:
        return False
    try:
        scanned = 0
        scan_cap = 8000
        for s in placement_engine.iter_family_symbols(doc_, category_bic=None, limit=None):
            scanned += 1
            if scan_cap and scanned > scan_cap:
                break
            try:
                cat = getattr(s, 'Category', None)
                if not cat or (cat.Name or u'') != u'Выключатели':
                    continue
            except Exception:
                continue
            try:
                if _is_hosted_symbol(s):
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False


def _get_linked_wall_face_ref_and_point(link_wall, link_inst, point_link):
    """Return (link_face_ref, projected_point_link) or (None, None)."""
    if link_wall is None or link_inst is None or point_link is None:
        return None, None
    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Interior))
        except Exception:
            refs += []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Exterior))
        except Exception:
            refs += []

        if not refs:
            return None, None

        best_ref = None
        best_d = None
        best_pt = None

        for r in refs:
            try:
                face = link_wall.GetGeometryObjectFromReference(r)
            except Exception:
                face = None
            if face is None:
                continue
            try:
                ir = face.Project(point_link)
            except Exception:
                ir = None
            if ir is None:
                continue
            try:
                d = float(ir.Distance)
            except Exception:
                d = None
            if d is None:
                continue
            try:
                pt = getattr(ir, 'XYZPoint', None)
                if pt is None:
                    pt = getattr(ir, 'Point', None)
            except Exception:
                pt = None
            if pt is None:
                continue

            if best_d is None or d < best_d:
                best_ref = r
                best_d = d
                best_pt = pt

        if best_ref is None or best_pt is None:
            return None, None

        try:
            link_ref = DB.Reference.CreateLinkReference(link_inst, best_ref)
        except Exception:
            try:
                link_ref = best_ref.CreateLinkReference(link_inst)
            except Exception:
                link_ref = None

        return link_ref, best_pt
    except Exception:
        return None, None


def _try_flip_facing_to_dir(inst, desired_dir_host):
    """Best-effort: ensure instance faces towards desired_dir_host (XY).

    This fixes common cases when face-hosted electrical devices are placed with their
    front pointing into the wall ("button in wall").
    """
    if inst is None or desired_dir_host is None:
        return False

    des = _xy_unit(desired_dir_host)
    if des is None:
        return False

    cur = None
    try:
        cur = getattr(inst, 'FacingOrientation', None)
    except Exception:
        cur = None
    cur = _xy_unit(cur)
    if cur is None:
        return False

    dp = None
    try:
        dp = float(cur.DotProduct(des))
    except Exception:
        dp = None
    if dp is None or dp >= 0.0:
        return False

    # 1) Preferred API
    try:
        inst.FlipFacing()
        return True
    except Exception:
        pass

    # 2) Fallback: toggle built-in facing flipped parameter if available
    try:
        for bip_name in ('INSTANCE_FACING_FLIPPED', 'FACING_FLIPPED'):
            try:
                bip = getattr(DB.BuiltInParameter, bip_name, None)
            except Exception:
                bip = None
            if bip is None:
                continue
            p = None
            try:
                p = inst.get_Parameter(bip)
            except Exception:
                p = None
            if p is None:
                continue
            try:
                if p.IsReadOnly:
                    continue
            except Exception:
                pass
            try:
                if p.StorageType != DB.StorageType.Integer:
                    continue
            except Exception:
                pass
            try:
                v = p.AsInteger()
                v2 = 0 if int(v or 0) else 1
                p.Set(int(v2))
                return True
            except Exception:
                continue
    except Exception:
        pass

    # 3) Last resort: rotate 180° around vertical axis at insertion point
    try:
        lp = None
        try:
            loc = getattr(inst, 'Location', None)
            lp = loc.Point if loc and hasattr(loc, 'Point') else None
        except Exception:
            lp = None
        if lp is None:
            try:
                bb = inst.get_BoundingBox(None)
                if bb:
                    lp = (bb.Min + bb.Max) * 0.5
            except Exception:
                lp = None
        if lp is None:
            return False

        axis = DB.Line.CreateBound(lp, lp + DB.XYZ.BasisZ)
        DB.ElementTransformUtils.RotateElement(inst.Document, inst.Id, axis, float(math.pi))
        return True
    except Exception:
        return False


def _place_switch_instance(
    doc_,
    symbol,
    pt_host,
    door_link,
    link_inst,
    pt_link,
    total_transform,
    view=None,
    allow_point_fallback=False,
    host_walls=None,
    wall_search_ft=0.0,
):
    """Place a switch instance. Supports point-based and hosted (face/wall) families."""
    if doc_ is None or symbol is None or pt_host is None:
        return None

    # Desired facing: button should face the room side (not into the wall).
    desired_facing_host = None
    try:
        c0 = _door_center_point_link(door_link)
        n0 = _try_get_door_facing_xy(door_link)
        if n0 is None:
            try:
                host0 = getattr(door_link, 'Host', None)
                n0 = getattr(host0, 'Orientation', None) if host0 is not None else None
            except Exception:
                n0 = None
        n0 = _xy_unit(n0)

        if c0 is not None and n0 is not None and pt_link is not None:
            v = DB.XYZ(float(pt_link.X) - float(c0.X), float(pt_link.Y) - float(c0.Y), 0.0)
            vv = _xy_unit(v)
            if vv is not None:
                try:
                    if float(vv.DotProduct(n0)) < 0.0:
                        n0 = DB.XYZ(-float(n0.X), -float(n0.Y), 0.0)
                except Exception:
                    pass

            try:
                desired_facing_host = total_transform.OfVector(n0) if total_transform is not None else n0
            except Exception:
                desired_facing_host = n0
    except Exception:
        desired_facing_host = None

    # Prefer hosting on linked wall face whenever possible (prevents "floating" for wall-mounted devices).
    pt_fallback = pt_host

    try:
        wall_link = getattr(door_link, 'Host', None)
    except Exception:
        wall_link = None
    if wall_link is not None and isinstance(wall_link, DB.Wall):
        link_ref, proj_pt_link = _get_linked_wall_face_ref_and_point(wall_link, link_inst, pt_link)
        if link_ref is not None and proj_pt_link is not None:
            try:
                pt_on_face_host = total_transform.OfPoint(proj_pt_link)
            except Exception:
                pt_on_face_host = pt_host
            pt_fallback = pt_on_face_host

            # Prefer a facing direction derived from the actual hosting face: (face -> room point).
            # This is more reliable than Door.FacingOrientation for many families.
            try:
                if pt_link is not None and proj_pt_link is not None:
                    vv = DB.XYZ(float(pt_link.X) - float(proj_pt_link.X), float(pt_link.Y) - float(proj_pt_link.Y), 0.0)
                    vv = _xy_unit(vv)
                    if vv is not None:
                        try:
                            desired_facing_host = total_transform.OfVector(vv) if total_transform is not None else vv
                        except Exception:
                            desired_facing_host = vv
            except Exception:
                pass

            # referenceDirection must lie IN the face plane; use wall tangent (XY) not wall normal.
            dir_link = None
            try:
                dir_link = _xy_perp(_try_get_door_facing_xy(door_link))
            except Exception:
                dir_link = None
            if dir_link is None:
                try:
                    dir_link = _xy_perp(getattr(wall_link, 'Orientation', None))
                except Exception:
                    dir_link = None
            if dir_link is None:
                dir_link = DB.XYZ.BasisX
            try:
                dir_host = total_transform.OfVector(dir_link) if total_transform is not None else dir_link
            except Exception:
                dir_host = DB.XYZ.BasisX

            try:
                ensure_symbol_active(doc_, symbol)
            except Exception:
                pass

            # Try hosted placement first
            try:
                inst = doc_.Create.NewFamilyInstance(link_ref, pt_on_face_host, dir_host, symbol)
            except Exception:
                inst = None

            if inst is None:
                try:
                    inst = doc_.Create.NewFamilyInstance(link_ref, pt_on_face_host, symbol)
                except Exception:
                    inst = None

            if inst is not None:
                try:
                    _try_flip_facing_to_dir(inst, desired_facing_host)
                except Exception:
                    pass
                return inst

    # Host wall fallback (when link face hosting is not available)
    try:
        host_wall = _nearest_host_wall(host_walls, pt_host, wall_search_ft)
    except Exception:
        host_wall = None
    if host_wall is not None:
        host_ref, proj_pt_host = _get_host_wall_face_ref_and_point(host_wall, pt_host)
        if host_ref is not None and proj_pt_host is not None:
            if _is_hosted_symbol(symbol):
                dir_host = _wall_tangent_xy(host_wall) or DB.XYZ.BasisX
                try:
                    ensure_symbol_active(doc_, symbol)
                except Exception:
                    pass
                inst = None
                try:
                    inst = doc_.Create.NewFamilyInstance(host_ref, proj_pt_host, dir_host, symbol)
                except Exception:
                    inst = None
                if inst is None:
                    try:
                        inst = doc_.Create.NewFamilyInstance(host_ref, proj_pt_host, symbol)
                    except Exception:
                        inst = None
                if inst is not None:
                    try:
                        _try_flip_facing_to_dir(inst, desired_facing_host)
                    except Exception:
                        pass
                    return inst
            pt_fallback = proj_pt_host

    if not allow_point_fallback:
        return None

    # Fallback: point-based placement at the projected wall face point (so it doesn't float in the room)
    try:
        inst = placement_engine.place_point_family_instance(doc_, symbol, pt_fallback, view=view)
    except Exception:
        inst = None

    if inst is not None:
        try:
            _try_flip_facing_to_dir(inst, desired_facing_host)
        except Exception:
            pass

    return inst


SWITCH_STRONG_KEYWORDS = [u'выключ', u'switch']
SWITCH_NEGATIVE_KEYWORDS = [
    u'розет', u'socket', u'панел', u'щит', u'шк', u'panel', u'shk',
    u'свет', u'light', u'lum', u'светиль',
    u'датчик', u'sensor', u'detector', u'motion', u'pir', u'presence',
    # avoid picking special switch variants by default
    u'проход', u'прк', u'перекрест', u'пкс', u'димер', u'dimmer'
]
SWITCH_1G_KEYWORDS = [u'1к', u'1-к', u'1 клав', u'одноклав', u'1gang', u'1-gang', u'1g', u'single']
SWITCH_2G_KEYWORDS = [u'2к', u'2-к', u'2 клав', u'двухклав', u'2gang', u'2-gang', u'2g', u'double']

# Common RU abbreviations used in type names
try:
    SWITCH_1G_KEYWORDS += [u'1кл']
    SWITCH_2G_KEYWORDS += [u'2кл']
except Exception:
    pass


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


def _load_symbol_from_saved_id(doc_, cfg, key):
    if doc_ is None or cfg is None:
        return None
    try:
        val = getattr(cfg, key, None)
        if val is None:
            return None
        eid = DB.ElementId(int(val))
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


def _score_switch_symbol(symbol, want_two_gang=False, prefer_fullname=None):
    if symbol is None:
        return None

    try:
        if not _is_supported_switch_placement(symbol):
            return None
    except Exception:
        return None

    try:
        label = placement_engine.format_family_type(symbol)
    except Exception:
        label = u''
    nlabel = _norm(label)

    s = 0

    # exact-ish match boost
    try:
        if prefer_fullname and _norm(prefer_fullname) == nlabel:
            s += 500
    except Exception:
        pass

    strong_hit = False
    for kw in SWITCH_STRONG_KEYWORDS:
        if _norm(kw) and _norm(kw) in nlabel:
            s += 80
            strong_hit = True

    # Gang hints (used both for scoring and as a safety filter)
    hit1 = False
    hit2 = False
    for kw in SWITCH_1G_KEYWORDS:
        if _norm(kw) and _norm(kw) in nlabel:
            hit1 = True
            break
    for kw in SWITCH_2G_KEYWORDS:
        if _norm(kw) and _norm(kw) in nlabel:
            hit2 = True
            break

    # Safety: avoid auto-picking unrelated electrical devices.
    # Require either an explicit gang marker or a strong "switch" keyword (or exact preferred match).
    try:
        prefer_exact = bool(prefer_fullname and _norm(prefer_fullname) == nlabel)
    except Exception:
        prefer_exact = False
    if (not prefer_exact) and (not strong_hit) and (not hit1) and (not hit2):
        return None

    for kw in SWITCH_NEGATIVE_KEYWORDS:
        if _norm(kw) and _norm(kw) in nlabel:
            s -= 120

    if want_two_gang:
        # Prefer explicit 2-gang markers
        if hit2:
            s += 60
        if hit1:
            s -= 30
    else:
        # Prefer explicit 1-gang markers
        if hit1:
            s += 60
        if hit2:
            s -= 30

    if 'eom' in nlabel:
        s += 10

    return s


def _find_symbol_by_fullname(doc_, fullname):
    if not fullname:
        return None

    # Try typical categories first; then fallback to any.
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        try:
            sym = placement_engine.find_family_symbol(doc_, fullname, category_bic=bic, limit=5000)
        except Exception:
            sym = None
        if sym is None:
            continue
        try:
            if _is_supported_switch_placement(sym):
                return sym
        except Exception:
            continue

    # fuzzy fallback (handles Cyrillic/Latin look-alikes)
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        try:
            sym = _find_symbol_by_fullname_fuzzy(doc_, fullname, category_bic=bic, scan_cap=8000)
        except Exception:
            sym = None

        if sym is not None:
            return sym

    return None


def _find_symbol_by_fullname_fuzzy(doc_, fullname, category_bic=None, scan_cap=8000):
    """Fuzzy fallback: match by type name with simple normalization.

    This helps when users copy type names that contain Cyrillic/Latin look-alikes.
    """
    if not fullname:
        return None

    # Parse "Family : Type"; if no colon, treat fullname as type name.
    try:
        parts = [p.strip() for p in (fullname or u'').split(':')]
    except Exception:
        parts = [fullname]

    if len(parts) <= 1:
        fam_name = None
        tname = fullname
    else:
        fam_name = parts[0]
        tname = u':'.join(parts[1:]).strip()

    key_type = _norm_type_key(tname)
    key_fam = _norm_type_key(fam_name) if fam_name else None
    if not key_type:
        return None

    scanned = 0
    for s in placement_engine.iter_family_symbols(doc_, category_bic=category_bic, limit=None):
        scanned += 1
        if scan_cap and scanned > int(scan_cap):
            break
        try:
            if not _is_supported_switch_placement(s):
                continue
        except Exception:
            continue

        try:
            if _norm_type_key(getattr(s, 'Name', '')) != key_type:
                continue
        except Exception:
            continue

        if key_fam:
            try:
                s_fam = None
                try:
                    s_fam = getattr(s, 'FamilyName', None)
                except Exception:
                    s_fam = None
                if not s_fam:
                    try:
                        s_fam = getattr(getattr(s, 'Family', None), 'Name', None)
                    except Exception:
                        s_fam = None
                if _norm_type_key(s_fam) != key_fam:
                    continue
            except Exception:
                continue

        return s

    return None


def _auto_pick_switch_symbol(doc_, want_two_gang=False, prefer_fullname=None, require_hosted=False):
    best = None
    best_score = None
    top = []

    # Scan a bounded number of symbols to avoid UI freeze.
    # Prefer electrical fixture categories first; then fallback to any.
    scan_cap = 8000
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=bic, limit=None):
            scanned += 1
            if scanned > scan_cap:
                break

            if require_hosted:
                try:
                    if not _is_hosted_symbol(s):
                        continue
                except Exception:
                    continue

            try:
                sc = _score_switch_symbol(s, want_two_gang=want_two_gang, prefer_fullname=prefer_fullname)
            except Exception:
                sc = None
            if sc is None:
                continue

            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''

            top.append((int(sc), lbl, s))
            if best is None or sc > best_score:
                best = s
                best_score = sc

    top = sorted(top, key=lambda x: (-x[0], _norm(x[1])))
    top10 = [u'{0}  (score={1})'.format(x[1], x[0]) for x in top[:10]]
    # Safety net: don't pick a random device when switch types are missing.
    try:
        if best_score is None or int(best_score) < 40:
            return None, None, top10
    except Exception:
        if best is None:
            return None, None, top10

    return best, (placement_engine.format_family_type(best) if best else None), top10


def _as_name_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            try:
                s = (x or u'').strip()
            except Exception:
                s = u''
            if s:
                out.append(s)
        return out
    try:
        s = (v or u'').strip()
    except Exception:
        s = u''
    return [s] if s else []


def _format_prefer_names(prefer_names):
    try:
        items = [u'- {0}'.format(x) for x in (prefer_names or []) if x]
    except Exception:
        items = []
    return u'\n'.join(items)


def _extract_type_name(fullname):
    try:
        return (fullname or u'').split(':')[-1].strip()
    except Exception:
        return fullname or u''


def _switch_name_similarity(pref_key, cand_key):
    if not pref_key or not cand_key:
        return 0.0
    try:
        return difflib.SequenceMatcher(None, pref_key, cand_key).ratio()
    except Exception:
        return 0.0


def _pick_similar_switch_symbol(doc_, prefer_fullname, want_two_gang=False, require_hosted=False):
    if not prefer_fullname:
        return None, None, None

    pref_key = _norm_type_key(_extract_type_name(prefer_fullname))
    if not pref_key:
        return None, None, None

    best = None
    best_lbl = None
    best_ratio = 0.0

    scan_cap = 8000
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_LightingDevices, None):
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=bic, limit=None):
            scanned += 1
            if scanned > scan_cap:
                break

            if require_hosted:
                try:
                    if not _is_hosted_symbol(s):
                        continue
                except Exception:
                    continue

            try:
                if _score_switch_symbol(s, want_two_gang=want_two_gang, prefer_fullname=None) is None:
                    continue
            except Exception:
                continue

            try:
                lbl = placement_engine.format_family_type(s)
            except Exception:
                lbl = u''

            cand_key = _norm_type_key(_extract_type_name(lbl))
            ratio = _switch_name_similarity(pref_key, cand_key)
            if ratio > best_ratio:
                best = s
                best_lbl = lbl
                best_ratio = ratio

    return best, best_lbl, best_ratio


def _pick_switch_symbol(
    doc_,
    cfg,
    fullname,
    want_two_gang,
    cache_prefix,
    allow_auto_pick_fallback=True,
    require_hosted=False
):
    """Pick switch symbol from configured name(s) -> cache -> auto.

    `fullname` may be a string or a list of alias strings.
    If explicit names are provided and none match, auto-pick can be used as a fallback.
    """
    prefer_names = _as_name_list(fullname)
    prefer_fullname = prefer_names[0] if prefer_names else None

    # 1) Configured fullname(s) take precedence over cache to honor updated selections.
    if prefer_names:
        for nm in prefer_names:
            sym_cfg = _find_symbol_by_fullname(doc_, nm)
            if sym_cfg is not None:
                try:
                    if _is_supported_switch_placement(sym_cfg):
                        if require_hosted and (not _is_hosted_symbol(sym_cfg)):
                            continue
                        return sym_cfg, placement_engine.format_family_type(sym_cfg), []
                except Exception:
                    return sym_cfg, None, []

    # 2) Cache (only accept if it matches requested fullname when provided)
    sym = None
    try:
        sym = _load_symbol_from_saved_unique_id(doc_, cfg, cache_prefix + '_uid')
    except Exception:
        sym = None
    if sym is None:
        try:
            sym = _load_symbol_from_saved_id(doc_, cfg, cache_prefix + '_id')
        except Exception:
            sym = None

    if sym is not None:
        try:
            if _is_supported_switch_placement(sym):
                if require_hosted and (not _is_hosted_symbol(sym)):
                    sym = None
                else:
                    lbl = placement_engine.format_family_type(sym)
                    if not prefer_names:
                        return sym, lbl, []

                    # Accept cached symbol if it matches ANY preferred name.
                    for pn in prefer_names:
                        try:
                            prefer_has_family = (':' in pn)
                        except Exception:
                            prefer_has_family = False
                        if prefer_has_family:
                            if _norm_type_key(lbl) == _norm_type_key(pn):
                                return sym, lbl, []
                        else:
                            try:
                                lbl_type = lbl.split(':')[-1].strip()
                            except Exception:
                                lbl_type = lbl
                            if _norm_type_key(lbl_type) == _norm_type_key(pn):
                                return sym, lbl, []
        except Exception:
            pass
        sym = None

    if prefer_names:
        _sym_auto, _lbl_auto, top10 = _auto_pick_switch_symbol(
            doc_, want_two_gang=want_two_gang, prefer_fullname=prefer_fullname, require_hosted=require_hosted
        )
        if allow_auto_pick_fallback and _sym_auto is not None:
            return _sym_auto, _lbl_auto, top10
        if allow_auto_pick_fallback:
            try:
                _sym_sim, _lbl_sim, _sim_ratio = _pick_similar_switch_symbol(
                    doc_, prefer_fullname, want_two_gang=want_two_gang, require_hosted=require_hosted
                )
            except Exception:
                _sym_sim, _lbl_sim, _sim_ratio = None, None, None
            try:
                if _sym_sim is not None and (_sim_ratio is not None) and float(_sim_ratio) >= 0.72:
                    output.print_md(
                        u'**Подставлен похожий тип выключателя:** `{0}` (вместо `{1}`, похожесть {2:.2f})'.format(
                            _lbl_sim or placement_engine.format_family_type(_sym_sim),
                            prefer_fullname,
                            float(_sim_ratio)
                        )
                    )
                    return _sym_sim, _lbl_sim, top10
            except Exception:
                pass
        return None, None, top10

    return _auto_pick_switch_symbol(doc_, want_two_gang=want_two_gang, prefer_fullname=None, require_hosted=require_hosted)


def _find_point_based_symbol(doc_, fullname):
    sym = _find_symbol_by_fullname(doc_, fullname)
    if sym is None:
        return None
    try:
        if placement_engine.is_supported_point_placement(sym) and (not _is_hosted_symbol(sym)):
            return sym
    except Exception:
        return None
    return None


# --- dedupe index ---


class _XYZIndex(object):
    def __init__(self, cell_ft):
        try:
            self._c = float(cell_ft or 1.0)
        except Exception:
            self._c = 1.0
        if self._c <= 1e-6:
            self._c = 1.0
        self._grid = {}

    def _key(self, x, y):
        try:
            return (int(math.floor(float(x) / self._c)), int(math.floor(float(y) / self._c)))
        except Exception:
            return (0, 0)

    def add(self, x, y, z):
        k = self._key(x, y)
        b = self._grid.get(k)
        if b is None:
            b = []
            self._grid[k] = b
        b.append((float(x), float(y), float(z)))

    def has_near(self, x, y, z, r_ft):
        try:
            r = float(r_ft or 0.0)
        except Exception:
            r = 0.0
        if r <= 1e-9:
            return False

        try:
            x0 = float(x)
            y0 = float(y)
            z0 = float(z)
        except Exception:
            return False

        r2 = r * r
        k = self._key(x0, y0)
        # Check neighbor buckets
        for ix in (k[0] - 1, k[0], k[0] + 1):
            for iy in (k[1] - 1, k[1], k[1] + 1):
                b = self._grid.get((ix, iy))
                if not b:
                    continue
                for (xx, yy, zz) in b:
                    dx = xx - x0
                    dy = yy - y0
                    dz = zz - z0
                    if (dx * dx + dy * dy + dz * dz) <= r2:
                        return True
        return False


def _collect_existing_tagged_points(host_doc, tag_value):
    pts = []
    if not tag_value:
        return pts

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag_value, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag_value)
        pfilter = DB.ElementParameterFilter(rule)

        col = (DB.FilteredElementCollector(host_doc)
               .OfClass(DB.FamilyInstance)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))

        for e in col:
            try:
                loc = getattr(e, 'Location', None)
                pt = loc.Point if loc and hasattr(loc, 'Point') else None
                if pt is not None:
                    pts.append(pt)
            except Exception:
                continue
    except Exception:
        return pts

    return pts


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


def _get_or_create_debug_3d_view(doc, name, aliases=None):
    try:
        aliases = list(aliases or [])

        for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
            try:
                if not v or v.IsTemplate:
                    continue
                if v.Name == name:
                    return v
            except Exception:
                continue

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


def _bbox_from_element_ids(doc, ids, pad_ft=60.0, limit=500):
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


# NOTE: view-opening helpers are defined near the end of the file (close to their usage)


def _open_floorplan_at_switch_height(doc, uidoc, created_ids, height_ft):
    """Open a floor plan and adjust view range so the cut plane is near switch height."""
    if doc is None or uidoc is None or not created_ids:
        return False

    inst = None
    try:
        inst = doc.GetElement(created_ids[0])
    except Exception:
        inst = None
    if inst is None:
        return False

    lvl = None
    try:
        lid = getattr(inst, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId:
            lvl = doc.GetElement(lid)
    except Exception:
        lvl = None

    plan = None
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)
        for v in col:
            try:
                if (not v) or v.IsTemplate:
                    continue
                if v.ViewType != DB.ViewType.FloorPlan:
                    continue
                if lvl is not None and hasattr(v, 'GenLevel') and v.GenLevel is not None:
                    if int(v.GenLevel.Id.IntegerValue) != int(lvl.Id.IntegerValue):
                        continue
                plan = v
                break
            except Exception:
                continue
    except Exception:
        plan = None

    if plan is None:
        try:
            col = DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan)
            for v in col:
                try:
                    if (not v) or v.IsTemplate:
                        continue
                    if v.ViewType == DB.ViewType.FloorPlan:
                        plan = v
                        break
                except Exception:
                    continue
        except Exception:
            plan = None

    if plan is None:
        return False

    try:
        uidoc.RequestViewChange(plan)
    except Exception:
        return False

    vr = None
    try:
        vr = plan.GetViewRange()
    except Exception:
        vr = None
    if vr is not None and lvl is not None:
        with tx('ЭОМ: Установить диапазон вида (выключатели)', doc=doc, swallow_warnings=True):
            try:
                vr.SetLevelId(DB.PlanViewPlane.CutPlane, lvl.Id)
                vr.SetOffset(DB.PlanViewPlane.CutPlane, float(height_ft or 0.0))
            except Exception:
                pass
            try:
                vr.SetLevelId(DB.PlanViewPlane.TopClipPlane, lvl.Id)
                vr.SetOffset(DB.PlanViewPlane.TopClipPlane, float(mm_to_ft(2500) or 8.0))
            except Exception:
                pass
            try:
                vr.SetLevelId(DB.PlanViewPlane.BottomClipPlane, lvl.Id)
                vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, float(mm_to_ft(-500) or -2.0))
            except Exception:
                pass
            try:
                plan.SetViewRange(vr)
            except Exception:
                pass

    try:
        uidoc.ShowElements(created_ids[0])
    except Exception:
        pass
    return True


def main():
    output.print_md('# Размещение выключателей у дверей')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SWITCH'.format(comment_tag)

    height_mm = rules.get('switch_height_mm', 900)
    jamb_mm = rules.get('switch_offset_from_jamb_mm', 150)
    min_axis_mm = rules.get('switch_min_dist_to_door_axis_mm', 120)

    batch_size = int(rules.get('batch_size', 25) or 25)

    # For 1:1 "door -> switch" workflows we should not silently cap processing.
    # Use tool-specific limits; defaults are unlimited.
    scan_limit_doors = int(rules.get('switch_scan_limit_doors', 0) or 0)
    max_place = int(rules.get('switch_max_place_count', 0) or 0)
    auto_link_scan_limit_doors = int(rules.get('switch_auto_link_scan_limit_doors', 200) or 200)
    level_z_tol_mm = rules.get('switch_level_z_tol_mm', 1500)

    wet_rx = _compile_patterns(rules.get('switch_wet_room_name_patterns', []) or [])
    corridor_rx = _compile_patterns(rules.get('switch_corridor_room_name_patterns', []) or [])
    two_gang_rx = _compile_patterns(rules.get('switch_two_gang_room_name_patterns', []) or [])
    tech_room_rx = _compile_patterns(rules.get('switch_technical_room_name_patterns', []) or [])
    tech_level_rx = _compile_patterns(rules.get('switch_technical_level_name_patterns', []) or [])
    allow_auto_pick_fallback = bool(rules.get('switch_allow_auto_pick_fallback', True))
    allow_point_fallback = bool(rules.get('switch_allow_point_fallback', False))
    require_hosted = not allow_point_fallback

    if require_hosted:
        try:
            if not _has_hosted_switch_types(doc):
                output.print_md(u'**Предупреждение:** в шаблоне нет hosted-типов выключателей. Включаю point fallback для размещения.')
                allow_point_fallback = True
                require_hosted = False
        except Exception:
            pass
    wall_search_mm = rules.get('switch_host_wall_search_mm', None)
    if wall_search_mm is None:
        wall_search_mm = rules.get('host_wall_search_mm', 300)
    host_has_walls = _host_has_walls(doc)

    height_ft = mm_to_ft(height_mm) or 0.0
    jamb_ft = mm_to_ft(jamb_mm) or 0.0
    min_axis_ft = mm_to_ft(min_axis_mm) or 0.0

    fams = (rules.get('family_type_names', {}) or {})
    fam_1g = fams.get('switch_1g') or fams.get('switch') or ''
    fam_2g = fams.get('switch_2g') or ''
    fam_ip44 = fams.get('switch_1g_ip44') or fams.get('switch_ip44_1g') or fams.get('switch_ip44') or ''

    link_inst = _auto_pick_link_instance_ru(doc, scan_limit_doors=auto_link_scan_limit_doors)
    if link_inst is None:
        alert('Не найдены загруженные связи. Загрузите связь АР и повторите.')
        return
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её в «Управление связями» и повторите.')
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи. Убедитесь, что связь загружена.')
        return

    lvl = link_reader.select_level(link_doc, title='Выберите этаж (АР)', allow_none=False)
    if lvl is None:
        output.print_md('**Отменено.**')
        return

    level_id = lvl.Id if lvl is not None else None
    level_z_tol_ft = mm_to_ft(level_z_tol_mm) if level_z_tol_mm is not None else 0.0
    lim = None if scan_limit_doors <= 0 else scan_limit_doors
    doors = []
    skipped_level = 0
    for d in link_reader.iter_doors(link_doc, limit=lim, level_id=None):
        if lvl is not None and (not _door_matches_level(d, lvl, level_z_tol_ft)):
            skipped_level += 1
            continue
        doors.append(d)

    if not doors:
        alert('На выбранном этаже в связи не найдено дверей.')
        return

    if not host_has_walls and require_hosted:
        allow_point_fallback = True
        require_hosted = False

    global ALLOW_POINT_SWITCH
    ALLOW_POINT_SWITCH = bool(allow_point_fallback)

    wall_search_ft = mm_to_ft(wall_search_mm) if wall_search_mm is not None else 0.0
    host_walls = _collect_host_walls(doc) if host_has_walls and (wall_search_ft or allow_point_fallback) else []

    # Natural light (daylight) detection for rooms.
    # Rule: rooms WITH natural light -> switch inside; WITHOUT -> switch outside.
    scan_limit_windows = int(rules.get('switch_scan_limit_windows', 0) or 0)
    natural_light_param_names = rules.get('switch_natural_light_param_names', []) or []
    rooms_with_windows = set()
    win_scanned = 0
    win_bound = 0
    try:
        rooms_with_windows, win_scanned, win_bound = _collect_room_ids_with_windows(
            link_doc,
            limit=scan_limit_windows,
            level_id=level_id
        )
    except Exception:
        rooms_with_windows = set()
        win_scanned = 0
        win_bound = 0

    natural_light_enabled = True

    daylight_cache = {}

    def _has_natural_light(room):
        if not natural_light_enabled:
            return False
        return _room_has_natural_light(room, rooms_with_windows, param_names=natural_light_param_names, cache=daylight_cache, default_when_unknown=False)

    # Resolve symbols (no UI)
    cfg = _get_user_config()
    sym_1g, lbl_1g, top10_1g = _pick_switch_symbol(
        doc,
        cfg,
        fam_1g,
        want_two_gang=False,
        cache_prefix='last_switch_1g_symbol',
        allow_auto_pick_fallback=allow_auto_pick_fallback,
        require_hosted=require_hosted
    )
    sym_2g, lbl_2g, top10_2g = _pick_switch_symbol(
        doc,
        cfg,
        fam_2g,
        want_two_gang=True,
        cache_prefix='last_switch_2g_symbol',
        allow_auto_pick_fallback=allow_auto_pick_fallback,
        require_hosted=require_hosted
    )
    sym_ip44, lbl_ip44, top10_ip44 = _pick_switch_symbol(
        doc,
        cfg,
        fam_ip44,
        want_two_gang=False,
        cache_prefix='last_switch_1g_ip44_symbol',
        allow_auto_pick_fallback=allow_auto_pick_fallback,
        require_hosted=require_hosted
    )

    if sym_1g is None:
        if top10_1g:
            output.print_md('**Не найден тип 1G:** `{0}`'.format(fam_1g or u'<не задано>'))
            output.print_md('Топ кандидатов (поиск по проекту):')
            for s in top10_1g:
                output.print_md('- `{0}`'.format(s))
        prefer_names_1g = _as_name_list(fam_1g)
        msg = u'Не найден тип выключателя (1-клавишный):\n\n{0}'.format(prefer_names_1g[0] if prefer_names_1g else (fam_1g or u'<не задано>'))
        if require_hosted and prefer_names_1g:
            pt_sym = None
            for nm in prefer_names_1g:
                pt_sym = _find_point_based_symbol(doc, nm)
                if pt_sym is not None:
                    break
            if pt_sym is not None:
                try:
                    msg += u'\n\nТип найден, но он точечный (не hosted):\n{0}'.format(placement_engine.format_family_type(pt_sym))
                except Exception:
                    msg += u'\n\nТип найден, но он точечный (не hosted).'
        if prefer_names_1g and len(prefer_names_1g) > 1:
            msg += u'\n\nАлиасы (пробовали):\n{0}'.format(_format_prefer_names(prefer_names_1g))
        alert(msg)
        return

    if fam_2g and sym_2g is None:
        if top10_2g:
            output.print_md('**Не найден тип 2G:** `{0}`'.format(fam_2g))
            output.print_md('Топ кандидатов (поиск по проекту):')
            for s in top10_2g:
                output.print_md('- `{0}`'.format(s))
        prefer_names_2g = _as_name_list(fam_2g)
        msg = u'Не найден тип выключателя (2-клавишный):\n\n{0}'.format(prefer_names_2g[0] if prefer_names_2g else (fam_2g or u'<не задано>'))
        if require_hosted and prefer_names_2g:
            pt_sym = None
            for nm in prefer_names_2g:
                pt_sym = _find_point_based_symbol(doc, nm)
                if pt_sym is not None:
                    break
            if pt_sym is not None:
                try:
                    msg += u'\n\nТип найден, но он точечный (не hosted):\n{0}'.format(placement_engine.format_family_type(pt_sym))
                except Exception:
                    msg += u'\n\nТип найден, но он точечный (не hosted).'
        if prefer_names_2g and len(prefer_names_2g) > 1:
            msg += u'\n\nАлиасы (пробовали):\n{0}'.format(_format_prefer_names(prefer_names_2g))
        alert(msg)
        return
    if sym_2g is None:
        sym_2g = sym_1g
        lbl_2g = lbl_1g

    if fam_ip44 and sym_ip44 is None:
        if top10_ip44:
            output.print_md('**Не найден тип 1G IP44:** `{0}`'.format(fam_ip44))
            output.print_md('Топ кандидатов (поиск по проекту):')
            for s in top10_ip44:
                output.print_md('- `{0}`'.format(s))
        prefer_names_ip44 = _as_name_list(fam_ip44)
        msg = u'Не найден тип выключателя (IP44/техпомещения):\n\n{0}'.format(prefer_names_ip44[0] if prefer_names_ip44 else (fam_ip44 or u'<не задано>'))
        if require_hosted and prefer_names_ip44:
            pt_sym = None
            for nm in prefer_names_ip44:
                pt_sym = _find_point_based_symbol(doc, nm)
                if pt_sym is not None:
                    break
            if pt_sym is not None:
                try:
                    msg += u'\n\nТип найден, но он точечный (не hosted):\n{0}'.format(placement_engine.format_family_type(pt_sym))
                except Exception:
                    msg += u'\n\nТип найден, но он точечный (не hosted).'
        if prefer_names_ip44 and len(prefer_names_ip44) > 1:
            msg += u'\n\nАлиасы (пробовали):\n{0}'.format(_format_prefer_names(prefer_names_ip44))
        alert(msg)
        return
    if sym_ip44 is None:
        sym_ip44 = sym_1g
        lbl_ip44 = lbl_1g

    if (not allow_point_fallback):
        try:
            if not _has_hosted_switch_types(doc):
                msg = u'В шаблоне нет hosted-типов выключателей.\n\n'
                msg += u'Загрузите настенное/face-hosted семейство или включите switch_allow_point_fallback.'
                alert(msg)
                return
        except Exception:
            pass

    if not allow_point_fallback:
        point_based = []
        for s, lbl in ((sym_1g, lbl_1g), (sym_2g, lbl_2g), (sym_ip44, lbl_ip44)):
            if s is None:
                continue
            try:
                if placement_engine.is_supported_point_placement(s):
                    point_based.append(lbl or placement_engine.format_family_type(s))
            except Exception:
                continue
        if point_based:
            msg = u'Найдены точечные типы выключателей, но размещение без стен запрещено.\n\n'
            msg += u'Загрузите настенное/face-hosted семейство и повторите.\n\n'
            msg += u'Типы:\n- {0}'.format(u'\n- '.join(point_based))
            alert(msg)
            return

    # Cache for next run
    try:
        _store_symbol_id(cfg, 'last_switch_1g_symbol_id', sym_1g)
        _store_symbol_unique_id(cfg, 'last_switch_1g_symbol_uid', sym_1g)
        _store_symbol_id(cfg, 'last_switch_2g_symbol_id', sym_2g)
        _store_symbol_unique_id(cfg, 'last_switch_2g_symbol_uid', sym_2g)
        _store_symbol_id(cfg, 'last_switch_1g_ip44_symbol_id', sym_ip44)
        _store_symbol_unique_id(cfg, 'last_switch_1g_ip44_symbol_uid', sym_ip44)
        _save_user_config()
    except Exception:
        pass

    output.print_md('Связь: `{0}`'.format(link_inst.Name))
    if lvl is not None:
        output.print_md('Этаж: `{0}`'.format(lvl.Name))
    output.print_md('Тип 1G: `{0}`'.format(lbl_1g or placement_engine.format_family_type(sym_1g)))
    output.print_md('Тип 2G: `{0}`'.format(lbl_2g or placement_engine.format_family_type(sym_2g)))
    if sym_ip44 is not None:
        output.print_md('Тип 1G (IP44/техпомещения): `{0}`'.format(lbl_ip44 or placement_engine.format_family_type(sym_ip44)))
    output.print_md('Высота установки: **{0} мм**'.format(int(height_mm or 0)))
    output.print_md('Отступ от наличника: **{0} мм**'.format(int(jamb_mm or 0)))
    output.print_md('Дедупликация: **1 дверь = 1 выключатель**')
    output.print_md('Комментарий: `{0}`'.format(comment_value))
    output.print_md('Размещение точкой (fallback): **{0}**'.format(u'вкл' if allow_point_fallback else u'выкл'))
    try:
        output.print_md('Поиск ближайшей стены (fallback): **{0} мм**'.format(int(wall_search_mm or 0)))
    except Exception:
        pass
    if natural_light_enabled:
        try:
            output.print_md('Естественный свет: по окнам в АР (windows_scanned={0}, rooms_with_windows={1})'.format(int(win_scanned), int(len(rooms_with_windows))))
        except Exception:
            pass
    else:
        output.print_md('**Внимание:** не удалось определить естественный свет (нет надёжных данных по окнам/параметрам). Используется поведение по умолчанию: внутри (кроме санузлов).')

    if top10_1g:
        output.print_md('Топ вариантов (1G, автовыбор):')
        for x in top10_1g:
            output.print_md('- `{0}`'.format(x))
    if top10_2g:
        output.print_md('Топ вариантов (2G, автовыбор):')
        for x in top10_2g:
            output.print_md('- `{0}`'.format(x))
    try:
        if top10_ip44 and sym_ip44 is not None and sym_1g is not None and sym_ip44.Id != sym_1g.Id:
            output.print_md('Топ вариантов (1G IP44/тех., автовыбор):')
            for x in top10_ip44:
                output.print_md('- `{0}`'.format(x))
    except Exception:
        pass

    t = link_reader.get_total_transform(link_inst)
    inv_t = None
    try:
        inv_t = t.Inverse
    except Exception:
        inv_t = None

    # Track already-processed doors by key (prevents duplicates while keeping 1:1 per door)
    existing_by_door_key = {}
    existing_door_keys = set()
    try:
        existing_by_door_key = _collect_existing_switch_instances_by_door_key(doc, comment_value)
        existing_door_keys = set(existing_by_door_key.keys())
    except Exception:
        existing_by_door_key = {}
        existing_door_keys = set()

    planned = []
    planned_fix = []
    processed = 0
    created = 0
    created_1g = 0
    created_2g = 0
    updated_existing = 0
    updated_existing_retyped = 0
    updated_existing_flipped = 0
    updated_existing_failed = 0
    created_ids = []
    skipped_no_rooms = 0
    skipped_no_point = 0
    skipped_non_room = 0
    skipped_existing = 0
    skipped_no_place = 0
    skipped_max = 0
    cancelled = False

    pb_max = len(doors)
    with forms.ProgressBar(title='ЭОМ: Размещение выключателей у дверей', cancellable=True, step=1) as pb:
        pb.max_value = max(1, pb_max)
        for d in doors:
            processed += 1
            pb.update_progress(processed, pb_max)
            if pb.cancelled:
                cancelled = True
                break

            if max_place and created >= max_place:
                skipped_max += 1
                break

            door_key = _make_linked_door_key(link_inst, d)
            has_existing = bool(door_key and (door_key in existing_door_keys))

            fr, tr, ph = _get_from_to_rooms_with_phase(d, link_doc)
            if fr is None and tr is None:
                # fallback: probe rooms on both sides when FromRoom/ToRoom are not available
                try:
                    c0 = _door_center_point_link(d)
                    facing0 = _try_get_door_facing_xy(d)
                    fr2, tr2, ph2 = _probe_rooms_by_facing(d, link_doc, c0, facing0, phase_hint=ph)
                    fr = fr2 or fr
                    tr = tr2 or tr
                    ph = ph2 or ph
                except Exception:
                    pass
            # Extra wet-room safety: if both sides look wet (or the other side is missing),
            # re-probe by facing to recover a non-wet placement side.
            try:
                fr_wet = _match_any(wet_rx, _room_name(fr))
                tr_wet = _match_any(wet_rx, _room_name(tr))
            except Exception:
                fr_wet = False
                tr_wet = False
            if (fr_wet and (tr is None or tr_wet)) or (tr_wet and (fr is None or fr_wet)):
                try:
                    c0 = _door_center_point_link(d)
                    facing0 = _try_get_door_facing_xy(d)
                    fr2, tr2, ph2 = _probe_rooms_by_facing(d, link_doc, c0, facing0, phase_hint=ph)
                    if fr2 is not None:
                        fr = fr2
                    if tr2 is not None:
                        tr = tr2
                    ph = ph2 or ph
                except Exception:
                    pass
            if fr is None and tr is None:
                skipped_no_rooms += 1
                continue

            # If probe detects a wet room on either side, prefer probed rooms to enforce outside placement.
            try:
                c0 = _door_center_point_link(d)
                facing0 = _try_get_door_facing_xy(d)
                frp, trp, php = _probe_rooms_by_facing(d, link_doc, c0, facing0, phase_hint=ph)
                if frp is not None or trp is not None:
                    frp_wet = _match_any(wet_rx, _room_name(frp)) if frp is not None else False
                    trp_wet = _match_any(wet_rx, _room_name(trp)) if trp is not None else False
                    if frp_wet or trp_wet:
                        fr = frp or fr
                        tr = trp or tr
                        ph = php or ph
            except Exception:
                pass

            # Skip doors that are fully inside common areas (e.g. подъезд/лестница/коридор)
            try:
                if (fr is not None) and (tr is not None) and _is_corridor_room(fr, corridor_rx) and _is_corridor_room(tr, corridor_rx):
                    skipped_non_room += 1
                    continue
            except Exception:
                pass

            place_room, controlled_room, _is_outside = _choose_rooms_for_switch(fr, tr, wet_rx, corridor_rx, _has_natural_light)
            if place_room is None or controlled_room is None:
                skipped_no_rooms += 1
                continue

            is_technical = _is_technical_room_or_level(controlled_room, tech_room_rx, tech_level_rx)
            want_2g = (not is_technical) and _is_two_gang(controlled_room, two_gang_rx)
            symbol = sym_ip44 if is_technical else (sym_2g if want_2g else sym_1g)

            p_link = _calc_switch_point_link(d, link_doc, place_room, height_ft, jamb_ft, min_axis_ft, phase_hint=ph)
            if p_link is None:
                skipped_no_point += 1
                continue

            # If switch for this door already exists, fix its facing so the button is outside.
            if has_existing:
                desired_dir_host = _desired_facing_host_from_link_wall_face(d, link_inst, p_link, t)
                insts = []
                try:
                    insts = list(existing_by_door_key.get(door_key) or [])
                except Exception:
                    insts = []

                if not insts:
                    skipped_existing += 1
                    continue

                updated_existing += len(insts)
                for inst0 in insts:
                    try:
                        planned_fix.append((inst0.Id, desired_dir_host, symbol))
                    except Exception:
                        continue
                # Do not place a new switch for this door.
                if len(planned_fix) < max(1, batch_size):
                    continue

                with tx('ЭОМ: Исправить ориентацию выключателей (кнопка наружу)', doc=doc, swallow_warnings=True):
                    for eid, ddir, target_sym in planned_fix:
                        inst_fix = None
                        try:
                            inst_fix = doc.GetElement(eid)
                        except Exception:
                            inst_fix = None
                        if inst_fix is None:
                            continue
                        try:
                            if target_sym is not None and hasattr(target_sym, 'Id'):
                                try:
                                    cur_sym_id = inst_fix.Symbol.Id
                                except Exception:
                                    cur_sym_id = None
                                try:
                                    target_id = target_sym.Id
                                except Exception:
                                    target_id = None
                                if target_id is not None and (cur_sym_id is None or cur_sym_id != target_id):
                                    try:
                                        ensure_symbol_active(doc, target_sym)
                                    except Exception:
                                        pass
                                    try:
                                        inst_fix.ChangeTypeId(target_id)
                                        updated_existing_retyped += 1
                                    except Exception:
                                        updated_existing_failed += 1
                        except Exception:
                            updated_existing_failed += 1

                        try:
                            if ddir is not None and _try_flip_facing_to_dir(inst_fix, ddir):
                                updated_existing_flipped += 1
                        except Exception:
                            continue

                planned_fix = []
                continue

            # Transform to host
            try:
                p_host = t.OfPoint(p_link)
            except Exception:
                skipped_no_point += 1
                continue

            planned.append((symbol, p_host, p_link, d, door_key))

            if len(planned) < max(1, batch_size):
                continue

            with tx('ЭОМ: Разместить выключатели у дверей', doc=doc, swallow_warnings=True):
                for sym, pt_host, pt_link, door_link, dkey in planned:
                    inst = None
                    try:
                        inst = _place_switch_instance(
                            doc,
                            sym,
                            pt_host,
                            door_link,
                            link_inst,
                            pt_link,
                            t,
                            view=doc.ActiveView,
                            allow_point_fallback=allow_point_fallback,
                            host_walls=host_walls,
                            wall_search_ft=wall_search_ft
                        )
                    except Exception:
                        inst = None
                    if inst is None:
                        skipped_no_place += 1
                        continue
                    set_comments(inst, _comment_with_door_key(comment_value, dkey))
                    created += 1
                    if dkey:
                        existing_door_keys.add(dkey)
                    try:
                        if len(created_ids) < 2000:
                            created_ids.append(inst.Id)
                    except Exception:
                        pass
                    if sym.Id == sym_2g.Id:
                        created_2g += 1
                    else:
                        created_1g += 1

            planned = []

    # flush remainder
    if planned_fix:
        with tx('ЭОМ: Исправить ориентацию выключателей (кнопка наружу)', doc=doc, swallow_warnings=True):
            for eid, ddir, target_sym in planned_fix:
                inst_fix = None
                try:
                    inst_fix = doc.GetElement(eid)
                except Exception:
                    inst_fix = None
                if inst_fix is None:
                    continue
                try:
                    if target_sym is not None and hasattr(target_sym, 'Id'):
                        cur_id = None
                        try:
                            cur_id = inst_fix.Symbol.Id
                        except Exception:
                            cur_id = None
                        target_id = None
                        try:
                            target_id = target_sym.Id
                        except Exception:
                            target_id = None
                        if target_id is not None and (cur_id is None or cur_id != target_id):
                            try:
                                ensure_symbol_active(doc, target_sym)
                            except Exception:
                                pass
                            try:
                                inst_fix.ChangeTypeId(target_id)
                                updated_existing_retyped += 1
                            except Exception:
                                updated_existing_failed += 1
                except Exception:
                    updated_existing_failed += 1

                try:
                    if ddir is not None and _try_flip_facing_to_dir(inst_fix, ddir):
                        updated_existing_flipped += 1
                except Exception:
                    continue

    if planned:
        with tx('ЭОМ: Разместить выключатели у дверей', doc=doc, swallow_warnings=True):
            for sym, pt_host, pt_link, door_link, dkey in planned:
                inst = None
                try:
                    inst = _place_switch_instance(
                        doc,
                        sym,
                        pt_host,
                        door_link,
                        link_inst,
                        pt_link,
                        t,
                        view=doc.ActiveView,
                        allow_point_fallback=allow_point_fallback,
                        host_walls=host_walls,
                        wall_search_ft=wall_search_ft
                    )
                except Exception:
                    inst = None
                if inst is None:
                    skipped_no_place += 1
                    continue
                set_comments(inst, _comment_with_door_key(comment_value, dkey))
                created += 1
                if dkey:
                    existing_door_keys.add(dkey)
                try:
                    if len(created_ids) < 2000:
                        created_ids.append(inst.Id)
                except Exception:
                    pass
                if sym.Id == sym_2g.Id:
                    created_2g += 1
                else:
                    created_1g += 1

    output.print_md('---')
    output.print_md('Дверей обработано: **{0}**'.format(processed))
    output.print_md('Создано выключателей: **{0}**'.format(created))
    output.print_md('  - 1G: **{0}**'.format(created_1g))
    output.print_md('  - 2G: **{0}**'.format(created_2g))
    if updated_existing:
        output.print_md('Исправлено существующих: **{0}** (перевернуто={1}, тип сменён={2}, ошибки смены типа={3})'.format(updated_existing, updated_existing_flipped, updated_existing_retyped, updated_existing_failed))
    if skipped_no_rooms:
        output.print_md('Пропущено (не определены помещения): **{0}**'.format(skipped_no_rooms))
    if skipped_no_point:
        output.print_md('Пропущено (нет точки/геометрии): **{0}**'.format(skipped_no_point))
    if skipped_level:
        output.print_md('Пропущено (другой этаж): **{0}**'.format(skipped_level))
    if skipped_non_room:
        output.print_md('Пропущено (двери в общих зонах): **{0}**'.format(skipped_non_room))
    if skipped_existing:
        output.print_md('Пропущено (у двери уже есть выключатель, но не удалось исправить): **{0}**'.format(skipped_existing))
    if skipped_no_place:
        output.print_md('Пропущено (не удалось разместить): **{0}**'.format(skipped_no_place))
    if skipped_max:
        output.print_md('Остановлено по лимиту max_place_count: **{0}**'.format(max_place))
    if cancelled:
        output.print_md('**Операция отменена пользователем.**')

    # Debug: open a dedicated 3D view with a section box around created switches
    go3d = False
    if created_ids:
        try:
            go3d = forms.alert(
                'Открыть отладочный 3D-вид и приблизить к размещённым выключателям?',
                title='ЭОМ: Найти размещённые выключатели',
                warn_icon=False,
                yes=True,
                no=True
            )
        except Exception:
            go3d = False

    if go3d:
            try:
                bb = _bbox_from_element_ids(doc, created_ids, pad_ft=60.0, limit=500)
                v3d = None
                with tx('ЭОМ: Открыть отладочный 3D-вид (выключатели)', doc=doc, swallow_warnings=True):
                    v3d = _get_or_create_debug_3d_view(
                        doc,
                        'ЭОМ_ОТЛАДКА_Размещенные_Выключатели',
                        aliases=['EOM_DEBUG_Placed_Switches']
                    )
                    if v3d and bb:
                        try:
                            v3d.ViewTemplateId = DB.ElementId.InvalidElementId
                        except Exception:
                            pass
                        try:
                            v3d.DetailLevel = DB.ViewDetailLevel.Fine
                        except Exception:
                            pass
                        try:
                            v3d.DisplayStyle = DB.DisplayStyle.Shading
                        except Exception:
                            pass

                        try:
                            cat_links = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_RvtLinks)
                            if cat_links:
                                v3d.SetCategoryHidden(cat_links.Id, False)
                        except Exception:
                            pass

                        # Show typical electrical fixture categories and the chosen symbol categories
                        for bic in (
                            DB.BuiltInCategory.OST_ElectricalFixtures,
                            DB.BuiltInCategory.OST_ElectricalEquipment,
                        ):
                            try:
                                cat = doc.Settings.Categories.get_Item(bic)
                                if cat:
                                    v3d.SetCategoryHidden(cat.Id, False)
                            except Exception:
                                continue

                        try:
                            if sym_1g is not None and sym_1g.Category is not None:
                                v3d.SetCategoryHidden(sym_1g.Category.Id, False)
                        except Exception:
                            pass
                        try:
                            if sym_2g is not None and sym_2g.Category is not None:
                                v3d.SetCategoryHidden(sym_2g.Category.Id, False)
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
                        uidoc.RequestViewChange(v3d)
                        output.print_md('Открыт отладочный 3D-вид: `{0}`'.format(v3d.Name))
                    except Exception:
                        output.print_md('**Не удалось автоматически переключить вид.** Откройте 3D-вид `ЭОМ_ОТЛАДКА_Размещенные_Выключатели` в Диспетчере проекта.')

                    try:
                        av = uidoc.ActiveView
                        if av:
                            try:
                                if av.IsTemporaryHideIsolateActive():
                                    av.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    try:
                        uidoc.Selection.SetElementIds(_as_net_id_list(created_ids[:50]))
                    except Exception:
                        pass
                    try:
                        uidoc.ShowElements(created_ids[0])
                    except Exception:
                        pass
            except Exception:
                pass

    # Open floor plan at switch height for quick QC.
    try:
        _open_floorplan_at_switch_height(doc, uidoc, created_ids, height_ft)
    except Exception:
        pass

    logger.info(
        'SWITCH created=%s created_1g=%s created_2g=%s updated_existing=%s updated_existing_flipped=%s processed=%s skipped_no_rooms=%s skipped_no_point=%s skipped_non_room=%s skipped_existing=%s skipped_no_place=%s cancelled=%s',
        created, created_1g, created_2g, updated_existing, updated_existing_flipped, processed, skipped_no_rooms, skipped_no_point, skipped_non_room, skipped_existing, skipped_no_place, cancelled
    )


try:
    main()
except Exception:
    log_exception('Ошибка инструмента Place_Switches_ByDoors')
    alert('Ошибка. Подробности смотрите в выводе pyRevit.')
