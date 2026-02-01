# -*- coding: utf-8 -*-
"""Pytest fixtures for EOMTemplateTools tests."""
import json
import os
import sys
import tempfile
import types
from unittest.mock import MagicMock

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)


if "pyrevit" not in sys.modules:
    pyrevit_stub = types.ModuleType("pyrevit")
    try:
        from mocks.revit_api import DB as MockDB
    except Exception:
        MockDB = MagicMock()
    pyrevit_stub.DB = MockDB
    pyrevit_stub.forms = MagicMock()
    pyrevit_stub.revit = MagicMock()
    pyrevit_stub.script = MagicMock()
    sys.modules["pyrevit"] = pyrevit_stub


@pytest.fixture
def temp_config_file():
    """Create a temporary config file and return its path. Cleans up after test."""
    files = []

    def _create(data):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        f.close()
        files.append(f.name)
        return f.name

    yield _create

    for path in files:
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def sample_room_names_cyrillic():
    """Sample room names in Russian."""
    return [
        u"Кухня",
        u"Гостиная",
        u"Спальня",
        u"Санузел",
        u"Сан. узел",
        u"Ванная",
        u"Коридор",
        u"Прихожая",
        u"Балкон",
        u"Лоджия",
        u"Лифтовая шахта",
        u"Машинное отделение лифта",
    ]


@pytest.fixture
def sample_room_names_latin():
    """Sample room names in English."""
    return [
        "Kitchen",
        "Living Room",
        "Bedroom",
        "Bathroom",
        "WC",
        "Corridor",
        "Hallway",
        "Balcony",
        "Loggia",
        "Elevator Shaft",
        "Machine Room",
    ]


@pytest.fixture
def hydrant_keywords():
    """Keywords for fire hydrant detection."""
    return {
        "include": [u"пожарн", u"пк", u"hydrant", u"fire hose"],
        "exclude": [u"пкс", u"перекрест", u"switch"],
    }


@pytest.fixture
def wet_room_keywords():
    """Keywords for wet room detection."""
    return [
        u"сануз",
        u"ванн",
        u"душ",
        u"wc",
        u"bathroom",
        u"toilet",
        u"shower",
    ]


@pytest.fixture
def kitchen_keywords():
    """Keywords for kitchen detection."""
    return [
        u"кухн",
        u"kitchen",
        u"кухня-гостиная",
    ]
