# -*- coding: utf-8 -*-
"""Tests for Hub command file mode (single command file)."""

import os
import sys
from pathlib import Path


def _import_tools(tmp_path):
    root = Path(__file__).resolve().parents[1]
    hub_src = root / "EOMHub" / "src"
    if str(hub_src) not in sys.path:
        sys.path.insert(0, str(hub_src))

    os.environ["TEMP"] = str(tmp_path)
    os.environ["TMP"] = str(tmp_path)
    os.environ["EOM_SESSION_ID"] = "session_test"

    import api.tools as tools
    return tools


def test_run_tool_writes_single_command_file(tmp_path, monkeypatch):
    tools = _import_tools(tmp_path)
    monkeypatch.setattr(tools, "get_revit_status", lambda: {"connected": True})

    job_id = "job_test_123"
    result = tools.run_tool("lights_center", job_id=job_id)
    assert result.get("success") is True

    command_file = Path(tmp_path) / "eom_hub_command.txt"
    assert command_file.exists()
    assert command_file.read_text(encoding="utf-8") == "run:lights_center:{0}".format(job_id)

    per_job = Path(tmp_path) / "eom_hub_command_{0}.txt".format(job_id)
    assert per_job.exists()
