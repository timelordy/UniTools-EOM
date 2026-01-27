# -*- coding: utf-8 -*-

import sys
import os

# Add lib path to sys.path
try:
    lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib')
    if lib_path not in sys.path:
        sys.path.append(lib_path)
except Exception:
    pass

from pyrevit import revit, script
from utils_revit import log_exception
from time_savings import report_time_saved
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    created = orchestrator.run(doc, output)
    if created:
        # Подсчитаем размещенные элементы для отчета о времени
        # created - это словарь с информацией по комнатам
        # Для отчета о времени используем количество созданных элементов
        total_elements = 0
        for room_data in created.values():
            if room_data.get('created'):
                total_elements += 1  # Одна комната = 3 элемента (щиток, выключатель, светильник)
        report_time_saved(output, 'storage_equipment', total_elements)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_exception('Error in 08_Кладовые')
