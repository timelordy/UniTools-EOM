 # -*- coding: utf-8 -*-
 """Tests for rollback_utils module."""
 import os
 import sys
 import unittest
 from datetime import datetime
 from unittest.mock import MagicMock, patch
 
 ROOT = os.path.dirname(os.path.dirname(__file__))
 EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
 LIB = os.path.join(EXT, "lib")
 if LIB not in sys.path:
     sys.path.insert(0, LIB)
 
 # Mock pyrevit before importing rollback_utils
 sys.modules['pyrevit'] = MagicMock()
 
 import rollback_utils
 
 
 class TestParseTag(unittest.TestCase):
     def test_full_tag_with_timestamp(self):
         result = rollback_utils.parse_tag("AUTO_EOM:SOCKET:20260117_143022")
         self.assertIsNotNone(result)
         self.assertEqual(result["prefix"], "AUTO_EOM")
         self.assertEqual(result["tool"], "SOCKET")
         self.assertEqual(result["timestamp"], "20260117_143022")
 
     def test_tag_without_timestamp(self):
         result = rollback_utils.parse_tag("AUTO_EOM:LIGHT")
         self.assertIsNotNone(result)
         self.assertEqual(result["prefix"], "AUTO_EOM")
         self.assertEqual(result["tool"], "LIGHT")
         self.assertIsNone(result["timestamp"])
 
     def test_simple_prefix_only(self):
         result = rollback_utils.parse_tag("AUTO_EOM")
         self.assertIsNotNone(result)
         self.assertEqual(result["prefix"], "AUTO_EOM")
 
     def test_invalid_tag(self):
         result = rollback_utils.parse_tag("Some random comment")
         self.assertIsNone(result)
 
     def test_none_input(self):
         result = rollback_utils.parse_tag(None)
         self.assertIsNone(result)
 
     def test_empty_string(self):
         result = rollback_utils.parse_tag("")
         self.assertIsNone(result)
 
     def test_case_insensitive(self):
         result = rollback_utils.parse_tag("auto_eom:socket")
         self.assertIsNotNone(result)
         self.assertEqual(result["tool"], "socket")
 
     def test_whitespace_handling(self):
         result = rollback_utils.parse_tag("  AUTO_EOM:SWITCH  ")
         self.assertIsNotNone(result)
         self.assertEqual(result["tool"], "SWITCH")
 
     def test_legacy_format(self):
         result = rollback_utils.parse_tag("AUTO_EOM:LIGHT_FROM_LINK")
         self.assertIsNotNone(result)
         self.assertEqual(result["tool"], "LIGHT_FROM_LINK")
 
 
 class TestGenerateTag(unittest.TestCase):
     def test_without_timestamp(self):
         tag = rollback_utils.generate_tag("SOCKET", include_timestamp=False)
         self.assertEqual(tag, "AUTO_EOM:SOCKET")
 
     def test_with_timestamp(self):
         tag = rollback_utils.generate_tag("LIGHT", include_timestamp=True)
         self.assertTrue(tag.startswith("AUTO_EOM:LIGHT:"))
         # Check timestamp format
         parts = tag.split(":")
         self.assertEqual(len(parts), 3)
         self.assertRegex(parts[2], r"\d{8}_\d{6}")
 
     def test_tool_name_normalization(self):
         tag = rollback_utils.generate_tag("my tool", include_timestamp=False)
         self.assertEqual(tag, "AUTO_EOM:MY_TOOL")
 
     def test_lowercase_conversion(self):
         tag = rollback_utils.generate_tag("socket", include_timestamp=False)
         self.assertEqual(tag, "AUTO_EOM:SOCKET")
 
 
 class TestTagPattern(unittest.TestCase):
     def test_pattern_matches_full_tag(self):
         match = rollback_utils.TAG_PATTERN.match("AUTO_EOM:SOCKET:20260117_143022")
         self.assertIsNotNone(match)
         self.assertEqual(match.group(1), "AUTO_EOM")
         self.assertEqual(match.group(2), "SOCKET")
         self.assertEqual(match.group(3), "20260117_143022")
 
     def test_pattern_matches_partial_tag(self):
         match = rollback_utils.TAG_PATTERN.match("AUTO_EOM:LIGHT")
         self.assertIsNotNone(match)
         self.assertEqual(match.group(2), "LIGHT")
 
     def test_pattern_no_match(self):
         match = rollback_utils.TAG_PATTERN.match("RANDOM_TEXT")
         self.assertIsNone(match)
 
 
 class TestFindTaggedElements(unittest.TestCase):
     def test_returns_empty_list_for_none_doc(self):
         result = rollback_utils.find_tagged_elements(None)
         self.assertEqual(result, [])
 
     def test_returns_empty_list_when_db_is_none(self):
         # DB is mocked, so this tests the guard clause
         rollback_utils.DB = None
         result = rollback_utils.find_tagged_elements(MagicMock())
         self.assertEqual(result, [])
 
 
 class TestDeleteElements(unittest.TestCase):
     def test_returns_zero_for_none_doc(self):
         result = rollback_utils.delete_elements(None, [MagicMock()])
         self.assertEqual(result, 0)
 
     def test_returns_zero_for_empty_list(self):
         result = rollback_utils.delete_elements(MagicMock(), [])
         self.assertEqual(result, 0)
 
     def test_returns_zero_when_db_is_none(self):
         rollback_utils.DB = None
         result = rollback_utils.delete_elements(MagicMock(), [MagicMock()])
         self.assertEqual(result, 0)
 
 
 class TestGetUniqueTags(unittest.TestCase):
     def test_returns_empty_for_none_doc(self):
         result = rollback_utils.get_unique_tags(None)
         self.assertEqual(result, [])
 
 
 class TestGetUniqueTools(unittest.TestCase):
     def test_returns_empty_for_none_doc(self):
         result = rollback_utils.get_unique_tools(None)
         self.assertEqual(result, [])
 
 
 if __name__ == "__main__":
     unittest.main()
