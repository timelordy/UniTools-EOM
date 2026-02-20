# -*- coding: utf-8 -*-

from pyrevit import DB, revit

import adapters
import constants
import domain
from utils_units import ft_to_mm
from utils_revit import find_nearest_level, set_comments, tx


def _collect_doors(doc, uidoc):
    doors = []
    used_selection = False
    try:
        sel_ids = list(uidoc.Selection.GetElementIds()) if uidoc else []
    except Exception:
        sel_ids = []

    if sel_ids:
        for eid in sel_ids:
            try:
                el = doc.GetElement(eid)
            except Exception:
                el = None
            if el is not None and domain.is_door(el):
                doors.append(el)
        if doors:
            used_selection = True

    if not doors:
        try:
            col = DB.FilteredElementCollector(doc)
            col = col.OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
            doors = list(col)
        except Exception:
            doors = []

    return doors, used_selection


def _collect_existing_door_ids(doc):
    existing = set()
    elems = []

    try:
        elems.extend(list(DB.FilteredElementCollector(doc).OfClass(DB.FamilyInstance).WhereElementIsNotElementType()))
    except Exception:
        pass
    try:
        elems.extend(list(DB.FilteredElementCollector(doc).OfClass(DB.DirectShape).WhereElementIsNotElementType()))
    except Exception:
        pass

    for e in elems:
        try:
            comment = domain.get_string_param(
                e,
                bip=DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS,
                name='Comments'
            )
            door_id = domain.parse_door_id_from_comment(comment, constants.PLACEHOLDER_TAG)
            if door_id is not None:
                existing.add(int(door_id))
        except Exception:
            continue

    return existing


def _offset_point(p, vec, dist):
    return DB.XYZ(
        float(p.X) + float(vec.X) * float(dist),
        float(p.Y) + float(vec.Y) * float(dist),
        float(p.Z)
    )


def run(doc, output=None):
    if doc is None:
        return {'created': 0, 'skipped': 0, 'errors': 1}

    uidoc = revit.uidoc
    doors, used_selection = _collect_doors(doc, uidoc)
    if not doors:
        return {'created': 0, 'skipped': 0, 'errors': 0, 'used_selection': used_selection}

    existing_door_ids = _collect_existing_door_ids(doc)
    lintel_symbols = adapters.collect_lintel_symbols(doc)

    created = 0
    skipped = 0
    errors = 0
    family_created = 0
    placeholder_created = 0
    used_symbols = {}

    with tx('AR: Перемычки над дверями'):
        for door in doors:
            try:
                door_id = int(door.Id.IntegerValue)
            except Exception:
                door_id = None

            if door_id is not None and door_id in existing_door_ids:
                skipped += 1
                continue

            wall = None
            try:
                wall = getattr(door, 'Host', None)
            except Exception:
                wall = None
            if wall is None or not isinstance(wall, DB.Wall):
                skipped += 1
                continue

            center_xy = domain.get_location_point(door)
            head_z = domain.get_door_head_z(door)
            if center_xy is None or head_z is None:
                skipped += 1
                continue

            dir_wall, dir_norm = domain.get_door_axes(door, wall)
            if dir_wall is None or dir_norm is None:
                skipped += 1
                continue

            lintel_count = domain.lintel_count_for_wall(wall)

            door_width_ft = domain.get_door_width_ft(door)
            if door_width_ft is None:
                door_width_ft = constants.DEFAULT_OPENING_WIDTH_FT

            required_length_ft = domain.required_lintel_length_ft(door_width_ft)
            target_width_ft = domain.target_lintel_width_ft(wall, lintel_count)

            picked = adapters.pick_lintel_symbol(lintel_symbols, target_width_ft, required_length_ft)
            picked_label = None
            if picked is not None:
                picked_label = "{0}:{1}".format(picked.get('family_name') or '', picked.get('type_name') or '')
                used_symbols[picked_label] = int(used_symbols.get(picked_label, 0)) + 1

            lintel_length_ft = float(required_length_ft)
            if picked is not None and picked.get('length_ft') is not None:
                lintel_length_ft = float(picked.get('length_ft'))

            lintel_width_ft = float(constants.LINTEL_WIDTH_FT)
            if picked is not None and picked.get('width_ft') is not None:
                lintel_width_ft = float(picked.get('width_ft'))
            elif target_width_ft is not None:
                lintel_width_ft = float(target_width_ft)

            lintel_height_ft = float(constants.LINTEL_HEIGHT_FT)

            try:
                if wall.Width and float(wall.Width) > 0:
                    lintel_width_ft = min(lintel_width_ft, float(wall.Width))
            except Exception:
                pass

            offset = 0.0
            if lintel_count == 2:
                offset = domain.lintel_offset_for_wall(wall, lintel_width_ft)
                if offset <= 1e-6:
                    try:
                        offset = max(float(wall.Width) * 0.25, constants.LINTEL_WIDTH_FT * 0.5)
                    except Exception:
                        offset = constants.LINTEL_WIDTH_FT * 0.5

            centers = []
            base_center = DB.XYZ(float(center_xy.X), float(center_xy.Y), float(head_z) + lintel_height_ft * 0.5)
            if lintel_count == 2:
                centers.append(_offset_point(base_center, dir_norm, offset))
                centers.append(_offset_point(base_center, dir_norm, -offset))
            else:
                centers.append(base_center)

            for c in centers:
                created_elem = None

                if picked is not None:
                    level = find_nearest_level(doc, float(c.Z))
                    created_elem = adapters.place_lintel_family_instance(
                        doc,
                        picked.get('symbol'),
                        c,
                        dir_wall,
                        wall=wall,
                        level=level,
                    )

                if created_elem is None:
                    solid = adapters.make_lintel_solid(
                        c,
                        dir_wall,
                        dir_norm,
                        lintel_length_ft,
                        lintel_width_ft,
                        lintel_height_ft
                    )
                    if solid is None:
                        errors += 1
                        continue
                    created_elem = adapters.create_directshape(doc, solid, name=constants.PLACEHOLDER_TAG)
                    if created_elem is None:
                        errors += 1
                        continue
                    placeholder_created += 1
                else:
                    family_created += 1

                try:
                    length_mm = ft_to_mm(lintel_length_ft)
                    width_mm = ft_to_mm(lintel_width_ft)
                    height_mm = ft_to_mm(lintel_height_ft)
                    comment = domain.build_comment(
                        constants.PLACEHOLDER_TAG,
                        door_id or 0,
                        lintel_count,
                        length_mm,
                        width_mm,
                        height_mm,
                        symbol_label=picked_label if picked_label else 'DirectShape'
                    )
                    set_comments(created_elem, comment)
                except Exception:
                    pass

                created += 1

    return {
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'family_created': family_created,
        'placeholder_created': placeholder_created,
        'family_symbols_total': len(lintel_symbols),
        'used_symbols': used_symbols,
        'used_selection': used_selection,
        'doors_total': len(doors),
    }
