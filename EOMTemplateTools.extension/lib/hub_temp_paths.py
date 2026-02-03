# -*- coding: utf-8 -*-
"""Helpers for resolving temp root candidates."""

import os
import re


_GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def get_root_temp_dir(temp_dir):
    """Return root temp dir if temp_dir is a GUID subfolder."""
    if not temp_dir:
        return temp_dir
    try:
        base = os.path.basename(temp_dir.rstrip("\\/"))
    except Exception:
        return temp_dir
    if base and _GUID_RE.match(base):
        try:
            parent = os.path.dirname(temp_dir)
            return parent or temp_dir
        except Exception:
            return temp_dir
    return temp_dir


def iter_temp_roots(temp_dir):
    """Return candidate temp roots, including GUID parent if present."""
    if not temp_dir:
        return []
    roots = [temp_dir]
    root = get_root_temp_dir(temp_dir)
    if root and root != temp_dir:
        roots.append(root)
    return roots
