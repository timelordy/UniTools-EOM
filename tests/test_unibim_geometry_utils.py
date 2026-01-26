# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim import geometry_utils  # noqa: E402


class TestGeometryUtils(unittest.TestCase):
    def test_midpoint_basic(self):
        m = geometry_utils.midpoint((0, 0, 0), (10, 20, 30))
        self.assertEqual(m, (5, 10, 15))


if __name__ == '__main__':
    unittest.main()
