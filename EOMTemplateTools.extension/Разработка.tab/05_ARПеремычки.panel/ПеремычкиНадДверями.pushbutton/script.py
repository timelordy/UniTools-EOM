# -*- coding: utf-8 -*-

import os
import re

from pyrevit import DB, revit, script

import constants
import orchestrator
from utils_revit import alert, find_nearest_level, log_exception, tx
from utils_units import ft_to_mm, mm_to_ft


def _to_int(val, default=0):
    try:
        return int(val)
    except Exception:
        return int(default)


def _to_float(val, default=None):
    try:
        return float(val)
    except Exception:
        return default


def _md_cell(val):
    try:
        txt = str(val if val is not None else '')
    except Exception:
        txt = ''
    return txt.replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def _print_kv_table(output, title, rows):
    if not rows:
        return
    output.print_md('#### {0}'.format(_md_cell(title)))
    output.print_md('| Показатель | Значение |')
    output.print_md('|---|---:|')
    for key, val in rows:
        output.print_md('| {0} | {1} |'.format(_md_cell(key), _md_cell(val)))


def _print_counter_table(output, title, counter, key_title):
    if not counter:
        return
    output.print_md('#### {0}'.format(_md_cell(title)))
    output.print_md('| {0} | Кол-во |'.format(_md_cell(key_title)))
    output.print_md('|---|---:|')
    rows = sorted(
        ((str(k), _to_int(v, 0)) for k, v in dict(counter).items()),
        key=lambda x: (-x[1], x[0].lower())
    )
    for key, val in rows:
        output.print_md('| {0} | {1} |'.format(_md_cell(key), val))


_STATUS_LABELS = {
    'created': 'Создано',
    'skipped': 'Пропущено',
    'error': 'Ошибка',
    'failed': 'Ошибка создания',
    'info': 'Информация',
}

_REASON_LABELS = {
    'pgp_single': 'Стена ПГП 80 мм (1 перемычка)',
    'pgp_double': 'Стена ПГП (2 перемычки)',
    'silicate_single': 'Силикатный кирпич 120 мм (1 перемычка)',
    'silicate_double': 'Силикатный кирпич 250 мм (2 перемычки)',
    'ceramic_single': 'Керамический кирпич 120 мм (1 перемычка)',
    'ceramic_double': 'Керамический кирпич 250 мм (2 перемычки)',
    'unsupported_wall_material': 'Другой материал/тип стены',
    'unsupported_wall_thickness': 'Неподдерживаемая толщина стены',
    'non_wall_host': 'Дверь размещена не в стене',
    'already_has_lintel': 'Для двери перемычка уже существует',
    'lintel_family_not_loaded': 'Не загружены семейства перемычек',
    'door_geometry_unavailable': 'Не удалось получить геометрию двери',
    'door_axes_unavailable': 'Не удалось определить направление двери/стены',
    'lintel_symbol_not_found_for_door': 'Не найден подходящий тип перемычки',
    'lintel_instance_create_failed': 'Не удалось создать экземпляр перемычки',
    'doc_is_none': 'Не удалось получить документ Revit',
    'unknown': 'Неизвестно',
}

_MAX_ISSUE_LOG_ROWS = 200


def _display_value(val, fallback='—'):
    txt = str(val or '').strip()
    if not txt:
        return fallback
    if txt.lower() == 'n/a':
        return fallback
    return txt


def _translate_status(status_code):
    key = str(status_code or '').strip().lower()
    if not key:
        return '—'
    return _STATUS_LABELS.get(key, key)


def _translate_reason(reason_code):
    raw = str(reason_code or '').strip()
    if not raw:
        return '—'
    key = raw.lower()
    return _REASON_LABELS.get(key, raw)


def _translate_counter_keys(counter):
    translated = {}
    for key, val in dict(counter or {}).items():
        ru_key = _translate_reason(key)
        translated[ru_key] = _to_int(translated.get(ru_key, 0), 0) + _to_int(val, 0)
    return translated


def _parse_debug_line(line):
    raw = str(line or '')
    row = {
        'raw': raw,
        'door': '',
        'status': '',
        'reason': '',
        'fields': {}
    }

    m = re.match(r'^\s*door=([^:]+):\s*(.*)$', raw)
    if not m:
        row['status'] = 'info'
        return row

    row['door'] = (m.group(1) or '').strip()
    tail = (m.group(2) or '').strip()

    m_created = re.match(r'^created=(\d+)\s*\(([^)]*)\)\s*(.*)$', tail)
    m_skipped = re.match(r'^skipped\s*\(([^)]*)\)\s*(.*)$', tail)
    m_error = re.match(r'^error\s*\(([^)]*)\)\s*(.*)$', tail)
    m_failed = re.match(r'^failed_to_create\s*\(([^)]*)\)\s*(.*)$', tail)

    if m_created:
        row['status'] = 'created'
        row['reason'] = (m_created.group(2) or '').strip()
    elif m_skipped:
        row['status'] = 'skipped'
        row['reason'] = (m_skipped.group(1) or '').strip()
    elif m_error:
        row['status'] = 'error'
        row['reason'] = (m_error.group(1) or '').strip()
    elif m_failed:
        row['status'] = 'failed'
        row['reason'] = (m_failed.group(1) or '').strip()
    else:
        row['status'] = 'info'

    for mm in re.finditer(r"([A-Za-z0-9_]+)=('([^']*)'|\"([^\"]*)\"|[^ ]+)", tail):
        key = (mm.group(1) or '').strip()
        if not key:
            continue
        val = mm.group(3) if mm.group(3) is not None else (mm.group(4) if mm.group(4) is not None else mm.group(2))
        row['fields'][key] = str(val or '').strip()

    return row


def _build_used_types(rows, fallback=None):
    counter = dict(fallback or {})
    for r in rows:
        if str(r.get('status')) != 'created':
            continue
        fields = dict(r.get('fields') or {})
        symbol = str(fields.get('symbol', '') or '').strip()
        if not symbol:
            continue
        cnt = _to_int(fields.get('created', 1), 1)
        counter[symbol] = _to_int(counter.get(symbol, 0), 0) + cnt
    return counter


def _door_size_text(fields):
    w = str(fields.get('door_w_mm', '') or '').strip()
    h = str(fields.get('door_h_mm', '') or '').strip()
    if w and h:
        return '{0}x{1}'.format(w, h)
    nominal = str(fields.get('nominal_wh_mm', '') or '').strip()
    return nominal or '—'


def _print_door_log_table(output, parsed_rows):
    if not parsed_rows:
        return
    issue_rows = []
    for row in parsed_rows:
        status_key = str(row.get('status', '') or '').strip().lower()
        if status_key in ('skipped', 'error', 'failed'):
            issue_rows.append(row)

    output.print_md('#### Проблемные двери (сводно)')
    if not issue_rows:
        output.print_md('Проблемных дверей нет.')
        return

    grouped = {}
    for r in issue_rows:
        fields = dict(r.get('fields') or {})
        wall_name = _display_value(fields.get('wall', ''), fallback='Без типа стены')
        status_ru = _translate_status(r.get('status', ''))
        reason_ru = _translate_reason(r.get('reason', ''))
        key = (wall_name, status_ru, reason_ru)
        grouped[key] = _to_int(grouped.get(key, 0), 0) + 1

    rows = sorted(grouped.items(), key=lambda x: (-_to_int(x[1], 0), x[0][0].lower(), x[0][1].lower(), x[0][2].lower()))
    if len(rows) > _MAX_ISSUE_LOG_ROWS:
        rows = rows[:_MAX_ISSUE_LOG_ROWS]

    output.print_md('| Тип стены | Результат | Причина | Кол-во дверей |')
    output.print_md('|---|---|---|---:|')
    for key, cnt in rows:
        wall_name, status_ru, reason_ru = key
        output.print_md(
            '| {wall} | {status} | {reason} | {count} |'.format(
                wall=_md_cell(wall_name),
                status=_md_cell(status_ru),
                reason=_md_cell(reason_ru),
                count=_to_int(cnt, 0),
            )
        )


def _find_floor_plan_type(doc):
    if doc is None:
        return None
    try:
        for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.FloorPlan:
                    return vft
            except Exception:
                continue
    except Exception:
        return None
    return None


def _find_view_plan_by_name(doc, view_name):
    if doc is None or not view_name:
        return None
    try:
        for view in DB.FilteredElementCollector(doc).OfClass(DB.ViewPlan):
            try:
                if bool(getattr(view, 'IsTemplate', False)):
                    continue
                if str(getattr(view, 'Name', '') or '').strip() == str(view_name).strip():
                    return view
            except Exception:
                continue
    except Exception:
        return None
    return None


def _set_view_range_at_lintel(view, level, cut_z_ft, bottom_z_ft, top_z_ft):
    if view is None or level is None:
        return False

    cut_z = _to_float(cut_z_ft)
    if cut_z is None:
        return False
    bottom_z = _to_float(bottom_z_ft, cut_z)
    top_z = _to_float(top_z_ft, cut_z)
    level_z = _to_float(getattr(level, 'Elevation', None))
    if level_z is None:
        return False

    margin_ft = _to_float(mm_to_ft(constants.DEBUG_PLAN_VERTICAL_MARGIN_MM), 0.0) or 0.0
    min_range_ft = _to_float(mm_to_ft(constants.DEBUG_PLAN_MIN_RANGE_MM), 0.0) or 0.0

    cut_offset = cut_z - level_z
    bottom_offset = (bottom_z - margin_ft) - level_z
    top_offset = (top_z + margin_ft) - level_z

    if bottom_offset >= cut_offset:
        bottom_offset = cut_offset - max(min_range_ft * 0.5, mm_to_ft(100.0))
    if top_offset <= cut_offset:
        top_offset = cut_offset + max(min_range_ft * 0.5, mm_to_ft(100.0))

    if top_offset - bottom_offset < min_range_ft:
        half = min_range_ft * 0.5
        bottom_offset = min(bottom_offset, cut_offset - half)
        top_offset = max(top_offset, cut_offset + half)

    try:
        vr = view.GetViewRange()
        vr.SetOffset(DB.PlanViewPlane.CutPlane, float(cut_offset))
        vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, float(bottom_offset))
        vr.SetOffset(DB.PlanViewPlane.TopClipPlane, float(top_offset))
        vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, float(bottom_offset))
        view.SetViewRange(vr)
        return True
    except Exception:
        return False


def _apply_debug_plan(doc, res):
    if not isinstance(res, dict):
        return res
    if not bool(getattr(constants, 'DEBUG_CREATE_PLAN_AT_END', False)):
        return res

    cut_z_ft = _to_float(res.get('debug_lintel_cut_z_ft'))
    if cut_z_ft is None:
        return res
    bottom_z_ft = _to_float(res.get('debug_lintel_bottom_z_ft'), cut_z_ft)
    top_z_ft = _to_float(res.get('debug_lintel_top_z_ft'), cut_z_ft)

    level = find_nearest_level(doc, cut_z_ft)
    if level is None:
        res['debug_plan_error'] = 'Не найден ближайший уровень для отладочного плана.'
        return res

    plan_type = _find_floor_plan_type(doc)
    if plan_type is None:
        res['debug_plan_error'] = 'Не найден тип вида Floor Plan.'
        return res

    level_name = str(getattr(level, 'Name', '') or '').strip()
    base_name = str(getattr(constants, 'DEBUG_PLAN_NAME', '') or '').strip() or 'UT_AR_Перемычки_Отладка'
    view_name = '{0} [{1}]'.format(base_name, level_name if level_name else 'Level')

    view = None
    created_now = False
    try:
        with tx('UT AR: Debug Lintel Plan', doc=doc):
            view = _find_view_plan_by_name(doc, view_name)
            if view is None:
                view = DB.ViewPlan.Create(doc, plan_type.Id, level.Id)
                if view is None:
                    res['debug_plan_error'] = 'Не удалось создать отладочный план.'
                    return res
                try:
                    view.Name = view_name
                except Exception:
                    pass
                created_now = True

            if not _set_view_range_at_lintel(view, level, cut_z_ft, bottom_z_ft, top_z_ft):
                res['debug_plan_error'] = 'Не удалось настроить диапазон вида отладочного плана.'
                return res
    except Exception:
        res['debug_plan_error'] = 'Ошибка при создании/обновлении отладочного плана.'
        return res

    try:
        res['debug_plan_name'] = str(getattr(view, 'Name', '') or view_name)
    except Exception:
        res['debug_plan_name'] = view_name
    res['debug_plan_level'] = level_name
    res['debug_plan_cut_mm'] = round(float(ft_to_mm(cut_z_ft)), 1)
    res['debug_plan_created'] = bool(created_now)

    if bool(getattr(constants, 'DEBUG_PLAN_OPEN_AFTER_CREATE', False)):
        try:
            uidoc = revit.uidoc
            if uidoc is not None and view is not None:
                uidoc.ActiveView = view
        except Exception:
            pass
    return res


def _print_summary(output, res):
    if not output or not isinstance(res, dict):
        return
    created = _to_int(res.get('created', 0), 0)
    skipped = _to_int(res.get('skipped', 0), 0)
    errors = _to_int(res.get('errors', 0), 0)
    doors_total = _to_int(res.get('doors_total', 0), 0)
    doors_on_pgp = _to_int(res.get('doors_on_pgp', 0), 0)
    doors_on_ceramic = _to_int(res.get('doors_on_ceramic', 0), 0)
    doors_on_silicate = _to_int(res.get('doors_on_silicate', 0), 0)
    doors_on_other_material = _to_int(res.get('doors_on_other_material', res.get('doors_on_other_walls', 0)), 0)
    doors_on_non_wall_host = _to_int(res.get('doors_on_non_wall_host', 0), 0)
    used_selection = bool(res.get('used_selection', False))
    scope = 'выделение' if used_selection else 'модель'
    lintel_symbol = str(res.get('lintel_symbol', '') or '')
    required_families = [str(x).strip() for x in list(res.get('required_lintel_families') or []) if str(x).strip()]
    missing_families = [str(x).strip() for x in list(res.get('missing_lintel_families') or []) if str(x).strip()]
    required_families_text = ', '.join(required_families) if required_families else 'не указаны'
    missing_families_text = ', '.join(missing_families) if missing_families else 'нет'
    skip_reasons = dict(res.get('skip_reasons') or {})
    error_reasons = dict(res.get('error_reasons') or {})
    debug_samples = list(res.get('debug_samples') or [])
    parsed_rows = [_parse_debug_line(x) for x in debug_samples]
    used_types = _build_used_types(parsed_rows, fallback=dict(res.get('used_lintel_types') or {}))
    skip_reasons_ru = _translate_counter_keys(skip_reasons)
    error_reasons_ru = _translate_counter_keys(error_reasons)
    debug_plan_name = str(res.get('debug_plan_name', '') or '').strip()
    debug_plan_error = str(res.get('debug_plan_error', '') or '').strip()
    debug_plan_cut_mm = res.get('debug_plan_cut_mm', None)
    debug_plan_status = debug_plan_name if debug_plan_name else (debug_plan_error or 'не создан')
    debug_plan_cut_text = debug_plan_cut_mm if debug_plan_cut_mm is not None else '—'

    output.print_md('### Перемычки над дверями')
    summary_rows = [
        ('Путь скрипта', os.path.abspath(__file__)),
        ('Область', scope),
        ('Дверей обработано', doors_total),
        ('Дверей в стенах ПГП', doors_on_pgp),
        ('Дверей в стенах из керамического кирпича', doors_on_ceramic),
        ('Дверей в стенах из силикатного кирпича', doors_on_silicate),
        ('Дверей в стенах с другим материалом/типом', doors_on_other_material),
        ('Дверей без хост-стены', doors_on_non_wall_host),
        ('Перемычек создано', created),
        ('Дверей пропущено', skipped),
        ('Ошибок', errors),
        ('Правило шт', 'стена > 120 мм -> 2 шт, иначе 1 шт'),
        ('Семейство/тип перемычки', lintel_symbol if lintel_symbol else 'НЕ НАЙДЕН'),
        ('Требуемые семейства перемычек', required_families_text),
        ('Отсутствующие семейства', missing_families_text),
    ]
    if bool(getattr(constants, 'DEBUG_CREATE_PLAN_AT_END', False)):
        summary_rows.extend([
            ('Отладочный план', debug_plan_status),
            ('Высота сечения отладочного плана, мм', debug_plan_cut_text),
        ])
    _print_kv_table(output, 'Сводка', summary_rows)
    _print_counter_table(output, 'Использованные типы перемычек', used_types, 'Тип')
    _print_counter_table(output, 'Причины пропуска', skip_reasons_ru, 'Причина')
    _print_counter_table(output, 'Причины ошибок', error_reasons_ru, 'Причина')
    _print_door_log_table(output, parsed_rows)


def main():
    doc = revit.doc
    output = script.get_output()
    res = orchestrator.run(doc, output)
    if res is None:
        alert('Инструмент не вернул результат.')
        return
    res = _apply_debug_plan(doc, res)
    _print_summary(output, res)
    missing_families = [str(x).strip() for x in list(res.get('missing_lintel_families') or []) if str(x).strip()]
    required_families = [str(x).strip() for x in list(res.get('required_lintel_families') or []) if str(x).strip()]
    if res.get('doors_total', 0) == 0:
        alert('В текущей области не найдено дверей.')
    elif missing_families:
        alert('Семейства перемычек не найдены в проекте. Загрузите семейства: {0}.'.format(', '.join(missing_families)))
    elif (not res.get('lintel_symbol')) and int(res.get('errors', 0) or 0) > 0:
        alert(
            'Типы перемычек не найдены в загруженных семействах. Проверьте семейства: {0}.'.format(
                ', '.join(required_families) if required_families else 'не указаны'
            )
        )


try:
    main()
except Exception:
    log_exception('Перемычки над дверями: ошибка')
    alert('Инструмент завершился с ошибкой. Подробности в pyRevit Output.')
