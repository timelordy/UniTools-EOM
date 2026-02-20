# -*- coding: utf-8 -*-

from pyrevit import DB

import floor_panel_niches as fpn
import link_reader


def same_level(room, level_id):
    try:
        rid = getattr(room, 'LevelId', None)
        return bool(rid and rid.IntegerValue == level_id.IntegerValue)
    except Exception:
        return False


def room_text(room):
    return fpn.room_text(room)


def pick_corridor_room(rooms_on_level, corridor_patterns):
    candidates = []
    rx = fpn.compile_patterns(corridor_patterns)
    for room in rooms_on_level:
        try:
            if room is None or float(getattr(room, 'Area', 0.0) or 0.0) <= 0.0:
                continue
        except Exception:
            continue

        text = room_text(room)
        if not fpn.match_any(rx, text):
            continue

        center = link_reader.get_room_center_ex_safe(room)
        if center is None:
            continue

        candidates.append((room, center, text))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (item[2] or u'').lower())
    return candidates[0][0], candidates[0][1]


def collect_opening_instances(link_doc, opening_type_names):
    instances = []
    for inst in link_reader.iter_family_instances_by_family_type(link_doc, opening_type_names):
        if inst is None:
            continue
        instances.append(inst)
    return instances


def _instance_point_link(inst):
    point = link_reader.get_instance_fallback_point(inst)
    if point is None:
        return None
    return DB.XYZ(float(point.X), float(point.Y), float(point.Z))


def _instance_level_id(inst):
    if inst is None:
        return None

    try:
        level_id = getattr(inst, 'LevelId', None)
        if level_id is not None and level_id.IntegerValue > 0:
            return level_id
    except Exception:
        pass

    # Fallback for families where LevelId is invalid/empty.
    for bip in (
        DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
        DB.BuiltInParameter.FAMILY_LEVEL_PARAM,
        DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
    ):
        try:
            param = inst.get_Parameter(bip)
            if param is None:
                continue
            level_id = param.AsElementId()
            if level_id is not None and level_id.IntegerValue > 0:
                return level_id
        except Exception:
            continue

    return None


def pick_opening_near_corridor(instances, corridor_center_link, level_id_link, level_elev_link, level_tol_ft):
    if corridor_center_link is None:
        return None, None

    best_inst = None
    best_point = None
    best_score = None

    for inst in instances:
        point = _instance_point_link(inst)
        if point is None:
            continue

        # Priority model:
        #   0) strict LevelId match
        #   1) close in Z within level tolerance
        #   2) close in Z within 3x tolerance
        #   3) fallback by nearest plan distance (for "dirty" links)
        inst_level_id = _instance_level_id(inst)
        level_match = False
        try:
            if level_id_link is not None and inst_level_id is not None:
                level_match = inst_level_id.IntegerValue == level_id_link.IntegerValue
        except Exception:
            level_match = False

        dz = 1e9
        try:
            if level_elev_link is not None:
                dz = abs(float(point.Z) - float(level_elev_link))
        except Exception:
            dz = 1e9

        dx = float(point.X) - float(corridor_center_link.X)
        dy = float(point.Y) - float(corridor_center_link.Y)
        dist_plan = (dx * dx + dy * dy) ** 0.5

        tol = None
        try:
            if level_tol_ft is not None:
                tol = float(level_tol_ft)
        except Exception:
            tol = None

        if level_match:
            score = (0, dist_plan, dz)
        elif tol is not None and dz <= tol:
            score = (1, dist_plan, dz)
        elif tol is not None and dz <= (tol * 3.0):
            score = (2, dz, dist_plan)
        else:
            score = (3, dz, dist_plan)

        if best_score is None or score < best_score:
            best_score = score
            best_inst = inst
            best_point = point

    return best_inst, best_point
