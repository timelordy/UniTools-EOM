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


class TestShortCircuitGlobals(unittest.TestCase):
    def test_shortcircuit_globals_values(self):
        spec = importlib.util.find_spec("unibim.shortcircuit_globals")
        self.assertIsNotNone(spec)
        module = importlib.import_module("unibim.shortcircuit_globals")
        data = module.get_shortcircuit_globals()
        self.assertIsInstance(data, dict)
        self.assertEqual(
            data["Guidstr_ShortCircuit_Settings"],
            "feed43d6-2017-4488-a83f-8fde400df18e",
        )
        self.assertEqual(data["FieldName_for_ShortCircuit_Settings_10"], "QF_Resistance_xkv")
        self.assertEqual(data["Param_Short_Circuit_3ph"], u"Ток КЗ 3ф (кА)")
        self.assertEqual(data["Param_Short_Circuit_1ph"], u"Ток КЗ 1ф (кА)")
        self.assertIn(u"TSL_Кабель", data["using_auxiliary_cables"])
        self.assertEqual(
            data["avt_family_names"],
            [
                u"TSL_2D автоматический выключатель_ВРУ",
                u"TSL_2D автоматический выключатель_Щит",
            ],
        )


if __name__ == "__main__":
    unittest.main()
