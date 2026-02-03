# -*- coding: utf-8 -*-
"""Tests for L-shaped room light placement logic."""
import os
import sys

from mocks.revit_api import DB


ROOT = os.path.dirname(os.path.dirname(__file__))
DOMAIN_DIR = os.path.join(
    ROOT,
    "EOMTemplateTools.extension",
    "EOM.tab",
    "02_Освещение.panel",
    "СветПоЦентру.pushbutton",
)
if DOMAIN_DIR not in sys.path:
    sys.path.insert(0, DOMAIN_DIR)

import domain  # noqa: E402  pylint: disable=wrong-import-position


class DummyRoom(object):
    """Minimal room stub for testing domain logic."""

    def __init__(self, area_ft2, name="Room"):
        self.Area = area_ft2
        self.Name = name

    def get_BoundingBox(self, view=None):
        return None

    def get_Parameter(self, bip):
        return None

    def LookupParameter(self, name):
        return None


def _make_l_shape_points_notch_top_right():
    # x0 < x1 < x2, y0 < y1 < y2
    x0, x1, x2 = 0.0, 2.0, 5.0
    y0, y1, y2 = 0.0, 3.0, 7.0
    # Missing outer corner: (x2, y2)
    pts = [
        DB.XYZ(x0, y0, 0.0),
        DB.XYZ(x2, y0, 0.0),
        DB.XYZ(x2, y1, 0.0),
        DB.XYZ(x1, y1, 0.0),
        DB.XYZ(x1, y2, 0.0),
        DB.XYZ(x0, y2, 0.0),
    ]
    return pts


def _pt_key(pt):
    return (round(pt.X, 3), round(pt.Y, 3), round(pt.Z, 3))


def test_l_shape_rect_centers_top_right_notch():
    pts = _make_l_shape_points_notch_top_right()
    centers = domain._get_l_shape_rect_centers(pts, fallback_z=0.0)
    assert centers is not None
    assert len(centers) == 2

    expected = {
        (2.5, 1.5, 0.0),  # horizontal bottom bar center
        (1.0, 3.5, 0.0),  # vertical left bar center
    }
    assert {_pt_key(p) for p in centers} == expected


def test_get_room_centers_multi_l_shape_large_area_returns_two(monkeypatch):
    pts = _make_l_shape_points_notch_top_right()

    monkeypatch.setattr(domain, "_get_room_boundary_points", lambda room: pts)

    def _boom(_room):
        raise AssertionError("get_room_center_link should not be called")

    monkeypatch.setattr(domain, "get_room_center_link", _boom)

    # 12 m^2 in ft^2 (~129.17)
    room = DummyRoom(area_ft2=130.0)
    centers = domain.get_room_centers_multi(room)
    assert len(centers) == 2

