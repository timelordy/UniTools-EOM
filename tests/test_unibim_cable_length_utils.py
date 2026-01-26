# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.cable_length_utils import summarize_lengths  # noqa: E402


class TestCableLengthUtils(unittest.TestCase):
    def test_summarize_lengths(self):
        total_len, max_len = summarize_lengths([1.0, 2.5, 0.5])
        self.assertAlmostEqual(total_len, 4.0)
        self.assertAlmostEqual(max_len, 2.5)

    def test_summarize_lengths_empty(self):
        total_len, max_len = summarize_lengths([])
        self.assertEqual(total_len, 0.0)
        self.assertEqual(max_len, 0.0)


if __name__ == '__main__':
    unittest.main()
