# -*- coding: utf-8 -*-

from pyrevit import revit, script

from utils_revit import alert, log_exception
import orchestrator


def _print_summary(output, res):
    if not output or not isinstance(res, dict):
        return
    created = int(res.get('created', 0) or 0)
    skipped = int(res.get('skipped', 0) or 0)
    errors = int(res.get('errors', 0) or 0)
    family_created = int(res.get('family_created', 0) or 0)
    placeholder_created = int(res.get('placeholder_created', 0) or 0)
    family_symbols_total = int(res.get('family_symbols_total', 0) or 0)
    doors_total = int(res.get('doors_total', 0) or 0)
    used_selection = bool(res.get('used_selection', False))
    scope = 'выделение' if used_selection else 'модель'
    used_symbols = res.get('used_symbols', {}) or {}

    output.print_md('### Перемычки над дверями')
    output.print_md('* Область: `{0}`'.format(scope))
    output.print_md('* Дверей обработано: `{0}`'.format(doors_total))
    output.print_md('* Подходящих типов перемычек в модели: `{0}`'.format(family_symbols_total))
    output.print_md('* Перемычек создано: `{0}`'.format(created))
    output.print_md('* Создано через семейства: `{0}`'.format(family_created))
    output.print_md('* Создано болванками (DirectShape): `{0}`'.format(placeholder_created))
    output.print_md('* Дверей пропущено: `{0}`'.format(skipped))
    if used_symbols:
        for key in sorted(used_symbols.keys()):
            output.print_md('* Тип: `{0}` -> `{1}`'.format(key, int(used_symbols.get(key) or 0)))
    if errors:
        output.print_md('* Ошибок: `{0}`'.format(errors))


def main():
    doc = revit.doc
    output = script.get_output()
    res = orchestrator.run(doc, output)
    if res is None:
        alert('Инструмент не вернул результат.')
        return
    _print_summary(output, res)
    if res.get('doors_total', 0) == 0:
        alert('В текущей области не найдено дверей.')


try:
    main()
except Exception:
    log_exception('Перемычки над дверями: ошибка')
    alert('Инструмент завершился с ошибкой. Подробности в pyRevit Output.')
