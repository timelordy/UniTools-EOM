# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms

import os
import tempfile
import datetime

try:
    from pyrevit import script
except Exception:
    script = None


def _dbg_enabled():
    """Вернуть True, если включено отладочное логирование символов семейств.

    Включить через переменную окружения: EOM_FAMILY_DEBUG=1
    """
    try:
        v = os.environ.get('EOM_FAMILY_DEBUG', '')
        return str(v).strip().lower() in ('1', 'true', 'yes', 'on', 'y')
    except Exception:
        return False


def _dbg_log_path():
    """Вернуть путь к записываемому логу (по возможности)."""
    try:
        if script is not None:
            try:
                # Папка вывода скрипта pyRevit для каждого запуска и всегда доступна для записи.
                out_dir = script.get_output().get_output_dir()
                if out_dir:
                    return os.path.join(out_dir, 'family_symbol_debug.log')
            except Exception:
                pass
    except Exception:
        pass

    try:
        base = tempfile.gettempdir() or '.'
    except Exception:
        base = '.'
    return os.path.join(base, 'EOMTemplateTools_family_symbol_debug.log')


def _dbg_write(msg):
    """Добавить строку в отладочный лог; никогда не вызывает ошибок."""
    if not _dbg_enabled():
        return
    try:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        ts = ''
    try:
        line = u'[{0}] {1}'.format(ts, msg)
    except Exception:
        try:
            line = '[{0}] {1}'.format(ts, str(msg))
        except Exception:
            return
    try:
        p = _dbg_log_path()
        with open(p, 'a') as f:
            try:
                f.write((line + u'\n').encode('utf-8'))
            except Exception:
                # Fallback for CPython unicode behavior differences
                f.write((str(line) + '\n'))
    except Exception:
        return


def _dbg_codepoints(label, text, max_len=120):
    """Вернуть компактную строку с кодовыми точками для первых max_len символов."""
    try:
        t = text or u''
    except Exception:
        t = ''
    try:
        t = t[:max_len]
    except Exception:
        pass
    parts = []
    try:
        for ch in t:
            try:
                parts.append(u'U+{0:04X}'.format(ord(ch)))
            except Exception:
                parts.append(u'?')
    except Exception:
        parts = []
    try:
        return u'{0}: {1}'.format(label, u' '.join(parts))
    except Exception:
        return ''


def _dbg_similarity(a, b):
    try:
        import difflib
        return float(difflib.SequenceMatcher(None, a or '', b or '').ratio())
    except Exception:
        return 0.0

from utils_revit import ensure_symbol_active, find_nearest_level, set_comments


def get_symbol_type_name(symbol):
    """Вернуть имя типа FamilySymbol с надежным запасным вариантом для особенностей IronPython/Revit API."""
    if symbol is None:
        return ''

    # Первичный путь.
    try:
        n = getattr(symbol, 'Name', None) or ''
        if n:
            return n
    except Exception:
        pass

    # Некоторые сессии IronPython/Revit предоставляют имена элементов только через статический геттер API.
    try:
        name_getter = getattr(DB.Element, 'Name', None)
    except Exception:
        name_getter = None
    if name_getter is not None:
        try:
            n = name_getter.GetValue(symbol) or ''
            if n:
                return n
        except Exception:
            pass

    # Запасной вариант, безопасный для Revit.
    try:
        p = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
    except Exception:
        p = None
    if p is not None:
        try:
            n = p.AsString() or ''
            if n:
                return n
        except Exception:
            pass
        try:
            n = p.AsValueString() or ''
            if n:
                return n
        except Exception:
            pass

    # Последнее средство поиска по локализованным именам параметров.
    for pname in ('Type Name', u'Имя типа'):
        try:
            p2 = symbol.LookupParameter(pname)
            if p2 is None:
                continue
            n = p2.AsString() or p2.AsValueString() or ''
            if n:
                return n
        except Exception:
            continue

    return ''


def format_family_type(symbol):
    """Вернуть метку 'Семейство : Тип'."""
    if symbol is None:
        return ''

    fam_name = ''
    # Предпочитать FamilyName (строка) перед Family.Name (может быть более тяжелым / менее стабильным в некоторых сессиях).
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
    type_name = get_symbol_type_name(symbol)
    return u'{0} : {1}'.format(fam_name, type_name).strip()


def list_family_symbols(doc, category_bic=None):
    """Вывести FamilySymbol в doc. Если установлен category_bic, фильтровать по категории."""
    # Deprecated для больших проектов (может быть тяжелым). Сохранено для обратной совместимости.
    return list(iter_family_symbols(doc, category_bic=category_bic, limit=None))


def iter_family_symbols(doc, category_bic=None, limit=None):
    """Генерирует FamilySymbol, опционально отфильтрованные по категории, с опциональным лимитом.

    Избегает материализации всех символов в память (снижает риск зависания UI).
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
            # Это должно быть безопасно для FamilySymbol; не подавлять безмолвно.
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
    """Вернуть (значение_перечисления, имя_перечисления) для FamilyPlacementType, по возможности."""
    try:
        f = symbol.Family if symbol else None
        pt = f.FamilyPlacementType if f else None
        return pt, str(pt)
    except Exception:
        return None, 'Unknown'


def is_supported_point_placement(symbol):
    """Мы поддерживаем только семейства с простым точечным размещением.

    На практике: OneLevelBased (или WorkPlaneBased, если активный вид поддерживает).
    Размещаемые (потолок/поверхность) семейства намеренно НЕ поддерживаются в этой демонстрации.
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
                         title='Выбор типа семейства',
                         category_bic=None,
                         only_supported=True,
                         allow_none=True,
                         button_name='Выбрать',
                         search_text=None,
                         limit=200,
                         scan_cap=5000):
    """Выбрать FamilySymbol из загруженных типов с опциональным фильтром подстроки и ограничением.

    `search_text` фильтрует по "Семейство : Тип" (без учета регистра).
    `limit` ограничивает количество отображаемых элементов, чтобы избежать огромных списков в UI.
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

    # Сортировка небольших списков в порядке.
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


def _norm_ft(value):
    """Нормализовать имена семейств/типов для сопоставления.

    Теперь используется normalize_type_key из модуля floor_panel_niches для
    последовательной нормализации из кириллицы в латиницу.
    """
    try:
        import floor_panel_niches as fpn
        return fpn.normalize_type_key(value)
    except Exception:
        # Возврат к исходной логике, если импорт не удался.
        try:
            t = (value or u'').strip().lower()
        except Exception:
            return ''
        if not t:
            return t
        try:
            t = t.replace(u'\u00a0', u' ').replace(u'\u202f', u' ')
        except Exception:
            pass
        try:
            for ch in (u'–', u'—', u'‑', u'−'):
                t = t.replace(ch, u'-')
        except Exception:
            pass
        try:
            t = u' '.join(t.split())
        except Exception:
            pass
        return t


def _normalize_name(s):
    try:
        return ' '.join((s or '').replace(':', ' : ').split()).strip()
    except Exception:
        return ''


def _parse_family_type(fullname):
    """Разбирает 'Семейство : Тип' -> (семейство, тип)"""
    if not fullname:
        return None, None
    cleaned = _normalize_name(fullname)
    # Поддерживаемые варианты:
    # - "Семейство : Тип" (предпочтительно)
    # - "Семейство:Тип" (без пробелов)
    # - "Семейство :Тип" / "Семейство: Тип" (смешанный)
    # _normalize_name уже расширяет ':' до ' : ' и схлопывает пробелы.
    parts = [p.strip() for p in cleaned.split(' : ')]
    if len(parts) == 1:
        # может быть "Семейство - Тип" или просто Тип
        return None, parts[0]
    family = parts[0] or None
    type_name = ' : '.join(parts[1:]).strip()
    return family, type_name


def _contains_panel_token(text, token):
    try:
        t = (text or u"").lower()
        k = (token or u"").lower()
        return bool(k) and (k in t)
    except Exception:
        return False


def debug_dump_family_symbols(doc,
                             title='EOM Template Tools',
                             category_bics=None,
                             search_text=None,
                             limit=80,
                             scan_cap=8000):
    """Показать диагностический список загруженных FamilySymbol.

    Предназначено для устранения несоответствий конфигурации; безопасное чтение.
    """
    bics = list(category_bics or [])
    if not bics:
        bics = [
            DB.BuiltInCategory.OST_ElectricalEquipment,
            DB.BuiltInCategory.OST_ElectricalFixtures,
            DB.BuiltInCategory.OST_GenericModel,
        ]

    sfilter = _norm(search_text)
    out = []
    scanned = 0
    scan_lim = 8000
    try:
        scan_lim = int(scan_cap or 8000)
    except Exception:
        scan_lim = 8000
    try:
        lim = int(limit or 80)
    except Exception:
        lim = 80
    lim = max(lim, 20)

    for bic in bics:
        for s in iter_family_symbols(doc, category_bic=bic, limit=None):
            scanned += 1
            try:
                label = format_family_type(s)
                if not label:
                    continue
                if sfilter and (sfilter not in _norm(label)):
                    continue
                out.append(label)
                if len(out) >= lim:
                    break
            except Exception:
                continue
            if scanned >= scan_lim:
                break
        if len(out) >= lim or scanned >= scan_lim:
            break

    if not out:
        forms.alert(
            'No matching family types found.\n\n'
            'Filter: {0}'.format(search_text or ''),
            title=title,
            warn_icon=True,
        )
        return []

    out = sorted(list(set(out)), key=lambda x: (x or u'').lower())
    msg = u'Loaded family types (candidates)\n\n{0}'.format(u'\n'.join(out[:lim]))
    if len(out) > lim:
        msg += u'\n\n... and {0} more'.format(len(out) - lim)
    forms.alert(msg, title=title, warn_icon=False)
    return out


def find_family_symbol(doc, fullname, category_bic=None, limit=5000):
    """Найти FamilySymbol по строке 'Семейство : Тип'.

    Если установлен category_bic, сначала искать в этой категории.
    """
    fam_name, type_name = _parse_family_type(fullname)
    n_fam = _norm_ft(fam_name)
    n_type = _norm_ft(type_name)
    if not n_type:
        return None

    if _dbg_enabled():
        try:
            _dbg_write(u'--- find_family_symbol ---')
            _dbg_write(u'request.fullname.raw = {0}'.format(fullname))
            _dbg_write(u'request.family.raw   = {0}'.format(fam_name))
            _dbg_write(u'request.type.raw     = {0}'.format(type_name))
            _dbg_write(u'request.family.norm  = {0}'.format(n_fam))
            _dbg_write(u'request.type.norm    = {0}'.format(n_type))
            _dbg_write(_dbg_codepoints(u'request.fullname.codepoints', fullname))
            _dbg_write(_dbg_codepoints(u'request.type.codepoints', type_name))
            _dbg_write(u'category_bic={0} limit={1}'.format(category_bic, limit))
            _dbg_write(u'log_file={0}'.format(_dbg_log_path()))
        except Exception:
            pass

    # Опционально: запасной вариант для номера панели (например, "ЩЭ-3"), устойчивый к транслитерации.
    panel_token = None
    panel_num = None
    panel_num_from = None
    try:
        import floor_panel_niches as fpn
        panel_num = fpn.extract_panel_number_from_type_name(type_name or fullname)
        panel_num_from = fpn.extract_panel_number_from_type_name
    except Exception:
        panel_num = None
        panel_num_from = None
    if panel_num is not None:
        try:
            panel_token = u'ЩЭ-{0}'.format(int(panel_num))
        except Exception:
            panel_token = None

    def _iter_symbols(collector, require_family):
        for s in collector:
            try:
                sym_name_raw = get_symbol_type_name(s)
                sym_name_fam, sym_name_type = _parse_family_type(sym_name_raw)
                sym_type = _norm_ft(sym_name_type or sym_name_raw)

                sym_fam = ''
                try:
                    sym_fam = _norm_ft(getattr(s, 'FamilyName', None))
                except Exception:
                    sym_fam = ''
                if not sym_fam:
                    try:
                        fam = getattr(s, 'Family', None)
                        sym_fam = _norm_ft(fam.Name) if fam else ''
                    except Exception:
                        sym_fam = ''
                if not sym_fam and sym_name_fam:
                    sym_fam = _norm_ft(sym_name_fam)

                if sym_type != n_type:
                    # Запасной вариант: сопоставление по номеру панели при точном несовпадении типа.
                    matched_by_num = False
                    label = None
                    if panel_num is not None:
                        sym_num = None
                        try:
                            if panel_num_from is not None:
                                sym_num = panel_num_from(sym_type)
                        except Exception:
                            sym_num = None
                        if sym_num is None:
                            try:
                                label = format_family_type(s)
                            except Exception:
                                label = sym_name_raw
                            try:
                                if panel_num_from is not None:
                                    sym_num = panel_num_from(label)
                            except Exception:
                                sym_num = None
                        try:
                            matched_by_num = (sym_num is not None and int(sym_num) == int(panel_num))
                        except Exception:
                            matched_by_num = False

                    if not matched_by_num:
                        # Устаревший запасной вариант: проверка токена на наличие.
                        if panel_token:
                            if label is None:
                                try:
                                    label = format_family_type(s)
                                except Exception:
                                    label = sym_name_raw
                            if not (_contains_panel_token(sym_type, panel_token) or _contains_panel_token(label, panel_token)):
                                continue
                        else:
                            continue
                if require_family and n_fam and sym_fam != n_fam:
                    continue
                return s
            except Exception:
                continue
        return None

    def _dbg_collect_top_matches(bic, max_scan=2000, top_n=15):
        """Собрать N наиболее близких совпадений по нормализованной строке типа."""
        if not _dbg_enabled():
            return
        scored = []
        scanned = 0
        try:
            for s in iter_family_symbols(doc, category_bic=bic, limit=None):
                scanned += 1
                try:
                    label = format_family_type(s)
                except Exception:
                    label = ''

                try:
                    sym_name_raw = get_symbol_type_name(s)
                except Exception:
                    sym_name_raw = None

                sym_name_fam, sym_name_type = _parse_family_type(sym_name_raw)
                cand_type_raw = sym_name_type or sym_name_raw or ''
                cand_type_norm = _norm_ft(cand_type_raw)
                ratio = _dbg_similarity(n_type, cand_type_norm)

                scored.append((ratio, label, sym_name_raw, cand_type_raw, cand_type_norm))
                if scanned >= max_scan:
                    break
                # keep list bounded
                if len(scored) > top_n * 8:
                    scored = sorted(scored, key=lambda x: x[0], reverse=True)[:top_n * 4]
        except Exception:
            pass

        try:
            scored = sorted(scored, key=lambda x: x[0], reverse=True)
            _dbg_write(u'closest_matches: bic={0} scanned={1} showing_top={2}'.format(bic, scanned, top_n))
            for i, (ratio, label, sym_name_raw, cand_type_raw, cand_type_norm) in enumerate(scored[:top_n]):
                try:
                    _dbg_write(u'  #{0:02d} ratio={1:.3f} label={2}'.format(i + 1, ratio, label))
                    _dbg_write(u'      sym.Name.raw={0}'.format(sym_name_raw))
                    _dbg_write(u'      cand.type.raw={0}'.format(cand_type_raw))
                    _dbg_write(u'      cand.type.norm={0}'.format(cand_type_norm))
                except Exception:
                    continue
            if scored:
                try:
                    best = scored[0]
                    _dbg_write(_dbg_codepoints(u'best.cand.type.codepoints', best[3]))
                except Exception:
                    pass
        except Exception:
            return

    try:
        # Счетчики сканирования (по возможности)
        scanned_cat = None
        scanned_all = None
        if _dbg_enabled():
            try:
                # Приблизительные подсчеты с ранним ограничением для предотвращения зависания UI.
                c = 0
                for _ in iter_family_symbols(doc, category_bic=category_bic, limit=None):
                    c += 1
                    if c >= 8000:
                        break
                scanned_cat = c
            except Exception:
                scanned_cat = None
            try:
                c = 0
                for _ in iter_family_symbols(doc, category_bic=None, limit=None):
                    c += 1
                    if c >= 8000:
                        break
                scanned_all = c
            except Exception:
                scanned_all = None
            try:
                _dbg_write(u'scan_counts (capped@8000): in_category={0} global={1}'.format(scanned_cat, scanned_all))
            except Exception:
                pass

        if n_fam:
            found = _iter_symbols(iter_family_symbols(doc, category_bic=category_bic, limit=limit), True)
            if found:
                if _dbg_enabled():
                    try:
                        _dbg_write(u'FOUND in category require_family=True: {0}'.format(format_family_type(found)))
                    except Exception:
                        pass
                return found
            found = _iter_symbols(iter_family_symbols(doc, category_bic=category_bic, limit=limit), False)
            if found:
                if _dbg_enabled():
                    try:
                        _dbg_write(u'FOUND in category require_family=False: {0}'.format(format_family_type(found)))
                    except Exception:
                        pass
                return found
        else:
            found = _iter_symbols(iter_family_symbols(doc, category_bic=category_bic, limit=limit), False)
            if found:
                if _dbg_enabled():
                    try:
                        _dbg_write(u'FOUND in category (no family): {0}'.format(format_family_type(found)))
                    except Exception:
                        pass
                return found

        if category_bic is not None:
            if n_fam:
                found = _iter_symbols(iter_family_symbols(doc, category_bic=None, limit=limit), True)
                if found:
                    if _dbg_enabled():
                        try:
                            _dbg_write(u'FOUND global require_family=True: {0}'.format(format_family_type(found)))
                        except Exception:
                            pass
                    return found
                found2 = _iter_symbols(iter_family_symbols(doc, category_bic=None, limit=limit), False)
                if found2 and _dbg_enabled():
                    try:
                        _dbg_write(u'FOUND global require_family=False: {0}'.format(format_family_type(found2)))
                    except Exception:
                        pass
                if not found2 and _dbg_enabled():
                    _dbg_collect_top_matches(category_bic, max_scan=min(int(limit or 5000), 3000), top_n=15)
                    _dbg_collect_top_matches(None, max_scan=2000, top_n=15)
                return found2
            found3 = _iter_symbols(iter_family_symbols(doc, category_bic=None, limit=limit), False)
            if not found3 and _dbg_enabled():
                _dbg_collect_top_matches(category_bic, max_scan=min(int(limit or 5000), 3000), top_n=15)
                _dbg_collect_top_matches(None, max_scan=2000, top_n=15)
            return found3
        return None
    except Exception:
        return None


def get_or_load_family_symbol(doc, fullname, category_bic=None, title='EOM Template Tools'):
    """Возвращает FamilySymbol, если присутствует; в противном случае предлагает пользователю загрузить его вручную."""
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
    """Размещает экземпляр семейства, основанного на точке, в XYZ. Возвращает созданный экземпляр или None."""
    if doc is None or symbol is None or point_xyz is None:
        return None

    pt_enum, pt_name = get_symbol_placement_type(symbol)
    if not is_supported_point_placement(symbol):
        raise Exception('Unsupported family placement type for demo placement: {0}'.format(pt_name))

    ensure_symbol_active(doc, symbol)

    # Семейства WorkPlaneBased размещаются в контексте вида.
    try:
        if pt_enum == DB.FamilyPlacementType.WorkPlaneBased:
            v = view or doc.ActiveView
            # Если у вида нет плоскости эскиза, размещение может непредсказуемо завершиться ошибкой.
            try:
                sp = getattr(v, 'SketchPlane', None)
                if sp is None:
                    raise Exception('Active view has no work plane (SketchPlane is None).')
            except Exception:
                # все еще пытаться; некоторые виды не показывают SketchPlane
                pass

            return doc.Create.NewFamilyInstance(point_xyz, symbol, v)
    except Exception:
        # НЕ возвращаться к размещению на основе уровня для семейств WorkPlaneBased.
        raise

    # Семейства OneLevelBased: размещение по ближайшему уровню
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
    """Размещает светильники в указанных точках. Возвращает список созданных экземпляров."""
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
