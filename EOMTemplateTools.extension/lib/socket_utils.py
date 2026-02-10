# -*- coding: utf-8 -*-
import math
import re
from pyrevit import DB, forms, revit, script
import link_reader
import placement_engine
from utils_revit import alert, tx, ensure_symbol_active, set_comments
from utils_units import mm_to_ft

def _is_socket_instance(inst):
    if inst is None or not isinstance(inst, DB.FamilyInstance): return False
    try:
        cat = inst.Category
        if cat:
            cid = int(cat.Id.IntegerValue)
            if cid not in (int(DB.BuiltInCategory.OST_ElectricalFixtures), int(DB.BuiltInCategory.OST_ElectricalEquipment)):
                return False
    except: return False
    # Дополнительно: проверить, является ли это действительно розеткой по имени семейства или параметрам, если необходимо
    return True

def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''

def _norm_type_key(s):
    t = _norm(s)
    if not t: return t
    try:
        for ch in (u'–', u'—', u'‑', u'−'): t = t.replace(ch, u'-')
    except: pass
    try:
        repl = {u'а': u'a', u'в': u'b', u'е': u'e', u'з': u'3', u'к': u'k', u'м': u'm', u'н': u'h', u'о': u'o', u'р': u'p', u'с': u'c', u'т': u't', u'у': u'y', u'х': u'x', u'п': u'n'}
        for k, v in repl.items(): t = t.replace(k, v)
    except: pass
    # Общие смешанные кириллические/латинские варианты в именовании поставщиков
    try:
        t = t.replace(u'р3т', u'p3t')
        t = t.replace(u'рзт', u'p3t')
        t = t.replace(u'розет', u'p3t')
    except: pass
    try:
        t = u' '.join(t.split())
        t = t.replace(u' : ', u':').replace(u' :', u':').replace(u': ', u':')
    except: pass
    try:
        for ch in (u' ', u'\t', u'\r', u'\n', u'-'): t = t.replace(ch, u'_')
        while u'__' in t: t = t.replace(u'__', u'_')
    except: pass
    return t

def _list_loaded_socket_type_labels(doc_, limit=50, scan_cap=15000):
    if doc_ is None: return []
    lim = max(10, int(limit or 50))
    cap = max(lim, int(scan_cap or 15000))
    keys = [u'tsl_ef', u'рзт', u'р3т', u'розет', u'socket', u'outlet']
    seen = set()
    out = []
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=bic, limit=None):
            scanned += 1
            if scanned > cap: break
            try: lbl = placement_engine.format_family_type(s)
            except: lbl = ''
            if not lbl: continue
            t = _norm(lbl)
            if not t: continue
            hit = False
            for k in keys:
                try:
                    if _norm(k) in t: hit = True; break
                except: continue
            if not hit: continue
            if t in seen: continue
            seen.add(t)
            out.append(lbl)
            if len(out) >= lim: break
        if len(out) >= lim: break
    return sorted(out, key=lambda x: _norm(x))

def _compile_patterns(patterns):
    out = []
    for p in (patterns or []):
        try:
            s = (p or u'').strip()
            if s: out.append(re.compile(s, re.IGNORECASE))
        except:
            try:
                s2 = (p or u'').strip()
                if s2: out.append(re.compile(re.escape(s2), re.IGNORECASE))
            except: continue
    return out

def _match_any(rx_list, text):
    t = text or u''
    for rx in rx_list or []:
        try:
            if rx.search(t): return True
        except: continue
    return False

def _get_param_as_string(elem, bip=None, name=None):
    if elem is None: return u''
    p = None
    try:
        if bip: p = elem.get_Parameter(bip)
    except: p = None
    if p is None and name:
        try: p = elem.LookupParameter(name)
        except: p = None
    if p:
        try: return p.AsString() or u''
        except: return u''
    return u''

def _room_text(room):
    if room is None: return u''
    parts = []
    try: parts.append(room.Name)
    except: pass
    parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NAME, name='Name'))
    parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER, name='Number'))
    parts.append(_get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT, name='Department'))
    return u' '.join([p for p in parts if p])


def get_room_apartment_number(room):
    """
    Извлечь номер квартиры из помещения.
    Стратегия:
    1. Проверить параметр 'Квартира' (Явное предпочтительнее).
    2. Проверить 'Department' (BuiltInParameter.ROOM_DEPARTMENT).
    3. Проверить 'Number' (BuiltInParameter.ROOM_NUMBER), разделяя по точке.
    """
    if room is None: return None

    def _is_valid_apt(val):
        if not val: return False
        v = val.strip().lower()
        if not v: return False
        # Отклонить общие слова
        if v in [u'квартира', u'apartment', u'flat', u'room', u'моп']: return False
        # Must contain at least one digit to be a valid apartment number
        return any(c.isdigit() for c in v)

    # 1. 'Квартира' param - HIGHEST PRIORITY
    # (ADSK Standard or explicit override)
    try:
        p = room.LookupParameter(u'Квартира')
        if p:
            val = p.AsString()
            clean_val = _clean_apt_number(val)
            if _is_valid_apt(clean_val):
                return clean_val
    except: pass

    # 2. Department
    try:
        dept = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_DEPARTMENT)
        clean_dept = _clean_apt_number(dept)
        if _is_valid_apt(clean_dept):
            return clean_dept
    except: pass
    
    # 3. Room Number parsing (101.1 -> 101) - FALLBACK
    # Ambiguous: 101.1 (Apt 101) vs 1.102 (Section 1, Room 102)
    # Use only if other methods fail.
    try:
        num = _get_param_as_string(room, bip=DB.BuiltInParameter.ROOM_NUMBER)
        if num:
            parts = num.split('.')
            if len(parts) > 1 and parts[0].isdigit():
                return parts[0]
    except: pass

    return None

def _clean_apt_number(val):
    if not val: return u''
    v = val.strip()
    # Regex to remove "кв." prefix (case insensitive)
    # ^(кв\.?|apt\.?)\s*
    import re
    v = re.sub(r'^(кв\.?|apt\.?|квартира)\s*', '', v, flags=re.IGNORECASE)
    return v.upper()


def _room_is_wc(room, rules=None):
    """Best-effort: определить WC/Санузел по тексту помещения.

    Использует rules['wet_room_name_patterns'] если предоставлено; в противном случае
    использует надежный встроенный набор, который распознает вариации 'Сан. узел'.
    """
    txt = _room_text(room)
    patterns = None
    try:
        patterns = (rules or {}).get('wet_room_name_patterns', None)
    except Exception:
        patterns = None
    if patterns:
        rx = _compile_patterns(patterns)
        if _match_any(rx, txt):
            return True

    # Extra hard-coded variants that are common but NOT covered by 'сануз' substring.
    low = _norm(txt)
    try:
        if (u'сан. уз' in low) or (u'сан уз' in low) or (u'санузел' in low):
            return True
    except Exception:
        pass
    return False

def _select_link_instance_ru(host_doc, title):
    return link_reader.select_link_instance_auto(host_doc)

def _get_all_linked_rooms(link_doc, limit=None, level_ids=None):
    rooms = []
    if link_doc is None: return rooms
    try:
        if level_ids:
            for lid in level_ids:
                it = link_reader.iter_rooms(link_doc, limit=limit, level_id=lid)
                for r in it: rooms.append(r)
        else:
            it = link_reader.iter_rooms(link_doc, limit=limit, level_id=None)
            for r in it: rooms.append(r)
    except: pass
    return rooms

def _room_level_elevation_ft(room, link_doc):
    if room is None or link_doc is None: return 0.0
    try:
        lid = getattr(room, 'LevelId', None)
        if lid and lid != DB.ElementId.InvalidElementId:
            lvl = link_doc.GetElement(lid)
            if lvl and hasattr(lvl, 'Elevation'): return float(lvl.Elevation)
    except: pass
    try:
        loc = getattr(room, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt: return float(pt.Z)
    except: pass
    return 0.0

def _get_room_outer_boundary_segments(room, opts=None):
    if room is None: return None
    try:
        if opts is None: opts = DB.SpatialElementBoundaryOptions()
        seglists = room.GetBoundarySegments(opts)
        if not seglists: return None
        best = None
        best_len = -1.0
        for segs in seglists:
            total = 0.0
            for s in segs:
                c = s.GetCurve()
                if c: total += float(c.Length)
            if total > best_len:
                best = segs
                best_len = total
        return best
    except: return None

def _inst_center_point(inst):
    if inst is None: return None
    try:
        loc = getattr(inst, 'Location', None)
        pt = loc.Point if loc and hasattr(loc, 'Point') else None
        if pt: return pt
    except: pass
    try:
        bb = inst.get_BoundingBox(None)
        if bb: return (bb.Min + bb.Max) * 0.5
    except: pass
    return None

def _door_center_point(door): return _inst_center_point(door)

def _get_comments_text(elem):
    """Get comments text from element (Comments parameter or Mark fallback)."""
    if elem is None:
        return u''
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    for nm in (u'\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438', u'Comments'):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsString()
                if v:
                    return v
        except Exception:
            continue
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p:
            v = p.AsString()
            if v:
                return v
    except Exception:
        pass
    return u''

def _try_get_width_ft(elem, bips=None, names=None):
    if elem is None: return None
    for bip in (bips or []):
        try:
            p = elem.get_Parameter(bip)
            if p:
                v = p.AsDouble()
                if v is not None and float(v) > 1e-6: return float(v)
        except: continue
    for nm in (names or []):
        try:
            p = elem.LookupParameter(nm)
            if p:
                v = p.AsDouble()
                if v is not None and float(v) > 1e-6: return float(v)
        except: continue
    return None

def _fallback_width_from_bbox_ft(inst):
    if inst is None: return None
    try:
        bb = inst.get_BoundingBox(None)
        if not bb: return None
        dx = abs(float(bb.Max.X) - float(bb.Min.X))
        dy = abs(float(bb.Max.Y) - float(bb.Min.Y))
        w = max(dx, dy)
        return float(w) if w > 1e-6 else None
    except: return None

def _get_opening_width_ft(inst, primary_bip=None, fallback_width_mm=None):
    if inst is None: return None
    bips = []
    if primary_bip: bips.append(primary_bip)
    bips.append(DB.BuiltInParameter.FAMILY_WIDTH_PARAM)
    names = [u'Width', u'ширина', u'Ширина']
    w = _try_get_width_ft(inst, bips=bips, names=names)
    if w is not None: return w
    try:
        sym = getattr(inst, 'Symbol', None)
        if sym:
            w = _try_get_width_ft(sym, bips=bips, names=names)
            if w is not None: return w
    except: pass
    w = _fallback_width_from_bbox_ft(inst)
    if w is not None: return w
    if fallback_width_mm: return float(mm_to_ft(fallback_width_mm) or 0.0)
    return None

def _is_curtain_wall(wall):
    if wall is None or not isinstance(wall, DB.Wall): return False
    try:
        wt = getattr(wall, 'WallType', None)
        if wt and getattr(wt, 'Kind', None) == DB.WallKind.Curtain: return True
    except: pass
    try:
        if getattr(wall, 'CurtainGrid', None): return True
    except: pass
    try:
        nm = _norm(getattr(getattr(wall, 'WallType', None), 'Name', '') or '')
        if nm and (u'curtain' in nm or u'витраж' in nm or u'витрин' in nm): return True
    except: pass
    return False

def _get_wall_openings_cached(link_doc, wall, cache):
    if link_doc is None or wall is None or cache is None: return {'doors': [], 'windows': []}
    try: wid = int(wall.Id.IntegerValue)
    except: return {'doors': [], 'windows': []}
    if wid in cache: return cache[wid]
    data = {'doors': [], 'windows': []}
    try: ids = wall.FindInserts(True, True, True, True)
    except: ids = []
    for eid in ids or []:
        e = link_doc.GetElement(eid)
        if not e: continue
        cat = getattr(e, 'Category', None)
        if not cat: continue
        cid = int(cat.Id.IntegerValue)
        pt = _inst_center_point(e)
        if not pt: continue
        if cid == int(DB.BuiltInCategory.OST_Doors):
            w = _get_opening_width_ft(e, primary_bip=DB.BuiltInParameter.DOOR_WIDTH, fallback_width_mm=900)
            data['doors'].append((pt, w))
        elif cid == int(DB.BuiltInCategory.OST_Windows):
            w = _get_opening_width_ft(e, primary_bip=DB.BuiltInParameter.WINDOW_WIDTH, fallback_width_mm=1200)
            data['windows'].append((pt, w))
    cache[wid] = data
    return data

def _project_dist_on_curve_xy_ft(curve, seg_len_ft, pt_xyz, tol_ft, end_extension_ft=None):
    if not curve or not pt_xyz: return None
    try: p = DB.XYZ(float(pt_xyz.X), float(pt_xyz.Y), float(curve.GetEndPoint(0).Z))
    except: return None
    try: ir = curve.Project(p)
    except: return None
    if not ir: return None
    if tol_ft and float(tol_ft) > 1e-9 and ir.Distance > float(tol_ft): return None
    try: norm = curve.ComputeNormalizedParameter(ir.Parameter)
    except:
        # fallback
        try:
            p0, p1 = curve.GetEndParameter(0), curve.GetEndParameter(1)
            norm = (ir.Parameter - p0)/(p1 - p0)
        except: return None
    
    seg_len = float(seg_len_ft or 0.0)
    end_ext = float(end_extension_ft or 0.0)
    if norm < 0.0:
        if end_ext > 1e-9 and (abs(norm)*seg_len) <= end_ext: norm = 0.0
        else: return None
    elif norm > 1.0:
        if end_ext > 1e-9 and ((norm-1.0)*seg_len) <= end_ext: norm = 1.0
        else: return None
    return norm * seg_len

def _merge_intervals(intervals, lo, hi):
    out = []
    if hi <= lo: return out
    cleaned = []
    for a, b in intervals:
        if b < a: a, b = b, a
        if b <= lo or a >= hi: continue
        cleaned.append((max(lo, a), min(hi, b)))
    if not cleaned: return out
    cleaned.sort(key=lambda x: x[0])
    cur_a, cur_b = cleaned[0]
    for a, b in cleaned[1:]:
        if a <= cur_b + 1e-6: cur_b = max(cur_b, b)
        else:
            out.append((cur_a, cur_b))
            cur_a, cur_b = a, b
    out.append((cur_a, cur_b))
    return out

def _invert_intervals(blocked, lo, hi):
    out = []
    cur = lo
    for a, b in blocked:
        if a > cur + 1e-6: out.append((cur, a))
        cur = max(cur, b)
        if cur >= hi - 1e-6: break
    if cur < hi - 1e-6: out.append((cur, hi))
    return out

def _elem_text(e):
    if e is None: return u''
    parts = []
    try: parts.append(getattr(e, 'Name', u'') or u'')
    except: pass
    # Включить марку экземпляра для поддержки коротких меток, таких как "БК", используемых для котлов/приборов.
    try:
        parts.append(_get_param_as_string(e, bip=DB.BuiltInParameter.ALL_MODEL_MARK, name=u'Марка'))
    except: pass
    # Общие общие параметры в русских шаблонах (+ некоторые текстовые/именные параметры, часто используемые в аннотациях)
    for nm in (
        u'ADSK_Марка', u'ADSK_Mark', u'BS_Марка', u'BS_Mark', u'Mark',
        u'Код', u'Code',
        u'Комментарии', u'Comments', u'Описание', u'Description',
        u'Text', u'Текст', u'Text 1', u'Text1', u'Текст 1',
        u'ADSK_Наименование', u'ADSK_Name', u'Наименование', u'Имя', u'Name',
        u'Подпись', u'Label'
    ):
        try:
            v = _get_param_as_string(e, name=nm)
            if v: parts.append(v)
        except Exception:
            pass
    try:
        sym = getattr(e, 'Symbol', None)
        if sym:
            try:
                parts.append(_get_param_as_string(sym, bip=DB.BuiltInParameter.ALL_MODEL_TYPE_MARK, name=u'Марка типоразмера'))
            except: pass
            for nm in (u'ADSK_Марка типоразмера', u'ADSK_TypeMark', u'Type Mark', u'Комментарии типоразмера', u'Type Comments'):
                try:
                    v = _get_param_as_string(sym, name=nm)
                    if v: parts.append(v)
                except Exception:
                    pass
            parts.append(getattr(sym, 'Name', u'') or u'')
            fam = getattr(sym, 'Family', None)
            if fam: parts.append(getattr(fam, 'Name', u'') or u'')
    except: pass
    return _norm(u' '.join([p for p in parts if p]))

def _collect_textnote_points(link_doc, keys):
    pts = []
    if link_doc is None or not keys:
        return pts
    try:
        col = DB.FilteredElementCollector(link_doc).OfClass(DB.TextNote)
        for tn in col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not txt:
                continue
            if not _text_has_any_keyword(txt, keys):
                continue
            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass
    return pts


def _collect_independent_tag_points(link_doc, keys, allowed_bics=None):
    """Собирает точки для элементов IndependentTag, чей TagText соответствует ключам.

    Многие АР-модели размещают марки оборудования, такие как "BK/БК" или "ПС",
    с помощью тегов, а не TextNotes или смоделированных семейств.
    """
    pts = []
    if link_doc is None or not keys:
        return pts

    allowed_ids = None
    try:
        if allowed_bics:
            s = set()
            for bic in (allowed_bics or []):
                try:
                    if bic is None:
                        continue
                    s.add(int(bic))
                except Exception:
                    continue
            if s:
                allowed_ids = s
    except Exception:
        allowed_ids = None

    try:
        col = DB.FilteredElementCollector(link_doc).OfClass(DB.IndependentTag)
    except Exception:
        return pts

    for tag in col:
        try:
            if tag is None:
                continue
            try:
                if hasattr(tag, 'IsValidObject') and (not tag.IsValidObject):
                    continue
            except Exception:
                pass

            if allowed_ids is not None:
                try:
                    cat = getattr(tag, 'Category', None)
                    if not cat:
                        continue
                    if int(cat.Id.IntegerValue) not in allowed_ids:
                        continue
                except Exception:
                    # If we cannot read category, do not filter it out
                    pass

            txt = u''
            try:
                txt = getattr(tag, 'TagText', u'') or u''
            except Exception:
                txt = u''
            if not txt:
                # Some tag families store the visible string in a parameter
                try:
                    txt = _get_param_as_string(tag, name=u'Text')
                except Exception:
                    txt = u''
            if not txt:
                continue
            if not _text_has_any_keyword(txt, keys):
                continue

            pt = None
            # Предпочитать центр элемента, к которому прикреплен тег, если доступен
            # (голова тега может быть перемещена произвольно).
            host_ids = []
            try:
                host_ids = list(tag.GetTaggedLocalElementIds() or [])
            except Exception:
                host_ids = []
            if not host_ids:
                try:
                    hid = getattr(tag, 'TaggedLocalElementId', None)
                    if hid and hid != DB.ElementId.InvalidElementId:
                        host_ids = [hid]
                except Exception:
                    host_ids = []

            for hid in host_ids:
                try:
                    host = link_doc.GetElement(hid)
                except Exception:
                    host = None
                if host is None:
                    continue
                pt = _inst_center_point(host)
                if pt is not None:
                    break

            if pt is None:
                try:
                    pt = getattr(tag, 'TagHeadPosition', None)
                except Exception:
                    pt = None
            if pt is None:
                try:
                    loc = getattr(tag, 'Location', None)
                    pt = loc.Point if loc and hasattr(loc, 'Point') else None
                except Exception:
                    pt = None

            if pt is not None:
                pts.append(pt)
        except Exception:
            continue

    return pts

def _text_has_any_keyword(norm_text, keys):
    try:
        t = _norm(norm_text)
    except Exception:
        t = u''
    if not t: return False
    key_norms = []
    for k in (keys or []):
        nk = _norm(k)
        if nk: key_norms.append(nk)
    if not key_norms: return False

    tokens = None
    for nk in key_norms:
    # Короткие ключи, такие как "bk", должны совпадать как токен (избегать ложных срабатываний, таких как подстроки).
        if len(nk) <= 2:
            if tokens is None:
                try:
                    tokens = re.findall(u'[a-zа-я0-9]+', t)
                except Exception:
                    tokens = []
            if nk in tokens:
                return True
            # Также разрешить шаблоны BK1, BK2 ..., обычно используемые в марках.
            try:
                for tok in tokens:
                    if tok.startswith(nk) and tok[len(nk):].isdigit():
                        return True
            except Exception:
                pass
        else:
            if nk in t:
                return True
    return False

def _collect_points_by_keywords(link_doc, keys, bic):
    pts = []
    if link_doc is None or not keys: return pts
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        for e in col:
            t = _elem_text(e)
            if not t: continue
            if not _text_has_any_keyword(t, keys):
                continue
            pt = _inst_center_point(e)
            if pt: pts.append(pt)
    except: pass
    return pts

def _collect_radiator_points(link_doc):
    pts = []
    if not link_doc: return pts
    keys = [u'радиатор', u'radiator']
    bics = (DB.BuiltInCategory.OST_MechanicalEquipment, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_SpecialityEquipment)
    for bic in bics:
        pts.extend(_collect_points_by_keywords(link_doc, keys, bic))
    return pts

def _collect_sinks_points(link_doc, rules):
    if link_doc is None:
        return []

    strong_keys = rules.get('sink_family_keywords', []) or [
        u'раков', u'умыв', u'мойк', u'sink', u'washbasin', u'basin', u'lavatory'
    ]
    mark_keys = rules.get('sink_mark_keywords', None) or [u'мк', u'mk']
    try:
        if not any((_norm(u'мойк') in _norm(k)) for k in (strong_keys or [])):
            strong_keys = list(strong_keys) + [u'мойк']
    except Exception:
        pass

    pts = []

    # Элементы модели
    bics_model = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
    ]
    # Необязательные категории (избегать жесткой зависимости)
    for nm in ('OST_FoodServiceEquipment',):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                bics_model.append(bic)
        except Exception:
            continue

    for bic in bics_model:
        pts.extend(_collect_points_by_keywords(link_doc, strong_keys, bic))
        # Марки типа "МК" иногда хранятся в Mark/Tag для семейств раковин.
        pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))

    # Аннотационные символы (на основе FamilyInstance). Принимать короткие марки только тогда, когда метка короткая.
    for bic in (DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_DetailComponents):
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                t = _elem_text(e)
            except Exception:
                t = u''
            if not t:
                continue
            ok = False
            try:
                ok = _text_has_any_keyword(t, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    tokens = re.findall(u'[a-zа-я0-9]+', t)
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(t, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue
            try:
                pt = _inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    # TextNotes
    try:
        tn_col = DB.FilteredElementCollector(link_doc).OfClass(DB.TextNote)
        for tn in tn_col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not txt:
                continue

            ok = False
            try:
                ok = _text_has_any_keyword(txt, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    tnorm = _norm(txt)
                    tokens = re.findall(u'[a-zа-я0-9]+', tnorm) if tnorm else []
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(txt, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue

            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_PlumbingFixtureTags',
            'OST_CaseworkTags',
            'OST_GenericModelTags',
            'OST_FurnitureTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=(tag_bics if tag_bics else None))
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts


def _collect_stoves_points(link_doc, rules):
    """Собирает точки электрических плит/варочных панелей в связанном АР.

    Использует как элементы модели, так и аннотации (TextNotes/IndependentTags).
    """
    if link_doc is None:
        return []

    # Сильные ключевые слова, которые, вероятно, появятся в названиях/марках элементов модели.
    strong_keys = (
        rules.get('stove_family_keywords', None)
        or rules.get('stove_keywords', None)
        or [u'плит', u'вароч', u'электроплит', u'варочная', u'cooktop', u'stove', u'oven', u'range', u'hob']
    )

    # Короткие марки на плане, часто используемые в тегах/тексте.
    mark_keys = rules.get('stove_mark_keywords', None) or [u'эп']

    pts = []

    # Элементы модели
    for bic in (
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_ElectricalEquipment,
        DB.BuiltInCategory.OST_ElectricalFixtures,
        DB.BuiltInCategory.OST_PlumbingFixtures,
    ):
        pts.extend(_collect_points_by_keywords(link_doc, strong_keys, bic))
        pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))

    # Аннотационные символы (на основе FamilyInstance). Принимать марки только для коротких меток.
    for bic in (DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_DetailComponents):
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                t = _elem_text(e)
            except Exception:
                t = u''
            if not t:
                continue
            ok = False
            try:
                ok = _text_has_any_keyword(t, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    tokens = re.findall(u'[a-zа-я0-9]+', _norm(t))
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(t, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue
            try:
                pt = _inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    # TextNotes
    try:
        tn_col = DB.FilteredElementCollector(link_doc).OfClass(DB.TextNote)
        for tn in tn_col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not txt:
                continue

            ok = False
            try:
                ok = _text_has_any_keyword(txt, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    tnorm = _norm(txt)
                    tokens = re.findall(u'[a-zа-я0-9]+', tnorm) if tnorm else []
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(txt, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue

            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_MechanicalEquipmentTags',
            'OST_SpecialityEquipmentTags',
            'OST_ElectricalEquipmentTags',
            'OST_ElectricalFixtureTags',
            'OST_FurnitureTags',
            'OST_GenericModelTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=(tag_bics if tag_bics else None))
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts


def _collect_fridges_points(link_doc, rules):
    """Собирает точки холодильников в связанном АР.

    Использует как элементы модели, так и аннотации (TextNotes/IndependentTags).
    """
    if link_doc is None:
        return []

    strong_keys = (
        rules.get('fridge_family_keywords', None)
        or rules.get('fridge_keywords', None)
        or [u'холод', u'холодил', u'fridge', u'refriger', u'refrigerator', u'freezer']
    )

    # Избегать сопоставления коротких марок для холодильников по умолчанию (слишком много ложных срабатываний).
    mark_keys = rules.get('fridge_mark_keywords', None) or []

    pts = []

    bics_model = [
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
    ]
    for nm in ('OST_FoodServiceEquipment',):
        try:
            bic = getattr(DB.BuiltInCategory, nm, None)
            if bic is not None:
                bics_model.append(bic)
        except Exception:
            continue

    for bic in bics_model:
        pts.extend(_collect_points_by_keywords(link_doc, strong_keys, bic))
        if mark_keys:
            pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))

    # Annotation symbols (FamilyInstance-based)
    for bic in (DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_DetailComponents):
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                t = _elem_text(e)
            except Exception:
                t = u''
            if not t:
                continue
            ok = False
            try:
                ok = _text_has_any_keyword(t, strong_keys)
            except Exception:
                ok = False
            if not ok and mark_keys:
                try:
                    tokens = re.findall(u'[a-zа-я0-9]+', _norm(t))
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(t, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue
            try:
                pt = _inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    # TextNotes
    try:
        tn_col = DB.FilteredElementCollector(link_doc).OfClass(DB.TextNote)
        for tn in tn_col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not txt:
                continue
            ok = False
            try:
                ok = _text_has_any_keyword(txt, strong_keys)
            except Exception:
                ok = False
            if not ok and mark_keys:
                try:
                    tnorm = _norm(txt)
                    tokens = re.findall(u'[a-zа-я0-9]+', tnorm) if tnorm else []
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(txt, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue
            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_FurnitureTags',
            'OST_SpecialityEquipmentTags',
            'OST_MechanicalEquipmentTags',
            'OST_GenericModelTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_keys = list(strong_keys or [])
        if mark_keys:
            tag_keys = list(mark_keys or []) + tag_keys
        tag_pts = _collect_independent_tag_points(link_doc, tag_keys, allowed_bics=(tag_bics if tag_bics else None))
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, tag_keys, allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts

def _collect_washing_machines_points(link_doc, rules):
    if link_doc is None:
        return []

    # Сильные ключевые слова, которые, вероятно, появятся в названиях/марках элементов модели.
    strong_keys = rules.get('washing_machine_keywords', []) or [u'стирал', u'washing', u'machine']
    # Короткие марки на плане часто используются в тегах/тексте (избегать сопоставления подстрок; _text_has_any_keyword учитывает токены).
    mark_keys = rules.get('washing_machine_mark_keywords', None) or [u'см', u'wm']

    pts = []

    # Элементы модели
    for bic in (
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
    ):
        pts.extend(_collect_points_by_keywords(link_doc, strong_keys, bic))
        pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))

    # Аннотационные символы (на основе FamilyInstance). Принимать марки только для коротких меток.
    for bic in (DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_DetailComponents):
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            col = None
        if not col:
            continue
        for e in col:
            try:
                t = _elem_text(e)
            except Exception:
                t = u''
            if not t:
                continue
            ok = False
            try:
                ok = _text_has_any_keyword(t, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    tokens = re.findall(u'[a-zа-я0-9]+', t)
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(t, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue
            try:
                pt = _inst_center_point(e)
            except Exception:
                pt = None
            if pt:
                pts.append(pt)

    # TextNotes: принимать сильные ключевые слова; принимать марки только тогда, когда текст представляет собой простую короткую марку (например, "СМ", "СМ1").
    try:
        tn_col = DB.FilteredElementCollector(link_doc).OfClass(DB.TextNote)
        for tn in tn_col:
            try:
                txt = tn.Text
            except Exception:
                txt = u''
            if not txt:
                continue

            ok = False
            try:
                ok = _text_has_any_keyword(txt, strong_keys)
            except Exception:
                ok = False
            if not ok:
                try:
                    # Марки типа "см" неоднозначны в общих примечаниях; принимать только если примечание короткое.
                    tnorm = _norm(txt)
                    tokens = re.findall(u'[a-zа-я0-9]+', tnorm) if tnorm else []
                    if tokens and len(tokens) <= 2 and _text_has_any_keyword(txt, mark_keys):
                        ok = True
                except Exception:
                    ok = False
            if not ok:
                continue

            try:
                pt = tn.Coord
            except Exception:
                pt = None
            if pt:
                pts.append(pt)
    except Exception:
        pass

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_MechanicalEquipmentTags',
            'OST_PlumbingFixtureTags',
            'OST_SpecialityEquipmentTags',
            'OST_GenericModelTags',
            'OST_FurnitureTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=(tag_bics if tag_bics else None))
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, (mark_keys + strong_keys), allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts

def _collect_boilers_points(link_doc):
    # Сильные, однозначные ключевые слова бойлера.
    strong_keys = [
        u'boiler', u'boyler',
        u'water heater', u'waterheater', u'water_heater',
        u'vodonagrevatel', u'водонагреватель', u'водонагрев', u'водонагр', u'водонагрeв',
        u'бойлер'
    ]
    # Короткие марки, такие как BK/БК, неоднозначны в элементах модели (могут появляться на сантехнике),
    # поэтому мы принимаем их только в аннотациях/тексте или в механическом/специальном оборудовании.
    mark_keys = [u'bk', u'бк']

    strong_pts = []
    mark_pts = []
    ann_pts = []

    # Элементы модели by strong keywords.
    for bic in (
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_PipeAccessory,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
    ):
        strong_pts.extend(_collect_points_by_keywords(link_doc, strong_keys, bic))

    # Элементы модели by mark only.
    # Default: exclude PlumbingFixtures to avoid WC false-positives.
    for bic in (
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_PipeAccessory,
    ):
        mark_pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))

    # If we found nothing by strong keywords, allow BK/БК marks in PlumbingFixtures as a fallback.
    if not strong_pts:
        mark_pts.extend(_collect_points_by_keywords(link_doc, mark_keys, DB.BuiltInCategory.OST_PlumbingFixtures))

    # Annotations/text marks (FamilyInstance-based)
    for bic in (DB.BuiltInCategory.OST_GenericAnnotation, DB.BuiltInCategory.OST_DetailComponents):
        ann_pts.extend(_collect_points_by_keywords(link_doc, mark_keys, bic))
    ann_pts.extend(_collect_textnote_points(link_doc, mark_keys))

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_MechanicalEquipmentTags',
            'OST_PlumbingFixtureTags',
            'OST_PipeAccessoryTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_pts = _collect_independent_tag_points(link_doc, mark_keys + strong_keys, allowed_bics=(tag_bics if tag_bics else None))
        # Fallback: some projects use non-standard tag categories; scan all IndependentTags if filtered scan found nothing.
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, mark_keys + strong_keys, allowed_bics=None)
        ann_pts.extend(tag_pts)
    except Exception:
        pass

    return strong_pts + mark_pts + ann_pts

def _collect_towel_rails_points(link_doc):
    # Включает общие аббревиатуры, используемые в планах/тегах: "ПС" (полотенцесушитель).
    keys = [
        u'polotence', u'sushitel', u'towel', u'dryer',
        u'сушител', u'полотенце', u'полотенцесуш',
        u'пс', u'п/с', u'ps'
    ]

    pts = []
    for bic in (
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_PipeAccessory,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_GenericAnnotation,
        DB.BuiltInCategory.OST_DetailComponents,
    ):
        pts.extend(_collect_points_by_keywords(link_doc, keys, bic))

    # Некоторые проекты аннотируют рейки как текст; также поддерживают TextNotes.
    pts.extend(_collect_textnote_points(link_doc, keys))

    # Tags (IndependentTag)
    try:
        tag_bics = []
        for nm in (
            'OST_MechanicalEquipmentTags',
            'OST_PlumbingFixtureTags',
            'OST_PipeAccessoryTags',
            'OST_GenericAnnotation',
        ):
            try:
                bic = getattr(DB.BuiltInCategory, nm, None)
                if bic is not None:
                    tag_bics.append(bic)
            except Exception:
                continue
        tag_pts = _collect_independent_tag_points(link_doc, keys, allowed_bics=(tag_bics if tag_bics else None))
        if (not tag_pts) and tag_bics:
            tag_pts = _collect_independent_tag_points(link_doc, keys, allowed_bics=None)
        pts.extend(tag_pts)
    except Exception:
        pass

    return pts

def _collect_toilets_data(link_doc):
    data = []
    if not link_doc: return data
    
    # Ключевые слова для унитазов (WC)
    keys = [u'унитаз', u'toilet', u'wc', u'closet', u'инсталляция', u'инсталяция']
    bics = [DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel]
    
    for bic in bics:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
            for e in col:
                t = _elem_text(e)
                if not t: continue
                if not any(_norm(k) in t for k in keys): continue
                
                pt = _inst_center_point(e)
                if pt:
                    data.append(pt)
        except: pass
    return data

def _collect_bathtubs_data(link_doc):
    data = []
    if not link_doc: return data
    keys = [u'ванн', u'bath', u'tub', u'jacuzzi', u'джакузи']
    bics = [DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Furniture]
    
    for bic in bics:
        try:
            col = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
            for e in col:
                t = _elem_text(e)
                if not t: continue
                if not any(_norm(k) in t for k in keys): continue
                bb = e.get_BoundingBox(None)
                if bb:
    # Принудительно использовать центр BoundingBox для ванн, так как Точка Вставки часто находится в углу
                    p_center = (bb.Min + bb.Max) * 0.5
                    
                    # Попробовать найти коннектор или специальную точку, указывающую на "головную" (смеситель) сторону.
                    # Соединители MEP являются наиболее надежным способом, если семейства являются MEP.
                    faucet_pt = None
                    try:
                        mep_model = e.MEPModel
                        if mep_model:
                            connectors = mep_model.ConnectorManager.Connectors
                            if connectors:
                                for c in connectors:
                                    # Предположим, что соединитель водоснабжения/канализации находится рядом со смесителем/сливом
                                    # Выбор первого часто достаточен для "односторонних" объектов, таких как ванны
                                    faucet_pt = c.Origin
                                    break
                    except: pass
                    
                    # Если нет коннекторов, проверить, значительно ли точка расположения смещена от центра (часто вставка находится в углу/сливе)
                    if not faucet_pt:
                        try:
                            loc = getattr(e, 'Location', None)
                            loc_pt = loc.Point if loc and hasattr(loc, 'Point') else None
                            if loc_pt:
                                d_from_center = loc_pt.DistanceTo(p_center)
                                # Если точка вставки находится далеко от центра, это может быть угол/сторона слива.
                                # Но точки вставки непоследовательны. Коннекторы лучше.
                                # Сохраним точку вставки как подсказку для отката.
                                faucet_pt = loc_pt
                        except: pass

                    # Хранить: (CenterPoint, BBoxMin, BBoxMax, FaucetHintPoint)
                    data.append((p_center, bb.Min, bb.Max, faucet_pt))
        except: pass
    return data

def _dist_xy(a, b):
    try: return ((float(a.X)-float(b.X))**2 + (float(a.Y)-float(b.Y))**2)**0.5
    except: return 1e9

def _is_near_any_xy(pt, pts, r_ft):
    r = float(r_ft or 0.0)
    if r <= 1e-9: return False
    for p in pts:
        if _dist_xy(pt, p) <= r: return True
    return False

def _is_point_near_rect_xy(pt, r_min, r_max, r_ft):
    try:
        r = float(r_ft or 0.0)
        px, py = float(pt.X), float(pt.Y)
        minx, miny = float(r_min.X), float(r_min.Y)
        maxx, maxy = float(r_max.X), float(r_max.Y)
        dx = max(minx - px, 0.0, px - maxx)
        dy = max(miny - py, 0.0, py - maxy)
        return ((dx*dx + dy*dy)**0.5 <= r)
    except: return False


def _points_in_room(points, room, padding_ft=0.0):
    """Фильтрует точки XYZ, которые попадают внутрь помещения (+ необязательный отступ XY).

    Использует Room.IsPointInRoom, если доступно; в противном случае использует ограничивающую рамку.
    """
    if not points or room is None:
        return []

    pad = float(padding_ft or 0.0)
    out = []

    # Prefer precise test.
    try:
        has_is = hasattr(room, 'IsPointInRoom')
    except Exception:
        has_is = False

    if has_is:
        for p in points:
            if p is None:
                continue
            try:
                if room.IsPointInRoom(p):
                    out.append(p)
                    continue
            except Exception:
                pass
            if pad > 1e-9:
                try:
                    for dx, dy in ((pad, 0.0), (-pad, 0.0), (0.0, pad), (0.0, -pad)):
                        pp = DB.XYZ(float(p.X) + dx, float(p.Y) + dy, float(p.Z))
                        if room.IsPointInRoom(pp):
                            out.append(p)
                            break
                except Exception:
                    pass
        return out

    # Fallback: bounding box.
    try:
        bb = room.get_BoundingBox(None)
    except Exception:
        bb = None
    if not bb:
        return []

    minx = float(bb.Min.X) - pad
    miny = float(bb.Min.Y) - pad
    maxx = float(bb.Max.X) + pad
    maxy = float(bb.Max.Y) + pad

    for p in points:
        if p is None:
            continue
        try:
            x = float(p.X)
            y = float(p.Y)
            if (minx <= x <= maxx) and (miny <= y <= maxy):
                out.append(p)
        except Exception:
            continue
    return out

class _XYZIndex(object):
    def __init__(self, cell_ft):
        self._c = max(1.0, float(cell_ft or 1.0))
        self._grid = {}
    def _key(self, x, y):
        return (int(math.floor(float(x)/self._c)), int(math.floor(float(y)/self._c)))
    def add(self, x, y, z):
        k = self._key(x, y)
        self._grid.setdefault(k, []).append((float(x), float(y), float(z)))
    def has_near(self, x, y, z, r_ft):
        r = float(r_ft or 0.0)
        if r <= 1e-9: return False
        x0, y0, z0 = float(x), float(y), float(z)
        r2 = r*r
        k = self._key(x0, y0)
        for ix in (k[0]-1, k[0], k[0]+1):
            for iy in (k[1]-1, k[1], k[1]+1):
                for (xx, yy, zz) in self._grid.get((ix, iy), []):
                    if ((xx-x0)**2 + (yy-y0)**2 + (zz-z0)**2) <= r2: return True
        return False

def _get_sketchplane_cached(doc_, origin_xyz, normal_xyz, cache):
    if not doc_ or not origin_xyz or not normal_xyz or cache is None: return None
    try:
        n = normal_xyz.Normalize()
        d = n.DotProduct(origin_xyz)
        key = (round(n.X,6), round(n.Y,6), round(n.Z,6), round(d,6))
        if key in cache: return cache[key]
        plane = DB.Plane.CreateByNormalAndOrigin(n, origin_xyz)
        sp = DB.SketchPlane.Create(doc_, plane)
        cache[key] = sp
        return sp
    except: return None

def _rotate_instance_to_xy_dir(inst, origin_xyz, target_dir_xy):
    if not inst or not origin_xyz or not target_dir_xy: return
    try:
        tgt = target_dir_xy.Normalize()
        cur = inst.FacingOrientation.Normalize()
        a0 = math.atan2(cur.Y, cur.X)
        a1 = math.atan2(tgt.Y, tgt.X)
        da = a1 - a0
        axis = DB.Line.CreateBound(origin_xyz, origin_xyz + DB.XYZ.BasisZ)
        inst.Location.Rotate(axis, da)
    except: pass

def _collect_existing_tagged_points(host_doc, tag_value):
    pts = []
    if not host_doc or not tag_value: return pts
    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        rule = DB.FilterStringRule(provider, DB.FilterStringContains(), tag_value) # 2022+ signature might vary
        pfilter = DB.ElementParameterFilter(rule)
        col = DB.FilteredElementCollector(host_doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType().WherePasses(pfilter)
        for e in col:
            pt = _inst_center_point(e)
            if pt: pts.append(pt)
    except: pass
    return pts

def _get_linked_wall_face_ref_and_point(link_wall, link_inst, point_link, faces_cache=None, prefer_n_link=None):
    if not link_wall or not link_inst or not point_link: return None, None, None
    try:
        # Prioritize SideFaces (ShellLayerType) - most robust for hosting
        side_refs = []
        try: side_refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Interior))
        except: pass
        try: side_refs += list(DB.HostObjectUtils.GetSideFaces(link_wall, DB.ShellLayerType.Exterior))
        except: pass
        
        valid_faces = []
        wid = None
        if faces_cache is not None:
            try: wid = int(link_wall.Id.IntegerValue)
            except: wid = None
            if wid is not None:
                try:
                    if wid in faces_cache:
                        valid_faces = faces_cache.get(wid) or []
                except: valid_faces = []
        
        if not valid_faces:
            # 1. Process SideRefs first
            for r in side_refs:
                face = link_wall.GetGeometryObjectFromReference(r)
                if face: valid_faces.append((face, r))
                
            # 2. Fallback to Solid Geometry if SideRefs fail or return nothing
            if not valid_faces:
                try:
                    opt = DB.Options()
                    opt.ComputeReferences = True
                    opt.DetailLevel = DB.ViewDetailLevel.Fine
                    geom = link_wall.get_Geometry(opt)
                    for go in geom:
                        if isinstance(go, DB.Solid):
                            for f in go.Faces:
                                # Filter roughly vertical faces
                                if isinstance(f, DB.PlanarFace):
                                    if abs(f.FaceNormal.Z) < 0.1:
                                        valid_faces.append((f, f.Reference))
                except: pass

            if faces_cache is not None and wid is not None:
                try: faces_cache[wid] = valid_faces
                except: pass

        best_ref, best_d, best_pt, best_face, best_uv = None, None, None, None, None

        # Optional preference: pick the face whose normal aligns with prefer_n_link (XY).
        prefer2 = None
        try:
            if prefer_n_link is not None:
                prefer2 = DB.XYZ(float(prefer_n_link.X), float(prefer_n_link.Y), 0.0)
                prefer2 = prefer2.Normalize() if prefer2.GetLength() > 1e-9 else None
        except:
            prefer2 = None

        def _face_penalty_ft(face_obj):
            if prefer2 is None: return 0.0
            if not isinstance(face_obj, DB.PlanarFace): return 0.0
            try:
                fn = face_obj.FaceNormal
                fn2 = DB.XYZ(float(fn.X), float(fn.Y), 0.0)
                if fn2.GetLength() <= 1e-9: return 0.0
                fn2 = fn2.Normalize()
                dot = float(fn2.DotProduct(prefer2))
                # Strongly penalize faces pointing away from preferred direction.
                return 1000.0 if dot < 0.0 else 0.0
            except:
                return 0.0
        
        # Project logic
        def try_proj_face(f, r, p):
            try: ir = f.Project(p)
            except: ir = None
            if not ir: return None, None, None, None
            uv = getattr(ir, 'UVPoint', None)
            if uv is not None and hasattr(f, 'IsInside'):
                try:
                    if not f.IsInside(uv): return None, None, None, None
                except: pass
            dist = ir.Distance
            xyz = ir.XYZPoint if hasattr(ir, 'XYZPoint') else getattr(ir, 'Point', None)
            return dist, xyz, f, uv

        # Try exact point first
        for face, ref in valid_faces:
            d, pt, f, uv = try_proj_face(face, ref, point_link)
            if d is not None:
                try: score = float(d) + float(_face_penalty_ft(f))
                except: score = d
                if best_d is None or score < best_d:
                    best_d, best_pt, best_face, best_ref, best_uv = score, pt, f, ref, uv
        
        # If fail, try base (1ft above bottom)
        if not best_ref:
             try:
                bbox = link_wall.get_BoundingBox(None)
                if bbox:
                    pt_base = DB.XYZ(point_link.X, point_link.Y, bbox.Min.Z + 1.0)
                    for face, ref in valid_faces:
                        d, pt, f, uv = try_proj_face(face, ref, pt_base)
                        if d is not None:
                            if isinstance(f, DB.PlanarFace):
                                fn = f.FaceNormal
                                v = point_link - f.Origin
                                dist = v.DotProduct(fn)
                                proj_pt = point_link - fn.Multiply(dist)
                                try:
                                    ir2 = f.Project(proj_pt)
                                    uv2 = getattr(ir2, 'UVPoint', None) if ir2 else None
                                    if uv2 is not None and hasattr(f, 'IsInside'):
                                        if not f.IsInside(uv2):
                                            continue
                                except: pass
                                try: score2 = float(abs(dist)) + float(_face_penalty_ft(f))
                                except: score2 = abs(dist)
                                if best_d is None or score2 < best_d:
                                    best_d, best_pt, best_face, best_ref, best_uv = score2, proj_pt, f, ref, uv
             except: pass

        if not best_face: return None, None, None
        
        # Reference recovery
        if not best_ref:
            try: best_ref = best_face.Reference
            except: pass

        # Create Link Reference
        link_ref = None
        if best_ref:
            try: link_ref = DB.Reference.CreateLinkReference(link_inst, best_ref)
            except: 
                try: link_ref = best_ref.CreateLinkReference(link_inst)
                except: pass
        
        # Normal calc
        n = None
        if isinstance(best_face, DB.PlanarFace):
            try: n = best_face.FaceNormal
            except: pass
        if not n and best_uv:
            try: n = best_face.ComputeNormal(best_uv)
            except: pass
        
        # IMPORTANT: Return best_pt even if link_ref is None, so OneLevel placement works correctly
        return link_ref, best_pt, n
    except: return None, None, None


def _collect_host_walls(host_doc, scan_cap=8000):
    walls = []
    if host_doc is None:
        return walls
    try:
        col = DB.FilteredElementCollector(host_doc).OfClass(DB.Wall)
        i = 0
        for w in col:
            i += 1
            if scan_cap and i > int(scan_cap):
                break
            try:
                bb = w.get_BoundingBox(None)
            except Exception:
                bb = None
            walls.append((w, bb))
    except Exception:
        return walls
    return walls


def _nearest_host_wall_to_point(walls_with_bb, pt, max_dist_ft=1.0):
    if not walls_with_bb or not pt:
        return None

    best_w = None
    best_d = None

    for w, bb in walls_with_bb:
        if not w:
            continue

        if bb:
            try:
                if (
                    pt.X < bb.Min.X - max_dist_ft or pt.X > bb.Max.X + max_dist_ft or
                    pt.Y < bb.Min.Y - max_dist_ft or pt.Y > bb.Max.Y + max_dist_ft or
                    pt.Z < bb.Min.Z - max_dist_ft or pt.Z > bb.Max.Z + max_dist_ft
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
        if not c:
            continue

        try:
            p = DB.XYZ(float(pt.X), float(pt.Y), float(c.GetEndPoint(0).Z))
            ir = c.Project(p)
        except Exception:
            ir = None
        if not ir:
            continue

        try:
            proj = ir.XYZPoint
        except Exception:
            proj = None
        if not proj:
            continue

        try:
            d = _dist_xy(proj, pt)
        except Exception:
            continue

        if best_d is None or d < best_d:
            best_d = d
            best_w = w

    if best_w is None or best_d is None:
        return None

    try:
        if float(best_d) > float(max_dist_ft):
            return None
    except Exception:
        pass

    return best_w


def _get_host_wall_face_ref_and_point(host_wall, point_host, prefer_n_host=None):
    if not host_wall or not point_host:
        return None, None, None
    try:
        refs = []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Interior))
        except Exception:
            refs += []
        try:
            refs += list(DB.HostObjectUtils.GetSideFaces(host_wall, DB.ShellLayerType.Exterior))
        except Exception:
            refs += []

        valid_faces = []
        for r in refs:
            try:
                face = host_wall.GetGeometryObjectFromReference(r)
            except Exception:
                face = None
            if face:
                valid_faces.append((face, r))

        if not valid_faces:
            return None, None, None

        prefer2 = None
        try:
            if prefer_n_host is not None:
                prefer2 = DB.XYZ(float(prefer_n_host.X), float(prefer_n_host.Y), 0.0)
                prefer2 = prefer2.Normalize() if prefer2.GetLength() > 1e-9 else None
        except Exception:
            prefer2 = None

        def _face_penalty_ft(face_obj):
            if prefer2 is None:
                return 0.0
            if not isinstance(face_obj, DB.PlanarFace):
                return 0.0
            try:
                fn = face_obj.FaceNormal
                fn2 = DB.XYZ(float(fn.X), float(fn.Y), 0.0)
                if fn2.GetLength() <= 1e-9:
                    return 0.0
                fn2 = fn2.Normalize()
                dotp = abs(fn2.DotProduct(prefer2))
                return (1.0 - dotp) * 3.0
            except Exception:
                return 0.0

        best_ref = None
        best_d = None
        best_pt = None
        best_face = None

        for face, ref in valid_faces:
            try:
                ir = face.Project(point_host)
            except Exception:
                ir = None
            if not ir:
                continue
            try:
                d = float(ir.Distance)
                pt = ir.XYZPoint
            except Exception:
                d = None
                pt = None
            if d is None or pt is None:
                continue
            try:
                score = float(d) + float(_face_penalty_ft(face))
            except Exception:
                score = float(d)
            if best_d is None or score < best_d:
                best_d = score
                best_ref = ref
                best_pt = pt
                best_face = face

        n = None
        if isinstance(best_face, DB.PlanarFace):
            try:
                n = best_face.FaceNormal
            except Exception:
                n = None

        return best_ref, best_pt, n
    except Exception:
        return None, None, None

def _place_socket_batch(host_doc, link_inst, t, batch, sym_flags, sp_cache, comment_value, strict_hosting=False, wall_search_ft=None):
    created = created_face = created_workplane = created_point_on_face = 0
    created_verified = 0 # New counter for "Verified Geometry" placements
    skipped_no_face = skipped_no_place = 0

    faces_cache = {}
    try:
        ws = float(wall_search_ft) if wall_search_ft is not None else float(mm_to_ft(300))
    except Exception:
        ws = float(mm_to_ft(300))
    host_walls = _collect_host_walls(host_doc, scan_cap=8000) if host_doc and strict_hosting else []
    
    if not host_doc or not link_inst or not t or not batch:
        return 0,0,0,0,0,0,0

    with tx('ЭОМ: Разместить розетки (batch)', doc=host_doc, swallow_warnings=True):
        uniq = {}
        for item in (batch or []):
            try:
                s = item[3]
            except Exception:
                s = None
            if s:
                try:
                    uniq[s.Id.IntegerValue] = s
                except Exception:
                    continue
        for s in uniq.values(): ensure_symbol_active(host_doc, s)

        for item in (batch or []):
            item_comment = comment_value
            prefer_n_link = None
            try:
                wall_link, pt_link, wall_dir_link, sym_inst, _seg_len = item[:5]
                try:
                    if len(item) > 5 and item[5]:
                        item_comment = item[5]
                except Exception:
                    item_comment = comment_value
                try:
                    if len(item) > 6:
                        prefer_n_link = item[6]
                except Exception:
                    prefer_n_link = None
            except Exception:
                skipped_no_place += 1
                continue
            if not wall_link or not pt_link or not sym_inst:
                skipped_no_place += 1
                continue
            
            sid = sym_inst.Id.IntegerValue
            is_wp = sym_flags.get(sid, (False, False))[0]
            is_ol = sym_flags.get(sid, (False, False))[1]
            
            inst = None
            # Save the original target Z from pt_link BEFORE any transformations
            # This is critical for low-height placements (e.g., ШДУП at 300mm)
            original_pt_link_z = float(pt_link.Z) if pt_link else None

            link_ref, proj_pt_link, face_n_link = _get_linked_wall_face_ref_and_point(wall_link, link_inst, pt_link, faces_cache=faces_cache, prefer_n_link=prefer_n_link)

    # Если не найдена грань на целевой высоте, попробовать найти на других высотах (для низких размещений, таких как ШДУП на 300 мм)
            # Strategy: find face at higher elevation to confirm wall geometry exists, then use host wall for actual placement
            found_geometry_at_higher_z = False
            if (proj_pt_link is None) and strict_hosting:
                try:
                    for z_probe_mm in (500, 800, 1200, 1500):
                        z_probe_ft = mm_to_ft(z_probe_mm)
                        pt_probe = DB.XYZ(float(pt_link.X), float(pt_link.Y), float(pt_link.Z) + z_probe_ft)
                        lr_probe, pp_probe, nn_probe = _get_linked_wall_face_ref_and_point(wall_link, link_inst, pt_probe, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                        if pp_probe is not None:
                            # Found face at higher elevation - geometry exists
                            # Save the normal, mark as found, but don't use the reference (wrong Z)
                            found_geometry_at_higher_z = True
                            face_n_link = nn_probe
                            # Create a projected point at original Z for verification
                            proj_pt_link = DB.XYZ(float(pp_probe.X), float(pp_probe.Y), float(pt_link.Z))
                            break
                except: pass

            try:
                wd = None
                if wall_dir_link:
                    try: wd = DB.XYZ(float(wall_dir_link.X), float(wall_dir_link.Y), 0.0)
                    except: wd = None
                if wd and wd.GetLength() > 1e-9:
                    wd = wd.Normalize()
                    step_ft = float(mm_to_ft(50) or 0.0)
                    max_ft = float(mm_to_ft(1200) or 0.0)
                    support_half_ft = float(mm_to_ft(200) or 0.0)
                    try:
                        if _seg_len and support_half_ft > 1e-9:
                            support_half_ft = min(support_half_ft, float(_seg_len) * 0.45)
                    except: pass

                    def _solid_at(p):
                        lr0, pp0, nn0 = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                        # If no face at this point, try higher elevations
                        if pp0 is None:
                            try:
                                for z_probe_mm in (500, 800, 1200):
                                    z_probe_ft = mm_to_ft(z_probe_mm)
                                    p_probe = DB.XYZ(float(p.X), float(p.Y), float(p.Z) + z_probe_ft)
                                    lr_pr, pp_pr, nn_pr = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p_probe, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                                    if pp_pr is not None:
                                        lr0 = lr_pr
                                        pp0 = DB.XYZ(float(pp_pr.X), float(pp_pr.Y), float(p.Z))
                                        nn0 = nn_pr
                                        break
                            except: pass
                        if pp0 is None: return None, None, None
                        if support_half_ft > 1e-9:
                            p_a = DB.XYZ(p.X + wd.X * support_half_ft, p.Y + wd.Y * support_half_ft, p.Z)
                            p_b = DB.XYZ(p.X - wd.X * support_half_ft, p.Y - wd.Y * support_half_ft, p.Z)
                            _, pp_a, _ = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p_a, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                            if pp_a is None: return None, None, None
                            _, pp_b, _ = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p_b, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                            if pp_b is None: return None, None, None
                        return lr0, pp0, nn0

                    need = (proj_pt_link is None)
                    if (not need) and support_half_ft > 1e-9:
                        p_a = DB.XYZ(pt_link.X + wd.X * support_half_ft, pt_link.Y + wd.Y * support_half_ft, pt_link.Z)
                        p_b = DB.XYZ(pt_link.X - wd.X * support_half_ft, pt_link.Y - wd.Y * support_half_ft, pt_link.Z)
                        _, pp_a, _ = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p_a, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                        _, pp_b, _ = _get_linked_wall_face_ref_and_point(wall_link, link_inst, p_b, faces_cache=faces_cache, prefer_n_link=prefer_n_link)
                        if pp_a is None or pp_b is None: need = True

                    if need and step_ft > 1e-9 and max_ft > 1e-9:
                        lr0, pp0, nn0 = _solid_at(pt_link)
                        if pp0 is not None:
                            link_ref, proj_pt_link, face_n_link = lr0, pp0, nn0
                        else:
                            steps = int(max(1, math.ceil(max_ft / step_ft)))
                            found = False
                            for i in range(1, steps + 1):
                                off = step_ft * i
                                for sgn in (-1.0, 1.0):
                                    p_try = DB.XYZ(pt_link.X + wd.X * off * sgn, pt_link.Y + wd.Y * off * sgn, pt_link.Z)
                                    lr0, pp0, nn0 = _solid_at(p_try)
                                    if pp0 is not None:
                                        pt_link = p_try
                                        link_ref, proj_pt_link, face_n_link = lr0, pp0, nn0
                                        found = True
                                        break
                                if found: break
            except: pass
            
            # If link_ref failed but we are in strict_hosting, check if proj_pt_link was found (geometry exists)
            # If so, we treat it as "verified" for OneLevel placement purposes.
            pt_host = t.OfPoint(pt_link)
            pt_host_on_face = t.OfPoint(proj_pt_link) if proj_pt_link else pt_host

            # Calculate original target Z in host coordinates
            # Transform the original pt_link Z to host coordinates to get the true target height
            try:
                if original_pt_link_z is not None:
                    # Create a point at original Z in link coords and transform it
                    pt_link_at_original_z = DB.XYZ(float(pt_link.X), float(pt_link.Y), original_pt_link_z)
                    pt_host_at_original_z = t.OfPoint(pt_link_at_original_z)
                    original_target_z = float(pt_host_at_original_z.Z)
                else:
                    original_target_z = float(pt_host_on_face.Z) if pt_host_on_face else None
            except:
                original_target_z = float(pt_host_on_face.Z) if pt_host_on_face else None

            n_link = face_n_link or getattr(wall_link, 'Orientation', None)
            n_host = t.OfVector(n_link) if n_link else None

            host_ref = None
            host_face_pt = None
            host_n = None
            if (not link_ref) and strict_hosting:
                # Try to find host wall face - critical when link face not available
                # This is especially important for low-height placements (e.g., ШДУП at 300mm)
                host_wall = _nearest_host_wall_to_point(host_walls, pt_host_on_face, max_dist_ft=ws)
                if host_wall is not None:
                    hr0, hp0, hn0 = _get_host_wall_face_ref_and_point(host_wall, pt_host_on_face, prefer_n_host=n_host)
                    if hr0 and hp0:
                        host_ref, host_face_pt, host_n = hr0, hp0, hn0
                        pt_host_on_face = host_face_pt
                        if host_n:
                            n_host = host_n
                    # If still not found, try at higher elevations
                    # This is critical for low placements where wall may not have geometry at target height
                    if not hr0:
                        try:
                            for z_probe_mm in (500, 800, 1200, 1500):
                                z_probe_ft = mm_to_ft(z_probe_mm)
                                # Use original_target_z to ensure we always probe from the same base height
                                pt_probe_host = DB.XYZ(float(pt_host_on_face.X), float(pt_host_on_face.Y), float(original_target_z) + z_probe_ft)
                                hr_probe, hp_probe, hn_probe = _get_host_wall_face_ref_and_point(host_wall, pt_probe_host, prefer_n_host=n_host)
                                if hr_probe and hp_probe:
                                    # Found face at higher elevation
                                    # For Face-based families: use the reference directly (Revit will project to face)
                                    # For WorkPlane/OneLevel: project point back to original Z
                                    host_ref = hr_probe
                                    host_n = hn_probe
                                    # Keep original Z but use found X,Y projection
                                    host_face_pt = DB.XYZ(float(hp_probe.X), float(hp_probe.Y), float(original_target_z))
                                    pt_host_on_face = host_face_pt
                                    if host_n:
                                        n_host = host_n
                                    break
                        except: pass

            is_verified = (link_ref is not None) or (host_ref is not None) or (proj_pt_link is not None) or found_geometry_at_higher_z
            
            dir_host = t.OfVector(wall_dir_link) if wall_dir_link else DB.XYZ.BasisX
            if n_host and n_host.GetLength() > 1e-9:
                n = n_host.Normalize()
                comp = n.Multiply(dir_host.DotProduct(n))
                dir_host = dir_host - comp
            dir_host = dir_host.Normalize() if dir_host.GetLength() > 1e-9 else DB.XYZ.BasisX
            
            # 1. Face Hosted (Priority)
            if link_ref:
                try: inst = host_doc.Create.NewFamilyInstance(link_ref, pt_host_on_face, dir_host, sym_inst)
                except Exception as e: 
                    # Try fallback signature
                    try: inst = host_doc.Create.NewFamilyInstance(link_ref, pt_host_on_face, sym_inst)
                    except: pass
                
                if inst: 
                    created_face += 1
                    created_verified += 1
                else:
                    pass

            # 1b. Host wall face when link face ref is missing
            if not inst and host_ref:
                try: inst = host_doc.Create.NewFamilyInstance(host_ref, pt_host_on_face, dir_host, sym_inst)
                except Exception:
                    try: inst = host_doc.Create.NewFamilyInstance(host_ref, pt_host_on_face, sym_inst)
                    except: pass
                if inst:
                    created_face += 1
                    created_verified += 1

            if strict_hosting and (not is_verified):
                skipped_no_face += 1
                skipped_no_place += 1
                continue
            
            # 2. Work Plane (Fallback only if Face Failed AND allowed)
            # Relaxed strict_hosting check: verify geometry (proj_pt_link or link_ref), not just link_ref
            if not inst and (not strict_hosting or is_verified) and is_wp and n_host:
                sp = _get_sketchplane_cached(host_doc, pt_host_on_face, n_host, sp_cache)
                if sp:
                    try: inst = host_doc.Create.NewFamilyInstance(pt_host_on_face, sym_inst, sp, DB.Structure.StructuralType.NonStructural)
                    except:
                        try: inst = host_doc.Create.NewFamilyInstance(pt_host_on_face, sym_inst, sp)
                        except: pass
                    if inst:
                        created_workplane += 1
                        if is_verified: created_verified += 1

            # 2b. OneLevel placement when WorkPlane failed or not supported
            # In strict_hosting mode with verified geometry, try OneLevel as a fallback
            if not inst and (not strict_hosting or is_verified) and is_ol:
                try: inst = placement_engine.place_point_family_instance(host_doc, sym_inst, pt_host_on_face)
                except: inst = None
                if inst:
                    created_point_on_face += 1
                    if is_verified: created_verified += 1
                    if n_host: _rotate_instance_to_xy_dir(inst, pt_host_on_face, n_host)

            # Ensure facing points to the room side: face normal should oppose the wall normal (in host coords)
            # because sockets must be oriented "into" the room, not outwards.
            try:
                if inst is not None and n_host is not None:
                    fo = getattr(inst, 'FacingOrientation', None)
                    if fo is not None:
                        f2 = DB.XYZ(float(fo.X), float(fo.Y), 0.0)
                        n2 = DB.XYZ(float(n_host.X), float(n_host.Y), 0.0)
                        if f2.GetLength() > 1e-9 and n2.GetLength() > 1e-9:
                            f2 = f2.Normalize()
                            n2 = n2.Normalize()
                            # If facing is aligned with wall normal (points out of room), flip.
                            if float(f2.DotProduct(n2)) > 0.2:
                                try:
                                    inst.flipFacing()
                                except Exception:
                                    try:
                                        inst.FacingFlipped = (not bool(getattr(inst, 'FacingFlipped', False)))
                                    except Exception:
                                        pass
            except Exception:
                pass

            if not inst:
                if not is_verified: skipped_no_face += 1
                skipped_no_place += 1
            else:
                # For OneLevelBased families the API overload can ignore the Z of pt_host_on_face.
                # Force the instance to the target height via "Elevation from Level" / offset params.
                try:
                    if is_ol:
                        # Use the original target Z that we saved before any host wall searches
                        target_z = original_target_z if original_target_z is not None else float(getattr(pt_host_on_face, 'Z', None) if pt_host_on_face else None)
                    else:
                        target_z = None
                except Exception:
                    target_z = None

                if target_z is not None:
                    try:
                        lvl = None
                        try:
                            lid = getattr(inst, 'LevelId', None)
                            if lid and lid != DB.ElementId.InvalidElementId:
                                lvl = host_doc.GetElement(lid)
                        except Exception:
                            lvl = None
                        lvl_z = float(getattr(lvl, 'Elevation', None) if lvl else None) if lvl else None
                    except Exception:
                        lvl_z = None

                    if lvl_z is not None:
                        off = float(target_z) - float(lvl_z)
                        set_ok = False
                        # Built-in param
                        try:
                            p = inst.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
                            if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                                p.Set(off)
                                set_ok = True
                        except Exception:
                            set_ok = False
                        # Common localized names
                        if not set_ok:
                            for nm in (
                                u'Отметка от уровня',
                                u'Смещение от уровня',
                                u'Elevation from Level',
                                u'Offset from Level',
                            ):
                                try:
                                    p = inst.LookupParameter(nm)
                                    if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                                        p.Set(off)
                                        set_ok = True
                                        break
                                except Exception:
                                    continue

                        # Last resort: move by Z
                        if not set_ok:
                            try:
                                pt0 = _inst_center_point(inst)
                                if pt0 is not None:
                                    dz = float(target_z) - float(pt0.Z)
                                    if abs(dz) > 1e-6:
                                        DB.ElementTransformUtils.MoveElement(host_doc, inst.Id, DB.XYZ(0.0, 0.0, dz))
                            except Exception:
                                pass

                # Allow callers to pass empty comment_value and only tag via item_comment when provided.
                try:
                    if item_comment is not None and item_comment != u'':
                        set_comments(inst, item_comment)
                except Exception:
                    pass
                created += 1
                
    # Return 7 values now
    return created, created_face, created_workplane, created_point_on_face, skipped_no_face, skipped_no_place, created_verified

SOCKET_STRONG_KEYWORDS = [u'розетка', u'рзт', u'tsl_ef', u'socket', u'outlet']
SOCKET_NEGATIVE_KEYWORDS = [u'свет', u'light', u'выкл', u'switch', u'панель', u'panel']

def _is_wall_or_face_based(symbol):
    try:
        fam = symbol.Family if symbol else None
        pt = fam.FamilyPlacementType if fam else None
        if pt is None: return False
        pt_name = _norm(str(pt))
        # pyRevit/Revit may report placement type as OneLevelBased for many electrical fixture families
        # that are still placeable on faces/work planes via Create family instance APIs.
        return ('wall' in pt_name) or ('face' in pt_name) or ('host' in pt_name) or ('onelevel' in pt_name) or ('workplane' in pt_name)
    except: return False

def _is_supported_socket_placement(symbol):
    if symbol is None: return False
    return _is_wall_or_face_based(symbol)

def _score_socket_symbol(symbol):
    if symbol is None: return -999
    try:
        if not _is_supported_socket_placement(symbol): return -999
    except: return -999
    try: label = placement_engine.format_family_type(symbol)
    except: label = ''
    t = _norm(label)
    if not t: return -999
    score = 0
    if 'eom' in t: score += 20
    for kw in SOCKET_STRONG_KEYWORDS:
        if _norm(kw) in t: score += 40
    for kw in SOCKET_NEGATIVE_KEYWORDS:
        if _norm(kw) in t: score -= 50
    return score

def _find_symbol_by_fullname(doc_, fullname):
    if not fullname: return None
    
    def _find_by_family_name(fam_only, category_bic=None, scan_cap=20000):
        key_fam = _norm_type_key(fam_only)
        if not key_fam: return None
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=category_bic, limit=None):
            scanned += 1
            if scan_cap and scanned > int(scan_cap): break
            try: fam = getattr(getattr(s, 'Family', None), 'Name', u'') or u''
            except: fam = u''
            try:
                if _norm_type_key(fam) == key_fam: return s
            except: continue
        return None

    try:
        if ':' in (fullname or ''):
            parts = [p.strip() for p in (fullname or '').split(':')]
            fam_only = parts[0] if parts else ''
            type_only = u':'.join(parts[1:]).strip() if len(parts) > 1 else ''
            if fam_only and (not type_only):
                for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment, None):
                    sym = _find_by_family_name(fam_only, category_bic=bic, scan_cap=20000)
                    if sym is not None: return sym
    except: pass

    def _find_fuzzy(category_bic=None, scan_cap=20000):
        try: parts = [p.strip() for p in (fullname or u'').split(':')]
        except: parts = [fullname]
        if len(parts) <= 1:
            fam_name, tname = None, fullname
        else:
            fam_name, tname = parts[0], u':'.join(parts[1:]).strip()
        
        key_type = _norm_type_key(tname)
        key_fam = _norm_type_key(fam_name) if fam_name else None
        if not key_type: return None
        
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=category_bic, limit=None):
            scanned += 1
            if scan_cap and scanned > int(scan_cap): break
            try:
                if _norm_type_key(getattr(s, 'Name', u'')) != key_type: continue
            except: continue
            
            if key_fam:
                try:
                    fam = getattr(s, 'Family', None)
                    famn = getattr(fam, 'Name', u'') if fam else u''
                    if _norm_type_key(famn) != key_fam: continue
                except: continue
            return s
        return None

    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment, None):
        try: sym = placement_engine.find_family_symbol(doc_, fullname, category_bic=bic, limit=5000)
        except: sym = None
        if sym: return sym

    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment, None):
        try: sym = _find_fuzzy(category_bic=bic, scan_cap=20000)
        except: sym = None
        if sym: return sym

    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment, None):
        try: sym = _find_by_family_name(fullname, category_bic=bic, scan_cap=20000)
        except: sym = None
        if sym: return sym
    return None

def _auto_pick_socket_symbol(doc_, prefer_fullname=None):
    best = None
    best_score = -9999
    top = []
    scan_cap = 8000
    for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
        scanned = 0
        for s in placement_engine.iter_family_symbols(doc_, category_bic=bic, limit=None):
            scanned += 1
            if scanned > scan_cap: break
            try: sc = _score_socket_symbol(s)
            except: sc = None
            if sc is None: continue
            if prefer_fullname:
                try:
                    if _norm(placement_engine.format_family_type(s)) == _norm(prefer_fullname): sc += 1000
                except: pass
            try: label = placement_engine.format_family_type(s)
            except: label = ''
            if not label: continue
            if best is None or sc > best_score:
                best, best_score = s, sc
            top.append((sc, label))
    top = sorted(top, key=lambda x: (-x[0], _norm(x[1])))
    top_labels = [t[1] for t in top[:10]]
    return best, (placement_engine.format_family_type(best) if best else None), top_labels

def _get_user_config():
    try: return script.get_config()
    except: return None

def _save_user_config():
    try: script.save_config(); return True
    except: return False

def _load_symbol_from_saved_id(doc_, cfg, key):
    if not doc_ or not cfg: return None
    try:
        val = getattr(cfg, key, None)
        if val is None: return None
        e = doc_.GetElement(DB.ElementId(int(val)))
        if e and isinstance(e, DB.FamilySymbol): return e
    except: pass
    return None

def _load_symbol_from_saved_unique_id(doc_, cfg, key):
    if not doc_ or not cfg: return None
    try:
        uid = getattr(cfg, key, None)
        if not uid: return None
        e = doc_.GetElement(str(uid))
        if e and isinstance(e, DB.FamilySymbol): return e
    except: pass
    return None

def _store_symbol_id(cfg, key, symbol):
    if not cfg or not symbol: return
    try: setattr(cfg, key, int(symbol.Id.IntegerValue))
    except: pass

def _store_symbol_unique_id(cfg, key, symbol):
    if not cfg or not symbol: return
    try: setattr(cfg, key, str(symbol.UniqueId))
    except: pass

def _pick_socket_symbol(doc_, cfg, fullname, cache_prefix='socket_general'):
    def _symbol_matches_fullname(sym, want_fullname):
        if not sym or not want_fullname: return False
        try: want = _norm(want_fullname)
        except: want = ''
        if not want: return False
        try: lbl = _norm(placement_engine.format_family_type(sym))
        except: lbl = ''
        has_colon = (':' in (want_fullname or ''))
        if has_colon: return (lbl == want)
        try:
            if _norm(getattr(sym, 'Name', '')) == want: return True
        except: pass
        try:
            fam = getattr(sym, 'Family', None)
            if fam and _norm(getattr(fam, 'Name', '')) == want: return True
        except: pass
        try:
            if lbl:
                t = _norm(lbl.split(':')[-1].strip())
                if t == want: return True
        except: pass
        return False

    def _cache_keys(prefix):
        p = (prefix or '').strip()
        if p == 'socket_general': return 'last_socket_general_symbol_uid', 'last_socket_general_symbol_id'
        if not p: p = 'socket'
        return 'last_{0}_symbol_uid'.format(p), 'last_{0}_symbol_id'.format(p)

    key_uid, key_id = _cache_keys(cache_prefix)

    def _try_pick_from_cache():
        sym = _load_symbol_from_saved_unique_id(doc_, cfg, key_uid)
        if not sym: sym = _load_symbol_from_saved_id(doc_, cfg, key_id)
        return sym

    prefer_fullnames = []
    try:
        if isinstance(fullname, (list, tuple)): prefer_fullnames = [x for x in fullname if x]
        elif fullname: prefer_fullnames = [fullname]
    except: prefer_fullnames = [fullname] if fullname else []

    if prefer_fullnames:
        for want in prefer_fullnames:
            sym_cfg = _find_symbol_by_fullname(doc_, want)
            if sym_cfg:
                try:
                    if not _is_supported_socket_placement(sym_cfg):
                        continue
                except Exception:
                    continue
                try: return sym_cfg, placement_engine.format_family_type(sym_cfg), []
                except: return sym_cfg, None, []
        
        sym_cache = _try_pick_from_cache()
        if sym_cache:
            try:
                if not _is_supported_socket_placement(sym_cache):
                    sym_cache = None
                for want in prefer_fullnames:
                    if _symbol_matches_fullname(sym_cache, want):
                        try: return sym_cache, placement_engine.format_family_type(sym_cache), []
                        except: return sym_cache, None, []
            except: pass
        
        _sym_auto, _lbl_auto, top10 = _auto_pick_socket_symbol(doc_, prefer_fullname=None)
        return None, None, top10

    sym = _try_pick_from_cache()
    if sym:
        try: return sym, placement_engine.format_family_type(sym), []
        except: return sym, None, []

    return _auto_pick_socket_symbol(doc_, prefer_fullname=None)
