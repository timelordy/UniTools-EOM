# -*- coding: utf-8 -*-
"""Helpers for tool-specific PostCommand mapping (pure Python)."""

try:
    from hub_postcommand import normalize_command_id
except Exception:
    normalize_command_id = None


def _ensure_text(value):
    try:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)
    except Exception:
        try:
            return value.decode("utf-8", "ignore")
        except Exception:
            return None


def normalize_tool_id(value):
    """Return cleaned tool id or None."""
    s = _ensure_text(value)
    if s is None:
        return None
    try:
        if isinstance(s, bytes):
            s = s.decode("utf-8", "ignore")
    except Exception:
        try:
            if hasattr(s, "decode"):
                s = s.decode("utf-8", "ignore")
        except Exception:
            pass
    s = s.strip()
    try:
        if s.startswith(u"\ufeff") or s.startswith(u"\ufffe"):
            s = s.lstrip(u"\ufeff").lstrip(u"\ufffe")
    except Exception:
        pass
    return s if s else None


def _normalize_command_id(value):
    if normalize_command_id:
        try:
            return normalize_command_id(value)
        except Exception:
            pass
    s = _ensure_text(value)
    if s is None:
        return None
    s = s.strip()
    return s if s else None


def parse_command_map(raw):
    """Parse tool->command map from json or simple lines."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        result = {}
        for k, v in raw.items():
            nk = normalize_tool_id(k)
            nv = _normalize_command_id(v)
            if nk and nv:
                result[nk] = nv
        return result

    s = _ensure_text(raw)
    if s is None:
        return {}
    s = s.strip()
    if not s:
        return {}

    if s.lstrip().startswith("{"):
        try:
            import json
            data = json.loads(s)
        except Exception:
            data = None
        if isinstance(data, dict):
            return parse_command_map(data)

    result = {}
    for line in s.splitlines():
        try:
            line = line.strip()
        except Exception:
            continue
        if not line:
            continue
        if line.startswith("#") or line.startswith("//"):
            continue
        sep = None
        if "=" in line:
            sep = "="
        elif ":" in line:
            sep = ":"
        if not sep:
            continue
        parts = line.split(sep, 1)
        if len(parts) < 2:
            continue
        nk = normalize_tool_id(parts[0])
        nv = _normalize_command_id(parts[1])
        if nk and nv:
            result[nk] = nv
    return result


def select_command_id_for_tool(tool_id, env_raw, file_raw):
    """Select command id for tool_id, prefer env_raw over file_raw."""
    tid = normalize_tool_id(tool_id)
    if not tid:
        return None
    env_map = parse_command_map(env_raw)
    if tid in env_map:
        return env_map.get(tid)
    file_map = parse_command_map(file_raw)
    return file_map.get(tid)
