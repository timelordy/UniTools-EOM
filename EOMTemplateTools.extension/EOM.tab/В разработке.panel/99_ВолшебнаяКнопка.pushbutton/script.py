# -*- coding: utf-8 -*-
"""Волшебная кнопка - запускает все основные скрипты по порядку.

Последовательность:
1. 01 - Общие розетки
2. 02 - Кухня блок  
3. 05 - Влажные зоны
4. 07 - ШДУП
5. Щит над дверью
6. Выключатели у дверей
7. Свет по центру
"""

import sys
import os

from pyrevit import revit, script, forms

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()


def get_extension_dir():
    """Получить путь к extension."""
    try:
        # __file__ -> .../99_ВолшебнаяКнопка.pushbutton/script.py
        # -> .../99_Обслуживание.panel
        # -> .../EOM.tab
        # -> .../EOMTemplateTools.extension
        return os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        )
    except:
        return None


def add_lib_to_path():
    """Добавить lib в sys.path."""
    try:
        ext_dir = get_extension_dir()
        if ext_dir:
            lib_path = os.path.join(ext_dir, 'lib')
            if lib_path not in sys.path:
                sys.path.insert(0, lib_path)
            return True
    except:
        pass
    return False


def run_script(script_rel_path, script_name):
    """Запустить скрипт."""
    output.print_md("\n## 🚀 {}".format(script_name))
    
    try:
        ext_dir = get_extension_dir()
        if not ext_dir:
            output.print_md("❌ Не удалось найти extension")
            return False
        
        script_path = os.path.normpath(os.path.join(ext_dir, script_rel_path))
        
        if not os.path.exists(script_path):
            output.print_md("❌ Скрипт не найден: `{}`".format(script_path))
            return False
        
        # Добавляем директорию скрипта в sys.path
        script_dir = os.path.dirname(script_path)
        old_path = list(sys.path)
        
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        try:
            # Выполняем скрипт
            with open(script_path, 'r') as f:
                code = compile(f.read(), script_path, 'exec')
                exec(code, {'__name__': '__main__', '__file__': script_path})
            
            output.print_md("✅ Завершено")
            return True
            
        except Exception as e:
            output.print_md("❌ Ошибка: {}".format(e))
            import traceback
            output.print_md("```\n{}\n```".format(traceback.format_exc()))
            return False
        finally:
            # Восстанавливаем sys.path
            sys.path = old_path
            
    except Exception as e:
        output.print_md("❌ Общая ошибка: {}".format(e))
        return False


def main():
    output.print_md("# 🪄 Волшебная кнопка")
    output.print_md("---")
    
    # Добавляем lib
    add_lib_to_path()
    
    # Список скриптов
    scripts = [
        ("EOM.tab/04_Розетки.panel/01_Общие.pushbutton/script.py", "01 - Общие розетки"),
        ("EOM.tab/04_Розетки.panel/02_КухняБлок.pushbutton/script.py", "02 - Кухня блок"),
        ("EOM.tab/04_Розетки.panel/05_ВлажныеЗоны.pushbutton/script.py", "05 - Влажные зоны"),
        ("EOM.tab/04_Розетки.panel/07_ШДУП.pushbutton/script.py", "07 - ШДУП"),
        ("EOM.tab/03_ЩитыВыключатели.panel/ЩитНадДверью.pushbutton/script.py", "Щит над дверью"),
        ("EOM.tab/03_ЩитыВыключатели.panel/ВыключателиУДверей.pushbutton/script.py", "Выключатели"),
        ("EOM.tab/03_ЩитыВыключатели.panel/НумерацияПодъезда.pushbutton/script.py", "Нумерация подъезда"),
        ("EOM.tab/02_Освещение.panel/СветПоЦентру.pushbutton/script.py", "Свет по центру"),
    ]
    
    success = 0
    failed = 0
    
    for script_path, name in scripts:
        if run_script(script_path, name):
            success += 1
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
    
    if failed == 0:
        forms.alert("✅ Готово!\n\nВсе {} скриптов выполнены.".format(success))
    else:
        forms.alert("⚠️ Завершено\n\nУспешно: {}\nОшибок: {}".format(success, failed))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        output.print_md("\n## ❌ Критическая ошибка")
        output.print_md("```\n{}\n```".format(e))
        import traceback
        output.print_md("```\n{}\n```".format(traceback.format_exc()))
