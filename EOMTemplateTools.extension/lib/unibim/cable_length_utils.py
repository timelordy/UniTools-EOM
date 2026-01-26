# -*- coding: utf-8 -*-


def summarize_lengths(lengths):
    if not lengths:
        return 0.0, 0.0
    total = 0.0
    max_len = 0.0
    for val in lengths:
        total += float(val)
        if val > max_len:
            max_len = float(val)
    return total, max_len
