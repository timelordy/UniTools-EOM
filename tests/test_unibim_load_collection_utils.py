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


class TestLoadCollectionUtils(unittest.TestCase):
    def test_compute_totals(self):
        spec = importlib.util.find_spec("unibim.load_collection_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.load_collection_utils")
        res = utils.compute_load_collection(py_sum=100.0, pp_sum=80.0, sp_sum=90.0, voltage_kv=0.4, round_value=1)
        self.assertAlmostEqual(res["kc_exist"], 0.8, places=3)
        self.assertAlmostEqual(res["cosf"], 0.8889, places=3)
        self.assertAlmostEqual(res["pp"], 80.0, places=3)
        self.assertAlmostEqual(res["ip"], 129.9, places=1)
        self.assertAlmostEqual(res["sp"], 90.0, places=1)

    def test_compute_totals_with_override(self):
        spec = importlib.util.find_spec("unibim.load_collection_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.load_collection_utils")
        res = utils.compute_load_collection(py_sum=100.0, pp_sum=80.0, sp_sum=90.0, voltage_kv=0.4, round_value=1, kc_override=0.7)
        self.assertAlmostEqual(res["pp"], 70.0, places=3)
        self.assertAlmostEqual(res["ip"], 113.7, places=1)
        self.assertAlmostEqual(res["sp"], 78.8, places=1)


if __name__ == "__main__":
    unittest.main()
