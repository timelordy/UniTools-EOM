# -*- coding: utf-8 -*-


def _split_items(values):
    if not values:
        return []
    out = []
    for value in values:
        if value is None:
            continue
        text = value if isinstance(value, str) else str(value)
        for part in text.split("\n"):
            part = part.strip()
            if part:
                out.append(part)
    return out


def normalize_circuits(values):
    items = _split_items(values)
    return sorted(set(items))


def merge_circuits(existing, selected, mode):
    existing_norm = normalize_circuits(existing)
    selected_norm = normalize_circuits(selected)
    existing_set = set(existing_norm)
    selected_set = set(selected_norm)

    if mode == "replace":
        result = selected_set
    elif mode == "add":
        result = existing_set | selected_set
    elif mode == "remove":
        result = existing_set - selected_set
    else:
        result = existing_set

    return sorted(result)
