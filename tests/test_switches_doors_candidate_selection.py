# -*- coding: utf-8 -*-
"""Regression tests for switch candidate selection in ВыключателиУДверей."""

import os
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))
DOMAIN_DIR = os.path.join(
    ROOT,
    "EOMTemplateTools.extension",
    "EOM.tab",
    "03_ЩитыВыключатели.panel",
    "ВыключателиУДверей.pushbutton",
)
if DOMAIN_DIR not in sys.path:
    sys.path.insert(0, DOMAIN_DIR)


import adapters_switches  # noqa: E402  pylint: disable=wrong-import-position
import domain  # noqa: E402  pylint: disable=wrong-import-position
import orchestrator  # noqa: E402  pylint: disable=wrong-import-position


class _IdentityTransform(object):
    """Identity transform for geometry-focused unit tests."""

    def __init__(self):
        self.Inverse = self

    def OfPoint(self, point):
        return point

    def OfVector(self, vector):
        return vector


def _make_room(room_id, name=u"", center=None):
    room = type("Room", (), {})()
    room.Id = type("RoomId", (), {"IntegerValue": room_id})()
    room.Name = name
    room._center = center
    return room


def test_prefer_farther_candidate_prefers_meaningfully_farther_point():
    current = domain.mm_to_ft(550)
    new = domain.mm_to_ft(720)

    assert adapters_switches.prefer_farther_candidate(current, new) is True


def test_prefer_farther_candidate_ignores_near_equal_distance_within_tolerance():
    current = domain.mm_to_ft(700)
    # +10mm is below default 20mm tolerance
    new = domain.mm_to_ft(710)

    assert adapters_switches.prefer_farther_candidate(current, new) is False


def test_prefer_farther_candidate_accepts_first_candidate_when_current_missing():
    new = domain.mm_to_ft(650)

    assert adapters_switches.prefer_farther_candidate(None, new) is True


def test_select_best_candidate_wet_room_skips_non_corridor_door(monkeypatch):
    room = _make_room(1, u"Санузел")
    bedroom = _make_room(2, u"Спальня")
    corridor = _make_room(3, u"Коридор")

    non_corridor_info = {"from_room": room, "to_room": bedroom, "center": None}
    corridor_info = {"from_room": room, "to_room": corridor, "center": None}

    calls = []

    def _fake_calc(info, place_inside_room, reference_room, link_transform, link_doc):
        calls.append(info)
        return adapters_switches.SwitchPlacementResult(
            adapters_switches.DB.XYZ(1.0, 0.0, 0.0),
            0.0,
            adapters_switches.SwitchPlacementDebug(),
        )

    monkeypatch.setattr(
        orchestrator,
        "get_room_name",
        lambda target: getattr(target, "Name", u"") if target else u"",
    )
    monkeypatch.setattr(orchestrator, "calc_switch_position_with_debug", _fake_calc)

    selection = orchestrator._select_best_candidate_for_room(
        room,
        u"Санузел",
        [(object(), non_corridor_info), (object(), corridor_info)],
        _IdentityTransform(),
        None,
        "sym_1g",
        "sym_2g",
    )

    assert selection is not None
    assert selection["best_info"] is corridor_info
    assert selection["symbol"] == "sym_1g"
    assert calls == [corridor_info]


def test_select_best_candidate_wet_room_accepts_corridor_abbreviation(monkeypatch):
    room = _make_room(11, u"Санузел")
    storage = _make_room(12, u"Кладовая")
    corridor_short = _make_room(13, u"Кор.")

    wrong_info = {"from_room": room, "to_room": storage, "center": None}
    short_corridor_info = {"from_room": room, "to_room": corridor_short, "center": None}

    calls = []

    def _fake_calc(info, place_inside_room, reference_room, link_transform, link_doc):
        calls.append(info)
        return adapters_switches.SwitchPlacementResult(
            adapters_switches.DB.XYZ(1.0, 0.0, 0.0),
            0.0,
            adapters_switches.SwitchPlacementDebug(),
        )

    monkeypatch.setattr(
        orchestrator,
        "get_room_name",
        lambda target: getattr(target, "Name", u"") if target else u"",
    )
    monkeypatch.setattr(orchestrator, "calc_switch_position_with_debug", _fake_calc)

    selection = orchestrator._select_best_candidate_for_room(
        room,
        u"Санузел",
        [(object(), wrong_info), (object(), short_corridor_info)],
        _IdentityTransform(),
        None,
        "sym_1g",
        "sym_2g",
    )

    assert selection is not None
    assert selection["best_info"] is short_corridor_info
    assert calls == [short_corridor_info]


def test_select_best_candidate_reports_wet_skip_reason_when_no_corridor(monkeypatch):
    room = _make_room(21, u"Ванная 2")
    bedroom = _make_room(22, u"Спальня")
    kitchen = _make_room(23, u"Кухня")

    bedroom_info = {"from_room": room, "to_room": bedroom, "center": None}
    kitchen_info = {"from_room": room, "to_room": kitchen, "center": None}

    monkeypatch.setattr(
        orchestrator,
        "get_room_name",
        lambda target: getattr(target, "Name", u"") if target else u"",
    )

    diagnostics = {}
    selection = orchestrator._select_best_candidate_for_room(
        room,
        u"Ванная 2",
        [(object(), bedroom_info), (object(), kitchen_info)],
        _IdentityTransform(),
        None,
        "sym_1g",
        "sym_2g",
        diagnostics=diagnostics,
    )

    assert selection is None
    assert diagnostics.get("skip_reason") == "WET_ROOM_HAS_NO_CORRIDOR_ADJACENT_DOOR"
    assert diagnostics.get("wet_rejected") == 2


def test_select_best_candidate_corridor_prefers_farther_entrance(monkeypatch):
    room = _make_room(10, u"Прихожая")

    info_non_entrance = {
        "entrance": False,
        "center": adapters_switches.DB.XYZ(0.0, 0.0, 0.0),
    }
    info_entrance_near = {
        "entrance": True,
        "center": adapters_switches.DB.XYZ(0.0, 0.0, 0.0),
    }
    info_entrance_far = {
        "entrance": True,
        "center": adapters_switches.DB.XYZ(0.0, 0.0, 0.0),
    }

    def _fake_is_entrance(info):
        return bool(info.get("entrance"))

    def _fake_calc(info, place_inside_room, reference_room, link_transform, link_doc):
        if info is info_entrance_near:
            point = adapters_switches.DB.XYZ(1.0, 0.0, 0.0)
        elif info is info_entrance_far:
            point = adapters_switches.DB.XYZ(3.0, 0.0, 0.0)
        else:
            point = adapters_switches.DB.XYZ(99.0, 0.0, 0.0)
        return adapters_switches.SwitchPlacementResult(
            point,
            0.0,
            adapters_switches.SwitchPlacementDebug(),
        )

    monkeypatch.setattr(orchestrator, "is_entrance_door", _fake_is_entrance)
    monkeypatch.setattr(orchestrator, "calc_switch_position_with_debug", _fake_calc)

    selection = orchestrator._select_best_candidate_for_room(
        room,
        u"Прихожая",
        [
            (object(), info_non_entrance),
            (object(), info_entrance_near),
            (object(), info_entrance_far),
        ],
        _IdentityTransform(),
        None,
        "sym_1g",
        "sym_2g",
    )

    assert selection is not None
    assert selection["best_info"] is info_entrance_far
    assert selection["selected_candidate_index"] == 2


def test_calc_switch_position_forces_flip_outside_when_point_stays_in_reference_room(monkeypatch):
    identity = _IdentityTransform()
    reference_room = _make_room(101, u"Санузел", center=adapters_switches.DB.XYZ(5.0, -5.0, 0.0))
    corridor_room = _make_room(102, u"Коридор", center=adapters_switches.DB.XYZ(5.0, 5.0, 0.0))

    door_info = {
        "center": adapters_switches.DB.XYZ(5.0, 0.0, 0.0),
        "hand": None,
        "facing": None,
        "wall_p0": adapters_switches.DB.XYZ(0.0, 0.0, 0.0),
        "wall_p1": adapters_switches.DB.XYZ(10.0, 0.0, 0.0),
        "wall_width": 0.4,
        "width": domain.mm_to_ft(900),
        "from_room": reference_room,
        "to_room": corridor_room,
        "wall": None,
        "type_name": u"",
    }

    monkeypatch.setattr(
        adapters_switches,
        "get_room_center",
        lambda room: getattr(room, "_center", None) if room else None,
    )

    def _fake_is_point_in_room_host(room, point_host, link_transform):
        if room is None or point_host is None:
            return None

        # Probe points are farther from wall than final/alt surface points.
        if abs(point_host.Y) > 0.3:
            return None

        if room is reference_room:
            return point_host.Y > 0
        if room is corridor_room:
            return point_host.Y < 0
        return None

    monkeypatch.setattr(adapters_switches, "_is_point_in_room_host", _fake_is_point_in_room_host)

    result = adapters_switches.calc_switch_position_with_debug(
        door_info,
        place_inside_room=False,
        reference_room=reference_room,
        link_transform=identity,
        link_doc=None,
    )
    point = result.point

    assert point is not None
    assert point.Y < 0
    assert result.debug.forced_flip_outside is True
    assert result.debug.surface_source == "forced_flip_outside"


def test_calc_switch_position_keeps_backward_compatible_tuple_api(monkeypatch):
    expected_point = adapters_switches.DB.XYZ(1.0, 2.0, 3.0)
    expected_rotation = 0.123
    fake_result = adapters_switches.SwitchPlacementResult(
        expected_point,
        expected_rotation,
        adapters_switches.SwitchPlacementDebug(),
    )
    monkeypatch.setattr(
        adapters_switches,
        "calc_switch_position_with_debug",
        lambda *args, **kwargs: fake_result,
    )

    point, rotation = adapters_switches.calc_switch_position(
        door_info={},
        place_inside_room=True,
        reference_room=None,
        link_transform=None,
        link_doc=None,
    )

    assert point is expected_point
    assert rotation == expected_rotation


def test_calc_switch_position_from_separation_line_respects_inside_outside_fallback(monkeypatch):
    identity = _IdentityTransform()
    room = _make_room(501, u"Комната", center=adapters_switches.DB.XYZ(5.0, 4.0, 0.0))

    sep_line_info = {
        "line_center": adapters_switches.DB.XYZ(5.0, 0.0, 0.0),
        "line_direction": adapters_switches.DB.XYZ(1.0, 0.0, 0.0),
        "line_length": domain.mm_to_ft(1000),
    }

    monkeypatch.setattr(
        adapters_switches,
        "find_wall_near_point",
        lambda link_doc, link_transform, point, search_radius_mm=1000: (
            object(),
            adapters_switches.DB.XYZ(0.0, 0.0, 0.0),
            adapters_switches.DB.XYZ(10.0, 0.0, 0.0),
            0.4,
        ),
    )
    monkeypatch.setattr(
        adapters_switches,
        "get_room_center",
        lambda target: getattr(target, "_center", None) if target else None,
    )
    monkeypatch.setattr(adapters_switches, "_is_point_in_room_host", lambda room, point, link_transform: None)

    point_inside, _ = adapters_switches.calc_switch_position_from_separation_line(
        sep_line_info,
        room,
        identity,
        link_doc=object(),
        place_inside_room=True,
    )
    point_outside, _ = adapters_switches.calc_switch_position_from_separation_line(
        sep_line_info,
        room,
        identity,
        link_doc=object(),
        place_inside_room=False,
    )

    assert point_inside is not None
    assert point_outside is not None
    assert point_inside.Y > 0
    assert point_outside.Y < 0
