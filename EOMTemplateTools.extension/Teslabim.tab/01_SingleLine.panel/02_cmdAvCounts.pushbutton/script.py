# -*- coding: utf-8 -*-

import io
import os

from pyrevit import revit, forms

import clr
clr.AddReference("System.Drawing")
from System.Drawing import Icon  # noqa: E402

from unibim.avcounts_globals import get_avcounts_globals


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
SCRIPT_PATH = os.path.join(RES_DIR, "Avcounts.py")
ICON_PATH = os.path.join(RES_DIR, "TeslaLogo.ico")

if not os.path.exists(SCRIPT_PATH):
    forms.alert(u"Не найден ресурс Avcounts.py", title=u"Расчёт схем", warn_icon=True)
    raise SystemExit

doc = revit.doc
uidoc = revit.uidoc

globals_dict = get_avcounts_globals(doc=doc, uidoc=uidoc, icon=_load_icon(ICON_PATH))
globals_dict["__file__"] = SCRIPT_PATH

with io.open(SCRIPT_PATH, "r", encoding="utf-8") as handle:
    code = handle.read()

exec(compile(code, SCRIPT_PATH, "exec"), globals_dict, globals_dict)
