# -*- coding: utf-8 -*-


DEFAULT_KNK_PARAMS = {
    "KnkCircuitNumber": u"TSL_КНК_Номер цепи",
    "KnkVolumeOfCombustibleMass": u"TSL_КНК_Объём горючей массы (л/м)",
    "KnkCableTrayOccupancy": u"TSL_КНК_Заполняемость лотка (%)",
    "KnkWeightSectionMass": u"TSL_КНК_Масса участка (кг/м)",
    "KnkCircuitNumberEM": u"TSL_КНК_Номер цепи ЭМ",
    "KnkCircuitNumberEO": u"TSL_КНК_Номер цепи ЭО",
    "KnkCircuitNumberES": u"TSL_КНК_Номер цепи ЭС",
}

_PARAM_KEYS = {
    "Param_name_24_for_Param_Names_Storage": "KnkCircuitNumber",
    "Param_name_25_for_Param_Names_Storage": "KnkVolumeOfCombustibleMass",
    "Param_name_26_for_Param_Names_Storage": "KnkCableTrayOccupancy",
    "Param_name_28_for_Param_Names_Storage": "KnkWeightSectionMass",
    "Param_name_47_for_Param_Names_Storage": "KnkCircuitNumberEM",
    "Param_name_48_for_Param_Names_Storage": "KnkCircuitNumberEO",
    "Param_name_49_for_Param_Names_Storage": "KnkCircuitNumberES",
}


def get_knk_param_names(settings_list):
    data = dict(DEFAULT_KNK_PARAMS)
    if not settings_list:
        return data
    for idx, key in enumerate(settings_list):
        target = _PARAM_KEYS.get(key)
        if not target:
            continue
        if idx + 1 < len(settings_list):
            data[target] = settings_list[idx + 1]
    return data
