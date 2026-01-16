# -*- coding: utf-8 -*-

import math

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception, set_comments, tx, trace
from utils_units import mm_to_ft


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


OUTSIDE_DEFAULT_PATTERNS = [
    u'улиц', u'наруж', u'внеш', u'street', u'outside', u'exterior'
]

ROOF_DEFAULT_PATTERNS = [
    u'кровл', u'roof'
]

ENTRANCE_DOOR_DEFAULT_PATTERNS = [
    u'вход', u'входн', u'entry', u'entrance', u'тамбур', u'вестиб'
]

ROOF_EXIT_DOOR_DEFAULT_PATTERNS = [
    u'кровл', u'roof', u'выход на кровлю'
]

ENTRANCE_INSIDE_ROOM_DEFAULT_PATTERNS = [
    u'тамбур', u'вестиб', u'холл', u'лестн', u'корид', u'подъезд',
    u'hall', u'corridor', u'lobby', u'stair', u'тбо'
]

ENTRANCE_PUBLIC_ROOM_DEFAULT_PATTERNS = [
    u'внеквартир', u'корид', u'холл', u'лестн', u'лифтов', u'тамбур',
    u'вестиб', u'подъезд', u'тбо', u'lobby', u'stair'
]

APARTMENT_ROOM_DEFAULT_PATTERNS = [
    u'квартир', u'прихож', u'кухн', u'спальн', u'гостин', u'комнат',
    u'жил', u'детск', u'кабин', u'клад', u'гардер', u'сан', u'с/у',
    u'ванн', u'душ', u'wc', u'toilet', u'bath', u'bedroom', u'living'
]

ENTRANCE_LEVEL_DEFAULT_PATTERNS = [
    u'э1', u'±0.000', u'+0.000', u'0.000', u'перв'
]


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


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _text_has_any(text, patterns):
    t = _norm(text)
    if not t:
        return False
    for p in patterns or []:
        np = _norm(p)
        if np and (np in t):
            return True
    return False


def _get_param_as_string(elem, bip=None, name=None):
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


def _door_family_type_text(door):
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

    return _norm(u'{0} {1}'.format(fam_name, typ_name))


def _door_text(door):
    try:
        nm = getattr(door, 'Name', u'') or u''
    except Exception:
        nm = u''
    mark = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name='Mark')
    comm = _get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name='Comments')
    ft = _door_family_type_text(door)
    return _norm(u'{0} {1} {2} {3}'.format(nm, mark, comm, ft))


def _get_last_phase(doc_):
    try:
        phases = list(doc_.Phases)
        return phases[-1] if phases else None
    except Exception:
        return None


def _get_from_to_rooms(door, link_doc):
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

    # Fallback: try non-phase properties (some links/rooms do not bind by phase).
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


def _room_name(room):
    if room is None:
        return u''
    try:
        name = getattr(room, 'Name', u'')
        if name:
            return _norm(name)
    except Exception:
        pass
    try:
        p = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        if p:
            return _norm(p.AsString())
    except Exception:
        pass
    return u''


def _room_matches(room, patterns):
    return _text_has_any(_room_name(room), patterns)


def _is_public_room(room, public_patterns):
    return _room_matches(room, public_patterns)


def _is_apartment_room(room, apt_patterns):
    return _room_matches(room, apt_patterns)


def _is_room_outside(room, outside_patterns, roof_patterns=None):
    if room is None:
        return True
    if _room_matches(room, outside_patterns):
        return True
    if roof_patterns and _room_matches(room, roof_patterns):
        return True
    return False


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


def _door_level_name(door, link_doc):
    if door is None or link_doc is None:
        return u''
    try:
        lvl = link_doc.GetElement(door.LevelId)
    except Exception:
        lvl = None
    try:
        return _norm(getattr(lvl, 'Name', u'')) if lvl is not None else u''
    except Exception:
        return u''


def _door_head_z_link(door):
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


def _try_get_door_facing_xy(door):
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


def _score_room_outside(room, outside_patterns, inside_patterns, roof_patterns=None):
    score = 0
    if room is None:
        score += 2
    if _room_matches(room, outside_patterns):
        score += 2
    if roof_patterns and _room_matches(room, roof_patterns):
        score += 3
    if _room_matches(room, inside_patterns):
        score -= 1
    return score


def _choose_outside_dir_by_probe(door, link_doc, center_pt, normal_xy, outside_patterns, inside_patterns, roof_patterns=None):
    n = normal_xy
    if center_pt is None or n is None or link_doc is None:
        return None

    ph = _get_last_phase(link_doc)
    th = _try_get_wall_thickness_ft(door)
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
        r_plus = _try_get_room_at_point(link_doc, p_plus, phase=ph)
        r_minus = _try_get_room_at_point(link_doc, p_minus, phase=ph)
        sp = _score_room_outside(r_plus, outside_patterns, inside_patterns, roof_patterns=roof_patterns)
        sm = _score_room_outside(r_minus, outside_patterns, inside_patterns, roof_patterns=roof_patterns)
        if sp > sm:
            return n
        if sm > sp:
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)

        if _is_room_outside(r_plus, outside_patterns, roof_patterns=roof_patterns) and (not _is_room_outside(r_minus, outside_patterns, roof_patterns=roof_patterns)):
            return n
        if _is_room_outside(r_minus, outside_patterns, roof_patterns=roof_patterns) and (not _is_room_outside(r_plus, outside_patterns, roof_patterns=roof_patterns)):
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)
    except Exception:
        pass

    return None


def _collect_existing_tagged_points(host_doc, tag):
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


class _PointGridIndex(object):
    def __init__(self, radius_ft):
        self.r = float(radius_ft or 0.0)
        self.r2 = self.r * self.r
        self.cell = self.r if self.r > 1e-9 else 1.0
        self._grid = {}

    def _key(self, p):
        try:
            return (
                int(math.floor(float(p.X) / self.cell)),
                int(math.floor(float(p.Y) / self.cell)),
                int(math.floor(float(p.Z) / self.cell)),
            )
        except Exception:
            return (0, 0, 0)

    def add(self, p):
        if p is None:
            return
        k = self._key(p)
        bucket = self._grid.get(k)
        if bucket is None:
            bucket = []
            self._grid[k] = bucket
        bucket.append(p)

    def add_many(self, pts):
        for p in pts or []:
            self.add(p)

    def is_near(self, p):
        if p is None or self.r <= 1e-9:
            return False
        k = self._key(p)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    kk = (k[0] + dx, k[1] + dy, k[2] + dz)
                    bucket = self._grid.get(kk)
                    if not bucket:
                        continue
                    for q in bucket:
                        try:
                            if float(p.DistanceTo(q)) <= self.r:
                                return True
                        except Exception:
                            continue
        return False


LIGHT_STRONG_KEYWORDS = [u'свет', u'light', u'lighting', u'светиль', u'lamp', u'lum']
LIGHT_EXTERIOR_KEYWORDS = [u'наруж', u'outdoor', u'exterior', u'фасад', u'wall']
LIGHT_NEGATIVE_KEYWORDS = [u'авар', u'emerg', u'emergency', u'exit', u'табло', u'указ', u'эвак']


def _score_light_symbol(symbol):
    try:
        label = placement_engine.format_family_type(symbol)
    except Exception:
        label = ''
    t = _norm(label)
    if not t:
        return -999

    score = 0
    if 'eom' in t:
        score += 10

    for kw in LIGHT_STRONG_KEYWORDS:
        if _norm(kw) in t:
            score += 20
    for kw in LIGHT_EXTERIOR_KEYWORDS:
        if _norm(kw) in t:
            score += 15
    for kw in LIGHT_NEGATIVE_KEYWORDS:
        if _norm(kw) in t:
            score -= 80

    return score


def _auto_pick_light_symbol(doc_, prefer_fullname=None):
    prefer = _norm(prefer_fullname)
    ranked = []
    scan_cap = 2000
    for s in placement_engine.iter_family_symbols(doc_, category_bic=DB.BuiltInCategory.OST_LightingFixtures, limit=scan_cap):
        try:
            if not placement_engine.is_supported_point_placement(s):
                continue
            lbl = placement_engine.format_family_type(s)
            if not lbl:
                continue
            sc = _score_light_symbol(s)
            if prefer and _norm(lbl) == prefer:
                sc += 1000
            ranked.append((sc, lbl, s))
        except Exception:
            continue

    if not ranked:
        return None, None, []

    ranked.sort(key=lambda x: (x[0], _norm(x[1])), reverse=True)
    best = ranked[0]
    return best[2], best[1], [r[1] for r in ranked[:10]]


def _pick_light_symbol(doc_, cfg, fullname=None):
    sym = None
    try:
        sym = _load_symbol_from_saved_unique_id(doc_, cfg, 'last_light_entrance_symbol_uid')
    except Exception:
        sym = None
    if sym is None:
        try:
            sym = _load_symbol_from_saved_id(doc_, cfg, 'last_light_entrance_symbol_id')
        except Exception:
            sym = None

    if sym is not None:
        try:
            if placement_engine.is_supported_point_placement(sym):
                return sym, placement_engine.format_family_type(sym), []
        except Exception:
            sym = None

    if fullname:
        try:
            sym = placement_engine.find_family_symbol(doc_, fullname, category_bic=DB.BuiltInCategory.OST_LightingFixtures, limit=5000)
        except Exception:
            sym = None
        if sym is not None:
            try:
                if placement_engine.is_supported_point_placement(sym):
                    return sym, placement_engine.format_family_type(sym), []
            except Exception:
                sym = None

    sym, picked_label, top10 = _auto_pick_light_symbol(doc_, prefer_fullname=fullname)
    if sym is not None:
        return sym, picked_label, top10

    sym = placement_engine.select_family_symbol(
        doc_,
        title='Выберите тип светильника (входы/кровля)',
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=True,
        allow_none=True,
        button_name='Выбрать',
        limit=200,
        scan_cap=5000
    )
    if sym is None:
        return None, None, []
    return sym, placement_engine.format_family_type(sym), []


def _door_matches_patterns(door, patterns):
    return _text_has_any(_door_text(door), patterns)


def _is_entrance_door(door, link_doc, entrance_patterns, outside_patterns, inside_patterns, public_room_patterns, apartment_room_patterns, entry_level_patterns):
    if _door_matches_patterns(door, entrance_patterns):
        return True

    fr, tr = _get_from_to_rooms(door, link_doc)
    if (fr is None) and (tr is None):
        return False

    if (fr is None) or (tr is None):
        room = fr if fr is not None else tr
        if _room_matches(room, inside_patterns):
            return True

    outside_side = _is_room_outside(fr, outside_patterns) or _is_room_outside(tr, outside_patterns)
    inside_side = _room_matches(fr, inside_patterns) or _room_matches(tr, inside_patterns)

    public_side = _is_public_room(fr, public_room_patterns) or _is_public_room(tr, public_room_patterns)
    apt_fr = _is_apartment_room(fr, apartment_room_patterns)
    apt_tr = _is_apartment_room(tr, apartment_room_patterns)

    if apt_fr and apt_tr:
        return False

    if outside_side and inside_side and public_side:
        return True

    return False


def _is_roof_exit_door(door, link_doc, roof_patterns, roof_room_patterns):
    if _door_matches_patterns(door, roof_patterns):
        return True

    fr, tr = _get_from_to_rooms(door, link_doc)
    if (fr is None) and (tr is None):
        return False

    return bool(_room_matches(fr, roof_room_patterns) or _room_matches(tr, roof_room_patterns))


def main():
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

    link_inst = _select_link_instance_ru(doc, title='Выберите связь АР')
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

    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни для обработки')
    if not selected_levels:
        output.print_md('**Отменено (уровни не выбраны).**')
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

    cfg = _get_user_config()
    symbol, picked_label, _ = _pick_light_symbol(doc, cfg, fam_entrance)
    if symbol is None:
        alert('Не найден подходящий тип светильника. Загрузите семейство и повторите.')
        return

    try:
        _store_symbol_id(cfg, 'last_light_entrance_symbol_id', symbol)
        _store_symbol_unique_id(cfg, 'last_light_entrance_symbol_uid', symbol)
        _save_user_config()
    except Exception:
        pass

    comment_value = '{0}:LIGHT_ENTRANCE_DOOR'.format(comment_tag)
    existing_pts = _collect_existing_tagged_points(doc, comment_value)
    grid = _PointGridIndex(dedupe_ft)
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

    def _process_door(door):
        try:
            if door is None or (hasattr(door, 'IsValidObject') and (not door.IsValidObject)):
                return
        except Exception:
            return

        counts['scanned'] += 1
        try:
            fr_dbg, tr_dbg = _get_from_to_rooms(door, link_doc)
            if (fr_dbg is not None) or (tr_dbg is not None):
                counts['with_rooms'] += 1
            inside_side_dbg = _room_matches(fr_dbg, inside_room_patterns) or _room_matches(tr_dbg, inside_room_patterns)
            outside_side_dbg = _is_room_outside(fr_dbg, outside_room_patterns) or _is_room_outside(tr_dbg, outside_room_patterns)
            if inside_side_dbg:
                counts['inside_side'] += 1
            if outside_side_dbg:
                counts['outside_side'] += 1
            if inside_side_dbg and outside_side_dbg:
                counts['both_sides'] += 1
        except Exception:
            pass

        is_roof = _is_roof_exit_door(door, link_doc, roof_exit_patterns, roof_room_patterns)
        is_entrance = _is_entrance_door(
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

        counts['total'] += 1
        c = _door_center_point_link(door)
        if c is None:
            counts['skipped'] += 1
            return

        z_head = _door_head_z_link(door)
        if z_head is None:
            z_head = float(c.Z)

        p_link = DB.XYZ(float(c.X), float(c.Y), float(z_head) + float(above_offset_ft))
        normal = _try_get_door_facing_xy(door)
        outside_dir = None
        if normal is not None:
            outside_dir = _choose_outside_dir_by_probe(
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
                th = _try_get_wall_thickness_ft(door)
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
                it = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, limit=scan_limit, level_id=lid)
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


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Place_Lights_EntranceDoors: error')
        alert('Ошибка. Подробности см. в журнале.')
