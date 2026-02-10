# -*- coding: utf-8 -*-
"""Оркестратор размещения щитов ШК над входными дверями квартир.

Orchestration Layer:
- Координирует domain и adapters
- Управляет workflow размещения
- Обрабатывает пользовательский ввод
- Управляет транзакциями и прогресс-барами
"""

# =========================================================================
# ВРЕМЕННОЕ РЕШЕНИЕ: Весь код main() пока импортируется из script_helpers
# =========================================================================
#
# Для завершения рефакторинга код функции main() из script_refactored_phase1.py
# должен быть перемещён сюда как функция run(doc, uidoc, output).
#
# На данный момент, чтобы не нарушить работоспособность, мы используем
# прямой импорт из script_refactored_phase1.py
#
# TODO Phase 4 (следующая итерация):
# 1. Скопировать функцию main() из script_refactored_phase1.py
# 2. Переименовать в run(doc, uidoc, output)
# 3. Добавить все необходимые импорты
# 4. Переместить helper-функции в adapters.py
# =========================================================================

def run(doc, uidoc, output):
    """Главная функция оркестратора размещения щитов ШК.

    Args:
        doc: Revit Document (ЭОМ модель)
        uidoc: UI Document
        output: pyRevit output object

    Returns:
        dict: Статистика размещения для Hub интеграции
    """
    # Временно делегируем выполнение в script_refactored_phase1.main()
    # который содержит полный функционал
    import sys
    import os

    # Добавляем текущую директорию в путь для импорта
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        # Импортируем как модуль из той же директории
        import script_refactored_phase1 as refactored
        return refactored.main()
    except ImportError as e:
        # Fallback на оригинальный script.py если refactored не найден
        output.print_md('**ОШИБКА:** orchestrator.py не может найти script_refactored_phase1.py')
        output.print_md('Причина: {}'.format(str(e)))
        output.print_md('Используйте оригинальный script.py или завершите рефакторинг.')
        return None
    except Exception as e:
        output.print_md('**ОШИБКА выполнения:** {}'.format(str(e)))
        raise
