# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim import reverse_lighting  # noqa: E402


class _DummyEnum(object):
    def __init__(self, value):
        self.value__ = value


class _DummyInstance(object):
    def __init__(self, can_flip, flipped):
        self.CanFlipWorkPlane = can_flip
        self.IsWorkPlaneFlipped = flipped


class TestReverseLighting(unittest.TestCase):
    def test_is_supported_view_type_accepts_allowed(self):
        self.assertTrue(reverse_lighting.is_supported_view_type(1))
        self.assertTrue(reverse_lighting.is_supported_view_type(2))
        self.assertTrue(reverse_lighting.is_supported_view_type(4))

    def test_is_supported_view_type_accepts_enum_like(self):
        self.assertTrue(reverse_lighting.is_supported_view_type(_DummyEnum(1)))

    def test_is_supported_view_type_rejects_other(self):
        self.assertFalse(reverse_lighting.is_supported_view_type(3))

    def test_flip_instances_toggles_only_when_possible(self):
        inst1 = _DummyInstance(True, False)
        inst2 = _DummyInstance(True, True)
        inst3 = _DummyInstance(False, False)
        reverse_lighting.flip_instances([inst1, inst2, inst3])
        self.assertTrue(inst1.IsWorkPlaneFlipped)
        self.assertFalse(inst2.IsWorkPlaneFlipped)
        self.assertFalse(inst3.IsWorkPlaneFlipped)


if __name__ == '__main__':
    unittest.main()
