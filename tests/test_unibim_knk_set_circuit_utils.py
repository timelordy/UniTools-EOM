# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_set_circuit_utils import merge_circuits, normalize_circuits  # noqa: E402


class TestKnkSetCircuitUtils(unittest.TestCase):
    def test_normalize_circuits_splits_and_trims(self):
        values = ["A\nB", "  ", "C ", None, "B"]
        self.assertEqual(normalize_circuits(values), ["A", "B", "C"])

    def test_merge_replace(self):
        existing = ["A", "B"]
        selected = ["B", "C"]
        self.assertEqual(merge_circuits(existing, selected, "replace"), ["B", "C"])

    def test_merge_add(self):
        existing = ["A"]
        selected = ["A", "B"]
        self.assertEqual(merge_circuits(existing, selected, "add"), ["A", "B"])

    def test_merge_remove(self):
        existing = ["A", "B"]
        selected = ["B"]
        self.assertEqual(merge_circuits(existing, selected, "remove"), ["A"])

    def test_merge_unknown_mode_keeps_existing(self):
        existing = ["A", "B"]
        selected = ["C"]
        self.assertEqual(merge_circuits(existing, selected, "noop"), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
