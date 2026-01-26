# -*- coding: utf-8 -*-

import math


def parse_cable_db(raw_text):
    if not raw_text:
        return []
    groups = raw_text.split("@@!!@@")
    items = []
    for group in groups:
        if not group:
            continue
        parts = group.split("&&??&&")
        if len(parts) < 3:
            continue
        mark = parts[2]
        payload = parts[1]
        chunks = payload.split("<<@@>>")
        if len(chunks) < 6:
            continue
        names = chunks[0].split("<<&&>>")
        veins = chunks[1].split("<<&&>>")
        cross = chunks[2].split("<<&&>>")
        weight = chunks[3].split("<<&&>>")
        diameter = chunks[4].split("<<&&>>")
        volume = chunks[5].split("<<&&>>")
        for idx in range(len(names)):
            try:
                name = names[idx]
                count_of_veins = int(veins[idx])
                cross_section = float(cross[idx].replace(" ", "").replace(",", "."))
                weight_val = float(weight[idx].replace(" ", "").replace(",", "."))
                diameter_val = float(diameter[idx].replace(" ", "").replace(",", "."))
                volume_val = float(volume[idx].replace(" ", "").replace(",", "."))
            except Exception:
                continue
            items.append(
                {
                    "mark": mark,
                    "name": name,
                    "count_of_veins": count_of_veins,
                    "cross_section": cross_section,
                    "weight": weight_val,
                    "diameter": diameter_val,
                    "volume": volume_val,
                }
            )
    return items


def match_cable_db(cable, db_items):
    if not cable or not db_items:
        return None
    matches = [
        item
        for item in db_items
        if item.get("mark") == cable.get("mark")
        and item.get("count_of_veins") == cable.get("count_of_veins")
        and item.get("cross_section") == cable.get("cross_section")
    ]
    if not matches:
        return None
    preferred = [item for item in matches if "66" in (item.get("name") or "")]
    if preferred:
        return sorted(preferred, key=lambda x: x.get("diameter", 0.0))[0]
    return sorted(matches, key=lambda x: x.get("diameter", 0.0))[0]


def compute_occupancy_percent(diameters_mm, height_mm, width_mm):
    if height_mm <= 0 or width_mm <= 0:
        return 0
    total_area = 0.0
    for diameter in diameters_mm:
        try:
            d = float(diameter)
        except Exception:
            continue
        total_area += math.pi * (d ** 2) / 4.0
    tray_area = height_mm * width_mm
    if tray_area <= 0:
        return 0
    return int(round(total_area / tray_area * 100.0))
