# -*- coding: utf-8 -*-

from pyrevit import DB, forms
import config_loader
import link_reader
import placement_engine
from utils_revit import alert, set_comments, tx, trace
from utils_units import mm_to_ft
try:
    import socket_utils as su
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su

from constants import (
    ENTRANCE_DOOR_DEFAULT_PATTERNS,
    ROOF_EXIT_DOOR_DEFAULT_PATTERNS,
    OUTSIDE_DEFAULT_PATTERNS,
    ROOF_DEFAULT_PATTERNS,
    ENTRANCE_INSIDE_ROOM_DEFAULT_PATTERNS,
    ENTRANCE_PUBLIC_ROOM_DEFAULT_PATTERNS,
    APARTMENT_ROOM_DEFAULT_PATTERNS,
    ENTRANCE_LEVEL_DEFAULT_PATTERNS,
)
from domain import (
    get_user_config,
    save_user_config,
    norm,
    text_has_any,
    PointGridIndex,
    score_room_outside,
)
from adapters import (
    pick_light_symbol,
    store_symbol_id,
    store_symbol_unique_id,
)


def get_param_as_string(elem, bip=None, name=None):
    if elem is None:
        return u''
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
        return u''
    try:
        s = p.AsString()
        return s if s is not None else u''
    except Exception:
        return u''


def door_family_type_text(door):
    if door is None:
        return u''
    try:
        sym = getattr(door, 'Symbol', None)
    except Exception:
        sym = None

    if sym is None:
        try:
            ddoc = getattr(door, 'Document', None)
            tid = door.GetTypeId() if hasattr(door, 'GetTypeId') else None
            if ddoc is not None and tid is not None and tid != DB.ElementId.InvalidElementId:
                sym = ddoc.GetElement(tid)
        except Exception:
            sym = None

    if sym is None:
        return u''

    try:
        fam = getattr(sym, 'Family', None)
        fam_name = getattr(fam, 'Name', u'') if fam else u''
    except Exception:
        fam_name = u''

    try:
        typ_name = getattr(sym, 'Name', u'') or u''
    except Exception:
        typ_name = u''

    return norm(u'{0} {1}'.format(fam_name, typ_name))


def door_text(door):
    try:
        nm = getattr(door, 'Name', u'') or u''
    except Exception:
        nm = u''
    mark = get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name='Mark')
    comm = get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name='Comments')
    ft = door_family_type_text(door)
    return norm(u'{0} {1} {2} {3}'.format(nm, mark, comm, ft))


def get_last_phase(doc_):
    try:
        phases = list(doc_.Phases)
        return phases[-1] if phases else None
    except Exception:
        return None


def get_from_to_rooms(door, link_doc):
    if door is None or link_doc is None:
        return None, None
    try:
        phases = list(link_doc.Phases)
    except Exception:
        phases = []
    if not phases:
        return None, None

    for ph in reversed(phases):
        fr = None
        tr = None
        try:
            m = getattr(door, 'get_FromRoom', None)
            if m is not None:
                fr = m(ph)
        except Exception:
            fr = None
        try:
            m = getattr(door, 'get_ToRoom', None)
            if m is not None:
                tr = m(ph)
        except Exception:
            tr = None

        if (fr is not None) or (tr is not None):
            return fr, tr

    try:
        fr = getattr(door, 'FromRoom', None)
    except Exception:
        fr = None
    try:
        tr = getattr(door, 'ToRoom', None)
    except Exception:
        tr = None

    if (fr is not None) or (tr is not None):
        return fr, tr

    return None, None


def try_get_room_at_point(doc_, pt, phase=None):
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


def room_name(room):
    if room is None:
        return u''
    try:
        name = getattr(room, 'Name', u'')
        if name:
            return norm(name)
    except Exception:
        pass
    try:
        p = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        if p:
            return norm(p.AsString())
    except Exception:
        pass
    return u''


def room_matches(room, patterns):
    return text_has_any(room_name(room), patterns)


def is_public_room(room, public_patterns):
    return room_matches(room, public_patterns)


def is_apartment_room(room, apt_patterns):
    return room_matches(room, apt_patterns)


def is_room_outside(room, outside_patterns, roof_patterns=None):
    if room is None:
        return True
    if room_matches(room, outside_patterns):
        return True
    if roof_patterns and room_matches(room, roof_patterns):
        return True
    return False


def door_center_point_link(door):
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


def door_head_z_link(door):
    if door is None:
        return None
    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return float(bb.Max.Z)
    except Exception:
        pass

    try:
        loc = getattr(door, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt is None:
            return None
        head = None
        try:
            p = door.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM)
            if p:
                head = p.AsDouble()
        except Exception:
            head = None
        if head is None:
            return float(pt.Z)
        return float(pt.Z) + float(head)
    except Exception:
        return None


def try_get_door_facing_xy(door):
    if door is None:
        return None
    try:
        fo = getattr(door, 'FacingOrientation', None)
        if fo is not None:
            v = DB.XYZ(float(fo.X), float(fo.Y), 0.0)
            if v.GetLength() > 1e-9:
                return v.Normalize()
    except Exception:
        pass

    try:
        host = getattr(door, 'Host', None)
        o = getattr(host, 'Orientation', None) if host is not None else None
        if o is not None:
            v = DB.XYZ(float(o.X), float(o.Y), 0.0)
            if v.GetLength() > 1e-9:
                return v.Normalize()
    except Exception:
        pass

    return None


def try_get_wall_thickness_ft(door):
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


def choose_outside_dir_by_probe(door, link_doc, center_pt, normal_xy, outside_patterns, inside_patterns, roof_patterns=None):
    n = normal_xy
    if center_pt is None or n is None or link_doc is None:
        return None

    ph = get_last_phase(link_doc)
    th = try_get_wall_thickness_ft(door)
    base_eps = mm_to_ft(500) or 0.0
    if th is not None:
        try:
            extra = (float(th) * 0.5) + (mm_to_ft(200) or 0.0)
            if extra > base_eps:
                base_eps = extra
        except Exception:
            pass

    try:
        zprobe = float(center_pt.Z) + (mm_to_ft(1000) or 0.0)
        base = DB.XYZ(float(center_pt.X), float(center_pt.Y), zprobe)
        p_plus = base + (n * float(base_eps))
        p_minus = base + (n * float(-base_eps))
        r_plus = try_get_room_at_point(link_doc, p_plus, phase=ph)
        r_minus = try_get_room_at_point(link_doc, p_minus, phase=ph)
        sp = score_room_outside(r_plus, outside_patterns, inside_patterns, roof_patterns=roof_patterns, room_matches_func=room_matches)
        sm = score_room_outside(r_minus, outside_patterns, inside_patterns, roof_patterns=roof_patterns, room_matches_func=room_matches)
        if sp > sm:
            return n
        if sm > sp:
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)

        if is_room_outside(r_plus, outside_patterns, roof_patterns=roof_patterns) and (not is_room_outside(r_minus, outside_patterns, roof_patterns=roof_patterns)):
            return n
        if is_room_outside(r_minus, outside_patterns, roof_patterns=roof_patterns) and (not is_room_outside(r_plus, outside_patterns, roof_patterns=roof_patterns)):
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)
    except Exception:
        pass

    return None


def collect_existing_tagged_points(host_doc, tag):
    pts = []
    if host_doc is None or (not tag):
        return pts

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, tag, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, tag)

        pfilter = DB.ElementParameterFilter(rule)
        for bic in (
            DB.BuiltInCategory.OST_LightingFixtures,
            DB.BuiltInCategory.OST_LightingDevices,
            DB.BuiltInCategory.OST_ElectricalFixtures,
        ):
            col = (DB.FilteredElementCollector(host_doc)
                   .WhereElementIsNotElementType()
                   .OfCategory(bic)
                   .WherePasses(pfilter))
            for e in col:
                try:
                    loc = getattr(e, 'Location', None)
                    p = loc.Point if loc and hasattr(loc, 'Point') else None
                except Exception:
                    p = None
                if p is None:
                    continue
                pts.append(p)
    except Exception:
        return []

    return pts


def door_matches_patterns(door, patterns):
    return text_has_any(door_text(door), patterns)


def is_entrance_door(door, link_doc, entrance_patterns, outside_patterns, inside_patterns, public_room_patterns, apartment_room_patterns, entry_level_patterns):
    dt = door_text(door)
    
    # 1. Negative check: Apartments and BALCONIES
    BALCONY_PATTERNS = [u'балкон', u'лоджия', u'терраса', u'balcony', u'loggia', u'terrace', u'витраж']
    if text_has_any(dt, apartment_room_patterns) or text_has_any(dt, BALCONY_PATTERNS):
        return False
        
    fr, tr = get_from_to_rooms(door, link_doc)
    if (fr is None) and (tr is None):
        return False

    out_fr = is_room_outside(fr, outside_patterns)
    out_tr = is_room_outside(tr, outside_patterns)
    
    has_fr = (fr is not None)
    has_tr = (tr is not None)

    # CRITICAL FIX 2: Reject connection between two INSIDE Public Rooms
    # e.g. Vestibule <-> Stair, Corridor <-> Vestibule
    in_fr_any = room_matches(fr, inside_patterns)
    in_tr_any = room_matches(tr, inside_patterns)
    
    if has_fr and has_tr and in_fr_any and in_tr_any:
        return False

    # CRITICAL FIX: Reject Internal Doors (General)
    # If both sides have rooms, and NEITHER is explicitly "Street/Outside", then it is an INTERNAL door.
    # We strictly want Entrance -> Outside.
    if has_fr and has_tr and (not out_fr) and (not out_tr):
        return False

    # Helper to check for Main Entrance Rooms but EXCLUDE "Sluice"
    def is_main_vestibule(room):
        if room is None: return False
        rn = room_name(room)
        if not text_has_any(rn, [u'тамбур', u'вестиб', u'холл входа']):
            return False
        if text_has_any(rn, [u'шлюз', u'sluice']):
            return False
        return True

    # Negative check for residential rooms
    if (has_fr and is_apartment_room(fr, apartment_room_patterns)) or \
       (has_tr and is_apartment_room(tr, apartment_room_patterns)):
        return False

    # MAIN LOGIC: Clean Vestibule <-> Outside/Nothing
    if is_main_vestibule(fr) and (not has_tr or out_tr):
        return True
    if is_main_vestibule(tr) and (not has_fr or out_fr):
        return True

    # Fallback: If named "Entrance" explicitly
    if text_has_any(dt, entrance_patterns):
         in_fr_any = room_matches(fr, inside_patterns)
         in_tr_any = room_matches(tr, inside_patterns)
         if (in_fr_any and (not has_tr or out_tr)) or (in_tr_any and (not has_fr or out_fr)):
             return True

    return False


def is_roof_exit_door(door, link_doc, roof_patterns, roof_room_patterns):
    dt = door_text(door)
    
    # 1. Name/Room Name matches (Standard explicit check)
    if text_has_any(dt, roof_patterns):
        return True

    fr, tr = get_from_to_rooms(door, link_doc)
    if (fr is None) and (tr is None):
        return False

    if room_matches(fr, roof_room_patterns) or room_matches(tr, roof_room_patterns):
        return True

    # 2. IMPLICIT CHECK: Stairwell -> Outside (common for roof exits)
    # Filter out Balconies first
    BALCONY_PATTERNS = [u'балкон', u'лоджия', u'терраса', u'balcony', u'loggia', u'terrace', u'витраж']
    if text_has_any(dt, BALCONY_PATTERNS):
        return False
        
    STAIR_PATTERNS = [u'лестн', u'stair']
    
    in_fr_stair = room_matches(fr, STAIR_PATTERNS)
    in_tr_stair = room_matches(tr, STAIR_PATTERNS)
    
    # Use global default for outside patterns since it's not passed here
    from constants import OUTSIDE_DEFAULT_PATTERNS
    
    out_fr = is_room_outside(fr, OUTSIDE_DEFAULT_PATTERNS)
    out_tr = is_room_outside(tr, OUTSIDE_DEFAULT_PATTERNS)
    
    has_fr = (fr is not None)
    has_tr = (tr is not None)

    # Stair <-> Outside/Nothing
    if in_fr_stair and (not has_tr or out_tr):
        return True
    if in_tr_stair and (not has_fr or out_fr):
        return True

    return False


def select_link_instance_ru(host_doc, title):
    return link_reader.select_link_instance_auto(host_doc)


def run_placement(doc, output, script_module):
    output.print_md('# Расстановка светильников над входами в здание')
    output.print_md('Документ (ЭОМ): `{0}`'.format(doc.Title))
    trace('Place_Lights_EntranceDoors: start')

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')

    above_offset_mm = rules.get('entrance_light_above_door_offset_mm', 200)
    outside_offset_mm = rules.get('entrance_light_outside_offset_mm', 150)
    dedupe_mm = rules.get('entrance_light_dedupe_radius_mm', 500)
    scan_limit = int(rules.get('entrance_light_scan_limit_doors', 500) or 500)

    entrance_door_patterns = rules.get('entrance_door_name_patterns', []) or ENTRANCE_DOOR_DEFAULT_PATTERNS
    roof_exit_patterns = rules.get('roof_exit_door_name_patterns', []) or ROOF_EXIT_DOOR_DEFAULT_PATTERNS
    outside_room_patterns = rules.get('outside_room_name_patterns', []) or OUTSIDE_DEFAULT_PATTERNS
    roof_room_patterns = rules.get('roof_room_name_patterns', []) or ROOF_DEFAULT_PATTERNS
    inside_room_patterns = rules.get('entrance_inside_room_name_patterns', []) or ENTRANCE_INSIDE_ROOM_DEFAULT_PATTERNS
    public_room_patterns = rules.get('entrance_public_room_name_patterns', []) or ENTRANCE_PUBLIC_ROOM_DEFAULT_PATTERNS
    apartment_room_patterns = rules.get('entrance_apartment_room_name_patterns', []) or APARTMENT_ROOM_DEFAULT_PATTERNS
    entry_level_patterns = rules.get('entrance_level_name_patterns', []) or ENTRANCE_LEVEL_DEFAULT_PATTERNS

    fam_names = rules.get('family_type_names', {}) or {}
    fam_entrance = fam_names.get('light_entrance_door_outside') or ''

    above_offset_ft = mm_to_ft(above_offset_mm) or 0.0
    outside_offset_ft = mm_to_ft(outside_offset_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0

    link_inst = select_link_instance_ru(doc, title='Выберите связь АР')
    if link_inst is None:
        output.print_md('**Отменено.**')
        return
    if not link_reader.is_link_loaded(link_inst):
        alert('Выбранная связь не загружена. Загрузите её и повторите.')
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Не удалось получить доступ к документу связи.')
        return

    selected_levels = link_reader.list_levels(link_doc)
    if not selected_levels:
        output.print_md('**Нет уровней в связанном файле.**')
        return

    level_ids = []
    for lvl in selected_levels:
        try:
            if hasattr(lvl, 'Id'):
                level_ids.append(int(lvl.Id.IntegerValue))
                continue
            if hasattr(lvl, 'IntegerValue'):
                level_ids.append(int(lvl.IntegerValue))
                continue
            level_ids.append(int(lvl))
        except Exception:
            continue

    cfg = get_user_config(script_module)
    symbol, picked_label, _ = pick_light_symbol(doc, cfg, fam_entrance)
    if symbol is None:
        alert('Не найден подходящий тип светильника. Загрузите семейство и повторите.')
        return

    try:
        store_symbol_id(cfg, 'last_light_entrance_symbol_id', symbol)
        store_symbol_unique_id(cfg, 'last_light_entrance_symbol_uid', symbol)
        save_user_config(script_module)
    except Exception:
        pass

    comment_value = '{0}:LIGHT_ENTRANCE_DOOR'.format(comment_tag)
    existing_pts = collect_existing_tagged_points(doc, comment_value)
    grid = PointGridIndex(dedupe_ft)
    grid.add_many(existing_pts)

    xf = None
    try:
        xf = link_inst.GetTotalTransform()
    except Exception:
        xf = None
    if xf is None:
        alert('Не удалось получить трансформацию связи.')
        return

    counts = {
        'scanned': 0,
        'with_rooms': 0,
        'inside_side': 0,
        'outside_side': 0,
        'both_sides': 0,
        'total': 0,
        'placed': 0,
        'skipped': 0,
    }

    def _get_level_name(d):
        try:
            lid = d.LevelId
            if lid:
                l = link_doc.GetElement(lid)
                return l.Name if l else str(lid)
        except Exception:
            pass
        return "?"

    def _process_door(door):
        try:
            if door is None or (hasattr(door, 'IsValidObject') and (not door.IsValidObject)):
                return
        except Exception:
            return

        counts['scanned'] += 1
        try:
            fr_dbg, tr_dbg = get_from_to_rooms(door, link_doc)
            if (fr_dbg is not None) or (tr_dbg is not None):
                counts['with_rooms'] += 1
            inside_side_dbg = room_matches(fr_dbg, inside_room_patterns) or room_matches(tr_dbg, inside_room_patterns)
            outside_side_dbg = is_room_outside(fr_dbg, outside_room_patterns) or is_room_outside(tr_dbg, outside_room_patterns)
            if inside_side_dbg:
                counts['inside_side'] += 1
            if outside_side_dbg:
                counts['outside_side'] += 1
            if inside_side_dbg and outside_side_dbg:
                counts['both_sides'] += 1
        except Exception:
            pass

        is_roof = is_roof_exit_door(door, link_doc, roof_exit_patterns, roof_room_patterns)
        is_entrance = is_entrance_door(
            door,
            link_doc,
            entrance_door_patterns,
            outside_room_patterns,
            inside_room_patterns,
            public_room_patterns,
            apartment_room_patterns,
            entry_level_patterns
        )
        if (not is_roof) and (not is_entrance):
            return
            
        # DEBUG LOGGING FOR USER
        fr_log, tr_log = get_from_to_rooms(door, link_doc)
        rn_fr = room_name(fr_log)
        rn_tr = room_name(tr_log)
        d_name = door_text(door)
        lvl_name = _get_level_name(door)
        
        kind = "ENTRANCE"
        if is_roof: kind = "ROOF"
        
        output.print_md(u'- ACCEPTED ({}): ID `{}` | Level: `{}` | Door: `{}` | Rooms: `{}` <-> `{}`'.format(kind, door.Id, lvl_name, d_name, rn_fr, rn_tr))

        counts['total'] += 1
        c = door_center_point_link(door)
        if c is None:
            counts['skipped'] += 1
            return

        z_head = door_head_z_link(door)
        if z_head is None:
            z_head = float(c.Z)

        p_link = DB.XYZ(float(c.X), float(c.Y), float(z_head) + float(above_offset_ft))
        normal = try_get_door_facing_xy(door)
        outside_dir = None
        if normal is not None:
            outside_dir = choose_outside_dir_by_probe(
                door,
                link_doc,
                c,
                normal,
                outside_room_patterns,
                inside_room_patterns,
                roof_patterns=roof_room_patterns if is_roof else None
            )
            if outside_dir is None:
                outside_dir = normal

        if outside_dir is not None:
            try:
                th = try_get_wall_thickness_ft(door)
                wall_off = (float(th) * 0.5) if th is not None else 0.0
                p_link = p_link + (outside_dir * (wall_off + float(outside_offset_ft)))
            except Exception:
                pass

        try:
            p_host = xf.OfPoint(p_link)
        except Exception:
            p_host = None

        if p_host is None:
            counts['skipped'] += 1
            return

        if grid.is_near(p_host):
            counts['skipped'] += 1
            return

        try:
            inst = placement_engine.place_point_family_instance(doc, symbol, p_host)
        except Exception:
            counts['skipped'] += 1
            return

        if inst is not None:
            set_comments(inst, comment_value)
            grid.add(p_host)
            counts['placed'] += 1
        else:
            counts['skipped'] += 1

    with tx('ЭОМ: Светильники над входами', doc=doc, swallow_warnings=True):
        for lid in level_ids:
            try:
                # Fix: pass DB.ElementId because link_reader expects an object with .IntegerValue
                it = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, limit=scan_limit, level_id=DB.ElementId(lid))
            except Exception:
                it = []

            for door in it:
                _process_door(door)

        if counts['total'] == 0:
            try:
                it = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, limit=scan_limit)
            except Exception:
                it = []
            for door in it:
                _process_door(door)

    output.print_md('Найдено дверей: **{0}**'.format(counts['total']))
    output.print_md('Просканировано дверей: **{0}**'.format(counts['scanned']))
    output.print_md('Дверей с комнатами: **{0}**'.format(counts['with_rooms']))
    output.print_md('Есть сторона внутри: **{0}**'.format(counts['inside_side']))
    output.print_md('Есть сторона снаружи: **{0}**'.format(counts['outside_side']))
    output.print_md('Есть обе стороны: **{0}**'.format(counts['both_sides']))
    output.print_md('Размещено светильников: **{0}**'.format(counts['placed']))
    output.print_md('Пропущено: **{0}**'.format(counts['skipped']))
