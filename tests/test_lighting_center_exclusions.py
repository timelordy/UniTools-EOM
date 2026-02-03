# -*- coding: utf-8 -*-
"""Tests for excluded room names in Свет по центру logic."""
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


class DummyParam(object):
    """Minimal parameter stub with AsString support."""

    def __init__(self, value):
        self._value = value

    def AsString(self):
        return self._value


class DummyRoom(object):
    """Minimal room stub for exclusion tests."""

    def __init__(self, name, params=None):
        self.Name = name
        self._params = params or {}

    def get_Parameter(self, bip):
        return self._params.get(bip)

    def LookupParameter(self, name):
        return self._params.get(name)


def test_excluded_balcony_loggia_terrace_variants():
    names = [
        u"Балкон",
        u"Балконы",
        u"Лоджия",
        u"Лоджии",
        u"Терраса",
        u"Террасы",
        u"Терасса",
        "Balcony",
        "Loggia",
        "Terrace",
    ]

    for name in names:
        room = DummyRoom(name)
        assert domain.is_excluded_room(room) is True, name


def test_excluded_tbo_variants():
    names = [
        u"ТБО",
        u"Т Б О",
        u"Т.Б.О",
    ]

    for name in names:
        room = DummyRoom(name)
        assert domain.is_excluded_room(room) is True, name


def test_excluded_department_match():
    params = {
        DB.BuiltInParameter.ROOM_DEPARTMENT: DummyParam(u"Терраса"),
    }
    room = DummyRoom("Space 49", params=params)
    assert domain.is_excluded_room(room) is True
