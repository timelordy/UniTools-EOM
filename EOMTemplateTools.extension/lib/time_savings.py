# -*- coding: utf-8 -*-

"""Time-saved reporting for EOM tools.

Estimates time saved based on manual placement rate and actual element count.

`MANUAL_TIME_PER_ITEM` values can be:
- float: fixed minutes per unit
- (min, max): range of minutes per unit
"""

import os
import io
import json
import tempfile
import time

try:
    text_type = unicode  # IronPython 2
except NameError:
    text_type = str


# Manual placement time estimates (minutes per element/room).
# NOTE: keep Python 2.7 compatibility (pyRevit/IronPython).
MANUAL_TIME_PER_ITEM = {
    # 01. Розетки (бытовые): 5–7 минут на комнату
    'sockets_general': (5.0, 7.0),
    # 02. Кухня блок: 5–7 минут на комнату
    'kitchen_block': (5.0, 7.0),
    # 05/06/07: per room
    'wet_zones': (1.0, 3.0),
    'low_voltage': (1.0, 3.0),
    'switches_doors': (1.0, 3.0),
    'lights_center': (1.0, 3.0),
    'shdup': (1.0, 3.0),
    # Свет в лифтах: per shaft (not per placed light)
    'lights_elevator': (10.0, 10.0),
    # Щит над дверью: per apartment
    'panel_door': (7.0, 7.0),

    # Other tools (kept for compatibility)
    'lights_entrance': (1.0, 3.0),
    'entrance_numbering': (10.0, 10.0),
    'storage_equipment': (15.0, 15.0),
    'panels_mop': (5.0, 5.0),
    'ac_sockets': (1.0, 3.0),
}


# Backward-compatible key aliases used by some scripts
TOOL_KEY_ALIASES = {
    'switches': 'switches_doors',
    'sockets_wet': 'wet_zones',
    'sockets_low_voltage': 'low_voltage',
    'kitchen_general': 'kitchen_block',
}


DEFAULT_TIME_PER_ITEM = 0.5
LIFT_SHAFT_TAG_SUFFIX = 'LIGHT_LIFT_SHAFT'
ROOM_COUNT_TOOLS = set([
    'sockets_general',
    'kitchen_block',
    'wet_zones',
    'low_voltage',
    'ac_sockets',
    'shdup',
])
ROOM_COUNT_TOOL_SUFFIXES = {
    'sockets_general': [':SOCKET_GENERAL'],
    'kitchen_block': [':SOCKET_KITCHEN_UNIT', ':SOCKET_FRIDGE', ':SOCKET_KITCHEN_GENERAL'],
    'wet_zones': [' (wet)'],
    'low_voltage': [':SOCKET_INTERCOM', ':SOCKET_ROUTER'],
    'ac_sockets': [':SOCKET_AC'],
    'shdup': [':SHDUP'],
}

# Session storage for element counts
_session_counts = {}
_lift_shaft_count_cache = None
_room_count_cache = {}
_room_count_override = {}
_link_rooms_cache = {}


def _get_counts_store_paths():
    temp_root = os.environ.get('TEMP') or os.environ.get('TMP') or tempfile.gettempdir()
    session_id = os.environ.get('EOM_SESSION_ID')
    paths = []
    if session_id:
        paths.append(os.path.join(temp_root, 'eom_time_savings_counts_{0}.json'.format(session_id)))
    paths.append(os.path.join(temp_root, 'eom_time_savings_counts.json'))
    return paths


def _get_log_paths():
    temp_root = os.environ.get('TEMP') or os.environ.get('TMP') or tempfile.gettempdir()
    session_id = os.environ.get('EOM_SESSION_ID')
    paths = []
    if session_id:
        paths.append(os.path.join(temp_root, 'eom_time_savings_log_{0}.jsonl'.format(session_id)))
    paths.append(os.path.join(temp_root, 'eom_time_savings_log.jsonl'))
    return paths


def _ensure_text(val):
    try:
        if isinstance(val, text_type):
            return val
        return val.decode('utf-8')
    except Exception:
        try:
            return text_type(val)
        except Exception:
            return u"" if text_type is not str else ""


def _get_lift_shaft_count_override():
    try:
        val = os.environ.get('EOM_LIFT_SHAFT_COUNT_OVERRIDE') or os.environ.get('EOM_LIFT_SHAFTS')
        if val is None:
            return None
        cnt = int(float(val))
        return cnt if cnt > 0 else None
    except Exception:
        return None


def _room_override_env_key(tool_key):
    try:
        key = normalize_tool_key(tool_key)
        key = ''.join([c.upper() if c.isalnum() else '_' for c in key])
        return 'EOM_ROOM_COUNT_OVERRIDE_{0}'.format(key)
    except Exception:
        return 'EOM_ROOM_COUNT_OVERRIDE'


def _get_room_count_override(tool_key):
    try:
        key = _room_override_env_key(tool_key)
        val = os.environ.get(key)
        if val is None:
            return None
        cnt = int(float(val))
        return cnt if cnt > 0 else None
    except Exception:
        return None


def set_room_count_override(tool_key, count):
    """Set explicit room count override for current session (non-persistent)."""
    try:
        key = normalize_tool_key(tool_key)
    except Exception:
        key = tool_key
    try:
        cnt = int(float(count))
    except Exception:
        cnt = None
    if cnt is None or cnt <= 0:
        try:
            _room_count_override.pop(key, None)
        except Exception:
            pass
        try:
            _room_count_cache.pop(key, None)
        except Exception:
            pass
        return None
    try:
        _room_count_override[key] = int(cnt)
        _room_count_cache[key] = int(cnt)
    except Exception:
        pass
    return cnt


def _get_room_id_from_element(doc, el):
    try:
        room = getattr(el, 'Room', None)
        if room is not None:
            return int(room.Id.IntegerValue)
    except Exception:
        pass
    try:
        from Autodesk.Revit import DB
        param = el.get_Parameter(DB.BuiltInParameter.ELEM_ROOM_ID)
        if param:
            rid = param.AsElementId()
            if rid and rid.IntegerValue > 0:
                return int(rid.IntegerValue)
    except Exception:
        pass
    try:
        loc = getattr(el, 'Location', None)
        pt = None
        if loc is not None and hasattr(loc, 'Point') and loc.Point is not None:
            pt = loc.Point
        elif loc is not None and hasattr(loc, 'Curve') and loc.Curve is not None:
            pt = loc.Curve.Evaluate(0.5, True)
        if pt is None:
            try:
                bb = el.get_BoundingBox(None)
                if bb is not None:
                    cx = (float(bb.Min.X) + float(bb.Max.X)) / 2.0
                    cy = (float(bb.Min.Y) + float(bb.Max.Y)) / 2.0
                    cz = (float(bb.Min.Z) + float(bb.Max.Z)) / 2.0
                    from Autodesk.Revit import DB
                    pt = DB.XYZ(cx, cy, cz)
            except Exception:
                pt = None
        if pt is None:
            return None
        if hasattr(doc, 'GetRoomAtPoint'):
            room = doc.GetRoomAtPoint(pt)
            if room is not None:
                return int(room.Id.IntegerValue)
    except Exception:
        pass
    return None


def _make_room_key(link_id, room_id):
    try:
        rid = int(room_id)
    except Exception:
        return None
    if link_id is None:
        return 'H:{0}'.format(rid)
    try:
        lid = int(link_id)
        return 'L{0}:{1}'.format(lid, rid)
    except Exception:
        return 'L?:{0}'.format(rid)


def _get_element_point(el):
    try:
        loc = getattr(el, 'Location', None)
        if loc is not None and hasattr(loc, 'Point') and loc.Point is not None:
            return loc.Point
        if loc is not None and hasattr(loc, 'Curve') and loc.Curve is not None:
            return loc.Curve.Evaluate(0.5, True)
    except Exception:
        pass
    try:
        bb = el.get_BoundingBox(None)
        if bb is not None:
            cx = (float(bb.Min.X) + float(bb.Max.X)) / 2.0
            cy = (float(bb.Min.Y) + float(bb.Max.Y)) / 2.0
            cz = (float(bb.Min.Z) + float(bb.Max.Z)) / 2.0
            from Autodesk.Revit import DB
            return DB.XYZ(cx, cy, cz)
    except Exception:
        return None
    return None


def _get_link_rooms_cached(link_doc):
    if link_doc is None:
        return []
    key = None
    try:
        key = int(link_doc.GetHashCode())
    except Exception:
        key = None
    if key is not None and key in _link_rooms_cache:
        return _link_rooms_cache.get(key, [])
    try:
        import link_reader
        rooms = link_reader.get_rooms(link_doc) or []
    except Exception:
        rooms = []
    if key is not None:
        _link_rooms_cache[key] = rooms
    return rooms


def _room_contains_point(room, pt):
    if room is None or pt is None:
        return False
    try:
        bb = room.get_BoundingBox(None)
        if bb is not None:
            if pt.X < bb.Min.X or pt.X > bb.Max.X:
                return False
            if pt.Y < bb.Min.Y or pt.Y > bb.Max.Y:
                return False
            # Z-check is optional; keep loose
            if pt.Z < bb.Min.Z - 1.0 or pt.Z > bb.Max.Z + 1.0:
                return False
    except Exception:
        pass
    try:
        if hasattr(room, 'IsPointInRoom'):
            return bool(room.IsPointInRoom(pt))
    except Exception:
        pass
    return False


def _find_room_in_rooms(rooms, pt):
    if not rooms or pt is None:
        return None
    for r in rooms:
        try:
            if _room_contains_point(r, pt):
                return r
        except Exception:
            continue
    return None


def _add_room_keys_from_links(doc, points, room_keys):
    if not points:
        return
    try:
        import link_reader
    except Exception:
        return
    try:
        links = link_reader.list_link_instances(doc)
    except Exception:
        links = []
    if not links:
        return

    for link_inst in links:
        try:
            if not link_reader.is_link_loaded(link_inst):
                continue
        except Exception:
            continue
        link_doc = None
        try:
            link_doc = link_reader.get_link_doc(link_inst)
        except Exception:
            link_doc = None
        if link_doc is None:
            continue
        try:
            t = link_reader.get_total_transform(link_inst)
        except Exception:
            t = None
        t_inv = None
        if t is not None:
            try:
                t_inv = t.Inverse
            except Exception:
                try:
                    t_inv = t.Inverse()
                except Exception:
                    t_inv = None

        rooms = _get_link_rooms_cached(link_doc)
        for pt in points:
            if pt is None:
                continue
            try:
                pt_link = t_inv.OfPoint(pt) if t_inv else pt
            except Exception:
                pt_link = pt
            room = None
            try:
                if hasattr(link_doc, 'GetRoomAtPoint'):
                    room = link_doc.GetRoomAtPoint(pt_link)
            except Exception:
                room = None
            if room is None and rooms:
                room = _find_room_in_rooms(rooms, pt_link)
            if room is not None:
                try:
                    link_id = link_inst.Id.IntegerValue
                except Exception:
                    link_id = None
                try:
                    rkey = _make_room_key(link_id, room.Id.IntegerValue)
                    if rkey:
                        room_keys.add(rkey)
                except Exception:
                    continue


def _collect_room_ids_by_family_type(doc, family_type_name):
    if not family_type_name:
        return set()
    try:
        from Autodesk.Revit import DB
    except Exception:
        return set()
    try:
        target = _ensure_text(family_type_name).lower()
    except Exception:
        try:
            target = text_type(family_type_name).lower()
        except Exception:
            return set()

    room_keys = set()
    points = []
    categories = []
    try:
        categories.append(DB.BuiltInCategory.OST_ElectricalFixtures)
    except Exception:
        pass
    try:
        categories.append(DB.BuiltInCategory.OST_ElectricalEquipment)
    except Exception:
        pass
    if not categories:
        return room_ids

    for cat in categories:
        try:
            collector = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()
        except Exception:
            continue
        for el in collector:
            try:
                sym = getattr(el, 'Symbol', None)
                sym_name = getattr(sym, 'Name', None) if sym else None
                fam_name = None
                try:
                    fam = getattr(sym, 'Family', None)
                    fam_name = getattr(fam, 'Name', None)
                except Exception:
                    fam_name = None

                def _norm(val):
                    try:
                        return _ensure_text(val).lower()
                    except Exception:
                        try:
                            return text_type(val).lower()
                        except Exception:
                            return u""

                if sym_name and _norm(sym_name) == target:
                    rid = _get_room_id_from_element(doc, el)
                    if rid:
                        room_ids.add(int(rid))
                    continue
                if fam_name and _norm(fam_name) == target:
                    rid = _get_room_id_from_element(doc, el)
                    if rid:
                        room_ids.add(int(rid))
            except Exception:
                continue
    return room_ids


def _estimate_room_count_for_tool(tool_key):
    key = normalize_tool_key(tool_key)
    suffixes = ROOM_COUNT_TOOL_SUFFIXES.get(key)
    if not suffixes:
        return None
    try:
        from pyrevit import revit
        from Autodesk.Revit import DB
    except Exception:
        return None

    doc = getattr(revit, 'doc', None)
    if doc is None:
        return None

    rules = None
    try:
        from config_loader import load_rules
        rules = load_rules()
        comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    except Exception:
        comment_tag = 'AUTO_EOM'

    try:
        comment_values = [u'{0}{1}'.format(comment_tag, s) for s in suffixes]
    except Exception:
        comment_values = [str(comment_tag) + str(s) for s in suffixes]
    comment_values = [v for v in comment_values if v]
    comment_values_lower = [v.lower() for v in comment_values]

    room_ids = set()

    categories = []
    try:
        categories.append(DB.BuiltInCategory.OST_ElectricalFixtures)
    except Exception:
        pass
    try:
        categories.append(DB.BuiltInCategory.OST_ElectricalEquipment)
    except Exception:
        pass

    if not categories:
        return None

    for cat in categories:
        try:
            collector = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()
        except Exception:
            continue
        for el in collector:
            try:
                param = el.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                val = param.AsString() if param else None
                if not val:
                    continue
                try:
                    val_l = _ensure_text(val).lower()
                except Exception:
                    val_l = str(val).lower()
                if not any(cv in val_l for cv in comment_values_lower):
                    continue
                rid = _get_room_id_from_element(doc, el)
                if rid:
                    rkey = _make_room_key(None, rid)
                    if rkey:
                        room_keys.add(rkey)
                else:
                    pt = _get_element_point(el)
                    if pt is not None:
                        points.append(pt)
            except Exception:
                continue

    if points:
        try:
            _add_room_keys_from_links(doc, points, room_keys)
        except Exception:
            pass

    if key == 'ac_sockets' and not room_keys:
        try:
            socket_type_name = None
            if rules and isinstance(rules, dict):
                socket_type_name = rules.get('socket_ac_family_type_name')
            extra_ids = _collect_room_ids_by_family_type(doc, socket_type_name)
            if extra_ids:
                for rid in extra_ids:
                    try:
                        rkey = _make_room_key(None, rid)
                        if rkey:
                            room_keys.add(rkey)
                    except Exception:
                        continue
        except Exception:
            pass

    try:
        return len(room_keys) if room_keys else None
    except Exception:
        return None


def _get_room_count(tool_key):
    override = _get_room_count_override(tool_key)
    if override:
        return override
    key = normalize_tool_key(tool_key)
    if key in _room_count_override:
        return _room_count_override.get(key)
    if key in _room_count_cache:
        return _room_count_cache.get(key)
    count = _estimate_room_count_for_tool(tool_key)
    if count is not None:
        _room_count_cache[key] = count
    return count


def _estimate_lift_shaft_count():
    """Estimate number of lift shafts (prefer shaft elements, fallback to lights)."""
    count = _estimate_lift_shaft_count_from_model()
    if count:
        return count
    return _estimate_lift_shaft_count_from_lights()


def _estimate_lift_shaft_count_from_model():
    try:
        from pyrevit import revit
        from Autodesk.Revit import DB
    except Exception:
        return None

    doc = getattr(revit, 'doc', None)
    if doc is None:
        return None

    try:
        from config_loader import load_rules
        rules = load_rules()
        dedupe_mm = float(rules.get('lift_shaft_dedupe_radius_mm', rules.get('dedupe_radius_mm', 500)) or 500)
        include_keywords = list(rules.get('lift_shaft_generic_model_keywords', []) or [])
        include_keywords += list(rules.get('lift_shaft_room_name_patterns', []) or [])
        include_exact = list(rules.get('lift_shaft_family_names', []) or [])
        exclude_keywords = list(rules.get('lift_shaft_generic_model_exclude_patterns', []) or [])
        exclude_keywords += list(rules.get('lift_shaft_room_exclude_patterns', []) or [])
    except Exception:
        dedupe_mm = 500
        include_keywords = []
        include_exact = []
        exclude_keywords = []

    try:
        tol_ft = float(dedupe_mm) / 304.8
    except Exception:
        tol_ft = 1.64

    def _norm(val):
        try:
            return _ensure_text(val).lower()
        except Exception:
            try:
                return text_type(val).lower()
            except Exception:
                return ""

    include_keywords = [_norm(x) for x in include_keywords if x]
    include_exact = [_norm(x) for x in include_exact if x]
    exclude_keywords = [_norm(x) for x in exclude_keywords if x]

    def _name_text(el):
        try:
            parts = []
            nm = getattr(el, 'Name', None)
            if nm:
                parts.append(_ensure_text(nm))
            sym = getattr(el, 'Symbol', None)
            if sym is not None:
                sn = getattr(sym, 'Name', None)
                if sn:
                    parts.append(_ensure_text(sn))
                fam = getattr(sym, 'Family', None)
                if fam is not None:
                    fn = getattr(fam, 'Name', None)
                    if fn:
                        parts.append(_ensure_text(fn))
            return u' '.join(parts)
        except Exception:
            return u""

    def _matches(name_text):
        if not name_text:
            return False
        text = _norm(name_text)
        if exclude_keywords:
            for p in exclude_keywords:
                if p and p in text:
                    return False
        if include_exact:
            for p in include_exact:
                if p and p in text:
                    return True
        if include_keywords:
            for p in include_keywords:
                if p and p in text:
                    return True
        return False

    def _get_xy(el):
        try:
            loc = el.Location
            if loc is not None and hasattr(loc, 'Point') and loc.Point is not None:
                pt = loc.Point
                return float(pt.X), float(pt.Y)
            if loc is not None and hasattr(loc, 'Curve') and loc.Curve is not None:
                pt = loc.Curve.Evaluate(0.5, True)
                return float(pt.X), float(pt.Y)
        except Exception:
            pass
        try:
            bb = el.get_BoundingBox(None)
            if bb is not None:
                cx = (float(bb.Min.X) + float(bb.Max.X)) / 2.0
                cy = (float(bb.Min.Y) + float(bb.Max.Y)) / 2.0
                return cx, cy
        except Exception:
            return None
        return None

    points = []

    # 1) Shaft openings (best signal).
    try:
        collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ShaftOpening).WhereElementIsNotElementType()
        for el in collector:
            xy = _get_xy(el)
            if xy:
                points.append(xy)
    except Exception:
        pass

    # 2) GenericModel/Furniture by keywords (fallback).
    if not points:
        for cat in [DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Furniture]:
            try:
                collector = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()
            except Exception:
                continue
            for el in collector:
                try:
                    if not _matches(_name_text(el)):
                        continue
                    xy = _get_xy(el)
                    if xy:
                        points.append(xy)
                except Exception:
                    continue

    if not points:
        return None

    try:
        return int(_cluster_xy_points(points, tol_ft))
    except Exception:
        return None


def _estimate_lift_shaft_count_from_lights():
    """Estimate number of lift shafts by clustering placed lift-shaft lights."""
    try:
        from pyrevit import revit
        from Autodesk.Revit import DB
    except Exception:
        return None

    doc = getattr(revit, 'doc', None)
    if doc is None:
        return None

    try:
        from config_loader import load_rules
        rules = load_rules()
        comment_tag = rules.get('comment_tag', 'AUTO_EOM')
        dedupe_mm = float(rules.get('lift_shaft_dedupe_radius_mm', rules.get('dedupe_radius_mm', 500)) or 500)
    except Exception:
        comment_tag = 'AUTO_EOM'
        dedupe_mm = 500

    try:
        tol_ft = float(dedupe_mm) / 304.8
    except Exception:
        tol_ft = 1.64

    try:
        tag_value = u'{0}:{1}'.format(comment_tag, LIFT_SHAFT_TAG_SUFFIX)
    except Exception:
        tag_value = 'AUTO_EOM:LIGHT_LIFT_SHAFT'

    def _get_xy(el):
        try:
            loc = el.Location
            if loc is not None and hasattr(loc, 'Point') and loc.Point is not None:
                pt = loc.Point
                return float(pt.X), float(pt.Y)
            if loc is not None and hasattr(loc, 'Curve') and loc.Curve is not None:
                pt = loc.Curve.Evaluate(0.5, True)
                return float(pt.X), float(pt.Y)
        except Exception:
            pass
        try:
            bb = el.get_BoundingBox(None)
            if bb is not None:
                cx = (float(bb.Min.X) + float(bb.Max.X)) / 2.0
                cy = (float(bb.Min.Y) + float(bb.Max.Y)) / 2.0
                return cx, cy
        except Exception:
            return None
        return None

    points = []
    categories = []
    try:
        categories.append(DB.BuiltInCategory.OST_LightingFixtures)
    except Exception:
        pass
    try:
        categories.append(DB.BuiltInCategory.OST_LightingDevices)
    except Exception:
        pass

    if not categories:
        return None

    for cat in categories:
        try:
            collector = DB.FilteredElementCollector(doc).OfCategory(cat).WhereElementIsNotElementType()
        except Exception:
            continue
        for el in collector:
            try:
                param = el.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                val = param.AsString() if param else None
                if not val or tag_value not in val:
                    continue
                xy = _get_xy(el)
                if xy:
                    points.append(xy)
            except Exception:
                continue

    if not points:
        return None

    try:
        return int(_cluster_xy_points(points, tol_ft))
    except Exception:
        return None


def _get_lift_shaft_count():
    override = _get_lift_shaft_count_override()
    if override:
        return override
    global _lift_shaft_count_cache
    if _lift_shaft_count_cache is None:
        _lift_shaft_count_cache = _estimate_lift_shaft_count()
    return _lift_shaft_count_cache


def _normalize_count(tool_key, count):
    key = normalize_tool_key(tool_key)
    if key in ROOM_COUNT_TOOLS:
        try:
            room_count = _get_room_count(tool_key)
            if room_count is not None and int(room_count) > 0:
                return int(room_count)
        except Exception:
            pass
    if key != 'lights_elevator':
        return count
    try:
        override = _get_lift_shaft_count()
        if override and int(override) > 0:
            return int(override)
    except Exception:
        pass
    return count


def _append_time_saved_log_entry(tool_key, count, minutes, minutes_min, minutes_max):
    paths = _get_log_paths()
    if not paths:
        return
    try:
        entry = {
            "tool_key": normalize_tool_key(tool_key),
            "count": int(count or 0),
            "minutes": float(minutes or 0.0),
            "minutes_min": float(minutes_min or 0.0),
            "minutes_max": float(minutes_max or 0.0),
            "timestamp": float(time.time()),
        }
    except Exception:
        return

    try:
        line = json.dumps(entry, ensure_ascii=False)
    except Exception:
        return

    try:
        path = paths[0]
        with io.open(path, 'a', encoding='utf-8') as f:
            f.write(_ensure_text(line))
            f.write(u"\n")
    except Exception:
        pass


def get_last_time_saved_entry(tool_key):
    """Return last log entry for tool or None."""
    key = normalize_tool_key(tool_key)
    for path in _get_log_paths():
        try:
            if not os.path.exists(path):
                continue
            last = None
            with io.open(path, 'r', encoding='utf-8') as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(data, dict):
                        continue
                    try:
                        entry_key = normalize_tool_key(data.get("tool_key"))
                    except Exception:
                        entry_key = data.get("tool_key")
                    if entry_key == key:
                        last = data
            if last:
                return last
        except Exception:
            continue
    return None


def _cluster_xy_points(points, tol_ft):
    if not points:
        return 0
    try:
        tol = float(tol_ft or 0.0)
    except Exception:
        tol = 0.0
    if tol <= 0:
        return len(points)
    tol2 = tol * tol
    clusters = []
    for x, y in points:
        assigned = False
        for c in clusters:
            dx = x - c[0]
            dy = y - c[1]
            if (dx * dx + dy * dy) <= tol2:
                c[0] = (c[0] * c[2] + x) / (c[2] + 1.0)
                c[1] = (c[1] * c[2] + y) / (c[2] + 1.0)
                c[2] = c[2] + 1.0
                assigned = True
                break
        if not assigned:
            clusters.append([x, y, 1.0])
    return len(clusters)


def _load_counts_store():
    for path in _get_counts_store_paths():
        try:
            if not os.path.exists(path):
                continue
            with io.open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _save_counts_store(data):
    paths = _get_counts_store_paths()
    if not paths:
        return
    path = paths[0]
    try:
        with io.open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def set_element_count(tool_key, count):
    """Store the number of elements created for time calculation."""
    count = _normalize_count(tool_key, count)
    key = normalize_tool_key(tool_key)
    try:
        _session_counts[key] = int(count or 0)
    except Exception:
        _session_counts[key] = 0
    try:
        store = _load_counts_store()
        store[key] = int(_session_counts[key] or 0)
        _save_counts_store(store)
    except Exception:
        pass


def get_element_count(tool_key):
    """Get stored element count."""
    key = normalize_tool_key(tool_key)
    try:
        if key in _session_counts:
            return int(_session_counts.get(key, 0) or 0)
    except Exception:
        return 0
    try:
        store = _load_counts_store()
        if key in store:
            _session_counts[key] = int(store.get(key, 0) or 0)
            return int(_session_counts.get(key, 0) or 0)
    except Exception:
        pass
    return 0


def normalize_tool_key(tool_key):
    """Return canonical tool key (handles legacy aliases)."""
    try:
        return TOOL_KEY_ALIASES.get(tool_key, tool_key)
    except Exception:
        return tool_key


def get_manual_time_per_item_range(tool_key):
    """Return (min, max) minutes per unit."""
    key = normalize_tool_key(tool_key)
    v = MANUAL_TIME_PER_ITEM.get(key, None)
    if v is None:
        return float(DEFAULT_TIME_PER_ITEM), float(DEFAULT_TIME_PER_ITEM)
    try:
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return float(v[0]), float(v[1])
    except Exception:
        pass
    try:
        fv = float(v)
        return fv, fv
    except Exception:
        return float(DEFAULT_TIME_PER_ITEM), float(DEFAULT_TIME_PER_ITEM)


def calculate_time_saved_range(tool_key, count=None):
    """Calculate (min, max) time saved in minutes based on element count."""
    if count is None:
        count = get_element_count(tool_key)
    count = _normalize_count(tool_key, count)
    try:
        cnt = int(count or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        return 0.0, 0.0

    rate_min, rate_max = get_manual_time_per_item_range(tool_key)
    return cnt * float(rate_min), cnt * float(rate_max)


def calculate_time_saved(tool_key, count=None):
    """Calculate time saved in minutes based on element count."""
    mn, mx = calculate_time_saved_range(tool_key, count)
    if mn <= 0 and mx <= 0:
        return 0.0
    return (float(mn) + float(mx)) / 2.0


def _format_minutes(minutes):
    try:
        minutes = float(minutes)
    except Exception:
        minutes = 0.0

    if minutes <= 0:
        return None

    if minutes < 1:
        return u'меньше минуты'
    elif minutes < 60:
        mins = int(round(minutes))
        if mins <= 0:
            return u'меньше минуты'
        if mins == 1:
            return u'~1 минута'
        # 2-4 minutes: "минуты", else "минут"
        if mins < 5:
            return u'~{0} минуты'.format(mins)
        return u'~{0} минут'.format(mins)
    else:
        hours = minutes / 60.0
        if hours < 2:
            return u'~{0:.1f} час'.format(hours)
        return u'~{0:.1f} часов'.format(hours)


def format_time_saved(tool_key, count=None):
    """Format time saved as human-readable string."""
    minutes = calculate_time_saved(tool_key, count)
    return _format_minutes(minutes)


def report(output, tool_key, count=None):
    """Report time saved to output.
    
    Args:
        output: pyRevit output object with print_md method
        tool_key: Tool identifier (e.g., 'sockets_general')
        count: Number of elements created. If None, uses stored count.
    """
    raw_count = None
    if count is not None:
        try:
            raw_count = int(count or 0)
        except Exception:
            raw_count = 0
        set_element_count(tool_key, count)
    else:
        try:
            override = _normalize_count(tool_key, None)
            if override is not None:
                set_element_count(tool_key, override)
        except Exception:
            pass

    saved_count = get_element_count(tool_key)
    time_str = format_time_saved(tool_key, saved_count)
    if not time_str:
        return False

    mn, mx = calculate_time_saved_range(tool_key, saved_count)
    range_str = None
    try:
        if abs(float(mx) - float(mn)) > 1e-6:
            range_str = u'диапазон: {0}–{1}'.format(_format_minutes(mn), _format_minutes(mx))
    except Exception:
        range_str = None

    try:
        avg_minutes = calculate_time_saved(tool_key, saved_count)
        _append_time_saved_log_entry(tool_key, saved_count, avg_minutes, mn, mx)
    except Exception:
        pass

    msg = u'Сэкономлено времени: **{0}**'.format(time_str)
    if range_str:
        msg += u' ({0})'.format(range_str)
    display_count = raw_count if raw_count is not None else saved_count
    msg += u' (создано элементов: {0})'.format(display_count)
    if raw_count is not None:
        try:
            key = normalize_tool_key(tool_key)
            if key in ROOM_COUNT_TOOLS and int(saved_count) != int(raw_count):
                msg += u' (комнат: {0})'.format(saved_count)
        except Exception:
            pass
    
    try:
        if output is not None and hasattr(output, 'print_md'):
            output.print_md(msg)
        else:
            from utils_revit import alert
            alert(msg, title='EOM Template Tools', warn_icon=False)
    except Exception:
        try:
            from utils_revit import get_logger
            get_logger().info(msg)
        except Exception:
            pass
    return True


# Backwards-compatible alias
report_time_saved = report
