# -*- coding: utf-8 -*-


def parse_circuit_numbers(value):
    if not value:
        return []
    parts = [item.strip() for item in value.split("\n")]
    items = [item for item in parts if item]
    return sorted(set(items))
