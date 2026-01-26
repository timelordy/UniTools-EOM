# -*- coding: utf-8 -*-

import re


def parse_laying_methods(text):
    if not text:
        return []
    # Normalize separators
    cleaned = text.replace("\n", ";")
    parts = [p.strip() for p in cleaned.split(";") if p.strip()]
    items = []
    for part in parts:
        if "-" not in part:
            continue
        method, value = part.split("-", 1)
        method = method.strip()
        value = value.strip()
        if not method or "," in value:
            continue
        match = re.search(r"\d+(\.\d+)?", value.replace(",", "."))
        if not match:
            continue
        try:
            length = float(match.group(0))
        except Exception:
            continue
        items.append((method, length))
    return items


def aggregate_by_bundle(entries):
    result = {}
    for entry in entries:
        bundle = entry.get("bundle") or "<Без комплекта>"
        method = entry.get("method")
        length = entry.get("length", 0.0)
        if not method:
            continue
        bucket = result.setdefault(bundle, {})
        bucket[method] = bucket.get(method, 0.0) + float(length)
    return result
