# -*- coding: utf-8 -*-
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import pk_indicator_rules as rules


class TestPkIndicatorRules(unittest.TestCase):
    def test_import(self):
        self.assertIsNotNone(rules)

    def test_match_any_basic(self):
        text = u"\u041f\u043e\u0436\u0430\u0440\u043d\u044b\u0439 \u043a\u0440\u0430\u043d \u041f\u041a"
        keywords = [
            u"\u043f\u043e\u0436\u0430\u0440\u043d",
            u"\u043f\u043a",
        ]
        self.assertTrue(rules.match_any(text, keywords))

    def test_match_any_latin(self):
        text = "Fire hose cabinet"
        keywords = ["hydrant", "fire hose"]
        self.assertTrue(rules.match_any(text, keywords))

    def test_exclude_keywords(self):
        text = u"\u041f\u0435\u0440\u0435\u043a\u0440\u0435\u0441\u0442\u043d\u044b\u0439 \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u0442\u0435\u043b\u044c \u041f\u041a\u0421"
        include = [u"\u043f\u043a"]
        exclude = [u"\u043f\u043a\u0441", u"\u043f\u0435\u0440\u0435\u043a\u0440\u0435\u0441\u0442"]
        self.assertFalse(rules.is_hydrant_candidate(text, include, exclude))

    def test_match_any_keyword_short_token(self):
        self.assertTrue(rules.match_any_keyword(u"\u041f\u041a-01", [u"\u043f\u043a"]))
        self.assertTrue(rules.match_any_keyword(u"\u041f\u041a1", [u"\u043f\u043a"]))
        self.assertFalse(rules.match_any_keyword(u"\u041f\u041a\u0421", [u"\u043f\u043a"]))


class TestNormFunction(unittest.TestCase):
    def test_norm_basic(self):
        self.assertEqual(rules._norm("  Hello World  "), "hello world")

    def test_norm_cyrillic(self):
        self.assertEqual(rules._norm(u"  Привет Мир  "), u"привет мир")

    def test_norm_none(self):
        self.assertEqual(rules._norm(None), u"")

    def test_norm_empty(self):
        self.assertEqual(rules._norm(""), u"")

    def test_norm_whitespace_only(self):
        self.assertEqual(rules._norm("   "), u"")


class TestMatchAnyEdgeCases(unittest.TestCase):
    def test_empty_text(self):
        self.assertFalse(rules.match_any("", ["keyword"]))

    def test_none_text(self):
        self.assertFalse(rules.match_any(None, ["keyword"]))

    def test_empty_keywords(self):
        self.assertFalse(rules.match_any("some text", []))

    def test_none_keywords(self):
        self.assertFalse(rules.match_any("some text", None))

    def test_partial_match(self):
        self.assertTrue(rules.match_any("firefighter", ["fire"]))

    def test_no_match(self):
        self.assertFalse(rules.match_any("hello world", ["foo", "bar"]))

    def test_case_insensitive(self):
        self.assertTrue(rules.match_any("HELLO WORLD", ["hello"]))
        self.assertTrue(rules.match_any("hello world", ["HELLO"]))


class TestMatchAnyKeywordEdgeCases(unittest.TestCase):
    def test_empty_text(self):
        self.assertFalse(rules.match_any_keyword("", ["pk"]))

    def test_none_text(self):
        self.assertFalse(rules.match_any_keyword(None, ["pk"]))

    def test_empty_keywords(self):
        self.assertFalse(rules.match_any_keyword("ПК-01", []))

    def test_none_keywords(self):
        self.assertFalse(rules.match_any_keyword("ПК-01", None))

    def test_long_keyword_substring(self):
        self.assertTrue(rules.match_any_keyword("пожарный кран", ["пожарн"]))

    def test_short_keyword_exact_token(self):
        self.assertTrue(rules.match_any_keyword("ПК 01", [u"пк"]))

    def test_short_keyword_with_number_suffix(self):
        self.assertTrue(rules.match_any_keyword("ПК123", [u"пк"]))

    def test_short_keyword_not_substring(self):
        self.assertFalse(rules.match_any_keyword("ПКСМ", [u"пк"]))


class TestIsHydrantCandidate(unittest.TestCase):
    def test_include_only(self):
        self.assertTrue(rules.is_hydrant_candidate("Пожарный кран ПК", [u"пожарн", u"пк"]))

    def test_exclude_blocks(self):
        self.assertFalse(rules.is_hydrant_candidate(
            "Переключатель ПКС",
            [u"пк"],
            [u"пкс"]
        ))

    def test_no_exclude(self):
        self.assertTrue(rules.is_hydrant_candidate("ПК-01", [u"пк"], None))

    def test_empty_exclude(self):
        self.assertTrue(rules.is_hydrant_candidate("ПК-01", [u"пк"], []))

    def test_no_include_match(self):
        self.assertFalse(rules.is_hydrant_candidate("Радиатор", [u"пк", u"пожарн"]))


if __name__ == "__main__":
    unittest.main()
