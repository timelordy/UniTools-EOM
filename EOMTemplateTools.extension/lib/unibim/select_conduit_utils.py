# -*- coding: utf-8 -*-

import math
import re


_FRLS_TABLE = {
    1: {
        1.5: 6.5,
        2.5: 6.9,
        4.0: 7.5,
        6.0: 8.5,
        10.0: 10.0,
        16.0: 9.4,
        25.0: 11.6,
        35.0: 12.6,
        50.0: 14.3,
    },
    2: {
        1.5: 11.9,
        2.5: 12.7,
        4.0: 13.2,
        6.0: 14.2,
        10.0: 17.6,
        16.0: 20.0,
        25.0: 23.0,
        35.0: 25.2,
        50.0: 28.2,
    },
    3: {
        1.5: 12.5,
        2.5: 13.4,
        4.0: 15.2,
        6.0: 16.0,
        10.0: 17.6,
        16.0: 21.6,
        25.0: 24.5,
        35.0: 26.7,
        50.0: 29.9,
    },
    4: {
        1.5: 13.7,
        2.5: 16.8,
        4.0: 18.9,
        6.0: 20.1,
        10.0: 22.1,
        16.0: 26.2,
        25.0: 28.9,
        35.0: 31.3,
        50.0: 35.4,
    },
    5: {
        1.5: 17.2,
        2.5: 18.2,
        4.0: 20.6,
        6.0: 21.9,
        10.0: 24.3,
        16.0: 28.7,
        25.0: 31.8,
        35.0: 34.9,
        50.0: 38.9,
    },
}

_DEFAULT_TABLE = {
    1: {1.5: 5.5, 2.5: 5.9, 4.0: 6.8, 6.0: 7.3, 10.0: 8.1, 16.0: 9.5, 25.0: 10.8},
    2: {1.5: 11.0, 2.5: 11.7, 4.0: 13.1, 6.0: 14.1, 10.0: 16.5, 16.0: 19.7, 25.0: 22.0, 35.0: 24.2, 50.0: 27.6},
    3: {1.5: 11.4, 2.5: 12.2, 4.0: 13.6, 6.0: 14.7, 10.0: 17.3, 16.0: 20.8, 25.0: 23.2, 35.0: 25.6, 50.0: 28.8},
    4: {1.5: 12.1, 2.5: 13.0, 4.0: 14.6, 6.0: 15.8, 10.0: 18.7, 16.0: 22.6, 25.0: 25.6, 35.0: 28.0, 50.0: 32.0},
    5: {1.5: 12.8, 2.5: 13.9, 4.0: 15.7, 6.0: 17.0, 10.0: 20.3, 16.0: 24.9, 25.0: 27.9, 35.0: 30.6, 50.0: 35.5},
}


def get_fallback_diameter(cable_mark, veins, cross_section):
    if not cable_mark:
        return 0.0, True
    mark_upper = cable_mark.upper()
    table = _FRLS_TABLE if "FRLS" in mark_upper else _DEFAULT_TABLE
    diameter = table.get(veins, {}).get(cross_section, 0.0)
    return diameter, True


def find_cable_diameter(cable_mark, veins, cross_section, cables):
    if cables:
        for cable in cables:
            try:
                mark = getattr(cable, "Mark", None) or cable.get("Mark")
                cnt = getattr(cable, "CountOfVeins", None) or cable.get("CountOfVeins")
                sec = getattr(cable, "CrossSection", None) or cable.get("CrossSection")
                dia = getattr(cable, "Diameter", None) or cable.get("Diameter")
            except Exception:
                continue
            if mark == cable_mark and cnt == veins and sec == cross_section and dia and dia > 0:
                return dia, False
    return get_fallback_diameter(cable_mark, veins, cross_section)


def compute_conduit_nominal_diameter(cable_diameter, conduit_setting):
    area_cable = math.pi * (cable_diameter ** 2) / 4.0
    percent = conduit_setting.get("Percent", 40.0)
    for model in conduit_setting.get("ConduitModels", []):
        inner = model.get("InnerDiameter", 0.0)
        nominal = model.get("NominalDiameter", 0.0)
        if inner <= 0.0:
            continue
        area_inner = math.pi * (inner ** 2) / 4.0
        if area_inner and (area_cable * 100.0 / area_inner) <= percent:
            return nominal
    return 0.0


def _format_nominal(value):
    try:
        if abs(value - int(value)) < 1e-6:
            return str(int(value))
    except Exception:
        pass
    return str(value)


def update_laying_method_text(text, cable_diameter, conduit_settings):
    if not text:
        return text, False, False
    parts = text.split(";")
    updated_parts = []
    had_unmatched = False
    replaced_any = False
    for part in parts:
        idx = part.rfind("-")
        if idx == -1:
            updated_parts.append(part)
            continue
        prefix = part[:idx]
        digits = "".join([c for c in prefix if c.isdigit()])
        if not digits:
            updated_parts.append(part)
            continue
        name_only = prefix.replace(digits, "").strip()
        nominal = 0.0
        for setting in conduit_settings:
            if name_only == (setting.get("Name", "")).strip():
                nominal = compute_conduit_nominal_diameter(cable_diameter, setting)
                break
        if nominal == 0.0:
            had_unmatched = True
            updated_parts.append(part)
            continue
        suffix = part.replace(prefix, "", 1)
        new_prefix = prefix.replace(digits, _format_nominal(nominal))
        updated_parts.append(new_prefix + suffix)
        replaced_any = True
    return ";".join(updated_parts), had_unmatched, replaced_any


def has_invalid_comma_separator(text):
    if not text:
        return False
    parts = text.strip().split(",")
    if len(parts) <= 1:
        return False
    for part in parts[1:]:
        if not re.match(r"^\d", part.strip()):
            return True
    return False
