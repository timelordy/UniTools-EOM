# -*- coding: utf-8 -*-
"""Regression tests for kitchen wall filtering rules."""
import importlib.util
import os
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))
LOGIC_PATH = os.path.join(
    ROOT,
    "EOMTemplateTools.extension",
    "EOM.tab",
    "04_Розетки.panel",
    "02_КухняБлок.pushbutton",
    "logic.py",
)


def _load_logic_module():
    module_dir = os.path.dirname(LOGIC_PATH)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    # Ensure local kitchen modules are loaded for this test module.
    sys.modules.pop("logic", None)
    sys.modules.pop("domain", None)

    spec = importlib.util.spec_from_file_location("kitchen_logic_test", LOGIC_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyId(object):
    def __init__(self, value):
        self.IntegerValue = int(value)


class _DummyWall(object):
    def __init__(self, wall_id, is_outer=False, is_structural=False, is_monolith=False):
        self.Id = _DummyId(wall_id)
        self.is_outer = bool(is_outer)
        self.is_structural = bool(is_structural)
        self.is_monolith = bool(is_monolith)


def _length_key(value):
    try:
        return round(float(value), 6)
    except Exception:
        return 0.0


def test_filter_room_wall_segments_applies_outer_openings_min_len_and_kzh(monkeypatch):
    logic = _load_logic_module()

    wall_outer_long = _DummyWall(1, is_outer=True)
    wall_outer_short = _DummyWall(2, is_outer=True)
    wall_outer_no_openings = _DummyWall(3, is_outer=True)
    wall_kzh = _DummyWall(4, is_monolith=True)
    wall_ok = _DummyWall(5)

    p = 0.0
    seg_outer_long = (logic.DB.XYZ(p, 0, 0), logic.DB.XYZ(p + logic.mm_to_ft(1200), 0, 0), wall_outer_long)
    p += 100.0
    seg_outer_short = (logic.DB.XYZ(p, 0, 0), logic.DB.XYZ(p + logic.mm_to_ft(400), 0, 0), wall_outer_short)
    p += 100.0
    seg_outer_no_openings = (logic.DB.XYZ(p, 0, 0), logic.DB.XYZ(p + logic.mm_to_ft(1300), 0, 0), wall_outer_no_openings)
    p += 100.0
    seg_kzh = (logic.DB.XYZ(p, 0, 0), logic.DB.XYZ(p + logic.mm_to_ft(1000), 0, 0), wall_kzh)
    p += 100.0
    seg_ok = (logic.DB.XYZ(p, 0, 0), logic.DB.XYZ(p + logic.mm_to_ft(900), 0, 0), wall_ok)
    segs = [seg_outer_long, seg_outer_short, seg_outer_no_openings, seg_kzh, seg_ok]

    outer_len_keys = {
        _length_key(logic.domain.dist_xy(seg_outer_long[0], seg_outer_long[1])),
        _length_key(logic.domain.dist_xy(seg_outer_short[0], seg_outer_short[1])),
        _length_key(logic.domain.dist_xy(seg_outer_no_openings[0], seg_outer_no_openings[1])),
    }

    openings_by_wall = {
        1: {"doors": [(logic.DB.XYZ(0, 0, 0), logic.mm_to_ft(900))], "windows": []},
        2: {"doors": [(logic.DB.XYZ(0, 0, 0), logic.mm_to_ft(900))], "windows": []},
        3: {"doors": [], "windows": []},
        4: {"doors": [], "windows": []},
        5: {"doors": [], "windows": []},
    }

    monkeypatch.setattr(logic.su, "_is_curtain_wall", lambda wall: False)
    monkeypatch.setattr(logic.su, "_is_structural_wall", lambda wall: bool(getattr(wall, "is_structural", False)))
    monkeypatch.setattr(
        logic.su,
        "_is_monolith_wall",
        lambda wall, patterns_rx=None: bool(getattr(wall, "is_monolith", False)),
    )
    monkeypatch.setattr(
        logic.su,
        "_is_room_outer_boundary_segment",
        lambda link_doc, room, curve, probe_mm=200.0: _length_key(getattr(curve, "Length", 0.0)) in outer_len_keys,
    )
    monkeypatch.setattr(
        logic.su,
        "_get_wall_openings_cached",
        lambda link_doc, wall, cache: openings_by_wall.get(int(wall.Id.IntegerValue), {"doors": [], "windows": []}),
    )

    wall_filter = logic.build_kitchen_wall_filter(
        {
            "socket_general_skip_exterior_walls": True,
            "socket_general_exterior_by_boundary_geometry": True,
            "socket_general_exterior_requires_openings": True,
            "socket_general_exterior_min_segment_mm": 500,
            "socket_general_skip_monolith_walls": True,
            "socket_general_skip_structural_walls": True,
        }
    )

    filtered = logic.filter_room_wall_segments(
        link_doc=object(),
        room=object(),
        segs=segs,
        wall_filter=wall_filter,
        openings_cache={},
    )
    filtered_ids = [int(seg[2].Id.IntegerValue) for seg in filtered]

    assert 1 not in filtered_ids
    assert 2 in filtered_ids
    assert 3 in filtered_ids
    assert 4 not in filtered_ids
    assert 5 in filtered_ids
