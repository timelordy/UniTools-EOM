# -*- coding: utf-8 -*-

import re

from pyrevit import DB

from utils_units import ft_to_mm
import constants


def is_door(elem):
    try:
        cat = getattr(elem, 'Category', None)
        return bool(cat and int(cat.Id.IntegerValue) == int(DB.BuiltInCategory.OST_Doors))
    except Exception:
        return False


def get_double_param(elem, bip=None, name=None):
    if elem is None:
        return None
    p = None
    if bip is not None:
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return None
    try:
        return p.AsDouble()
    except Exception:
        return None


def get_string_param(elem, bip=None, name=None):
    if elem is None:
        return ''
    p = None
    if bip is not None:
        try:
            p = elem.get_Parameter(bip)
        except Exception:
            p = None
    if p is None and name:
        try:
            p = elem.LookupParameter(name)
        except Exception:
            p = None
    if p is None:
        return ''
    try:
        return p.AsString() or ''
    except Exception:
        try:
            return p.AsValueString() or ''
        except Exception:
            return ''


def normalize(vec):
    if vec is None:
        return None
    try:
        if float(vec.GetLength()) < 1e-9:
            return None
        return vec.Normalize()
    except Exception:
        return None


def get_location_point(elem):
    if elem is None:
        return None
    try:
        loc = elem.Location
    except Exception:
        return None
    if loc is None:
        return None
    try:
        if isinstance(loc, DB.LocationPoint):
            return loc.Point
        if isinstance(loc, DB.LocationCurve):
            try:
                return loc.Curve.Evaluate(0.5, True)
            except Exception:
                return None
    except Exception:
        return None
    return None


def get_door_width_ft(door):
    if door is None:
        return None
    for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
        if target is None:
            continue
        val = get_double_param(target, bip=DB.BuiltInParameter.DOOR_WIDTH, name='Width')
        if val is not None:
            return val
    return None


def get_door_head_z(door):
    if door is None:
        return None

    level = None
    try:
        if door.LevelId:
            level = door.Document.GetElement(door.LevelId)
    except Exception:
        level = None
    level_z = float(level.Elevation) if level is not None else 0.0

    head = None
    for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
        if target is None:
            continue
        head = get_double_param(target, bip=DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM, name='Head Height')
        if head is not None:
            break
    if head is None:
        for target in (door, getattr(door, 'Symbol', None), door.Document.GetElement(door.GetTypeId())):
            if target is None:
                continue
            head = get_double_param(target, bip=DB.BuiltInParameter.DOOR_HEIGHT, name='Height')
            if head is not None:
                break

    if head is not None:
        return level_z + float(head)

    try:
        bb = door.get_BoundingBox(None)
        if bb:
            return float(bb.Max.Z)
    except Exception:
        pass
    return None


def get_door_axes(door, wall):
    hand = None
    facing = None
    try:
        hand = getattr(door, 'HandOrientation', None)
    except Exception:
        hand = None
    try:
        facing = getattr(door, 'FacingOrientation', None)
    except Exception:
        facing = None

    hand = normalize(hand)
    facing = normalize(facing)

    if facing is None and wall is not None:
        try:
            facing = normalize(wall.Orientation)
        except Exception:
            facing = None

    if hand is None and wall is not None:
        try:
            loc = wall.Location
            curve = loc.Curve if loc else None
            if curve is not None:
                try:
                    dir_vec = getattr(curve, 'Direction', None)
                    if dir_vec is None:
                        deriv = curve.ComputeDerivatives(0.5, True)
                        dir_vec = deriv.BasisX if deriv else None
                    hand = normalize(dir_vec)
                except Exception:
                    hand = None
        except Exception:
            hand = None

    if hand is None and facing is not None:
        try:
            hand = normalize(DB.XYZ.BasisZ.CrossProduct(facing))
        except Exception:
            hand = None

    if facing is None and hand is not None:
        try:
            facing = normalize(hand.CrossProduct(DB.XYZ.BasisZ))
        except Exception:
            facing = None

    return hand, facing


def lintel_count_for_wall(wall):
    if wall is None:
        return 1
    try:
        thickness_mm = ft_to_mm(float(wall.Width))
    except Exception:
        thickness_mm = None
    if thickness_mm is None:
        return 1
    return 2 if thickness_mm >= constants.DOUBLE_LINTEL_WALL_MM else 1


def lintel_offset_for_wall(wall, lintel_width_ft):
    if wall is None:
        return 0.0
    try:
        wall_w = float(wall.Width)
    except Exception:
        wall_w = 0.0
    if wall_w <= 0.0:
        return 0.0
    try:
        offset = wall_w * 0.5 - float(lintel_width_ft) * 0.5
    except Exception:
        offset = 0.0
    return offset if offset > 1e-6 else 0.0


def required_lintel_length_ft(door_width_ft):
    if door_width_ft is None:
        door_width_ft = constants.DEFAULT_OPENING_WIDTH_FT
    return float(door_width_ft) + 2.0 * float(constants.LINTEL_BEARING_FT)


def target_lintel_width_ft(wall, lintel_count):
    if wall is None:
        return float(constants.LINTEL_WIDTH_FT)
    try:
        wall_w = float(wall.Width)
    except Exception:
        wall_w = 0.0
    if wall_w <= 0.0:
        return float(constants.LINTEL_WIDTH_FT)
    if int(lintel_count) <= 1:
        return wall_w
    return wall_w / float(lintel_count)


def normalize_name(text):
    if text is None:
        return ""
    try:
        s = str(text)
    except Exception:
        return ""
    s = s.strip().lower()
    if s.endswith(".rfa"):
        s = s[:-4]
    return s


def matches_preferred_lintel_name(family_name, type_name):
    fam = normalize_name(family_name)
    typ = normalize_name(type_name)
    pair = (fam + " " + typ).strip()

    preferred = [normalize_name(x) for x in constants.PREFERRED_LINTEL_NAMES]
    if fam in preferred or typ in preferred or pair in preferred:
        return True

    prefix = normalize_name(constants.LINTEL_NAME_PREFIX)
    if prefix and (fam.startswith(prefix) or typ.startswith(prefix)):
        return True

    # Conservative fallback for similar naming in AR libraries.
    if u"перемычка" in fam and u"пб" in fam:
        return True
    if u"перемычка" in typ and u"пб" in typ:
        return True

    return False


def rank_from_name(family_name, type_name):
    label = "{0} {1}".format(type_name or "", family_name or "")
    try:
        m = re.search(r"(\d{4})(?:\.rfa)?\s*$", str(label), re.IGNORECASE)
    except Exception:
        m = None
    if not m:
        return 9999
    try:
        return int(m.group(1))
    except Exception:
        return 9999


def build_comment(tag, door_id, count, length_mm, width_mm, height_mm, symbol_label=None):
    base = "{0}|door={1}|count={2}|len_mm={3}|w_mm={4}|h_mm={5}".format(
        tag, int(door_id), int(count), int(round(length_mm)), int(round(width_mm)), int(round(height_mm))
    )
    if symbol_label:
        try:
            return "{0}|type={1}".format(base, str(symbol_label))
        except Exception:
            return base
    return base


def parse_door_id_from_comment(comment, tag):
    if not comment:
        return None
    try:
        if tag not in comment:
            return None
    except Exception:
        return None
    try:
        parts = str(comment).split('|')
    except Exception:
        return None
    for part in parts:
        part = part.strip()
        if part.startswith('door='):
            try:
                return int(part.split('=', 1)[1])
            except Exception:
                return None
    return None
