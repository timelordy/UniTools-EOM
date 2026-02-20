# -*- coding: utf-8 -*-

import heapq
import math

from pyrevit import DB
from pyrevit import forms
import magic_context


def _magic_active():
    try:
        return bool(magic_context.IS_RUNNING or getattr(magic_context, 'FORCE_SELECTION', False))
    except Exception:
        return False

def list_link_instances(doc):
    return list(DB.FilteredElementCollector(doc)
                .OfClass(DB.RevitLinkInstance)
                .WhereElementIsNotElementType()
                .ToElements())


def is_link_loaded(link_instance):
    try:
        return link_instance.GetLinkDocument() is not None
    except Exception:
        return False


def get_link_doc(link_instance):
    try:
        return link_instance.GetLinkDocument()
    except Exception:
        return None


def get_total_transform(link_instance):
    try:
        t = link_instance.GetTotalTransform()
        return t if t else DB.Transform.Identity
    except Exception:
        return DB.Transform.Identity


def _norm_key(value):
    try:
        import floor_panel_niches as fpn
        return fpn.normalize_type_key(value)
    except Exception:
        try:
            v = (value or u"")
            return u" ".join(v.lower().split())
        except Exception:
            return u""


def _split_family_type(name):
    if not name:
        return None, None
    try:
        cleaned = u" ".join((name or u"").replace(u":", u" : ").split())
        parts = [p.strip() for p in cleaned.split(u" : ")]
        if len(parts) == 1:
            return None, parts[0]
        fam = parts[0] or None
        tname = u" : ".join(parts[1:]).strip()
        return fam, tname
    except Exception:
        return None, name


def _get_symbol_type_name(sym):
    if sym is None:
        return u""

    try:
        n = getattr(sym, "Name", None) or u""
        if n:
            return n
    except Exception:
        pass

    try:
        name_getter = getattr(DB.Element, 'Name', None)
    except Exception:
        name_getter = None
    if name_getter is not None:
        try:
            n = name_getter.GetValue(sym) or u""
            if n:
                return n
        except Exception:
            pass

    try:
        p = sym.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    except Exception:
        p = None
    if p is not None:
        try:
            n = p.AsString() or p.AsValueString() or u""
            if n:
                return n
        except Exception:
            pass

    for pname in ("Type Name", u"Имя типа"):
        try:
            p2 = sym.LookupParameter(pname)
            if p2 is None:
                continue
            n = p2.AsString() or p2.AsValueString() or u""
            if n:
                return n
        except Exception:
            continue

    return u""


def iter_family_instances_by_family_type(doc, family_type_names=None, limit=None):
    """Возвращает FamilyInstance в документе, соответствующий нормализованным правилам 'Family : Type' или 'Type'."""
    if doc is None:
        return

    names = list(family_type_names or [])
    if not names:
        return

    wanted = []
    for n in names:
        fam, typ = _split_family_type(n)
        wanted.append((_norm_key(fam) if fam else None, _norm_key(typ or n)))

    lim = None
    try:
        if limit is not None:
            lim = int(limit)
    except Exception:
        lim = None

    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()
        i = 0
        for inst in col:
            try:
                sym = getattr(inst, 'Symbol', None)
                if sym is None:
                    continue

                try:
                    inst_type = _norm_key(_get_symbol_type_name(sym) or u"")
                except Exception:
                    inst_type = u""
                if not inst_type:
                    continue

                try:
                    inst_fam = _norm_key(getattr(sym, 'FamilyName', None) or getattr(sym.Family, 'Name', None) or u"")
                except Exception:
                    inst_fam = u""

                ok = False
                for wfam, wtyp in wanted:
                    if wtyp and (inst_type == wtyp or (wtyp in inst_type) or (inst_type in wtyp)):
                        if wfam:
                            if inst_fam == wfam:
                                ok = True
                                break
                        else:
                            ok = True
                            break
                if not ok:
                    continue

                yield inst
                i += 1
                if lim is not None and i >= lim:
                    break
            except Exception:
                continue
    except Exception:
        return


def try_get_instance_closed_contour_xy(inst, min_points=3):
    """Оптимальное усилие: возвращает список точек DB.XYZ (замкнутый контур, последняя точка не повторяется) в координатах экземпляра.

    Источники:
    - если экземпляр основан на линии (LocationCurve): использовать тесселяцию кривой как контур (редко)
    - в противном случае: None (заполнитель для более надежного извлечения позже)
    """
    if inst is None:
        return None

    loc = getattr(inst, 'Location', None)
    curve = getattr(loc, 'Curve', None) if loc else None
    if curve is None:
        return None

    try:
        pts = list(curve.Tessellate())
    except Exception:
        pts = None
    if not pts or len(pts) < int(min_points or 3):
        return None

    # Ensure we have a closed loop; if not, don't pretend.
    try:
        if pts[0].DistanceTo(pts[-1]) > 1e-6:
            return None
    except Exception:
        return None

    try:
        return pts[:-1]
    except Exception:
        return None


def get_instance_fallback_point(inst):
    if inst is None:
        return None

    loc = getattr(inst, 'Location', None)
    pt = getattr(loc, 'Point', None) if loc else None
    if pt:
        return pt

    try:
        bb = inst.get_BoundingBox(None)
        if not bb:
            return None
        return DB.XYZ(
            (float(bb.Min.X) + float(bb.Max.X)) / 2.0,
            (float(bb.Min.Y) + float(bb.Max.Y)) / 2.0,
            (float(bb.Min.Z) + float(bb.Max.Z)) / 2.0,
        )
    except Exception:
        return None


def try_get_link_path(host_doc, link_instance):
    """Оптимальное усилие: возвращает видимый пользователю путь для связи, или None."""
    try:
        link_type = host_doc.GetElement(link_instance.GetTypeId())
        if link_type is None:
            return None

        extref = DB.ExternalFileUtils.GetExternalFileReference(host_doc, link_type.Id)
        if extref is None:
            return None

        mp = extref.GetPath()
        if mp is None:
            return None

        return DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(mp)
    except Exception:
        return None


def get_rooms(link_doc):
    if link_doc is None:
        return []
    try:
        return list(DB.FilteredElementCollector(link_doc)
                    .OfCategory(DB.BuiltInCategory.OST_Rooms)
                    .WhereElementIsNotElementType()
                    .ToElements())
    except Exception:
        return []


def list_levels(doc):
    if doc is None:
        return []
    try:
        return list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements())
    except Exception:
        return []


def select_level(doc, title='Select Level', allow_none=True):
    # Проверка Magic Button
    if _magic_active() and magic_context.SELECTED_LEVELS:
        return magic_context.SELECTED_LEVELS[0]

    lvls = list_levels(doc)
    if not lvls:
        return None

    items = []
    for l in lvls:
        try:
            items.append((u'{0}  (elev={1:.2f}ft)'.format(l.Name, float(l.Elevation)), l))
        except Exception:
            items.append((u'{0}'.format(getattr(l, 'Name', 'Level')), l))

    items = sorted(items, key=lambda x: x[0].lower())
    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=False,
        button_name='Select',
        allow_none=allow_none
    )
    if not picked:
        return None

    for lbl, lvl in items:
        if lbl == picked:
            return lvl
    return None


def select_levels_multi(doc, title='Select Levels (Multi)', default_all=False):
    """Select multiple levels from doc using SelectFromList."""
    # Проверка Magic Button
    if _magic_active() and magic_context.SELECTED_LEVELS:
        return list(magic_context.SELECTED_LEVELS)

    lvls = list_levels(doc)
    if not lvls:
        return []

    if default_all:
        return list(lvls)

    items = []
    for l in lvls:
        try:
            items.append((u'{0}  (elev={1:.2f}ft)'.format(l.Name, float(l.Elevation)), l))
        except Exception:
            items.append((u'{0}'.format(getattr(l, 'Name', 'Level')), l))

    items = sorted(items, key=lambda x: x[0].lower())

    picked = forms.SelectFromList.show(
        [x[0] for x in items],
        title=title,
        multiselect=True,
        button_name='Select'
    )

    if not picked:
        return []

    selected_levels = []
    for p in picked:
        for lbl, lvl in items:
            if lbl == p:
                selected_levels.append(lvl)
                break
    
    return selected_levels


def select_link_instance_auto(host_doc):
    """Автоматический выбор первого загруженного экземпляра связи или первого доступного, если ни один не загружен."""
    # Проверка Magic Button
    if _magic_active() and magic_context.SELECTED_LINK:
        return magic_context.SELECTED_LINK

    links = list_link_instances(host_doc)
    if not links:
        return None
    
    # Предпочитать загруженные связи
    loaded = [ln for ln in links if is_link_loaded(ln)]
    if loaded:
        return loaded[0]
        
    # Fallback к первой связи
    return links[0]


def select_link_instances_multi(host_doc,
                                title=u'Выберите связь(и) АР',
                                default_all=True,
                                allow_none=True,
                                loaded_only=False):
    """Выбор нескольких связей Revit.

    Возвращает список DB.RevitLinkInstance.
    """
    if _magic_active():
        try:
            selected_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
        except Exception:
            selected_links = []
        if selected_links:
            return selected_links
        try:
            selected_link = getattr(magic_context, 'SELECTED_LINK', None)
        except Exception:
            selected_link = None
        if selected_link is not None:
            return [selected_link]

    links = list_link_instances(host_doc)
    if not links:
        return []

    if loaded_only:
        loaded = []
        for ln in links:
            try:
                if is_link_loaded(ln):
                    loaded.append(ln)
            except Exception:
                continue
        links = loaded
        if not links:
            return []

    if default_all:
        return list(links)

    if len(links) == 1:
        return [links[0]]

    items = []
    for ln in links:
        try:
            name = ln.Name
        except Exception:
            name = '<Link>'
        try:
            status = 'Loaded' if is_link_loaded(ln) else 'Not loaded'
        except Exception:
            status = 'Unknown'
        items.append((u'{0}  [{1}]'.format(name, status), ln))

    items_sorted = sorted(items, key=lambda x: x[0].lower())
    picked = forms.SelectFromList.show(
        [x[0] for x in items_sorted],
        title=title,
        multiselect=True,
        button_name='Select',
        allow_none=allow_none
    )

    if not picked:
        return []

    selected = []
    picked_set = set(picked if isinstance(picked, (list, tuple, set)) else [picked])
    for label, inst in items_sorted:
        if label in picked_set:
            selected.append(inst)
    return selected


def select_link_level_pairs(host_doc,
                            link_title=u'Выберите связь(и) АР',
                            level_title=u'Выберите уровни',
                            default_all_links=True,
                            default_all_levels=False,
                            loaded_only=True):
    """Выбирает несколько связей и уровни для каждой связи.

    Returns:
        list[dict]: [
            {
                'link_instance': DB.RevitLinkInstance,
                'link_doc': DB.Document,
                'transform': DB.Transform,
                'levels': list[DB.Level]
            }
        ]
    """
    link_instances = select_link_instances_multi(
        host_doc,
        title=link_title,
        default_all=default_all_links,
        allow_none=True,
        loaded_only=loaded_only
    )
    if not link_instances:
        return []

    pairs = []
    multi = len(link_instances) > 1
    for ln in link_instances:
        link_doc = get_link_doc(ln)
        if link_doc is None:
            continue

        try:
            link_name = ln.Name
        except Exception:
            link_name = u'<Связь>'

        levels_prompt = level_title
        if multi:
            levels_prompt = u'{0} ({1})'.format(level_title, link_name)
        levels = select_levels_multi(link_doc, title=levels_prompt, default_all=default_all_levels)
        if not levels:
            continue

        pairs.append({
            'link_instance': ln,
            'link_doc': link_doc,
            'transform': get_total_transform(ln),
            'levels': list(levels),
        })

    return pairs


def iter_elements_by_category(doc, bic, limit=None, level_id=None):
    """Возвращает элементы из документа по BuiltInCategory, опционально отфильтрованные по LevelId, с опциональным ограничением."""
    if doc is None:
        return

    lim = None
    try:
        if limit is not None:
            lim = int(limit)
    except Exception:
        lim = None

    try:
        col = (DB.FilteredElementCollector(doc)
               .OfCategory(bic)
               .WhereElementIsNotElementType())
        
        # Native ElementLevelFilter может быть нестабилен на некоторых файлах связей или при несоответствии LevelId.
        # Для безопасности/стабильности (особенно в "грязных" сессиях) мы полагаемся на фильтрацию на стороне Python,
        # которая немного медленнее, но гораздо менее подвержена сбоям.
        # Параметр 'limit' гарантирует, что мы в любом случае не сканируем слишком много.
        
        lid_int = None
        if level_id:
            try:
                lid_int = level_id.IntegerValue
            except Exception:
                lid_int = None

        i = 0
        for e in col:
            # Python fallback фильтр
            if lid_int is not None:
                try:
                    elid = e.LevelId
                    if elid and elid.IntegerValue != lid_int:
                        continue
                except Exception:
                    continue

            yield e
            i += 1
            if lim is not None and i >= lim:
                break
    except Exception:
        return


def iter_rooms(link_doc, limit=None, level_id=None):
    for e in iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Rooms, limit=limit, level_id=level_id):
        yield e


def get_doors(link_doc):
    if link_doc is None:
        return []
    try:
        return list(DB.FilteredElementCollector(link_doc)
                    .OfCategory(DB.BuiltInCategory.OST_Doors)
                    .WhereElementIsNotElementType()
                    .ToElements())
    except Exception:
        return []


def iter_doors(link_doc, limit=None, level_id=None):
    for e in iter_elements_by_category(link_doc, DB.BuiltInCategory.OST_Doors, limit=limit, level_id=level_id):
        yield e


def get_room_center(room):
    return get_room_center_ex(room, return_method=False)


def _poly_centroid_xy(pts):
    """Возвращает (cx, cy) для точек полигона (XYZ) в плоскости XY."""
    if not pts or len(pts) < 3:
        return None

    # Shoelace formula
    try:
        a2 = 0.0
        cx6 = 0.0
        cy6 = 0.0
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            x0 = float(p0.X)
            y0 = float(p0.Y)
            x1 = float(p1.X)
            y1 = float(p1.Y)
            cross = x0 * y1 - x1 * y0
            a2 += cross
            cx6 += (x0 + x1) * cross
            cy6 += (y0 + y1) * cross

        if abs(a2) < 1e-9:
            return None
        cx = cx6 / (3.0 * a2)
        cy = cy6 / (3.0 * a2)
        return cx, cy
    except Exception:
        return None


def _loop_perimeter_xy(pts):
    if not pts or len(pts) < 2:
        return 0.0
    try:
        p = 0.0
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            dx = float(p1.X) - float(p0.X)
            dy = float(p1.Y) - float(p0.Y)
            p += (dx * dx + dy * dy) ** 0.5
        return p
    except Exception:
        return 0.0


def _poly_area_xy(pts):
    if not pts or len(pts) < 3:
        return 0.0
    try:
        a2 = 0.0
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            x0 = float(p0.X)
            y0 = float(p0.Y)
            x1 = float(p1.X)
            y1 = float(p1.Y)
            a2 += (x0 * y1 - x1 * y0)
        return a2 * 0.5
    except Exception:
        return 0.0


def _point_in_poly_xy(x, y, pts):
    """Трассировка лучей "точка в полигоне" в XY. pts - это вершины XYZ."""
    if not pts or len(pts) < 3:
        return False
    try:
        inside = False
        n = len(pts)
        j = n - 1
        for i in range(n):
            xi = float(pts[i].X)
            yi = float(pts[i].Y)
            xj = float(pts[j].X)
            yj = float(pts[j].Y)
            inter = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) if abs(yj - yi) > 1e-12 else 1e-12) + xi)
            if inter:
                inside = not inside
            j = i
        return inside
    except Exception:
        return False


def _point_to_room_boundary_dist_xy(x, y, outer_pts, hole_pts_list=None):
    """Знаковое расстояние до границы помещения в XY.

    Положительное, если точка внутри помещения (внутри внешнего контура и вне отверстий), отрицательное в противном случае.
    Величина — это минимальное расстояние до любого сегмента границы.
    """
    if not outer_pts or len(outer_pts) < 3:
        return -1e9

    holes = hole_pts_list or []
    inside = _point_in_poly_xy(x, y, outer_pts)
    if inside and holes:
        for hp in holes:
            try:
                if hp and _point_in_poly_xy(x, y, hp):
                    inside = False
                    break
            except Exception:
                continue

    # Min distance to any boundary
    min_d2 = None
    n = len(outer_pts)
    for i in range(n):
        a = outer_pts[i]
        b = outer_pts[(i + 1) % n]
        try:
            ax = float(a.X)
            ay = float(a.Y)
            bx = float(b.X)
            by = float(b.Y)
        except Exception:
            continue

        cx, cy = _closest_point_on_segment_xy(x, y, ax, ay, bx, by)
        dx = x - cx
        dy = y - cy
        d2 = dx * dx + dy * dy
        if min_d2 is None or d2 < min_d2:
            min_d2 = d2

    for hp in holes:
        if not hp or len(hp) < 3:
            continue
        m = len(hp)
        for i in range(m):
            a = hp[i]
            b = hp[(i + 1) % m]
            try:
                ax = float(a.X)
                ay = float(a.Y)
                bx = float(b.X)
                by = float(b.Y)
            except Exception:
                continue

            cx, cy = _closest_point_on_segment_xy(x, y, ax, ay, bx, by)
            dx = x - cx
            dy = y - cy
            d2 = dx * dx + dy * dy
            if min_d2 is None or d2 < min_d2:
                min_d2 = d2

    if min_d2 is None:
        dist = 0.0
    else:
        dist = min_d2 ** 0.5

    return dist if inside else -dist


class _Cell(object):
    __slots__ = ('x', 'y', 'h', 'd', 'max')

    def __init__(self, x, y, h, outer_pts, holes):
        self.x = float(x)
        self.y = float(y)
        self.h = float(h)
        self.d = _point_to_room_boundary_dist_xy(self.x, self.y, outer_pts, holes)
        self.max = self.d + self.h * 1.41421356237


def _polylabel_xy(outer_pts, hole_pts_list=None, precision=0.2):
    """Приблизительный полюс недоступности (как mapbox/polylabel) в XY.

    outer_pts / holes — это вершины XYZ в плоскости XY помещения.
    precision — в футах.
    """
    if not outer_pts or len(outer_pts) < 3:
        return None, None

    holes = hole_pts_list or []
    try:
        prec = max(float(precision or 0.2), 1e-3)
    except Exception:
        prec = 0.2

    # Bounding box
    min_x = min(float(p.X) for p in outer_pts)
    min_y = min(float(p.Y) for p in outer_pts)
    max_x = max(float(p.X) for p in outer_pts)
    max_y = max(float(p.Y) for p in outer_pts)

    width = max_x - min_x
    height = max_y - min_y
    if width <= 1e-9 or height <= 1e-9:
        return None, None

    cell_size = min(width, height)
    h = cell_size / 2.0
    if cell_size <= 1e-9:
        return None, None

    # Приоритетная очередь (max-heap через отрицательное значение)
    q = []
    uid = 0
    x = min_x
    while x < max_x:
        y = min_y
        while y < max_y:
            c = _Cell(x + h, y + h, h, outer_pts, holes)
            heapq.heappush(q, (-c.max, uid, c))
            uid += 1
            y += cell_size
        x += cell_size

    # Начальное лучшее значение: центроид, если доступен, иначе центр ограничивающего параллелепипеда
    best_p = None
    best_d = None
    try:
        cc = _poly_centroid_xy(outer_pts)
        if cc:
            cx, cy = cc
            d = _point_to_room_boundary_dist_xy(cx, cy, outer_pts, holes)
            best_p = (cx, cy)
            best_d = d
    except Exception:
        best_p = None
        best_d = None

    if best_p is None:
        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5
        best_p = (cx, cy)
        best_d = _point_to_room_boundary_dist_xy(cx, cy, outer_pts, holes)

    # Уточнить
    it = 0
    it_cap = 20000
    while q and it < it_cap:
        it += 1
        _, _, cell = heapq.heappop(q)

        if cell.d > best_d:
            best_p = (cell.x, cell.y)
            best_d = cell.d

        if (cell.max - best_d) <= prec:
            continue

        h2 = cell.h / 2.0
        if h2 <= 1e-9:
            continue

        for dx in (-h2, h2):
            for dy in (-h2, h2):
                c = _Cell(cell.x + dx, cell.y + dy, h2, outer_pts, holes)
                heapq.heappush(q, (-c.max, uid, c))
                uid += 1

    return best_p, best_d


def _room_boundary_loop_points(room):
    """Возвращает наилучшие упорядоченные точки контура (внешний контур) для помещения."""
    outer, _ = _room_boundary_loops_points(room)
    return outer


def _room_boundary_loops_points(room):
    """Возвращает (outer_loop_pts, hole_loops_pts_list) как вершины XYZ."""
    if room is None:
        return None, []
    try:
        opts = DB.SpatialElementBoundaryOptions()
        seglists = room.GetBoundarySegments(opts)
        if not seglists:
            return None, []

        loops = []
        for segs in seglists:
            try:
                pts = []
                for s in segs:
                    try:
                        c = s.GetCurve()
                        if c is None:
                            continue
                        pts.append(c.GetEndPoint(0))
                    except Exception:
                        continue

                if len(pts) >= 3:
                    loops.append(pts)
            except Exception:
                continue

        if not loops:
            return None, []

        # Внешний цикл = max abs(площадь); fallback к максимальному периметру
        best_i = None
        best_val = None
        for i, pts in enumerate(loops):
            try:
                a = abs(_poly_area_xy(pts))
            except Exception:
                a = 0.0
            if best_i is None or a > best_val:
                best_i = i
                best_val = a

        if best_val is None or best_val <= 1e-9:
            best_i = None
            best_val = None
            for i, pts in enumerate(loops):
                try:
                    p = _loop_perimeter_xy(pts)
                except Exception:
                    p = 0.0
                if best_i is None or p > best_val:
                    best_i = i
                    best_val = p

        if best_i is None:
            return loops[0], loops[1:]

        outer = loops[best_i]
        holes = [loops[i] for i in range(len(loops)) if i != best_i]
        return outer, holes
    except Exception:
        return None, []


def _closest_point_on_segment_xy(px, py, ax, ay, bx, by):
    vx = bx - ax
    vy = by - ay
    den = vx * vx + vy * vy
    if den <= 1e-12:
        return ax, ay

    t = ((px - ax) * vx + (py - ay) * vy) / den
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0

    return ax + t * vx, ay + t * vy


def _min_dist_to_loop_xy(pt, loop_pts):
    """Возвращает (min_dist, closest_point_xyz) от pt до ребер полигона (XY), используя loop_pts в качестве вершин."""
    if pt is None or not loop_pts or len(loop_pts) < 2:
        return None, None

    try:
        px = float(pt.X)
        py = float(pt.Y)
    except Exception:
        return None, None

    min_d2 = None
    qx = None
    qy = None

    n = len(loop_pts)
    for i in range(n):
        a = loop_pts[i]
        b = loop_pts[(i + 1) % n]
        try:
            ax = float(a.X)
            ay = float(a.Y)
            bx = float(b.X)
            by = float(b.Y)
        except Exception:
            continue

        cx, cy = _closest_point_on_segment_xy(px, py, ax, ay, bx, by)
        dx = px - cx
        dy = py - cy
        d2 = dx * dx + dy * dy
        if min_d2 is None or d2 < min_d2:
            min_d2 = d2
            qx = cx
            qy = cy

    if min_d2 is None:
        return None, None

    try:
        z = float(getattr(pt, 'Z', 0.0))
    except Exception:
        z = 0.0

    try:
        return (min_d2 ** 0.5), DB.XYZ(float(qx), float(qy), z)
    except Exception:
        return (min_d2 ** 0.5), None


def get_room_center_ex(room, return_method=False):
    """Возвращает XYZ в координатах связи."""
    try:
        return get_room_center_ex_safe(room, min_wall_clearance_ft=0.0, return_method=return_method)
    except Exception:
        return (None, None) if return_method else None


def get_room_center_ex_safe(room, min_wall_clearance_ft=0.0, return_method=False):
    """Возвращает XYZ в координатах связи, стараясь избегать точек, слишком близких к границам помещения.

    Стратегия:
      - Генерация кандидатов: центроид границы, точка размещения, центр ограничивающего параллелепипеда
      - Если цикл границы доступен и min_wall_clearance_ft > 0, выбрать кандидата с
        наибольшим расстоянием до границ (приблизительно, XY) и сдвинуть его, если все еще находится за пределами зазора.
      - В противном случае fallback к поведению get_room_center_ex.
    """
    if room is None:
        return (None, None) if return_method else None

    # ЗАЩИТА ОТ СБОЕВ: Обход доступа к геометрии
    try:
        min_clear = float(min_wall_clearance_ft or 0.0)
    except Exception:
        min_clear = 0.0

    loop_pts = None
    hole_loops = []
    try:
        loop_pts, hole_loops = _room_boundary_loops_points(room)
    except Exception:
        loop_pts = None
        hole_loops = []

    # Быстрый путь: прямоугольные помещения -> точный центр ограничивающего параллелепипеда
    if loop_pts and (not hole_loops):
        try:
            min_x = min(float(p.X) for p in loop_pts)
            min_y = min(float(p.Y) for p in loop_pts)
            max_x = max(float(p.X) for p in loop_pts)
            max_y = max(float(p.Y) for p in loop_pts)
            bbox_area = (max_x - min_x) * (max_y - min_y)
            poly_area = abs(_poly_area_xy(loop_pts))
            if bbox_area > 1e-9 and poly_area > 1e-9:
                fill = poly_area / bbox_area
                # близко к прямоугольнику (и не сильно вогнутый)
                if fill >= 0.96:
                    zref = float(loop_pts[0].Z)
                    p = DB.XYZ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, zref)
                    # Пропустить IsPointInRoom для быстрого пути, чтобы избежать сбоев
                    return (p, 'rect') if return_method else p
        except Exception:
            pass

    candidates = []

    # Кандидат Polylabel (лучший для сложной геометрии)
    if loop_pts:
        try:
            # точность в футах (более высокая, если пользователь запрашивает зазор)
            prec = 0.2
            if min_clear > 0.0:
                prec = max(0.1, min(0.5, min_clear / 3.0))

            xy, d = _polylabel_xy(loop_pts, hole_pts_list=hole_loops, precision=prec)
            if xy and d is not None and d > 0.0:
                zref = float(loop_pts[0].Z)
                p = DB.XYZ(float(xy[0]), float(xy[1]), zref)
                
                # Проверить IsPointInRoom с безопасностью
                ok = True
                try:
                    if hasattr(room, 'IsPointInRoom'):
                        ok = bool(room.IsPointInRoom(p))
                except Exception:
                    # доверять геометрическим вычислениям, если Revit выдает ошибку
                    ok = True
                
                if ok:
                    candidates.append(('polylabel', p))
        except Exception:
            pass

    # Кандидат центроида границы
    if loop_pts:
        try:
            cc = _poly_centroid_xy(loop_pts)
            if cc:
                zref = float(loop_pts[0].Z)
                p = DB.XYZ(cc[0], cc[1], zref)
                ok = True
                try:
                    if hasattr(room, 'IsPointInRoom'):
                        ok = bool(room.IsPointInRoom(p))
                except Exception:
                    ok = True
                if ok:
                    candidates.append(('boundary', p))
        except Exception:
            pass

    # Кандидат точки расположения
    try:
        loc = room.Location
        if loc and hasattr(loc, 'Point'):
            p = loc.Point
            ok = True
            try:
                if hasattr(room, 'IsPointInRoom'):
                    ok = bool(room.IsPointInRoom(p))
            except Exception:
                ok = True
            if ok:
                candidates.append(('location', p))
    except Exception:
        pass

    # Кандидат BBox
    try:
        bb = room.get_BoundingBox(None)
        if bb:
            p = (bb.Min + bb.Max) * 0.5
            candidates.append(('bbox', p))
    except Exception:
        pass

    if not candidates:
        return (None, None) if return_method else None

    # Выбрать лучшего кандидата...
    # (Rest of logic remains same, but wrapped in general try-except of parent function if needed)
    
    # ... логика продолжается ...
    # Повторно вставляем остальную часть логики функции сюда или предполагаем, что она следует.
    # Поскольку я редактирую большой блок, я вставлю остальную часть исходного тела функции,
    # чтобы убедиться, что она не будет обрезана, но с дополнительной безопасностью.

    # Предпочесть точку, которая хорошо отделена от стен и визуально центрирована.
    # Среди кандидатов с почти максимальным зазором выбрать тот, который ближе всего к центру ограничивающего параллелепипеда помещения.
    if loop_pts:
        try:
            min_x = min(float(p.X) for p in loop_pts)
            min_y = min(float(p.Y) for p in loop_pts)
            max_x = max(float(p.X) for p in loop_pts)
            max_y = max(float(p.Y) for p in loop_pts)
            zref = float(loop_pts[0].Z)
            bbp = DB.XYZ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, zref)

            scored = []
            dmax = None
            for mm, pp in candidates:
                try:
                    d = _point_to_room_boundary_dist_xy(float(pp.X), float(pp.Y), loop_pts, hole_pts_list=hole_loops)
                    d = float(d)
                except Exception:
                    continue
                if d <= 0.0:
                    continue
                scored.append((mm, pp, d))
                if dmax is None or d > dmax:
                    dmax = d

            if scored and dmax is not None:
                thr = dmax * 0.95
                best_mm = None
                best_pp = None
                best_dist2 = None
                best_d = None
                for mm, pp, d in scored:
                    if d < thr:
                        continue
                    dx = float(pp.X) - float(bbp.X)
                    dy = float(pp.Y) - float(bbp.Y)
                    dist2 = dx * dx + dy * dy
                    if best_dist2 is None or dist2 < best_dist2:
                        best_mm = mm
                        best_pp = pp
                        best_dist2 = dist2
                        best_d = d

                if best_pp is not None:
                    # Сдвинуть от ближайшей границы, если меньше требуемого зазора
                    try:
                        if min_clear > 0.0 and best_d is not None and best_d < min_clear:
                            _, q = _min_dist_to_loop_xy(best_pp, loop_pts)
                            if q is not None:
                                vx = float(best_pp.X) - float(q.X)
                                vy = float(best_pp.Y) - float(q.Y)
                                ln = (vx * vx + vy * vy) ** 0.5
                                if ln > 1e-6:
                                    ux = vx / ln
                                    uy = vy / ln
                                    p2 = DB.XYZ(float(q.X) + ux * min_clear, float(q.Y) + uy * min_clear, float(best_pp.Z))
                                    ok = True
                                    try:
                                        if hasattr(room, 'IsPointInRoom'):
                                            ok = bool(room.IsPointInRoom(p2))
                                    except Exception:
                                        ok = True
                                    if ok:
                                        best_pp = p2
                    except Exception:
                        pass
                    return (best_pp, best_mm) if return_method else best_pp
        except Exception:
            pass

    # Если polylabel доступен, предпочитать его для непрямоугольной геометрии
    for mm, pp in candidates:
        if mm == 'polylabel':
            return (pp, mm) if return_method else pp

    # Если нет информации о границе или зазор не запрашивается -> сохранить исходное приоритетное поведение
    if (min_clear <= 0.0) or (not loop_pts):
        for m in ('boundary', 'location', 'bbox'):
            for mm, pp in candidates:
                if mm == m:
                    return (pp, mm) if return_method else pp
        mm, pp = candidates[0]
        return (pp, mm) if return_method else pp

    # Выбрать кандидата с максимальным зазором до границы
    def _prio(m):
        if m == 'boundary':
            return 2
        if m == 'location':
            return 1
        return 0


def get_room_centers_by_shape(room, min_wall_clearance_ft=0.0, return_meta=False, rules=None):
    """Возвращает 1 или 2 центральные точки (XYZ в координатах связи) на основе формы помещения.

    Использует существующий надежный поиск центра для сложных полигонов и добавляет возможность возвращать две точки
    для вытянутых помещений.
    """
    if room is None:
        return ([], {}) if return_meta else []

    # 1) Всегда сначала вычисляем лучший одиночный центр (стабильный fallback)
    c1, method = get_room_center_ex_safe(room, min_wall_clearance_ft=min_wall_clearance_ft, return_method=True)
    if c1 is None:
        return ([], {'count': 0, 'method': method}) if return_meta else []

    loop_pts = None
    hole_loops = []
    try:
        loop_pts, hole_loops = _room_boundary_loops_points(room)
    except Exception:
        loop_pts = None
        hole_loops = []

    if not loop_pts or len(loop_pts) < 3:
        centers = [c1]
        meta = {'count': 1, 'method': method, 'reason': 'no_boundary'}
        return (centers, meta) if return_meta else centers

    # 2) Вычислить метрики простой формы по ограничивающему параллелепипеду внешней границы
    try:
        xs = [float(p.X) for p in loop_pts]
        ys = [float(p.Y) for p in loop_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        dx = max_x - min_x
        dy = max_y - min_y
        long_dim = max(dx, dy)
        short_dim = min(dx, dy)
    except Exception:
        long_dim = 0.0
        short_dim = 0.0

    # Значения по умолчанию (футы) – правила могут переопределить
    try:
        elong_ratio = float((rules or {}).get('light_room_elongation_ratio', 2.2) or 2.2)
    except Exception:
        elong_ratio = 2.2
    try:
        min_long_ft = float(mm_to_ft(int((rules or {}).get('light_two_centers_min_long_mm', 4500) or 4500)) or 0.0)
    except Exception:
        min_long_ft = float(mm_to_ft(4500) or 0.0)
    try:
        min_clear = float(min_wall_clearance_ft or 0.0)
    except Exception:
        min_clear = 0.0

    ratio = (float(long_dim) / float(short_dim)) if (short_dim and short_dim > 1e-6) else 999.0
    need_two = bool(long_dim >= min_long_ft and ratio >= elong_ratio)

    if not need_two:
        centers = [c1]
        meta = {'count': 1, 'method': method, 'ratio': ratio, 'long_dim_ft': long_dim}
        return (centers, meta) if return_meta else centers

    # 3) Два центра: взять две точки вдоль длинной оси вокруг основного центра.
    # Использовать polylabel на двух обрезанных половинках как надежный способ оставаться внутри вогнутых комнат.
    try:
        zref = float(loop_pts[0].Z)
    except Exception:
        zref = float(getattr(c1, 'Z', 0.0) or 0.0)

    # Определить ось разделения по ограничивающему параллелепипеду
    split_x = bool(dx >= dy)
    try:
        mid_val = float(c1.X) if split_x else float(c1.Y)
    except Exception:
        mid_val = (min_x + max_x) * 0.5 if split_x else (min_y + max_y) * 0.5

    def _clip_loop(pts, keep_leq=True):
        out = []
        for p in pts:
            try:
                v = float(p.X) if split_x else float(p.Y)
            except Exception:
                continue
            if (v <= mid_val) if keep_leq else (v >= mid_val):
                out.append(p)
        # убедиться, что есть хотя бы треугольник
        return out if len(out) >= 3 else None

    left = _clip_loop(loop_pts, keep_leq=True)
    right = _clip_loop(loop_pts, keep_leq=False)

    centers = [c1]
    c2 = None
    c3 = None
    try:
        prec = 0.2
        if min_clear > 0.0:
            prec = max(0.1, min(0.5, min_clear / 3.0))

        if left:
            xy2, d2 = _polylabel_xy(left, hole_pts_list=hole_loops, precision=prec)
            if xy2 and d2 and d2 > 0.0:
                c2 = DB.XYZ(float(xy2[0]), float(xy2[1]), zref)
        if right:
            xy3, d3 = _polylabel_xy(right, hole_pts_list=hole_loops, precision=prec)
            if xy3 and d3 and d3 > 0.0:
                c3 = DB.XYZ(float(xy3[0]), float(xy3[1]), zref)
    except Exception:
        c2 = None
        c3 = None

    # Проверить, находятся ли точки внутри помещения
    valid = []
    for p in (c2, c3):
        if p is None:
            continue
        ok = True
        try:
            if hasattr(room, 'IsPointInRoom'):
                ok = bool(room.IsPointInRoom(p))
        except Exception:
            ok = True
        if ok:
            valid.append(p)

    # Если обе половины не удались, fallback к смещенным точкам вдоль оси от c1
    if len(valid) < 2:
        try:
            step = max(float(min_clear), float(mm_to_ft(1200) or 0.0))
            if split_x:
                p2 = DB.XYZ(float(c1.X) - step, float(c1.Y), float(c1.Z))
                p3 = DB.XYZ(float(c1.X) + step, float(c1.Y), float(c1.Z))
            else:
                p2 = DB.XYZ(float(c1.X), float(c1.Y) - step, float(c1.Z))
                p3 = DB.XYZ(float(c1.X), float(c1.Y) + step, float(c1.Z))
            valid = []
            for p in (p2, p3):
                ok = True
                try:
                    if hasattr(room, 'IsPointInRoom'):
                        ok = bool(room.IsPointInRoom(p))
                except Exception:
                    ok = True
                if ok:
                    valid.append(p)
        except Exception:
            valid = []

    if len(valid) >= 2:
        centers = [valid[0], valid[1]]
        meta = {'count': 2, 'method': method, 'ratio': ratio, 'long_dim_ft': long_dim, 'split_axis': 'X' if split_x else 'Y'}
        return (centers, meta) if return_meta else centers

    meta = {'count': 1, 'method': method, 'ratio': ratio, 'long_dim_ft': long_dim, 'reason': 'two_failed'}
    return ([c1], meta) if return_meta else [c1]

    scored = []
    for mm, pp in candidates:
        try:
            d, _ = _min_dist_to_loop_xy(pp, loop_pts)
            if d is None:
                d = -1.0
        except Exception:
            d = -1.0
        scored.append((float(d), _prio(mm), mm, pp))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    best_d, _, best_m, best_p = scored[0]

    # Сдвинуть от ближайшей границы, если слишком близко
    try:
        if best_d >= 0.0 and best_d < min_clear:
            d0, q = _min_dist_to_loop_xy(best_p, loop_pts)
            if q is not None:
                vx = float(best_p.X) - float(q.X)
                vy = float(best_p.Y) - float(q.Y)
                ln = (vx * vx + vy * vy) ** 0.5
                if ln > 1e-6:
                    ux = vx / ln
                    uy = vy / ln
                    p2 = DB.XYZ(float(q.X) + ux * min_clear, float(q.Y) + uy * min_clear, float(best_p.Z))
                    ok = True
                    try:
                        if hasattr(room, 'IsPointInRoom'):
                            ok = bool(room.IsPointInRoom(p2))
                    except Exception:
                        ok = True
                    if ok:
                        best_p = p2
    except Exception:
        pass

    return (best_p, best_m) if return_method else best_p


def select_link_instance(doc, title='Select AR Link', allow_none=False):
    if _magic_active():
        try:
            selected_link = getattr(magic_context, 'SELECTED_LINK', None)
        except Exception:
            selected_link = None
        if selected_link is not None:
            return selected_link
        try:
            selected_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
        except Exception:
            selected_links = []
        if selected_links:
            return selected_links[0]

    links = list_link_instances(doc)
    if not links:
        return None

    loaded_links = []
    for ln in links:
        try:
            if is_link_loaded(ln):
                loaded_links.append(ln)
        except Exception:
            continue

    if loaded_links:
        return loaded_links[0]

    # Fallback: если загруженных связей нет, вернуть первую доступную.
    return links[0]
