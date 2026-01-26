# -*- coding: utf-8 -*-


def to_roman(number):
    if number < 1:
        return ''
    values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    symbols = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    result = []
    for val, sym in zip(values, symbols):
        while number >= val:
            result.append(sym)
            number -= val
    return ''.join(result)


def assign_switch_codes(segments):
    num = 0
    switch_map = {}
    light_codes = {}

    for seg in segments or []:
        light_ids = seg.get('light_ids') or []
        if not light_ids:
            continue
        base_id = seg.get('base_id')
        if base_id is None:
            continue
        device_ids = seg.get('device_ids') or []

        existing = []
        if base_id in switch_map:
            existing = switch_map.pop(base_id)

        num += 1
        existing.append(num)

        target_ids = device_ids if (device_ids and light_ids) else [base_id]
        for sid in target_ids:
            switch_map[sid] = existing

        roman = to_roman(num)
        for lid in light_ids:
            light_codes[lid] = roman

    switch_codes = {}
    for sid, nums in switch_map.items():
        switch_codes[sid] = ','.join([to_roman(n) for n in nums])

    return {
        'light_codes': light_codes,
        'switch_codes': switch_codes,
    }
