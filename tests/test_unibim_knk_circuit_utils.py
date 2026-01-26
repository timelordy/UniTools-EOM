# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_circuit_utils import parse_circuit_numbers  # noqa: E402


class TestKnkCircuitUtils(unittest.TestCase):
    def test_parse_circuit_numbers_splits_and_trims(self):
        value = "A1\n\n B2 \nC3"
        self.assertEqual(parse_circuit_numbers(value), ["A1", "B2", "C3"])

    def test_parse_circuit_numbers_unique_and_sorted(self):
        value = "B2\nA1\nB2\nC3\nA1"
        self.assertEqual(parse_circuit_numbers(value), ["A1", "B2", "C3"])

    def test_parse_circuit_numbers_empty(self):
        self.assertEqual(parse_circuit_numbers(None), [])
        self.assertEqual(parse_circuit_numbers("   "), [])


if __name__ == '__main__':
    unittest.main()
