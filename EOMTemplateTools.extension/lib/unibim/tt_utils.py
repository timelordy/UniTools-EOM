# -*- coding: utf-8 -*-

import math


def _safe_div(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _safe_round(value, ndigits):
    try:
        if math.isinf(value) or math.isnan(value):
            return 0.0
    except Exception:
        pass
    return round(value, ndigits)


def compute_tt_results(
    i1,
    i2,
    current1,
    current2,
    current_min_line,
    zcontacts,
    tt_power,
    counter_length,
    counter_power,
    wire_section,
):
    ratio = _safe_div(i1, i2)
    current_tt20 = _safe_round(i1 * 1.2, 2)
    current40 = _safe_round(i2 * 0.4, 2)
    current_max2 = _safe_round(_safe_div(current2, ratio), 2)
    current_min2 = _safe_round(_safe_div(current_min_line, ratio), 2)
    current5 = _safe_round(i2 * 5.0 / 100.0, 2)

    if current2 == 0.0 or i1 == 0.0:
        check_peregruzka = u"Не производится"
    elif current_tt20 > current2:
        check_peregruzka = u"Выполняется"
    else:
        check_peregruzka = u"Не выполняется"

    if i2 == 0.0 or i1 == 0.0 or current2 == 0.0:
        check40 = u"Не производится"
    elif current_max2 >= current40:
        check40 = u"Выполняется"
    else:
        check40 = u"Не выполняется"

    if current1 == 0.0 or i1 == 0.0:
        check_norm = u"Не производится"
    elif current1 <= i1:
        check_norm = u"Выполняется"
    else:
        check_norm = u"Не выполняется"

    if current_min_line == 0.0 or i1 == 0.0 or i2 == 0.0:
        check_min = u"Не производится"
    elif current_min2 > 0.1:
        check_min = u"Выполняется"
    else:
        check_min = u"Не выполняется"

    if i2 == 0.0 or i1 == 0.0 or current_min_line == 0.0:
        check5 = u"Не производится"
    elif current_min_line > current5:
        check5 = u"Выполняется"
    else:
        check5 = u"Не выполняется"

    ttz = _safe_div(tt_power, i2 * i2)
    if math.isinf(ttz) or math.isnan(ttz):
        ttz = 0.0

    if wire_section == 0.0:
        z_provodov = 0.0
    else:
        z_provodov = _safe_round(_safe_div(counter_length, 57.0 * wire_section), 4)

    z_counter = _safe_round(_safe_div(counter_power, i2 * i2), 4)
    if math.isinf(z_counter) or math.isnan(z_counter):
        z_counter = 0.0

    z_nagruzka = z_counter + z_provodov + zcontacts

    if i2 == 0.0 or tt_power == 0.0 or counter_power == 0.0:
        check_z = u"Не производится"
    elif ttz == 0.0 or z_nagruzka == 0.0:
        check_z = u"Не производится"
    elif ttz > z_nagruzka:
        check_z = u"Выполняется"
    else:
        check_z = u"Не выполняется"

    return {
        "Ratio": ratio,
        "CurrentTT20": current_tt20,
        "Current40": current40,
        "CurrentMax2": current_max2,
        "CurrentMin2": current_min2,
        "Current5": current5,
        "CheckPeregruzka": check_peregruzka,
        "Check40": check40,
        "CheckNorm": check_norm,
        "CheckMin": check_min,
        "Check5": check5,
        "TTZ": ttz,
        "ZCounter": z_counter,
        "ZProvodov": z_provodov,
        "Znagruzka": z_nagruzka,
        "CheckZ": check_z,
    }
