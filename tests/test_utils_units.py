# -*- coding: utf-8 -*-
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import utils_units


class TestMmToFt(unittest.TestCase):
    def test_basic_conversion(self):
        self.assertAlmostEqual(utils_units.mm_to_ft(304.8), 1.0, places=6)
        self.assertAlmostEqual(utils_units.mm_to_ft(609.6), 2.0, places=6)

    def test_zero(self):
        self.assertEqual(utils_units.mm_to_ft(0), 0.0)

    def test_negative(self):
        self.assertAlmostEqual(utils_units.mm_to_ft(-304.8), -1.0, places=6)

    def test_none_returns_none(self):
        self.assertIsNone(utils_units.mm_to_ft(None))

    def test_small_value(self):
        self.assertAlmostEqual(utils_units.mm_to_ft(1), 1.0 / 304.8, places=9)

    def test_large_value(self):
        self.assertAlmostEqual(utils_units.mm_to_ft(1000000), 1000000 / 304.8, places=3)

    def test_float_input(self):
        self.assertAlmostEqual(utils_units.mm_to_ft(152.4), 0.5, places=6)

    def test_string_numeric(self):
        self.assertAlmostEqual(utils_units.mm_to_ft("304.8"), 1.0, places=6)


class TestFtToMm(unittest.TestCase):
    def test_basic_conversion(self):
        self.assertAlmostEqual(utils_units.ft_to_mm(1.0), 304.8, places=6)
        self.assertAlmostEqual(utils_units.ft_to_mm(2.0), 609.6, places=6)

    def test_zero(self):
        self.assertEqual(utils_units.ft_to_mm(0), 0.0)

    def test_negative(self):
        self.assertAlmostEqual(utils_units.ft_to_mm(-1.0), -304.8, places=6)

    def test_none_returns_none(self):
        self.assertIsNone(utils_units.ft_to_mm(None))

    def test_small_value(self):
        self.assertAlmostEqual(utils_units.ft_to_mm(0.001), 0.3048, places=6)

    def test_large_value(self):
        self.assertAlmostEqual(utils_units.ft_to_mm(10000), 10000 * 304.8, places=1)

    def test_float_input(self):
        self.assertAlmostEqual(utils_units.ft_to_mm(0.5), 152.4, places=6)

    def test_string_numeric(self):
        self.assertAlmostEqual(utils_units.ft_to_mm("1.0"), 304.8, places=6)


class TestRoundTrip(unittest.TestCase):
    def test_mm_to_ft_to_mm(self):
        original = 1234.5
        converted = utils_units.ft_to_mm(utils_units.mm_to_ft(original))
        self.assertAlmostEqual(converted, original, places=6)

    def test_ft_to_mm_to_ft(self):
        original = 5.5
        converted = utils_units.mm_to_ft(utils_units.ft_to_mm(original))
        self.assertAlmostEqual(converted, original, places=6)


if __name__ == "__main__":
    unittest.main()
