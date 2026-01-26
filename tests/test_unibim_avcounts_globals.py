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


class TestAvCountsGlobals(unittest.TestCase):
    def test_avcounts_globals_values(self):
        spec = importlib.util.find_spec("unibim.avcounts_globals")
        self.assertIsNotNone(spec)
        module = importlib.import_module("unibim.avcounts_globals")
        data = module.get_avcounts_globals()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["Param_Upit"], u"Напряжение")
        self.assertEqual(data["Param_Cable_length"], u"Длина проводника")
        self.assertEqual(data["Param_Circuit_number"], u"Номер цепи")
        self.assertEqual(data["Guidstr"], "c94ca2e5-771e-407d-9c09-f62feb4448b6")
        self.assertEqual(
            data["avt_family_names"],
            [
                u"TSL_2D автоматический выключатель_ВРУ",
                u"TSL_2D автоматический выключатель_Щит",
            ],
        )
        self.assertEqual(
            data["fam_param_names"][:2],
            [u"ADSK_Единица измерения", u"ADSK_Завод-изготовитель"],
        )


if __name__ == "__main__":
    unittest.main()
