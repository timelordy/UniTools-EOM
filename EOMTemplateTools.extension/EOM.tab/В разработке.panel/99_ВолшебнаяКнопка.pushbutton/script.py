# -*- coding: utf-8 -*-
"""Волшебная кнопка — запускает все основные скрипты по порядку.

Последовательность:
1. 01 - Общие розетки
2. 02 - Кухня блок
3. 05 - Мокрые точки
4. 07 - ШДУП
5. Щит над дверью
6. Выключатели у дверей
7. Свет по центру
"""
from __future__ import unicode_literals

import sys
import os
import io

from pyrevit import revit, script, forms

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()

# Lazy-loaded shared context (after lib is in path)
magic_context = None
link_reader = None
revit_context = None


def _ext_from_path(path):
    if not path:
        return None
    try:
        p = os.path.abspath(path)
    except Exception:
        p = path

    if os.path.isfile(p):
        base = p
        for _ in range(4):
            base = os.path.dirname(base)
        return base if os.path.isdir(base) else None

    if os.path.isdir(p):
        base = p
        for _ in range(3):
            base = os.path.dirname(base)
        return base if os.path.isdir(base) else None

    return None


def get_extension_dir():
    """Получить путь к extension (устойчиво к отсутствию __file__)."""
    candidates = []
    try:
        candidates.append(os.path.abspath(__file__))
    except Exception:
        pass

    try:
        candidates.append(script.get_bundle_file('script.py'))
    except Exception:
        pass

    try:
        candidates.append(script.get_script_path())
    except Exception:
        pass

    for pth in list(sys.path):
        try:
            if pth and pth.lower().endswith(os.path.join('eomtemplatetools.extension', 'lib').lower()):
                candidates.append(os.path.dirname(pth))
        except Exception:
            continue

    for cand in candidates:
        ext_dir = _ext_from_path(cand)
        if ext_dir:
            return ext_dir

    return None


def add_lib_to_path():
    """Добавить lib в sys.path."""
    try:
        # Already present?
        for pth in sys.path:
            if pth and pth.lower().endswith(os.path.join('eomtemplatetools.extension', 'lib').lower()):
                return True
        ext_dir = get_extension_dir()
        if ext_dir:
            lib_path = os.path.join(ext_dir, 'lib')
            if os.path.isdir(lib_path):
                if lib_path not in sys.path:
                    sys.path.insert(0, lib_path)
                return True
    except Exception:
        pass
    return False


def _ensure_magic_imports():
    global magic_context, link_reader, revit_context
    if magic_context is not None and link_reader is not None and revit_context is not None:
        return True
    if not add_lib_to_path():
        return False
    try:
        import magic_context as _mc
        import link_reader as _lr
        import revit_context as _rc
        magic_context = _mc
        link_reader = _lr
        revit_context = _rc
        return True
    except Exception:
        return False


def run_script(script_rel_path, script_name):
    """Запустить скрипт."""
    output.print_md("\n## {}".format(script_name))

    try:
        ext_dir = get_extension_dir()
        if not ext_dir:
            output.print_md("Ошибка: не удалось найти extension")
            return False

        script_path = os.path.normpath(os.path.join(ext_dir, script_rel_path))

        if not os.path.exists(script_path):
            output.print_md("Ошибка: скрипт не найден: `{}`".format(script_path))
            return False

        # Добавляем директорию скрипта в sys.path
        script_dir = os.path.dirname(script_path)
        old_path = list(sys.path)

        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        try:
            # Очищаем модули с пересекающимися именами
            to_remove = [
                'orchestrator', 'adapters', 'constants', 'domain', 'logic',
                'config_loader', 'placement_engine', 'entrance_numbering_utils',
                'utils_revit', 'utils_units'
            ]
            for m in list(sys.modules.keys()):
                if m in to_remove:
                    del sys.modules[m]

            # Выполняем скрипт (UTF-8)
            with io.open(script_path, 'r', encoding='utf-8-sig') as f:
                code = compile(f.read(), script_path, 'exec')
                uiapp = None
                try:
                    uiapp = revit_context.get_uiapp(revit) if revit_context else None
                except Exception:
                    uiapp = None
                exec(
                    code,
                    {
                        '__name__': '__main__',
                        '__file__': script_path,
                        '__revit__': uiapp,
                        '__window__': None,
                    }
                )

            output.print_md("Завершено")
            return True

        except Exception as e:
            output.print_md("Ошибка: {}".format(e))
            import traceback
            output.print_md("```\n{}\n```".format(traceback.format_exc()))
            return False
        finally:
            # Восстанавливаем sys.path
            sys.path = old_path

    except Exception as e:
        output.print_md("Ошибка: {}".format(e))
        return False


def main():
    output.print_md("# Волшебная кнопка")
    output.print_md("---")

    # Добавляем lib
    if not _ensure_magic_imports():
        output.print_md("Ошибка: не удалось загрузить lib (magic_context/link_reader).")
        return

    selected_pairs = link_reader.select_link_level_pairs(
        doc,
        link_title=u'Выберите связь(и) АР',
        level_title=u'Выберите этаж(и) для обработки',
        default_all_links=True,
        default_all_levels=False,
        loaded_only=True
    )
    if not selected_pairs:
        output.print_md("Ошибка: связи/уровни не выбраны. Отмена.")
        return

    # Активируем общий контекст для всех шагов
    magic_context.IS_RUNNING = True
    magic_context.FORCE_SELECTION = True

    scripts = [
        ("EOM.tab/04_Розетки.panel/01_Общие.pushbutton/script.py", "01 - Общие розетки"),
        ("EOM.tab/04_Розетки.panel/02_КухняБлок.pushbutton/script.py", "02 - Кухня блок"),
        ("EOM.tab/04_Розетки.panel/05_МокрыеТочки.pushbutton/script.py", "05 - Мокрые точки"),
        ("EOM.tab/04_Розетки.panel/07_ШДУП.pushbutton/script.py", "07 - ШДУП"),
        ("EOM.tab/03_ЩитыВыключатели.panel/ЩитНадДверью.pushbutton/script.py", "Щит над дверью"),
        ("EOM.tab/03_ЩитыВыключатели.panel/ВыключателиУДверей.pushbutton/script.py", "Выключатели"),
        ("Разработка.tab/03_ЩитыВыключатели_Dev.panel/НумерацияПодъезда.pushbutton/script.py", "Нумерация подъезда"),
        ("EOM.tab/02_Освещение.panel/СветПоЦентру.pushbutton/script.py", "Свет по центру"),
    ]

    success = 0
    failed = 0
    interrupted = False

    for pair in selected_pairs:
        link_inst = pair.get('link_instance')
        levels = list(pair.get('levels') or [])
        if link_inst is None or not levels:
            continue

        try:
            link_name = link_inst.Name
        except Exception:
            link_name = u'<Связь>'
        output.print_md("\n## Связь: `{}`".format(link_name))

        magic_context.SELECTED_LINK = link_inst
        magic_context.SELECTED_LINKS = [link_inst]
        magic_context.SELECTED_LEVELS = levels

        for script_path, name in scripts:
            if run_script(script_path, name):
                success += 1
            else:
                failed += 1
                if not forms.alert("Ошибка в скрипте '{}'.\n\nПродолжить?".format(name), yes=True, no=True):
                    output.print_md("\n---\n## Прервано пользователем")
                    interrupted = True
                    break
        if interrupted:
            break

    magic_context.IS_RUNNING = False
    magic_context.FORCE_SELECTION = False
    magic_context.SELECTED_LINK = None
    magic_context.SELECTED_LINKS = []
    magic_context.SELECTED_LEVELS = []

    output.print_md("\n---")
    output.print_md("## Итоги")
    output.print_md("- Успешно: **{}**".format(success))
    output.print_md("- Ошибок: **{}**".format(failed))

    if failed == 0:
        forms.alert("Готово!\n\nВсе {} скриптов выполнены.".format(success))
    else:
        forms.alert("Завершено\n\nУспешно: {}\nОшибок: {}".format(success, failed))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        output.print_md("\n## Критическая ошибка")
        output.print_md("```\n{}\n```".format(e))
        import traceback
        output.print_md("```\n{}\n```".format(traceback.format_exc()))
