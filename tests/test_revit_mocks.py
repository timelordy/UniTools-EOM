 # -*- coding: utf-8 -*-
 """Tests for Revit API mocks."""
 import math
 import unittest
 
 from mocks.revit_api import (
     DB,
     MockBoundingBox,
     MockElement,
     MockElementId,
     MockRoom,
     MockXYZ,
     mock_element,
     mock_room,
     mock_xyz,
 )
 
 
 class TestMockXYZ(unittest.TestCase):
     def test_creation(self):
         xyz = MockXYZ(1.0, 2.0, 3.0)
         self.assertEqual(xyz.X, 1.0)
         self.assertEqual(xyz.Y, 2.0)
         self.assertEqual(xyz.Z, 3.0)
 
     def test_default_values(self):
         xyz = MockXYZ()
         self.assertEqual(xyz.X, 0.0)
         self.assertEqual(xyz.Y, 0.0)
         self.assertEqual(xyz.Z, 0.0)
 
     def test_addition(self):
         a = MockXYZ(1, 2, 3)
         b = MockXYZ(4, 5, 6)
         result = a + b
         self.assertEqual(result.X, 5)
         self.assertEqual(result.Y, 7)
         self.assertEqual(result.Z, 9)
 
     def test_subtraction(self):
         a = MockXYZ(4, 5, 6)
         b = MockXYZ(1, 2, 3)
         result = a - b
         self.assertEqual(result.X, 3)
         self.assertEqual(result.Y, 3)
         self.assertEqual(result.Z, 3)
 
     def test_multiplication(self):
         xyz = MockXYZ(1, 2, 3)
         result = xyz * 2
         self.assertEqual(result.X, 2)
         self.assertEqual(result.Y, 4)
         self.assertEqual(result.Z, 6)
 
     def test_get_length(self):
         xyz = MockXYZ(3, 4, 0)
         self.assertAlmostEqual(xyz.GetLength(), 5.0)
 
     def test_normalize(self):
         xyz = MockXYZ(3, 4, 0)
         normalized = xyz.Normalize()
         self.assertAlmostEqual(normalized.X, 0.6)
         self.assertAlmostEqual(normalized.Y, 0.8)
         self.assertAlmostEqual(normalized.Z, 0.0)
 
     def test_normalize_zero(self):
         xyz = MockXYZ(0, 0, 0)
         normalized = xyz.Normalize()
         self.assertEqual(normalized.X, 0)
         self.assertEqual(normalized.Y, 0)
         self.assertEqual(normalized.Z, 0)
 
     def test_dot_product(self):
         a = MockXYZ(1, 2, 3)
         b = MockXYZ(4, 5, 6)
         self.assertEqual(a.DotProduct(b), 32)
 
     def test_cross_product(self):
         x = MockXYZ.BasisX()
         y = MockXYZ.BasisY()
         z = x.CrossProduct(y)
         self.assertAlmostEqual(z.X, 0)
         self.assertAlmostEqual(z.Y, 0)
         self.assertAlmostEqual(z.Z, 1)
 
     def test_equality(self):
         a = MockXYZ(1, 2, 3)
         b = MockXYZ(1, 2, 3)
         c = MockXYZ(1, 2, 4)
         self.assertEqual(a, b)
         self.assertNotEqual(a, c)
 
     def test_repr(self):
         xyz = MockXYZ(1, 2, 3)
         self.assertIn("1", repr(xyz))
         self.assertIn("2", repr(xyz))
         self.assertIn("3", repr(xyz))
 
 
 class TestMockElementId(unittest.TestCase):
     def test_creation(self):
         eid = MockElementId(123)
         self.assertEqual(eid.IntegerValue, 123)
 
     def test_invalid_element_id(self):
         self.assertEqual(MockElementId.InvalidElementId.IntegerValue, -1)
 
     def test_equality(self):
         a = MockElementId(1)
         b = MockElementId(1)
         c = MockElementId(2)
         self.assertEqual(a, b)
         self.assertNotEqual(a, c)
 
     def test_hash(self):
         a = MockElementId(1)
         b = MockElementId(1)
         self.assertEqual(hash(a), hash(b))
 
 
 class TestMockRoom(unittest.TestCase):
     def test_creation(self):
         room = MockRoom(name="Kitchen", number="101")
         self.assertEqual(room.Name, "Kitchen")
         self.assertEqual(room.Number, "101")
 
     def test_is_point_in_room(self):
         room = mock_room(name="Kitchen", center=(5, 5, 0), size=10)
         self.assertTrue(room.IsPointInRoom(mock_xyz(5, 5, 0)))
         self.assertTrue(room.IsPointInRoom(mock_xyz(0, 0, 0)))
         self.assertFalse(room.IsPointInRoom(mock_xyz(100, 100, 0)))
 
     def test_location(self):
         room = mock_room(center=(10, 20, 30))
         self.assertEqual(room.Location.Point.X, 10)
         self.assertEqual(room.Location.Point.Y, 20)
         self.assertEqual(room.Location.Point.Z, 30)
 
 
 class TestFactoryFunctions(unittest.TestCase):
     def test_mock_xyz(self):
         xyz = mock_xyz(1, 2, 3)
         self.assertIsInstance(xyz, MockXYZ)
         self.assertEqual(xyz.X, 1)
 
     def test_mock_element(self):
         elem = mock_element(element_id=42, name="TestElement")
         self.assertEqual(elem.Id.IntegerValue, 42)
         self.assertEqual(elem.Name, "TestElement")
 
     def test_mock_element_with_bbox(self):
         elem = mock_element(bbox_min=(0, 0, 0), bbox_max=(10, 10, 10))
         bbox = elem.get_BoundingBox(None)
         self.assertIsNotNone(bbox)
         self.assertEqual(bbox.Min.X, 0)
         self.assertEqual(bbox.Max.X, 10)
 
     def test_mock_room(self):
         room = mock_room(name="Bedroom", number="201", center=(5, 5, 0))
         self.assertEqual(room.Name, "Bedroom")
         self.assertEqual(room.Number, "201")
 
 
 class TestDBNamespace(unittest.TestCase):
     def test_xyz_access(self):
         xyz = DB.XYZ(1, 2, 3)
         self.assertIsInstance(xyz, MockXYZ)
 
     def test_element_id_access(self):
         eid = DB.ElementId(42)
         self.assertIsInstance(eid, MockElementId)
 
 
 if __name__ == "__main__":
     unittest.main()
