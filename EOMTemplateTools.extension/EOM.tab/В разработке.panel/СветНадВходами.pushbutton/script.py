# -*- coding: utf-8 -*-

import math
from pyrevit import DB, revit, script, forms
import config_loader
import link_reader
import placement_engine
from utils_revit import alert, set_comments, tx, trace
from utils_units import mm_to_ft

doc = revit.doc
output = script.get_output()

# --- Constants ---

OUTSIDE_PATTERNS = [u'улиц', u'наруж', u'внеш', u'street', u'outside', u'exterior']
ROOF_PATTERNS = [u'кровл', u'roof']
ENTRANCE_DOOR_PATTERNS = [u'вход', u'входн', u'entry', u'entrance', u'тамбур', u'вестиб']
ROOF_EXIT_DOOR_PATTERNS = [u'кровл', u'roof', u'выход на кровлю']
ENTRANCE_INSIDE_ROOM_PATTERNS = [u'тамбур', u'вестиб', u'холл', u'лестн', u'корид', u'подъезд', u'hall', u'corridor', u'lobby', u'stair', u'тбо']
ENTRANCE_PUBLIC_ROOM_PATTERNS = [u'внеквартир', u'корид', u'холл', u'лестн', u'лифтов', u'тамбур', u'вестиб', u'подъезд', u'тбо', u'lobby', u'stair']
APARTMENT_ROOM_PATTERNS = [u'квартир', u'прихож', u'кухн', u'спальн', u'гостин', u'комнат', u'жил', u'детск', u'кабин', u'клад', u'гардер', u'сан', u'с/у', u'ванн', u'душ', u'wc', u'toilet', u'bath', u'bedroom', u'living']
ENTRANCE_LEVEL_PATTERNS = [u'э1', u'±0.000', u'+0.000', u'0.000', u'перв']


# --- Helper Classes & Functions ---

def norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''

def text_has_any(text, patterns):
    t = norm(text)
    if not t:
        return False
    for p in patterns or []:
        np = norm(p)
        if np and (np in t):
            return True
    return False

class PointGridIndex(object):
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

def door_text(door):
    try:
        nm = getattr(door, 'Name', u'') or u''
    except Exception:
        nm = u''
    mark = get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name='Mark')
    comm = get_param_as_string(door, bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS, name='Comments')
    
    fam_name = u''
    typ_name = u''
    try:
        sym = getattr(door, 'Symbol', None)
        if not sym:
             tid = door.GetTypeId()
             if tid != DB.ElementId.InvalidElementId:
                 sym = door.Document.GetElement(tid)
        if sym:
             fam = getattr(sym, 'Family', None)
             fam_name = getattr(fam, 'Name', u'') if fam else u''
             typ_name = getattr(sym, 'Name', u'') or u''
    except Exception:
        pass
    
    return norm(u'{0} {1} {2} {3} {4}'.format(nm, mark, comm, fam_name, typ_name))

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
    
    # Fallback to current phase properties if phase lookup failed
    try:
        fr = getattr(door, 'FromRoom', None)
        tr = getattr(door, 'ToRoom', None)
        if (fr is not None) or (tr is not None):
            return fr, tr
    except Exception:
        pass
        
    return None, None

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

def is_room_outside(room, outside_patterns, roof_patterns=None):
    if room is None:
        return True # Treat None (void) as outside often
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
    return None

def door_head_z_link(door):
    if door is None:
        return None
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
            # Fallback to approx 2100mm if param missing? No, use Z
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

def score_room_outside_simple(room):
    if room is None:
        return 2
    rn = room_name(room)
    if text_has_any(rn, OUTSIDE_PATTERNS):
        return 2
    if text_has_any(rn, ROOF_PATTERNS):
        return 3
    if text_has_any(rn, ENTRANCE_INSIDE_ROOM_PATTERNS):
        return -1
    return 0

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

def choose_outside_dir_by_probe(door, link_doc, center_pt, normal_xy):
    n = normal_xy
    if center_pt is None or n is None or link_doc is None:
        return None

    ph = get_last_phase(link_doc)
    th = try_get_wall_thickness_ft(door)
    base_eps = mm_to_ft(500) or 1.64
    if th is not None:
        try:
            extra = (float(th) * 0.5) + (mm_to_ft(200) or 0.65)
            if extra > base_eps:
                base_eps = extra
        except Exception:
            pass

    try:
        zprobe = float(center_pt.Z) + (mm_to_ft(1000) or 3.28)
        base = DB.XYZ(float(center_pt.X), float(center_pt.Y), zprobe)
        p_plus = base + (n * float(base_eps))
        p_minus = base + (n * float(-base_eps))
        
        r_plus = try_get_room_at_point(link_doc, p_plus, phase=ph)
        r_minus = try_get_room_at_point(link_doc, p_minus, phase=ph)
        
        sp = score_room_outside_simple(r_plus)
        sm = score_room_outside_simple(r_minus)
        
        if sp > sm:
            return n
        if sm > sp:
            return DB.XYZ(-float(n.X), -float(n.Y), 0.0)
    except Exception:
        pass

    return None

def is_entrance_door(door, link_doc):
    dt = door_text(door)
    # 1. Negative check: If it's an apartment door, skip immediately
    if text_has_any(dt, APARTMENT_ROOM_PATTERNS):
        return False
        
    fr, tr = get_from_to_rooms(door, link_doc)
    
    # If both rooms are missing, we can't determine context -> Skip
    if (fr is None) and (tr is None):
        return False

    # Check properties of rooms
    in_fr = room_matches(fr, ENTRANCE_INSIDE_ROOM_PATTERNS)
    in_tr = room_matches(tr, ENTRANCE_INSIDE_ROOM_PATTERNS)
    
    out_fr = is_room_outside(fr, OUTSIDE_PATTERNS) # True if room is None or named Street
    out_tr = is_room_outside(tr, OUTSIDE_PATTERNS)
    
    # Explicitly check for "Real Room" vs "None/Void"
    has_fr = (fr is not None)
    has_tr = (tr is not None)
    
    # RESIDENTIAL GUARD:
    # If any connected room is clearly residential (Bedroom, Kitchen, Apt), reject.
    if (has_fr and room_matches(fr, APARTMENT_ROOM_PATTERNS)) or \
       (has_tr and room_matches(tr, APARTMENT_ROOM_PATTERNS)):
        return False

    # ONE-SIDED LOGIC (User Request):
    # We want doors where:
    #   Side A = Public Entrance Room (Vestibule, Lobby, Stair)
    #   Side B = None (Void) OR Explicit "Street" room
    
    # Case 1: FromRoom is Entrance, ToRoom is None/Street
    if in_fr and (not has_tr or out_tr):
        return True
        
    # Case 2: ToRoom is Entrance, FromRoom is None/Street
    if in_tr and (not has_fr or out_fr):
        return True

    # Note: We intentionally reject cases where both sides are defined rooms 
    # and neither is explicitly "Street". This kills all internal doors.
    
    return False

def is_roof_exit_door(door, link_doc):
    if text_has_any(door_text(door), ROOF_EXIT_DOOR_PATTERNS):
        return True
    
    fr, tr = get_from_to_rooms(door, link_doc)
    if (fr is None) and (tr is None):
        return False
        
    if room_matches(fr, ROOF_PATTERNS) or room_matches(tr, ROOF_PATTERNS):
        return True
        
    return False

def collect_existing_points(host_doc, comment_tag):
    pts = []
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        rule = DB.FilterStringRule(provider, evaluator, comment_tag) # 2024 API might differ slightly, but this is usually safe
        pfilter = DB.ElementParameterFilter(rule)
        
        col = DB.FilteredElementCollector(host_doc).OfCategory(DB.BuiltInCategory.OST_LightingFixtures).WhereElementIsNotElementType().WherePasses(pfilter)
        for e in col:
            loc = getattr(e, 'Location', None)
            if loc and hasattr(loc, 'Point'):
                pts.append(loc.Point)
    except Exception:
        pass
    return pts


# --- Main ---

def main():
    output.print_md('# Свет над входами (DEBUG)')
    
    # 1. Select Link
    link_inst = link_reader.select_link_instance_auto(doc)
    if not link_inst:
        alert('Связь АР не найдена или не выбрана.')
        return
    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        alert('Не удалось получить документ связи.')
        return

    # 2. Select Levels
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите уровни')
    if not selected_levels:
        return
    level_ids = [l.Id.IntegerValue for l in selected_levels if hasattr(l, 'Id')]

    # 3. Select Family
    symbol = placement_engine.select_family_symbol(
        doc, 
        title='Выберите тип светильника', 
        category_bic=DB.BuiltInCategory.OST_LightingFixtures,
        only_supported=True
    )
    if not symbol:
        return

    # Configuration
    above_offset_mm = 200
    outside_offset_mm = 150
    dedupe_mm = 500
    
    above_offset_ft = mm_to_ft(above_offset_mm)
    outside_offset_ft = mm_to_ft(outside_offset_mm)
    dedupe_ft = mm_to_ft(dedupe_mm)

    comment_tag = 'AUTO_EOM:ENTRANCE_LIGHT'
    existing_pts = collect_existing_points(doc, comment_tag)
    grid = PointGridIndex(dedupe_ft)
    grid.add_many(existing_pts)

    xf = link_inst.GetTotalTransform()
    
    count_placed = 0
    
    with tx('ЭОМ: Светильники над входами', doc=doc):
        # Gather doors
        doors = []
        for lid in level_ids:
            try:
                ds = link_reader.iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, level_id=lid)
                doors.extend(list(ds))
            except Exception:
                pass
        
        for door in doors:
            # Check criteria
            is_roof = is_roof_exit_door(door, link_doc)
            is_ent = is_entrance_door(door, link_doc)
            
            if (not is_roof) and (not is_ent):
                continue
                
            # DEBUG: Print candidate details
            fr_dbg, tr_dbg = get_from_to_rooms(door, link_doc)
            rn_fr = room_name(fr_dbg)
            rn_tr = room_name(tr_dbg)
            dt_dbg = door_text(door)
            output.print_md(u'- ID: `{}` | Type: `{}` | Rooms: `{}` <-> `{}`'.format(door.Id, dt_dbg, rn_fr, rn_tr))

            # Calc position
            c = door_center_point_link(door)
            if not c: continue
            
            z_head = door_head_z_link(door) or c.Z
            
            # Base point above head
            p_link = DB.XYZ(c.X, c.Y, z_head + above_offset_ft)
            
            # Determine outside direction
            normal = try_get_door_facing_xy(door)
            outside_dir = None
            if normal:
                outside_dir = choose_outside_dir_by_probe(door, link_doc, c, normal)
                if not outside_dir:
                    outside_dir = normal
            
            if outside_dir:
                th = try_get_wall_thickness_ft(door) or 0.0
                wall_off = th * 0.5
                p_link = p_link + (outside_dir * (wall_off + outside_offset_ft))
            
            # Transform to host
            p_host = xf.OfPoint(p_link)
            
            if grid.is_near(p_host):
                continue
                
            inst = placement_engine.place_point_family_instance(doc, symbol, p_host)
            if inst:
                set_comments(inst, comment_tag)
                grid.add(p_host)
                count_placed += 1

    output.print_md('Размещено светильников: **{}**'.format(count_placed))

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        alert('Ошибка при выполнении.')
