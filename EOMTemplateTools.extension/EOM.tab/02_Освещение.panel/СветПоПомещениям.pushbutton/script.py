# -*- coding: utf-8 -*-

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

from utils_revit import alert, log_exception, trace, tx
from utils_units import mm_to_ft
from constants import (
    LIGHT_STRONG_KEYWORDS,
    LIGHT_CEILING_KEYWORDS,
    LIGHT_POINT_KEYWORDS,
    LIGHT_NEGATIVE_KEYWORDS,
)
from domain import get_user_config, save_user_config
from adapters import (
    load_symbol_from_saved_id,
    load_symbol_from_saved_unique_id,
    store_symbol_id,
    store_symbol_unique_id,
    as_net_id_list,
    get_or_create_debug_3d_view,
    bbox_from_points,
)
from domain_debug import points_debug_stats


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()




from orchestrator import run_placement


def main():
    run_placement(doc, output, script)
try:
    main()
except Exception:
    log_exception('Place lights failed')
    alert('Tool failed. See pyRevit output for details.')
