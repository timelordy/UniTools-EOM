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


class TestCompensationUtils(unittest.TestCase):
    def test_compute_compensation_ukrm(self):
        spec = importlib.util.find_spec("unibim.compensation_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.compensation_utils")
        res = utils.compute_compensation(P=100.0, cos1=0.8, cos2=0.95, aukrm=False, regulation_step=2.5)
        self.assertAlmostEqual(res["Tg1"], 0.75, places=2)
        self.assertAlmostEqual(res["Tg2"], 0.329, places=3)
        self.assertAlmostEqual(res["Qr"], 42.13, places=2)
        self.assertEqual(res["Q"], "50")
        self.assertAlmostEqual(res["TgNew"], 0.25, places=2)
        self.assertAlmostEqual(res["CosNew"], 0.97, places=2)

    def test_compute_compensation_auk(self):
        spec = importlib.util.find_spec("unibim.compensation_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.compensation_utils")
        res = utils.compute_compensation(P=100.0, cos1=0.8, cos2=0.95, aukrm=True, regulation_step=2.5)
        self.assertEqual(res["Q"], "50")
        self.assertAlmostEqual(res["TgNew"], 0.325, places=3)
        self.assertAlmostEqual(res["CosNew"], 0.951, places=3)

    def test_compute_table_values(self):
        spec = importlib.util.find_spec("unibim.compensation_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.compensation_utils")
        ip, sp = utils.compute_table_values(Pp=100.0, voltage=400.0, cos_new=0.97)
        self.assertAlmostEqual(ip, 148.8, places=1)
        self.assertAlmostEqual(sp, 103.1, places=1)


if __name__ == "__main__":
    unittest.main()
