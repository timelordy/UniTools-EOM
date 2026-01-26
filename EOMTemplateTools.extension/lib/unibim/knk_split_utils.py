# -*- coding: utf-8 -*-


def classify_by_name(load_name, keywords):
    if not load_name:
        return None
    text = load_name.lower()
    for key in keywords:
        if key in text:
            return True
    return False


def split_by_name(circuits, load_map, keywords):
    eo = []
    em = []
    es = []
    for circuit in circuits:
        load_name = load_map.get(circuit, "")
        result = classify_by_name(load_name, keywords)
        if result is None:
            es.append(circuit)
        elif result:
            eo.append(circuit)
        else:
            em.append(circuit)
    return sorted(set(eo)), sorted(set(em)), sorted(set(es))


def split_by_flag(circuits, flag_map):
    eo = []
    em = []
    es = []
    for circuit in circuits:
        flag = flag_map.get(circuit)
        if flag is None:
            es.append(circuit)
        elif flag:
            eo.append(circuit)
        else:
            em.append(circuit)
    return sorted(set(eo)), sorted(set(em)), sorted(set(es))
