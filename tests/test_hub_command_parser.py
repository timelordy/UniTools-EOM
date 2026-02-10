# -*- coding: utf-8 -*-
"""Tests for hub command parsing helpers."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
EXT = os.path.join(ROOT, "EOMTemplateTools.extension")
LIB = os.path.join(EXT, "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_command_parser import parse_command


def test_parse_run_command():
    data = parse_command("run:lights_center:job123")
    assert data["action"] == "run"
    assert data["tool_id"] == "lights_center"
    assert data["job_id"] == "job123"
    assert data.get("mode") is None


def test_parse_run_command_with_mode():
    data = parse_command("run:lights_center:job123:manual")
    assert data["action"] == "run"
    assert data["tool_id"] == "lights_center"
    assert data["job_id"] == "job123"
    assert data.get("mode") == "manual"


def test_parse_cancel_command():
    data = parse_command("cancel")
    assert data["action"] == "cancel"


def test_parse_cancel_command_with_job_id():
    data = parse_command("run:cancel:job123")
    assert data["action"] == "cancel"
    assert data["job_id"] == "job123"
    assert data.get("mode") is None


def test_parse_cancel_command_with_job_id_and_mode():
    data = parse_command("run:cancel:job123:manual")
    assert data["action"] == "cancel"
    assert data["job_id"] == "job123"
    assert data.get("mode") == "manual"


def test_parse_plain_tool():
    data = parse_command("lights_center")
    assert data["action"] == "run"
    assert data["tool_id"] == "lights_center"
    assert data["job_id"] is None


def test_parse_empty_command():
    data = parse_command("")
    assert data["action"] is None
