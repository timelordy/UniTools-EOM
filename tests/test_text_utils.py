 # -*- coding: utf-8 -*-
 """Tests for text_utils module."""
 import os
 import sys
 import unittest
 
 ROOT = os.path.dirname(os.path.dirname(__file__))
 EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
 LIB = os.path.join(EXT, "lib")
 if LIB not in sys.path:
     sys.path.insert(0, LIB)
 
 import text_utils
 
 
 class TestNorm(unittest.TestCase):
     def test_basic(self):
         self.assertEqual(text_utils.norm("  Hello World  "), "hello world")
 
     def test_cyrillic(self):
         self.assertEqual(text_utils.norm(u"  Привет Мир  "), u"привет мир")
 
     def test_none(self):
         self.assertEqual(text_utils.norm(None), u"")
 
     def test_empty(self):
         self.assertEqual(text_utils.norm(""), u"")
 
     def test_mixed_case(self):
         self.assertEqual(text_utils.norm("HeLLo WoRLD"), "hello world")
 
 
 class TestNormTypeKey(unittest.TestCase):
     def test_basic(self):
         result = text_utils.norm_type_key("TSL_EF Socket : Type 01")
         self.assertIn("tsl_ef", result)
         self.assertIn("socket", result)
 
     def test_dash_normalization(self):
         result = text_utils.norm_type_key("Type–01")
         self.assertIn("type_01", result)
 
     def test_cyrillic_replacement(self):
         result = text_utils.norm_type_key(u"Розетка")
         self.assertEqual(result, "p3t_a")
 
     def test_empty(self):
         self.assertEqual(text_utils.norm_type_key(""), "")
 
     def test_none(self):
         self.assertEqual(text_utils.norm_type_key(None), "")
 
     def test_whitespace_collapse(self):
         result = text_utils.norm_type_key("Type   :   01")
         self.assertNotIn("   ", result)
 
 
 class TestMergeIntervals(unittest.TestCase):
     def test_no_overlap(self):
         result = text_utils.merge_intervals([(1, 2), (3, 4)], 0, 10)
         self.assertEqual(result, [(1, 2), (3, 4)])
 
     def test_overlap(self):
         result = text_utils.merge_intervals([(1, 3), (2, 4)], 0, 10)
         self.assertEqual(result, [(1, 4)])
 
     def test_adjacent(self):
         result = text_utils.merge_intervals([(1, 2), (2, 3)], 0, 10)
         self.assertEqual(result, [(1, 3)])
 
     def test_outside_bounds(self):
         result = text_utils.merge_intervals([(10, 20), (30, 40)], 0, 5)
         self.assertEqual(result, [])
 
     def test_clipped_to_bounds(self):
         result = text_utils.merge_intervals([(0, 5)], 2, 4)
         self.assertEqual(result, [(2, 4)])
 
     def test_empty_intervals(self):
         result = text_utils.merge_intervals([], 0, 10)
         self.assertEqual(result, [])
 
     def test_reversed_interval(self):
         result = text_utils.merge_intervals([(4, 2)], 0, 10)
         self.assertEqual(result, [(2, 4)])
 
     def test_hi_less_than_lo(self):
         result = text_utils.merge_intervals([(1, 2)], 10, 5)
         self.assertEqual(result, [])
 
     def test_multiple_merge(self):
         result = text_utils.merge_intervals([(1, 3), (2, 5), (4, 7), (10, 12)], 0, 15)
         self.assertEqual(result, [(1, 7), (10, 12)])
 
 
 class TestInvertIntervals(unittest.TestCase):
     def test_basic_inversion(self):
         result = text_utils.invert_intervals([(2, 4), (6, 8)], 0, 10)
         self.assertEqual(result, [(0, 2), (4, 6), (8, 10)])
 
     def test_no_blocked(self):
         result = text_utils.invert_intervals([], 0, 10)
         self.assertEqual(result, [(0, 10)])
 
     def test_fully_blocked(self):
         result = text_utils.invert_intervals([(0, 10)], 0, 10)
         self.assertEqual(result, [])
 
     def test_blocked_at_start(self):
         result = text_utils.invert_intervals([(0, 5)], 0, 10)
         self.assertEqual(result, [(5, 10)])
 
     def test_blocked_at_end(self):
         result = text_utils.invert_intervals([(5, 10)], 0, 10)
         self.assertEqual(result, [(0, 5)])
 
 
 class TestTextHasAnyKeyword(unittest.TestCase):
     def test_long_keyword_match(self):
         self.assertTrue(text_utils.text_has_any_keyword("пожарный кран", ["пожарн"]))
 
     def test_long_keyword_no_match(self):
         self.assertFalse(text_utils.text_has_any_keyword("радиатор", ["пожарн"]))
 
     def test_short_keyword_exact_token(self):
         self.assertTrue(text_utils.text_has_any_keyword("ПК 01", [u"пк"]))
 
     def test_short_keyword_with_number(self):
         self.assertTrue(text_utils.text_has_any_keyword("ПК123", [u"пк"]))
 
     def test_short_keyword_not_substring(self):
         self.assertFalse(text_utils.text_has_any_keyword("ПКСМ", [u"пк"]))
 
     def test_empty_text(self):
         self.assertFalse(text_utils.text_has_any_keyword("", ["пк"]))
 
     def test_none_text(self):
         self.assertFalse(text_utils.text_has_any_keyword(None, ["пк"]))
 
     def test_empty_keys(self):
         self.assertFalse(text_utils.text_has_any_keyword("ПК 01", []))
 
     def test_none_keys(self):
         self.assertFalse(text_utils.text_has_any_keyword("ПК 01", None))
 
     def test_latin_match(self):
         self.assertTrue(text_utils.text_has_any_keyword("fire hose cabinet", ["fire"]))
 
     def test_case_insensitive(self):
         self.assertTrue(text_utils.text_has_any_keyword("HELLO WORLD", ["hello"]))
 
     def test_multiple_keywords(self):
         self.assertTrue(text_utils.text_has_any_keyword("bathroom sink", ["kitchen", "sink"]))
 
     def test_short_latin_keyword(self):
         self.assertTrue(text_utils.text_has_any_keyword("BK 01", ["bk"]))
         self.assertFalse(text_utils.text_has_any_keyword("BKSM", ["bk"]))
 
 
 if __name__ == "__main__":
     unittest.main()
