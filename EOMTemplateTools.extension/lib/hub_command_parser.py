# -*- coding: utf-8 -*-
"""Парсинг командных строк hub в метаданные действий."""


def parse_command(raw):
    try:
        cmd = raw.strip() if raw is not None else ""
    except Exception:
        cmd = ""

    if not cmd:
        return {"action": None, "tool_id": None, "job_id": None, "mode": None}

    if cmd == "cancel":
        return {"action": "cancel", "tool_id": None, "job_id": None, "mode": None}

    if cmd.startswith("run:cancel"):
        parts = cmd.split(":")
        job_id = parts[2] if len(parts) >= 3 and parts[2] else None
        mode = parts[3] if len(parts) >= 4 and parts[3] else None
        return {"action": "cancel", "tool_id": None, "job_id": job_id, "mode": mode}

    if cmd.startswith("run:"):
        parts = cmd.split(":")
        tool_id = parts[1] if len(parts) >= 2 and parts[1] else None
        job_id = parts[2] if len(parts) >= 3 and parts[2] else None
        mode = parts[3] if len(parts) >= 4 and parts[3] else None
        return {"action": "run", "tool_id": tool_id, "job_id": job_id, "mode": mode}

    return {"action": "run", "tool_id": cmd, "job_id": None, "mode": None}
