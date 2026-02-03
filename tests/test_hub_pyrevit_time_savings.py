# -*- coding: utf-8 -*-
"""Static checks for time-savings capture in pyRevit command path."""

from pathlib import Path


def _read_script():
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


def test_time_savings_helpers_present():
    lines = _read_script()
    assert any("calculate_time_saved_range" in line for line in lines)
    assert any("time_saved_minutes" in line for line in lines)


def test_time_savings_log_reader_present():
    lines = _read_script()
    assert any("get_last_time_saved_entry" in line for line in lines)
