# -*- coding: utf-8 -*-

import math


_Q_STEPS = [
    0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0,
    60.0, 75.0, 80.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0,
    275.0, 300.0, 325.0, 350.0, 375.0, 400.0, 425.0, 450.0, 475.0, 500.0,
    550.0, 600.0, 650.0, 700.0, 750.0, 800.0, 850.0, 900.0, 1000.0, 1400.0,
]


def _tan_from_cos(cos_value):
    return math.tan(math.acos(cos_value))


def _cos_from_tg(tg_value):
    return 1.0 / math.sqrt(1.0 + tg_value ** 2)


def compute_compensation(P, cos1, cos2, aukrm, regulation_step):
    if P <= 0.0:
        raise ValueError("P must be > 0")
    if cos1 <= 0.0 or cos1 > 1.0:
        raise ValueError("Cos1 must be in (0,1]")
    if cos2 <= 0.0 or cos2 > 1.0:
        raise ValueError("Cos2 must be in (0,1]")

    tg1_raw = _tan_from_cos(cos1)
    tg2_raw = _tan_from_cos(cos2)
    tg1 = round(tg1_raw, 3)
    tg2 = round(tg2_raw, 3)
    qr = round(P * (tg1_raw - tg2_raw), 2)

    q_value = None
    for item in _Q_STEPS:
        if qr < item:
            q_value = item
            break

    if qr <= 0.0:
        return {
            "Qr": qr,
            "Q": u"Не требуется",
            "Tg1": tg1,
            "Tg2": tg2,
            "TgNew": tg1,
            "CosNew": cos1,
        }

    if q_value is None:
        q_value = _Q_STEPS[-1]

    if aukrm:
        if regulation_step <= 0.0 or (q_value % regulation_step) != 0.0:
            return {
                "Qr": qr,
                "Q": str(int(q_value)),
                "Tg1": tg1,
                "Tg2": tg2,
                "Error": u"STEP_MISMATCH",
            }
        tg_new = None
        cos_new = None
        step_count = int(q_value / regulation_step)
        for idx in range(step_count + 1):
            num4 = idx * regulation_step
            tg_tmp = (P * tg1_raw - num4) / P
            cos_tmp = _cos_from_tg(tg_tmp)
            if cos2 < cos_tmp:
                tg_new = round(tg_tmp, 3)
                cos_new = round(cos_tmp, 3)
                break
        if tg_new is None:
            tg_new = round((P * tg1_raw - q_value) / P, 3)
            cos_new = round(_cos_from_tg((P * tg1_raw - q_value) / P), 3)
        return {
            "Qr": qr,
            "Q": str(int(q_value)),
            "Tg1": tg1,
            "Tg2": tg2,
            "TgNew": tg_new,
            "CosNew": cos_new,
        }

    tg_new = round((P * tg1_raw - q_value) / P, 3)
    cos_new = round(_cos_from_tg((P * tg1_raw - q_value) / P), 3)
    return {
        "Qr": qr,
        "Q": str(int(q_value)),
        "Tg1": tg1,
        "Tg2": tg2,
        "TgNew": tg_new,
        "CosNew": cos_new,
    }


def compute_table_values(Pp, voltage, cos_new):
    if cos_new == 0.0:
        raise ValueError("CosNew must be > 0")
    if voltage > 300.0:
        ip = round(Pp * 1000.0 / (math.sqrt(3.0) * voltage * cos_new), 1)
    else:
        ip = round(Pp * 1000.0 / (voltage * cos_new), 1)
    sp = round(Pp / cos_new, 1)
    return ip, sp
