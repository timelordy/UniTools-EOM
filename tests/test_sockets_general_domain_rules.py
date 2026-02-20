# -*- coding: utf-8 -*-
"""Regression tests for socket general domain rules."""
import importlib.util
import os
import sys

import pytest


ROOT = os.path.dirname(os.path.dirname(__file__))
DOMAIN_PATH = os.path.join(
    ROOT,
    "EOMTemplateTools.extension",
    "EOM.tab",
    "04_Розетки.panel",
    "01_Общие.pushbutton",
    "domain.py",
)


def _load_domain_module():
    module_dir = os.path.dirname(DOMAIN_PATH)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    # Ensure local 01_Общие constants/domain are loaded for this test module.
    sys.modules.pop("domain", None)
    sys.modules.pop("constants", None)

    spec = importlib.util.spec_from_file_location("sockets_general_domain_test", DOMAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_count_uses_tolerance_for_exact_spacing_multiple():
    domain = _load_domain_module()
    spacing_ft = domain.mm_to_ft(3000.0)

    exact_len_ft = domain.mm_to_ft(12000.0)
    near_exact_plus_half_mm_ft = domain.mm_to_ft(12000.5)
    above_tolerance_plus_two_mm_ft = domain.mm_to_ft(12002.0)

    assert domain.calc_general_socket_count_and_step(exact_len_ft, spacing_ft)[0] == 4
    assert domain.calc_general_socket_count_and_step(near_exact_plus_half_mm_ft, spacing_ft)[0] == 4
    assert domain.calc_general_socket_count_and_step(above_tolerance_plus_two_mm_ft, spacing_ft)[0] == 5


def test_build_wall_filter_keeps_default_kzh_and_facade_markers():
    domain = _load_domain_module()
    wall_filter = domain.build_wall_filter(
        {
            "socket_general_monolith_wall_name_patterns": [],
            "socket_general_exterior_wall_name_patterns": [],
            "socket_general_facade_wall_name_patterns": [],
        }
    )

    monolith_patterns = [getattr(rx, "pattern", "") for rx in (wall_filter.get("monolith_rx") or [])]
    exterior_patterns = [getattr(rx, "pattern", "") for rx in (wall_filter.get("exterior_rx") or [])]
    facade_patterns = [getattr(rx, "pattern", "") for rx in (wall_filter.get("facade_rx") or [])]

    assert any(u"кж" in p for p in monolith_patterns)
    assert any(u"бетон" in p for p in monolith_patterns)
    assert any(u"наруж" in p for p in exterior_patterns)
    assert any(u"нр_" in p for p in facade_patterns)
    assert wall_filter.get("exterior_by_geom") is True
    assert wall_filter.get("exterior_requires_openings") is True


class _DummyCurve(object):
    def __init__(self, length):
        self.Length = float(length)


class _DummySegment(object):
    def __init__(self, element_id, length):
        self.ElementId = element_id
        self._curve = _DummyCurve(length)

    def GetCurve(self):
        return self._curve


class _DummyWall(object):
    def __init__(self, name, is_exterior=False, is_structural=False, is_monolith=False):
        self.Name = name
        self.is_exterior = bool(is_exterior)
        self.is_structural = bool(is_structural)
        self.is_monolith = bool(is_monolith)
        self.WallType = type("WallType", (), {"Name": name, "FamilyName": "Basic"})()


class _DummySeparator(object):
    pass


class _DummyLinkDoc(object):
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def GetElement(self, element_id):
        return self._mapping.get(element_id)


def test_calculate_allowed_path_skips_non_wall_and_filtered_wall_types(monkeypatch):
    domain = _load_domain_module()

    wall_ok = _DummyWall("Interior")
    wall_facade = _DummyWall("Facade", is_exterior=True)
    wall_structural = _DummyWall("Structural", is_structural=True, is_monolith=True)
    separator = _DummySeparator()

    segments = [
        _DummySegment(1, 10.0),
        _DummySegment(2, 8.0),
        _DummySegment(3, 7.0),
        _DummySegment(4, 5.0),
    ]
    link_doc = _DummyLinkDoc({1: wall_ok, 2: wall_facade, 3: wall_structural, 4: separator})

    monkeypatch.setattr(domain.su, "_get_room_outer_boundary_segments", lambda room, opts=None: segments)
    monkeypatch.setattr(domain.su, "_is_wall_element", lambda elem: isinstance(elem, _DummyWall))
    monkeypatch.setattr(domain.su, "_is_curtain_wall", lambda wall: False)
    monkeypatch.setattr(
        domain.su,
        "_is_room_outer_boundary_segment",
        lambda link_doc, room, curve, probe_mm=200.0: bool(abs(float(getattr(curve, "Length", 0.0)) - 8.0) < 1e-6),
    )
    monkeypatch.setattr(domain.su, "_is_facade_wall", lambda wall, patterns_rx=None: False)
    monkeypatch.setattr(domain.su, "_is_structural_wall", lambda wall: bool(getattr(wall, "is_structural", False)))
    monkeypatch.setattr(domain.su, "_is_monolith_wall", lambda wall, patterns_rx=None: bool(getattr(wall, "is_monolith", False)))
    monkeypatch.setattr(domain.su, "_get_wall_openings_cached", lambda *args, **kwargs: {"doors": [], "windows": []})

    wall_filter = domain.build_wall_filter(
        {
            "socket_general_skip_exterior_walls": True,
            "socket_general_exterior_requires_openings": False,
            "socket_general_exterior_min_segment_mm": 0,
            "socket_general_skip_facade_walls": True,
            "socket_general_skip_structural_walls": True,
            "socket_general_skip_monolith_walls": True,
        }
    )
    breakdown = domain.new_general_breakdown()
    allowed_path, effective_len_ft = domain.calculate_allowed_path(
        link_doc,
        room=object(),
        boundary_opts=None,
        avoid_door_ft=0.0,
        openings_cache={},
        wall_filter=wall_filter,
        breakdown=breakdown,
    )

    assert len(allowed_path) == 1
    assert allowed_path[0][0] is wall_ok
    assert effective_len_ft == pytest.approx(10.0)
    assert breakdown.get("wall_perimeter_ft") == pytest.approx(25.0)
    assert breakdown.get("minus_exterior_ft") == pytest.approx(8.0)
    assert breakdown.get("minus_kzh_ft") == pytest.approx(7.0)
    assert breakdown.get("minus_openings_ft") == pytest.approx(0.0)
    assert breakdown.get("allowed_ft") == pytest.approx(10.0)
