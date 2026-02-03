# -*- coding: utf-8 -*-
"""Static checks for pyRevit command execution path in Hub."""

from pathlib import Path


def _read_lines():
    root = Path(__file__).resolve().parents[1]
    script_path = (
        root
        / "EOMTemplateTools.extension"
        / "EOM.tab"
        / "01_Хаб.panel"
        / "Hub.pushbutton"
        / "script.py"
    )
    return script_path.read_text(encoding="utf-8").splitlines()


def _slice_between(lines, start_marker, end_marker):
    start = None
    end = None
    for idx, line in enumerate(lines):
        if start is None and start_marker in line:
            start = idx
            continue
        if start is not None and end_marker in line:
            end = idx
            break
    if start is None:
        return []
    return lines[start : end if end is not None else len(lines)]


def test_process_tool_uses_pyrevit_command_before_exec():
    lines = _read_lines()
    block = _slice_between(lines, "def process_tool", "exec(script_code")
    assert block, "process_tool block not found"
    assert any("run_tool_via_pyrevit_command" in line for line in block), (
        "Expected pyRevit command execution path before direct exec"
    )


def test_pyrevit_command_helper_present():
    lines = _read_lines()
    assert any("def _run_tool_via_pyrevit_command" in line for line in lines)


def test_pyrevit_command_uses_unique_name():
    lines = _read_lines()
    assert any("GenericUIComponent.make_unique_name" in line for line in lines)
    assert any("sessionmgr.execute_command" in line for line in lines)
