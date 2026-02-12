# -*- coding: utf-8 -*-
"""Static regression checks for switch-door candidate selection in script.py."""

from pathlib import Path


def _read_script_lines():
    root = Path(__file__).resolve().parents[1]
    script_path = (
        root
        / "EOMTemplateTools.extension"
        / "EOM.tab"
        / "03_ЩитыВыключатели.panel"
        / "ВыключателиУДверей.pushbutton"
        / "script.py"
    )
    return script_path.read_text(encoding="utf-8").splitlines()


def test_script_uses_prefer_farther_candidate_for_selection():
    lines = _read_script_lines()
    matches = [line for line in lines if "prefer_farther_candidate(" in line]
    # corridor path + regular rooms path
    assert len(matches) >= 2


def test_script_has_per_room_deduplication_set():
    lines = _read_script_lines()
    assert any("processed_room_keys = set()" in line for line in lines)
    assert any("if room_key and room_key in processed_room_keys" in line for line in lines)


def test_script_wet_rooms_outside_only_in_corridor():
    lines = _read_script_lines()
    assert any("if is_wet and corridor_bonus == 0:" in line for line in lines)


def test_adapters_switches_has_forced_flip_for_outside_placement():
    root = Path(__file__).resolve().parents[1]
    adapters_path = (
        root
        / "EOMTemplateTools.extension"
        / "EOM.tab"
        / "03_ЩитыВыключатели.panel"
        / "ВыключателиУДверей.pushbutton"
        / "adapters_switches.py"
    )
    lines = adapters_path.read_text(encoding="utf-8").splitlines()
    assert any("forced_flip_outside" in line for line in lines)
    assert any("if not place_inside_room and reference_room:" in line for line in lines)
