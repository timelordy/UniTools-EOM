# -*- coding: utf-8 -*-
"""Волшебная кнопка - запускает все основные скрипты по порядку.

Последовательность:
1. Свет по центру
2. Розетки общие
3. Розетки кухня
4. Влажная зона
5. Слаботочка
6. ШДУП
7. Выключатели у дверей
8. Щит над дверью
9. Свет в лифтах
"""

import sys
import os
import io

from pyrevit import revit, script, forms

# Import shared context - should be available via proper pythonpath
try:
    import magic_context
    import link_reader
    import adapters # Assumes adapters is available in path or we load it differently? 
    # Actually adapters is usually local to scripts, but let's see. 
    # We'll rely on link_reader which is in lib.
except ImportError:
    # Attempt to fix path
    ext_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    lib_path = os.path.join(ext_dir, 'lib')
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)
    import magic_context
    import link_reader


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()


def get_extension_dir():
    """Получить путь к extension."""
    try:
        return os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )
    except:
        return None


def run_script(script_rel_path, script_name):
    """Запустить скрипт."""
    output.print_md("\n## 🚀 {}".format(script_name))
    
    try:
        ext_dir = get_extension_dir()
        if not ext_dir:
            output.print_md("❌ Не удалось найти extension")
            return False, 0.0
        
        script_path = os.path.normpath(os.path.join(ext_dir, script_rel_path))
        
        if not os.path.exists(script_path):
            output.print_md("❌ Скрипт не найден: `{}`".format(script_path))
            return False, 0.0
        
        # Добавляем директорию скрипта в sys.path
        script_dir = os.path.dirname(script_path)
        old_path = list(sys.path)
        
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        try:
            # Clean sys.modules to force reload of script-local modules
            to_remove = [m for m in sys.modules if m in ['orchestrator', 'adapters', 'constants', 'domain', 'logic']]
            for m in to_remove:
                del sys.modules[m]

            # Выполняем скрипт
            # Use runpy or exec? exec allows us to keep the same globals if needed, 
            # but usually we want a fresh scope.
            # However, we need 'magic_context' to be visible/effective. 
            # Since 'magic_context' is a module in sys.modules, it persists across execs.
            
            with io.open(script_path, 'r', encoding='utf-8') as f:
                code = compile(f.read(), script_path, 'exec')
                
            exec_globals = {
                '__name__': '__main__',
                '__file__': script_path,
                '__revit__': revit.uiapp,
                '__window__': None
            }
            exec(code, exec_globals)
            
            minutes_min = 0.0
            minutes_max = 0.0
            try:
                hub_res = exec_globals.get('EOM_HUB_RESULT')
                if isinstance(hub_res, dict):
                    mn = hub_res.get('time_saved_minutes_min', None)
                    mx = hub_res.get('time_saved_minutes_max', None)
                    avg = hub_res.get('time_saved_minutes', None)
                    if mn is not None and mx is not None:
                        minutes_min = float(mn)
                        minutes_max = float(mx)
                    elif avg is not None:
                        minutes_min = float(avg)
                        minutes_max = float(avg)
            except Exception:
                pass

            output.print_md("✅ Завершено (saved: {:.1f}–{:.1f} min)".format(minutes_min, minutes_max))
            return True, minutes_min, minutes_max
            
        except SystemExit:
            # Script might call sys.exit() on simple returns
            output.print_md("✅ Завершено (выход)")
            return True, 0.0, 0.0
        except Exception as e:
            output.print_md("❌ Ошибка: {}".format(e))
            # import traceback
            # output.print_md("```\n{}\n```".format(traceback.format_exc()))
            return False, 0.0, 0.0
        finally:
            # Восстанавливаем sys.path
            sys.path[:] = old_path
            
    except Exception as e:
        output.print_md("❌ Общая ошибка: {}".format(e))
        return False, 0.0, 0.0


def main():
    output.print_md("# 🪄 Волшебная кнопка")
    output.print_md("---")
    
    # 1. Automatic Link Selection
    link_inst = link_reader.select_link_instance_auto(doc)
    
    if not link_inst:
        output.print_md("❌ Связь АР не найдена (автоматически). Проверьте, загружена ли связь.")
        return

    # 2. Ask for Levels
    link_doc = link_inst.GetLinkDocument()
    if not link_doc:
        output.print_md("❌ Связь не загружена. Отмена.")
        return
        
    selected_levels = link_reader.select_levels_multi(link_doc, title='Выберите этаж(и) для обработки')
    if not selected_levels:
        output.print_md("❌ Уровни не выбраны. Отмена.")
        return

    # 3. Setup Context
    magic_context.IS_RUNNING = True
    magic_context.SELECTED_LINK = link_inst
    magic_context.SELECTED_LEVELS = selected_levels

    try:
        # 4. List of scripts in desired order
        # 1. свет по центру
        # 2. розетки общие
        # 3. розетки кухня
        # 4 влажная зона
        # 5 .слаботочка
        # 6. шдуп
        # 7. выключатели у дверей
        # 8. щит над дверью 
        # 9 свет в лифтах

        scripts = [
            ("EOM.tab/02_Освещение.panel/СветПоЦентру.pushbutton/script.py", "1. Свет по центру"),
            ("EOM.tab/04_Розетки.panel/01_Общие.pushbutton/script.py", "2. Розетки общие (бытовые)"),
            ("EOM.tab/04_Розетки.panel/03_КухняОбщие.pushbutton/script.py", "3. Розетки кухня"),
            ("EOM.tab/04_Розетки.panel/05_ВлажныеЗоны.pushbutton/script.py", "4. Розетки влажная зона"),
            ("EOM.tab/04_Розетки.panel/07_ШДУП.pushbutton/script.py", "5. ШДУП"),
            ("EOM.tab/04_Розетки.panel/06_Слаботочка.pushbutton/script.py", "6. Слаботочка"),
            ("EOM.tab/03_ЩитыВыключатели.panel/ЩитНадДверью.pushbutton/script.py", "7. Щит над дверью"),
            ("EOM.tab/03_ЩитыВыключатели.panel/ВыключателиУДверей.pushbutton/script.py", "8. Выключатели у дверей"),
        ]
        
        success = 0
        failed = 0
        
        total_time_saved_min = 0.0
        total_time_saved_max = 0.0

        for script_path, name in scripts:
            is_ok, minutes_min, minutes_max = run_script(script_path, name)
            if is_ok:
                success += 1
                total_time_saved_min += minutes_min
                total_time_saved_max += minutes_max
            else:
                failed += 1
                # Спрашиваем продолжить?
                if not forms.alert("Ошибка в скрипте '{}'.\n\nПродолжить?".format(name), yes=True, no=True):
                    output.print_md("\n---\n## ⚠️ Прервано пользователем")
                    break
        
        output.print_md("\n---")
        output.print_md("## 📊 Итоги")
        output.print_md("- ✅ Успешно: **{}**".format(success))
        output.print_md("- ❌ Ошибок: **{}**".format(failed))
        
        # Report total time saved
        try:
            total_time_saved_avg = (float(total_time_saved_min) + float(total_time_saved_max)) / 2.0

            msg = u"Сэкономлено времени (всего): **{:.1f} минут** (диапазон: {:.1f}–{:.1f})".format(
                total_time_saved_avg, total_time_saved_min, total_time_saved_max
            )
            if total_time_saved_max >= 60:
                msg = u"Сэкономлено времени (всего): **{:.1f} часов** (диапазон: {:.1f}–{:.1f})".format(
                    total_time_saved_avg / 60.0, total_time_saved_min / 60.0, total_time_saved_max / 60.0
                )

            output.print_md(msg)

            global EOM_HUB_RESULT
            EOM_HUB_RESULT = {
                'stats': {'total': success + failed, 'processed': success, 'skipped': 0, 'errors': failed},
                'time_saved_minutes': total_time_saved_avg,
                'time_saved_minutes_min': total_time_saved_min,
                'time_saved_minutes_max': total_time_saved_max,
            }
        except Exception:
            pass

        if failed == 0:
            forms.alert("✅ Готово!\n\nВсе {} скриптов выполнены.".format(success))
        else:
            forms.alert("⚠️ Завершено\n\nУспешно: {}\nОшибок: {}".format(success, failed))

    finally:
        # 5. Reset Context
        magic_context.IS_RUNNING = False
        magic_context.SELECTED_LINK = None
        magic_context.SELECTED_LEVELS = []


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        output.print_md("\n## ❌ Критическая ошибка")
        output.print_md("```\n{}\n```".format(e))
        import traceback
        output.print_md("```\n{}\n```".format(traceback.format_exc()))
