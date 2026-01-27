# -*- coding: utf-8 -*-

import io
import os

from pyrevit import revit, forms

import clr
clr.AddReference("System.Drawing")
from System.Drawing import Icon  # noqa: E402


def _get_repo_root():
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", "..", "..", "..", "..", ".."))


def _load_icon(icon_path):
    try:
        return Icon(icon_path)
    except Exception:
        return None


ROOT = _get_repo_root()
RES_DIR = os.path.join(ROOT, "tools", "teslabim_resources")
SCRIPT_PATH = os.path.join(RES_DIR, "Syncscheme.py")
ICON_PATH = os.path.join(RES_DIR, "TeslaLogo.ico")

if not os.path.exists(SCRIPT_PATH):
    forms.alert(u"Не найден ресурс Syncscheme.py", title=u"Синхронизация", warn_icon=True)
    raise SystemExit

doc = revit.doc
uidoc = revit.uidoc

globals_dict = {
    "__file__": SCRIPT_PATH,
    "doc": doc,
    "uidoc": uidoc,
    "avt_family_names": [
        u"TSL_2D автоматический выключатель_ВРУ",
        u"TSL_2D автоматический выключатель_Щит",
    ],
    "using_auxiliary_cables": [
        u"TSL_Кабель",
        u"TSL_Кабель с текстом 1.8",
    ],
    "Control_board_family_names": [
        u"TSL_Ящик управления",
    ],
    "Control_board_family_names_Model": [
        u"EE_ШУВ",
    ],
    "using_calculated_tables": [
        u"TSL_Таблица_Расчетная для схемы",
        u"TSL_Таблица_Расчетная для щитов",
    ],
    "fam_param_names": [
        u"ADSK_Единица измерения",
        u"ADSK_Завод-изготовитель",
        u"ADSK_Наименование",
        u"ADSK_Обозначение",
    ],
    "Param_Py": "Py",
    "Param_Kc": "Kc",
    "Param_Cable_length": u"Длина проводника",
    "Param_Circuit_number": u"Номер цепи",
    "Param_3phase_CB": u"3-фазный аппарат",
    "Param_Accessory": u"Принадлежность щиту",
    "Param_PanelName": u"Имя панели",
    "Param_Circuit_breaker_nominal": u"Уставка аппарата",
    "Param_Cosf": "Cosf",
    "Param_Electric_receiver_Name": u"Наименование электроприёмника",
    "Param_Room_Name": u"Наименование помещения",
    "Param_Consumers_count": u"Число электроприёмников",
    "Guidstr": "c94ca2e5-771e-407d-9c09-f62feb4448b6",
    "FieldName_for_Tesla_settings": "Tesla_settings_list",
    "Cable_stock_for_Tesla_settings": "Cable_stock_for_circuitry",
    "Electrical_Circuit_PathMode_method_for_Tesla_settings": "Electrical_Circuit_PathMode_method",
    "Param_Laying_Method": u"Способ прокладки",
    "Param_FarestWireLength": u"Длина проводника до дальнего устройства",
    "Param_ReducedWireLength": u"Длина проводника приведённая",
    "Param_TSL_FarestWireLength": u"TSL_Длина проводника до дальнего устройства",
    "Param_TSL_ReducedWireLength": u"TSL_Длина проводника приведённая",
    "Guidstr_Param_Names_Storage": "44bf8d44-4a4a-4fde-ada8-cd7d802648c4",
    "SchemaName_for_Param_Names_Storage": "Param_Names_Storage",
    "FieldName_for_Param_Names_Storage": "Param_Names_Storage_list",
    "iconmy": _load_icon(ICON_PATH),
}

with io.open(SCRIPT_PATH, "r", encoding="utf-8") as handle:
    code = handle.read()

exec(compile(code, SCRIPT_PATH, "exec"), globals_dict, globals_dict)
