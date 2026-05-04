# -*- coding: utf-8 -*-
"""Тонкая точка входа для инструмента расстановки выключателей.

Основная бизнес-логика находится в ``orchestrator.py``.
"""

import os
import sys

# pyRevit переиспользует IronPython-движок, поэтому модули с общими именами
# могут остаться в кэше от другой команды. Принудительно берем локальные модули.
_BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BUNDLE_DIR not in sys.path:
    sys.path.insert(0, _BUNDLE_DIR)


def _drop_foreign_module(module_name):
    mod = sys.modules.get(module_name)
    if mod is None:
        return

    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        try:
            del sys.modules[module_name]
        except Exception:
            pass
        return

    try:
        mod_dir = os.path.dirname(os.path.abspath(mod_file))
    except Exception:
        mod_dir = None

    if mod_dir != _BUNDLE_DIR:
        try:
            del sys.modules[module_name]
        except Exception:
            pass


for _module_name in (
    "adapters",
    "adapters_doors",
    "adapters_geometry",
    "adapters_outlets",
    "adapters_symbols",
    "adapters_switches",
    "constants",
    "domain",
    "orchestrator",
    "room_selection",
    "room_policy",
    "switch_reporting",
):
    _drop_foreign_module(_module_name)

import orchestrator


def main():
    created = orchestrator.run()
    try:
        hub_result = getattr(orchestrator, "EOM_HUB_RESULT", None)
        if hub_result is not None:
            global EOM_HUB_RESULT
            EOM_HUB_RESULT = hub_result
    except Exception:
        pass
    return created


if __name__ == "__main__":
    main()
