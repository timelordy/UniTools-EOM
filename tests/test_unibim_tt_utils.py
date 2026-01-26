# -*- coding: utf-8 -*-

import importlib
import importlib.util
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "EOMTemplateTools.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)


class TestTTUtils(unittest.TestCase):
    def test_compute_tt_results(self):
        spec = importlib.util.find_spec("unibim.tt_utils")
        self.assertIsNotNone(spec)
        tt_utils = importlib.import_module("unibim.tt_utils")
        res = tt_utils.compute_tt_results(
            i1=100.0,
            i2=5.0,
            current1=80.0,
            current2=120.0,
            current_min_line=80.0,
            zcontacts=0.015,
            tt_power=5.0,
            counter_length=10.0,
            counter_power=2.0,
            wire_section=2.5,
        )
        self.assertEqual(res["CurrentTT20"], 120.0)
        self.assertEqual(res["Current40"], 2.0)
        self.assertEqual(res["Check40"], u"Выполняется")
        self.assertEqual(res["CheckNorm"], u"Выполняется")
        self.assertEqual(res["CheckMin"], u"Выполняется")
        self.assertEqual(res["Check5"], u"Выполняется")
        self.assertEqual(res["CheckPeregruzka"], u"Не выполняется")
        self.assertEqual(res["CheckZ"], u"Выполняется")

    def test_compute_tt_results_no_data(self):
        spec = importlib.util.find_spec("unibim.tt_utils")
        self.assertIsNotNone(spec)
        tt_utils = importlib.import_module("unibim.tt_utils")
        res = tt_utils.compute_tt_results(
            i1=0.0,
            i2=0.0,
            current1=0.0,
            current2=0.0,
            current_min_line=0.0,
            zcontacts=0.015,
            tt_power=0.0,
            counter_length=0.0,
            counter_power=0.0,
            wire_section=2.5,
        )
        self.assertEqual(res["CheckPeregruzka"], u"Не производится")
        self.assertEqual(res["Check40"], u"Не производится")
        self.assertEqual(res["CheckNorm"], u"Не производится")
        self.assertEqual(res["CheckMin"], u"Не производится")
        self.assertEqual(res["Check5"], u"Не производится")
        self.assertEqual(res["CheckZ"], u"Не производится")


if __name__ == "__main__":
    unittest.main()
