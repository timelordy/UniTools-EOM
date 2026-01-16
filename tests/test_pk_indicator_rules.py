# -*- coding: utf-8 -*-
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

_import_error = None
try:
    import pk_indicator_rules as rules  # noqa: F401
except Exception as exc:  # pragma: no cover - we want this to fail in RED
    rules = None
    _import_error = exc


class TestPkIndicatorRules(unittest.TestCase):
    def test_import(self):
        if rules is None:
            self.fail("pk_indicator_rules import failed: {0}".format(_import_error))

    def test_match_any_basic(self):
        if rules is None:
            self.fail("pk_indicator_rules not available")
        text = u"\u041f\u043e\u0436\u0430\u0440\u043d\u044b\u0439 \u043a\u0440\u0430\u043d \u041f\u041a"
        keywords = [
            u"\u043f\u043e\u0436\u0430\u0440\u043d",
            u"\u043f\u043a",
        ]
        self.assertTrue(rules.match_any(text, keywords))

    def test_match_any_latin(self):
        if rules is None:
            self.fail("pk_indicator_rules not available")
        text = "Fire hose cabinet"
        keywords = ["hydrant", "fire hose"]
        self.assertTrue(rules.match_any(text, keywords))

    def test_exclude_keywords(self):
        if rules is None:
            self.fail("pk_indicator_rules not available")
        text = u"\u041f\u0435\u0440\u0435\u043a\u0440\u0435\u0441\u0442\u043d\u044b\u0439 \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u0442\u0435\u043b\u044c \u041f\u041a\u0421"
        include = [u"\u043f\u043a"]
        exclude = [u"\u043f\u043a\u0441", u"\u043f\u0435\u0440\u0435\u043a\u0440\u0435\u0441\u0442"]
        self.assertFalse(rules.is_hydrant_candidate(text, include, exclude))

    def test_match_any_keyword_short_token(self):
        if rules is None:
            self.fail("pk_indicator_rules not available")
        self.assertTrue(rules.match_any_keyword(u"\u041f\u041a-01", [u"\u043f\u043a"]))
        self.assertTrue(rules.match_any_keyword(u"\u041f\u041a1", [u"\u043f\u043a"]))
        self.assertFalse(rules.match_any_keyword(u"\u041f\u041a\u0421", [u"\u043f\u043a"]))


if __name__ == "__main__":
    unittest.main()
