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


class TestSelectConduitUtils(unittest.TestCase):
    def test_fallback_diameter_frls(self):
        spec = importlib.util.find_spec("unibim.select_conduit_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.select_conduit_utils")
        diameter, used = utils.get_fallback_diameter("ВВГнг-FRLS", 3, 2.5)
        self.assertTrue(used)
        self.assertAlmostEqual(diameter, 13.4, places=1)

    def test_fallback_diameter_default(self):
        spec = importlib.util.find_spec("unibim.select_conduit_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.select_conduit_utils")
        diameter, used = utils.get_fallback_diameter("ВВГнг", 3, 2.5)
        self.assertTrue(used)
        self.assertAlmostEqual(diameter, 12.2, places=1)

    def test_update_laying_method_text(self):
        spec = importlib.util.find_spec("unibim.select_conduit_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.select_conduit_utils")
        settings = [
            {
                "Name": "ПВХ",
                "Percent": 40.0,
                "ConduitModels": [
                    {"InnerDiameter": 16.0, "NominalDiameter": 20.0},
                    {"InnerDiameter": 20.0, "NominalDiameter": 25.0},
                ],
            }
        ]
        text, had_unmatched, replaced = utils.update_laying_method_text("ПВХ20-1", 10.0, settings)
        self.assertTrue(replaced)
        self.assertFalse(had_unmatched)
        self.assertEqual(text, "ПВХ20-1")

    def test_invalid_comma_separator(self):
        spec = importlib.util.find_spec("unibim.select_conduit_utils")
        self.assertIsNotNone(spec)
        utils = importlib.import_module("unibim.select_conduit_utils")
        self.assertTrue(utils.has_invalid_comma_separator("10, ПВХ20"))
        self.assertFalse(utils.has_invalid_comma_separator("10,20"))


if __name__ == "__main__":
    unittest.main()
