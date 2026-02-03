# -*- coding: utf-8 -*-
"""Static checks for Hub script closures (pyRevit globals cleanup safety)."""

from pathlib import Path


def test_hub_script_captures_runner_helpers():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "EOMTemplateTools.extension" / "EOM.tab" / "01_Хаб.panel" / "Hub.pushbutton" / "script.py"
    content = script_path.read_text(encoding="utf-8")

    assert "get_tool_postcommand_id = _get_tool_postcommand_id" in content
    assert "set_runner_env = _set_runner_env" in content
    assert "clear_runner_env = _clear_runner_env" in content
    assert "os_mod = _os" in content
