# -*- coding: utf-8 -*-
"""Helpers for resolving a PostCommand id for Hub runs (pure Python)."""


def normalize_command_id(value):
    """Return a cleaned command id string or None."""
    try:
        if value is None:
            return None
        try:
            # Handle IronPython 2 bytes/unicode
            if isinstance(value, str):
                s = value
            else:
                s = str(value)
        except Exception:
            try:
                s = value.decode("utf-8", "ignore")
            except Exception:
                s = None
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
    except Exception:
        return None


def select_command_id(env_value, file_value):
    """Prefer env_value over file_value, return normalized id or None."""
    env_norm = normalize_command_id(env_value)
    if env_norm:
        return env_norm
    return normalize_command_id(file_value)

