# -*- coding: utf-8 -*-
"""Tests for hub_postcommand helper functions."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_postcommand import normalize_command_id, select_command_id


def test_normalize_command_id():
    assert normalize_command_id(None) is None
    assert normalize_command_id("") is None
    assert normalize_command_id("   ") is None
    assert normalize_command_id(" ABC ") == "ABC"
    assert normalize_command_id(u"\ufeffCMD") == "CMD"


def test_select_command_id_prefers_env():
    assert select_command_id("ENV", "FILE") == "ENV"
    assert select_command_id("", "FILE") == "FILE"
    assert select_command_id(None, " FILE ") == "FILE"
    assert select_command_id("   ", None) is None

