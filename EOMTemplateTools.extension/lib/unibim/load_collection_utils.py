# -*- coding: utf-8 -*-

import math


def compute_load_collection(py_sum, pp_sum, sp_sum, voltage_kv, round_value, kc_override=None):
    if py_sum == 0.0:
        raise ValueError("py_sum must be > 0")
    if sp_sum == 0.0:
        raise ValueError("sp_sum must be > 0")
    kc_exist = pp_sum / py_sum
    cosf = pp_sum / sp_sum
    kc_used = kc_override if kc_override is not None else kc_exist
    if kc_used <= 0.0 or kc_used > 1.0:
        raise ValueError("kc_used out of range")
    pp = py_sum * kc_used
    ip = 0.0
    if voltage_kv and cosf:
        ip = pp / (math.sqrt(3.0) * voltage_kv * cosf)
    sp = pp / cosf if cosf else 0.0
    return {
        "kc_exist": kc_exist,
        "kc_used": kc_used,
        "cosf": cosf,
        "pp": pp,
        "ip": ip,
        "sp": sp,
        "pp_round": round(pp, round_value),
        "ip_round": round(ip, round_value),
        "sp_round": round(sp, round_value),
        "kc_round": round(kc_used, 2),
        "cosf_round": round(cosf, 2),
    }
