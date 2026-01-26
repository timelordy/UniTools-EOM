# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_laying_methods_utils import (  # noqa: E402
    aggregate_by_bundle,
    parse_laying_methods,
)


class TestKnkLayingMethodsUtils(unittest.TestCase):
    def test_parse_laying_methods(self):
        text = "Труба-12м; Лоток-5м"
        self.assertEqual(parse_laying_methods(text), [("Труба", 12.0), ("Лоток", 5.0)])

    def test_parse_skips_commas(self):
        text = "Труба-12,5м"
        self.assertEqual(parse_laying_methods(text), [])

    def test_aggregate_by_bundle(self):
        entries = [
            {"bundle": "A", "method": "Труба", "length": 10},
            {"bundle": "A", "method": "Труба", "length": 5},
            {"bundle": "", "method": "Лоток", "length": 2},
        ]
        result = aggregate_by_bundle(entries)
        self.assertEqual(result["A"]["Труба"], 15.0)
        self.assertEqual(result["<Без комплекта>"]["Лоток"], 2.0)


if __name__ == "__main__":
    unittest.main()
