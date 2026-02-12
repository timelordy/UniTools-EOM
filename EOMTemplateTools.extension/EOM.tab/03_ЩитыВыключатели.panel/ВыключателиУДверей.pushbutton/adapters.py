# -*- coding: utf-8 -*-
"""Facade module for switch/door adapters.

Backward compatibility layer: keeps `from adapters import ...` working for script.py
and other legacy callers while implementation lives in specialized modules.
"""

from adapters_symbols import get_switch_symbol
from adapters_geometry import (
    find_adjacent_wall,
    find_wall_near_point,
    get_door_host_wall,
    get_room_center,
    get_room_name,
    get_room_separation_lines,
    get_wall_curve_and_width,
)
from adapters_doors import get_door_info, is_entrance_door
from adapters_switches import (
    calc_switch_position,
    calc_switch_position_from_separation_line,
    get_closest_level,
    place_switch,
    prefer_farther_candidate,
)
from adapters_outlets import calc_outlet_position, get_outlet_symbol, place_outlet


__all__ = [
    "calc_outlet_position",
    "calc_switch_position",
    "calc_switch_position_from_separation_line",
    "find_adjacent_wall",
    "find_wall_near_point",
    "get_closest_level",
    "get_door_host_wall",
    "get_door_info",
    "get_outlet_symbol",
    "get_room_center",
    "get_room_name",
    "get_room_separation_lines",
    "get_switch_symbol",
    "get_wall_curve_and_width",
    "is_entrance_door",
    "place_outlet",
    "place_switch",
    "prefer_farther_candidate",
]
