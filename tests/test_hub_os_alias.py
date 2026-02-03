# -*- coding: utf-8 -*-
"""Static checks for os alias usage in hub helpers."""

from pathlib import Path


def _slice_after(lines, marker, window=80):
    for idx, line in enumerate(lines):
        if marker in line:
            return lines[idx : idx + window]
    return []


def _assert_local_os_import(block):
    assert any("import os as _os" in line for line in block)


def test_get_tool_postcommand_uses_os_alias():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "EOMTemplateTools.extension" / "EOM.tab" / "01_Хаб.panel" / "Hub.pushbutton" / "script.py"
    lines = script_path.read_text(encoding="utf-8").splitlines()

    # Ensure alias exists at module top-level
    assert any("=_os" in line or " _os" in line for line in lines)

    block = _slice_after(lines, "def _get_tool_postcommand_id", window=120)
    assert block, "function _get_tool_postcommand_id not found"
    _assert_local_os_import(block)
    assert any("_os." in line for line in block)


def test_get_postcommand_uses_os_alias():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "EOMTemplateTools.extension" / "EOM.tab" / "01_Хаб.panel" / "Hub.pushbutton" / "script.py"
    lines = script_path.read_text(encoding="utf-8").splitlines()
    block = _slice_after(lines, "def _get_postcommand_id", window=120)
    assert block, "function _get_postcommand_id not found"
    _assert_local_os_import(block)
    assert any("_os." in line for line in block)
