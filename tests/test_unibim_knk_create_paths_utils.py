# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_create_paths_utils import LINE_EPS, should_create_segment  # noqa: E402


class TestKnkCreatePathsUtils(unittest.TestCase):
    def test_should_create_segment_false_when_too_short(self):
        p1 = (0.0, 0.0, 0.0)
        p2 = (LINE_EPS * 0.5, 0.0, 0.0)
        self.assertFalse(should_create_segment(p1, p2))

    def test_should_create_segment_true_when_long_enough(self):
        p1 = (0.0, 0.0, 0.0)
        p2 = (LINE_EPS * 2.0, 0.0, 0.0)
        self.assertTrue(should_create_segment(p1, p2))

    def test_should_create_segment_false_on_none(self):
        self.assertFalse(should_create_segment(None, (0.0, 0.0, 0.0)))
        self.assertFalse(should_create_segment((0.0, 0.0, 0.0), None))


if __name__ == '__main__':
    unittest.main()
