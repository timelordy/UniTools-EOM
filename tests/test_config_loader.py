 # -*- coding: utf-8 -*-
 import json
 import os
 import sys
 import tempfile
 import unittest
 
 ROOT = os.path.dirname(os.path.dirname(__file__))
 EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
 LIB = os.path.join(EXT, "lib")
 if LIB not in sys.path:
     sys.path.insert(0, LIB)
 
 import config_loader
 
 
 class TestLoadRules(unittest.TestCase):
     def test_load_valid_json(self):
         data = {"comment_tag": "TEST_TAG", "light_center_room_height_mm": 3000}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertEqual(result["comment_tag"], "TEST_TAG")
             self.assertEqual(result["light_center_room_height_mm"], 3000)
         finally:
             os.unlink(path)
 
     def test_default_values_applied(self):
         data = {}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertEqual(result["comment_tag"], "AUTO_EOM")
             self.assertEqual(result["light_center_room_height_mm"], 2700)
             self.assertEqual(result["min_light_spacing_mm"], 800)
             self.assertFalse(result["allow_two_lights_per_room"])
             self.assertEqual(result["max_lights_per_room"], 1)
             self.assertIn("exclude_room_name_keywords", result)
             self.assertIsInstance(result["exclude_room_name_keywords"], list)
         finally:
             os.unlink(path)
 
     def test_partial_config_gets_defaults(self):
         data = {"comment_tag": "CUSTOM", "max_lights_per_room": 5}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertEqual(result["comment_tag"], "CUSTOM")
             self.assertEqual(result["max_lights_per_room"], 5)
             self.assertEqual(result["light_center_room_height_mm"], 2700)
         finally:
             os.unlink(path)
 
     def test_utf8_content(self):
         data = {"exclude_room_name_keywords": ["ниша", "балкон", "лоджия"]}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f, ensure_ascii=False)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertIn("ниша", result["exclude_room_name_keywords"])
             self.assertIn("балкон", result["exclude_room_name_keywords"])
         finally:
             os.unlink(path)
 
     def test_load_default_rules_file(self):
         default_path = config_loader.get_default_rules_path()
         if os.path.exists(default_path):
             result = config_loader.load_rules()
             self.assertIsInstance(result, dict)
             self.assertIn("comment_tag", result)
 
     def test_socket_defaults(self):
         data = {}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertEqual(result["socket_spacing_mm"], 3000)
             self.assertEqual(result["socket_height_mm"], 300)
             self.assertEqual(result["avoid_door_mm"], 300)
             self.assertEqual(result["avoid_radiator_mm"], 500)
             self.assertEqual(result["socket_dedupe_radius_mm"], 300)
             self.assertEqual(result["host_wall_search_mm"], 300)
         finally:
             os.unlink(path)
 
     def test_lift_shaft_defaults(self):
         data = {}
         with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
             json.dump(data, f)
             f.flush()
             path = f.name
         try:
             result = config_loader.load_rules(path)
             self.assertIn("лифт", result["lift_shaft_room_name_patterns"])
             self.assertEqual(result["lift_shaft_light_height_mm"], 2500)
             self.assertEqual(result["lift_shaft_edge_offset_mm"], 500)
         finally:
             os.unlink(path)
 
 
 if __name__ == "__main__":
     unittest.main()
