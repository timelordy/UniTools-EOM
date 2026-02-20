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

import link_reader
import magic_context

doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()




from orchestrator import run_placement


def main():
    pairs = link_reader.select_link_level_pairs(
        doc,
        link_title=u'Выберите связь(и) АР',
        level_title=u'Выберите уровни для обработки',
        default_all_links=True,
        default_all_levels=False,
        loaded_only=True
    )
    if not pairs:
        output.print_md('**Отменено (связи/уровни не выбраны).**')
        return

    old_force = bool(getattr(magic_context, 'FORCE_SELECTION', False))
    old_link = getattr(magic_context, 'SELECTED_LINK', None)
    old_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
    old_levels = list(getattr(magic_context, 'SELECTED_LEVELS', []) or [])
    try:
        for pair in pairs:
            link_inst = pair.get('link_instance')
            levels = list(pair.get('levels') or [])
            if link_inst is None or not levels:
                continue

            try:
                link_name = link_inst.Name
            except Exception:
                link_name = u'<Связь>'
            output.print_md(u'## Обработка связи: `{0}`'.format(link_name))

            magic_context.FORCE_SELECTION = True
            magic_context.SELECTED_LINK = link_inst
            magic_context.SELECTED_LINKS = [link_inst]
            magic_context.SELECTED_LEVELS = levels

            run_placement(doc, output, script)
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels
try:
    main()
except Exception:
    log_exception('Place lights failed')
    alert('Tool failed. See pyRevit output for details.')
