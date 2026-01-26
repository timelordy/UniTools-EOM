# -*- coding: utf-8 -*-


DEFAULT_PARAM_NAMES = {
    "Units": u"ADSK_Единица измерения",
    "Manufacturer": u"ADSK_Завод-изготовитель",
    "Name": u"ADSK_Наименование",
    "TypeMark": u"ADSK_Марка",
}

_PARAM_KEYS = {
    "Param_name_0_for_Param_Names_Storage": "Units",
    "Param_name_1_for_Param_Names_Storage": "Manufacturer",
    "Param_name_2_for_Param_Names_Storage": "Name",
    "Param_name_3_for_Param_Names_Storage": "TypeMark",
}


def build_param_names(settings_list):
    data = dict(DEFAULT_PARAM_NAMES)
    if not settings_list:
        return data
    for idx, key in enumerate(settings_list):
        target = _PARAM_KEYS.get(key)
        if not target:
            continue
        if idx + 1 < len(settings_list):
            data[target] = settings_list[idx + 1]
    return data


def count_module_stats(module_counts):
    stats = {
        "count_device": 0,
        "count0p": 0,
        "count1p": 0,
        "count2p": 0,
        "count3p": 0,
        "count4p": 0,
        "count5p": 0,
        "count6p": 0,
        "count7p": 0,
        "count8p": 0,
        "count9p": 0,
        "count10p": 0,
        "count11p": 0,
        "count12p": 0,
        "all_modules": 0,
    }
    for modules in module_counts:
        stats["count_device"] += 1
        if modules == 0:
            stats["count0p"] += 1
        elif modules == 1:
            stats["count1p"] += 1
        elif modules == 2:
            stats["count2p"] += 1
        elif modules == 3:
            stats["count3p"] += 1
        elif modules == 4:
            stats["count4p"] += 1
        elif modules == 5:
            stats["count5p"] += 1
        elif modules == 6:
            stats["count6p"] += 1
        elif modules == 7:
            stats["count7p"] += 1
        elif modules == 8:
            stats["count8p"] += 1
        elif modules == 9:
            stats["count9p"] += 1
        elif modules == 10:
            stats["count10p"] += 1
        elif modules == 11:
            stats["count11p"] += 1
        elif modules == 12:
            stats["count12p"] += 1
        else:
            stats["count3p"] += 1

    stats["all_modules"] = (
        stats["count1p"]
        + stats["count2p"] * 2
        + stats["count3p"] * 3
        + stats["count4p"] * 4
        + stats["count5p"] * 5
        + stats["count6p"] * 6
        + stats["count7p"] * 7
        + stats["count8p"] * 8
        + stats["count9p"] * 9
        + stats["count10p"] * 10
        + stats["count11p"] * 11
        + stats["count12p"] * 12
    )
    return stats
