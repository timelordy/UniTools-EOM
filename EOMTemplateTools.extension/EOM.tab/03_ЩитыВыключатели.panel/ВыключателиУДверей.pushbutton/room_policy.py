# -*- coding: utf-8 -*-
"""Политики классификации помещений для расстановки выключателей."""

from constants import (
    CORRIDOR_ROOMS,
    NON_APARTMENT_ROOMS,
    SKIP_ROOMS,
    TWO_GANG_ROOMS,
    WET_ROOMS,
)
from domain import contains_any


def is_wet_room(room_name):
    return contains_any(room_name, WET_ROOMS)


def is_two_gang_room(room_name):
    return contains_any(room_name, TWO_GANG_ROOMS)


def is_corridor_room(room_name):
    return contains_any(room_name, CORRIDOR_ROOMS)


def is_skip_room(room_name):
    return contains_any(room_name, SKIP_ROOMS)


def is_non_apartment_room(room_name):
    return contains_any(room_name, NON_APARTMENT_ROOMS)


def should_place_inside_room(room_name):
    return not is_wet_room(room_name)


def corridor_bonus(room_name):
    return 1 if is_corridor_room(room_name) else 0


def is_wet_outside_allowed(is_wet, adjacent_room_name):
    if not is_wet:
        return True
    return is_corridor_room(adjacent_room_name)
