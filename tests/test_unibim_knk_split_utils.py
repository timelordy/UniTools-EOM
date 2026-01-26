# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_split_utils import (  # noqa: E402
    classify_by_name,
    split_by_flag,
    split_by_name,
)


class TestKnkSplitUtils(unittest.TestCase):
    def test_classify_by_name(self):
        self.assertTrue(classify_by_name("Освещение коридора", ["освещ"]))
        self.assertFalse(classify_by_name("Силовые розетки", ["освещ"]))
        self.assertIsNone(classify_by_name("", ["освещ"]))

    def test_split_by_name(self):
        circuits = ["C1", "C2", "C3"]
        load_map = {"C1": "Освещение", "C2": "Силовая", "C3": ""}
        eo, em, es = split_by_name(circuits, load_map, ["освещ"])
        self.assertEqual(eo, ["C1"])
        self.assertEqual(em, ["C2"])
        self.assertEqual(es, ["C3"])

    def test_split_by_flag(self):
        circuits = ["A", "B", "C"]
        flag_map = {"A": True, "B": False}
        eo, em, es = split_by_flag(circuits, flag_map)
        self.assertEqual(eo, ["A"])
        self.assertEqual(em, ["B"])
        self.assertEqual(es, ["C"])


if __name__ == "__main__":
    unittest.main()
