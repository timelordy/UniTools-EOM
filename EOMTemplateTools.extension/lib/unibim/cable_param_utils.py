# -*- coding: utf-8 -*-


DEFAULT_CABLE_PARAMS = {
    "CableLength": u"TSL_Длина проводника",
    "CableLengthAdjusted": u"TSL_Длина проводника приведённая",
    "CableLengthToRemoteDevice": u"TSL_Длина проводника до дальнего устройства",
    "CableLayingMethod": u"TSL_Способ прокладки",
}

_PARAM_KEYS = {
    "Param_name_20_for_Param_Names_Storage": "CableLength",
    "Param_name_41_for_Param_Names_Storage": "CableLengthToRemoteDevice",
    "Param_name_42_for_Param_Names_Storage": "CableLengthAdjusted",
    "Param_name_30_for_Param_Names_Storage": "CableLayingMethod",
}


def get_cable_param_names(settings_list):
    data = dict(DEFAULT_CABLE_PARAMS)
    if not settings_list:
        return data
    for idx, key in enumerate(settings_list):
        target = _PARAM_KEYS.get(key)
        if not target:
            continue
        if idx + 1 < len(settings_list):
            data[target] = settings_list[idx + 1]
    return data
