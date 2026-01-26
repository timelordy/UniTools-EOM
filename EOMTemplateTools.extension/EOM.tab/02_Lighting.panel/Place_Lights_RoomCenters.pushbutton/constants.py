# -*- coding: utf-8 -*-

ROOM_MIN_WALL_CLEAR_FT = 0.0

# NOTE: Linked-room geometry APIs (Room.GetBoundarySegments / Room.IsPointInRoom)
# are known to hard-crash Revit on some models. Keep these OFF by default.
USE_BOUNDARY_ROOM_CENTER = False
USE_NATIVE_IS_POINT_IN_ROOM = False

# Extra duplicate-room detection by geometric overlap can be unsafe when we do not
# have a reliable point-in-room test (bbox-only checks cause many false positives).
# Keep it disabled unless explicitly enabled AND native Room.IsPointInRoom is enabled.
ENABLE_OVERLAP_ROOM_DEDUPE = False
