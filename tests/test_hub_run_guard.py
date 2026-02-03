# -*- coding: utf-8 -*-
"""Tests for hub_run_guard helper."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_run_guard import should_defer_run


def test_should_defer_run():
    assert should_defer_run(False, None) is True
    assert should_defer_run(True, None) is False
    assert should_defer_run(True, False) is True
    assert should_defer_run(True, True) is False
