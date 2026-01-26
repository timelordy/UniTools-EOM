# -*- coding: utf-8 -*-
import webbrowser
import os
import os.path as op
from pyrevit import forms

# Получаем путь к корню репозитория
# script.py лежит в: EOMTemplateTools.extension/EOM.tab/00_Hub.panel/01_Hub.pushbutton/script.py
# Нам нужно подняться на 5 уровней вверх
current_dir = op.dirname(__file__)
root_dir = op.abspath(op.join(current_dir, "../../../../"))
html_path = op.join(root_dir, "time-savings-counter.html")

if op.exists(html_path):
    webbrowser.open(html_path)
else:
    forms.alert("Файл time-savings-counter.html не найден по пути:\n{}".format(html_path))
