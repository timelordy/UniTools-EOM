# -*- coding: utf-8 -*-
"""Хелперы для разрешения PostCommand id для Hub запусков (чистый Python)."""


def normalize_command_id(value):
    """Вернуть очищенную строку command id или None."""
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
    """Предпочитать env_value перед file_value, вернуть нормализованный id или None."""
    env_norm = normalize_command_id(env_value)
    if env_norm:
        return env_norm
    return normalize_command_id(file_value)

