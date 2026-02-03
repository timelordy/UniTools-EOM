# -*- coding: utf-8 -*-
"""Tests for hub_temp_paths helper."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_temp_paths import get_root_temp_dir, iter_temp_roots


def test_get_root_temp_dir_for_guid():
    temp_root = r"C:\Temp\123e4567-e89b-12d3-a456-426614174000"
    assert get_root_temp_dir(temp_root) == r"C:\Temp"


def test_get_root_temp_dir_for_regular_path():
    temp_root = r"C:\Temp"
    assert get_root_temp_dir(temp_root) == temp_root


def test_iter_temp_roots_includes_root():
    temp_root = r"C:\Temp\123e4567-e89b-12d3-a456-426614174000"
    roots = iter_temp_roots(temp_root)
    assert roots[0] == temp_root
    assert r"C:\Temp" in roots


def test_iter_temp_roots_no_duplicates():
    temp_root = r"C:\Temp"
    roots = iter_temp_roots(temp_root)
    assert roots == [temp_root]
