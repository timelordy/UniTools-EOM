# -*- coding: utf-8 -*-
"""Static check for PostCommand gating flag."""

from pathlib import Path


def test_postcommand_gate_flag_present():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "EOMTemplateTools.extension" / "EOM.tab" / "01_Хаб.panel" / "Hub.pushbutton" / "script.py"
    content = script_path.read_text(encoding="utf-8")
    assert "EOM_HUB_USE_POSTCOMMAND" in content
