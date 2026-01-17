 # -*- coding: utf-8 -*-
 """Mock Revit API classes for testing without Revit.
 
 This module provides lightweight mock implementations of commonly used
 Revit API classes (from Autodesk.Revit.DB namespace) for unit testing.
 
 Usage:
     from tests.mocks.revit_api import DB, mock_xyz, mock_room
     
     # Create a mock XYZ point
     point = mock_xyz(1.0, 2.0, 3.0)
     
     # Create a mock room
     room = mock_room(name="Kitchen", number="101")
 
 Note:
     These mocks are intentionally simple and only implement the methods
     needed for testing. They are NOT a complete Revit API implementation.
 """
 import math
 from typing import Any, List, Optional, Tuple
 
 
 class MockXYZ:
     """Mock for Autodesk.Revit.DB.XYZ."""
     
     def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
         self.X = float(x)
         self.Y = float(y)
         self.Z = float(z)
     
     def __repr__(self) -> str:
         return f"XYZ({self.X}, {self.Y}, {self.Z})"
     
     def __eq__(self, other: Any) -> bool:
         if not isinstance(other, MockXYZ):
             return False
         return (
             abs(self.X - other.X) < 1e-9 and
             abs(self.Y - other.Y) < 1e-9 and
             abs(self.Z - other.Z) < 1e-9
         )
     
     def __add__(self, other: "MockXYZ") -> "MockXYZ":
         return MockXYZ(self.X + other.X, self.Y + other.Y, self.Z + other.Z)
     
     def __sub__(self, other: "MockXYZ") -> "MockXYZ":
         return MockXYZ(self.X - other.X, self.Y - other.Y, self.Z - other.Z)
     
     def __mul__(self, scalar: float) -> "MockXYZ":
         return MockXYZ(self.X * scalar, self.Y * scalar, self.Z * scalar)
     
     def GetLength(self) -> float:
         return math.sqrt(self.X**2 + self.Y**2 + self.Z**2)
     
     def Normalize(self) -> "MockXYZ":
         length = self.GetLength()
         if length < 1e-9:
             return MockXYZ(0, 0, 0)
         return MockXYZ(self.X / length, self.Y / length, self.Z / length)
     
     def DotProduct(self, other: "MockXYZ") -> float:
         return self.X * other.X + self.Y * other.Y + self.Z * other.Z
     
     def CrossProduct(self, other: "MockXYZ") -> "MockXYZ":
         return MockXYZ(
             self.Y * other.Z - self.Z * other.Y,
             self.Z * other.X - self.X * other.Z,
             self.X * other.Y - self.Y * other.X
         )
     
     @staticmethod
     def BasisX() -> "MockXYZ":
         return MockXYZ(1, 0, 0)
     
     @staticmethod
     def BasisY() -> "MockXYZ":
         return MockXYZ(0, 1, 0)
     
     @staticmethod
     def BasisZ() -> "MockXYZ":
         return MockXYZ(0, 0, 1)
 
 
 class MockElementId:
     """Mock for Autodesk.Revit.DB.ElementId."""
     
     InvalidElementId: "MockElementId"
     
     def __init__(self, value: int = -1):
         self._value = value
     
     @property
     def IntegerValue(self) -> int:
         return self._value
     
     def __eq__(self, other: Any) -> bool:
         if isinstance(other, MockElementId):
             return self._value == other._value
         return False
     
     def __hash__(self) -> int:
         return hash(self._value)
     
     def __repr__(self) -> str:
         return f"ElementId({self._value})"
 
 
 MockElementId.InvalidElementId = MockElementId(-1)
 
 
 class MockBoundingBox:
     """Mock for Autodesk.Revit.DB.BoundingBoxXYZ."""
     
     def __init__(
         self,
         min_pt: Optional[MockXYZ] = None,
         max_pt: Optional[MockXYZ] = None
     ):
         self.Min = min_pt or MockXYZ(0, 0, 0)
         self.Max = max_pt or MockXYZ(1, 1, 1)
 
 
 class MockElement:
     """Mock for Autodesk.Revit.DB.Element."""
     
     def __init__(
         self,
         element_id: Optional[MockElementId] = None,
         name: str = "",
         category: Optional[Any] = None,
         bbox: Optional[MockBoundingBox] = None
     ):
         self.Id = element_id or MockElementId(1)
         self.Name = name
         self.Category = category
         self._bbox = bbox
         self._parameters: dict = {}
     
     def get_BoundingBox(self, view: Any = None) -> Optional[MockBoundingBox]:
         return self._bbox
     
     def LookupParameter(self, name: str) -> Optional[Any]:
         return self._parameters.get(name)
     
     def get_Parameter(self, bip: Any) -> Optional[Any]:
         return self._parameters.get(str(bip))
 
 
 class MockRoom(MockElement):
     """Mock for Autodesk.Revit.DB.Architecture.Room."""
     
     def __init__(
         self,
         name: str = "",
         number: str = "",
         level_id: Optional[MockElementId] = None,
         location: Optional[MockXYZ] = None,
         bbox: Optional[MockBoundingBox] = None
     ):
         super().__init__(name=name, bbox=bbox)
         self.Number = number
         self.LevelId = level_id or MockElementId.InvalidElementId
         self._location = location
     
     @property
     def Location(self) -> Optional[Any]:
         if self._location:
             return type("LocationPoint", (), {"Point": self._location})()
         return None
     
     def IsPointInRoom(self, point: MockXYZ) -> bool:
         if not self._bbox:
             return False
         return (
             self._bbox.Min.X <= point.X <= self._bbox.Max.X and
             self._bbox.Min.Y <= point.Y <= self._bbox.Max.Y
         )
 
 
 class MockBuiltInCategory:
     """Mock for Autodesk.Revit.DB.BuiltInCategory enum."""
     
     OST_Rooms = -2000160
     OST_Doors = -2000023
     OST_Windows = -2000014
     OST_Walls = -2000011
     OST_ElectricalFixtures = -2001060
     OST_ElectricalEquipment = -2001040
     OST_LightingFixtures = -2001120
     OST_MechanicalEquipment = -2001140
     OST_PlumbingFixtures = -2001160
     OST_GenericModel = -2000151
     OST_Furniture = -2000080
 
 
 class MockBuiltInParameter:
     """Mock for Autodesk.Revit.DB.BuiltInParameter enum."""
     
     ROOM_NAME = -1002505
     ROOM_NUMBER = -1002504
     ROOM_DEPARTMENT = -1002507
     ALL_MODEL_INSTANCE_COMMENTS = -1010106
     ALL_MODEL_MARK = -1010103
     DOOR_WIDTH = -1016207
     WINDOW_WIDTH = -1016207
     FAMILY_WIDTH_PARAM = -1016208
 
 
 class DB:
     """Mock namespace for Autodesk.Revit.DB."""
     
     XYZ = MockXYZ
     ElementId = MockElementId
     BoundingBoxXYZ = MockBoundingBox
     Element = MockElement
     BuiltInCategory = MockBuiltInCategory
     BuiltInParameter = MockBuiltInParameter
 
 
 # Factory functions for easier test creation
 
 def mock_xyz(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> MockXYZ:
     """Create a mock XYZ point."""
     return MockXYZ(x, y, z)
 
 
 def mock_element(
     element_id: int = 1,
     name: str = "",
     bbox_min: Optional[Tuple[float, float, float]] = None,
     bbox_max: Optional[Tuple[float, float, float]] = None
 ) -> MockElement:
     """Create a mock Element."""
     bbox = None
     if bbox_min and bbox_max:
         bbox = MockBoundingBox(
             MockXYZ(*bbox_min),
             MockXYZ(*bbox_max)
         )
     return MockElement(
         element_id=MockElementId(element_id),
         name=name,
         bbox=bbox
     )
 
 
 def mock_room(
     name: str = "",
     number: str = "",
     center: Optional[Tuple[float, float, float]] = None,
     size: float = 10.0
 ) -> MockRoom:
     """Create a mock Room with optional center and size."""
     location = MockXYZ(*center) if center else None
     bbox = None
     if center:
         half = size / 2
         bbox = MockBoundingBox(
             MockXYZ(center[0] - half, center[1] - half, center[2]),
             MockXYZ(center[0] + half, center[1] + half, center[2] + 3.0)
         )
     return MockRoom(name=name, number=number, location=location, bbox=bbox)
