# -*- coding: utf-8 -*-
"""Статические регрессионные проверки для оркестрации выключателей у дверей."""

from pathlib import Path


def _tool_dir():
    root = Path(__file__).resolve().parents[1]
    return (
        root
        / "EOMTemplateTools.extension"
        / "EOM.tab"
        / "03_ЩитыВыключатели.panel"
        / "ВыключателиУДверей.pushbutton"
    )


def _read_lines(filename):
    return (_tool_dir() / filename).read_text(encoding="utf-8").splitlines()


def test_orchestrator_uses_prefer_farther_candidate_for_selection():
    lines = _read_lines("room_selection.py")
    matches = [line for line in lines if "prefer_farther_candidate(" in line]
    # Ветка для коридоров + ветка для обычных комнат
    assert len(matches) >= 2


def test_orchestrator_has_per_room_deduplication_set():
    lines = _read_lines("orchestrator.py")
    assert any("processed_room_keys = set()" in line for line in lines)
    assert any("if room_key and room_key in processed_room_keys" in line for line in lines)


def test_orchestrator_wet_rooms_outside_only_in_corridor():
    lines = _read_lines("room_selection.py")
    assert any("if not is_wet_outside_allowed(is_wet, other_name):" in line for line in lines)


def test_script_is_thin_wrapper_and_calls_orchestrator():
    lines = _read_lines("script.py")
    assert any("import orchestrator" in line for line in lines)
    assert any("created = orchestrator.run()" in line for line in lines)
    assert any('"room_selection"' in line for line in lines)
    assert any('"room_policy"' in line for line in lines)
    assert any('"switch_reporting"' in line for line in lines)
    assert len(lines) < 100


def test_adapters_switches_has_forced_flip_for_outside_placement():
    lines = _read_lines("adapters_switches.py")
    assert any("forced_flip_outside" in line for line in lines)
    assert any("if not place_inside_room and reference_room:" in line for line in lines)


def test_orchestrator_has_room_separation_line_fallback_path():
    lines = _read_lines("orchestrator.py")
    assert any("sep_lines = adapter_ports.get_room_separation_lines(" in line for line in lines)
    assert any("if use_separation_line:" in line for line in lines)
    assert any("_try_place_from_separation_line(" in line for line in lines)


def test_orchestrator_delegates_selection_and_reporting_to_services():
    lines = _read_lines("orchestrator.py")
    assert any("from room_selection import select_best_candidate_for_room" in line for line in lines)
    assert any("from switch_reporting import print_selection_debug, publish_single_link_summary" in line for line in lines)


def test_orchestrator_prints_skip_reason_debug_for_unplaced_rooms():
    lines = _read_lines("orchestrator.py")
    assert any("def _print_room_skip_debug(" in line for line in lines)
    assert any("WET_ROOM_HAS_NO_CORRIDOR_ADJACENT_DOOR" in line for line in lines)
    assert any("_print_room_skip_debug(" in line for line in lines)


def test_constants_cover_short_corridor_room_names():
    lines = _read_lines("constants.py")
    assert any('u"кор."' in line for line in lines)
