# -*- coding: utf-8 -*-
"""Tests for hub_tool_commands helpers."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_tool_commands import parse_command_map, select_command_id_for_tool


def test_parse_command_map_json():
    raw = '{"lights_center": "CMD1", "other": "CMD2"}'
    data = parse_command_map(raw)
    assert data["lights_center"] == "CMD1"
    assert data["other"] == "CMD2"


def test_parse_command_map_lines():
    raw = "# comment\nlights_center=CMD1\nother:CMD2\n"
    data = parse_command_map(raw)
    assert data["lights_center"] == "CMD1"
    assert data["other"] == "CMD2"


def test_select_command_id_for_tool_prefers_env():
    env = "lights_center=ENV_CMD"
    file_raw = "lights_center=FILE_CMD"
    assert select_command_id_for_tool("lights_center", env, file_raw) == "ENV_CMD"


def test_select_command_id_for_tool_bom_key():
    raw = u"\ufefflights_center=CMD1"
    assert select_command_id_for_tool("lights_center", None, raw) == "CMD1"
