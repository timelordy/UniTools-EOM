# -*- coding: utf-8 -*-


_SUPPORTED_VIEW_TYPES = {1, 2, 4}


def _view_type_to_int(view_type):
    """Best-effort conversion for Revit ViewType enums or int-like values."""
    if view_type is None:
        return None
    try:
        return int(view_type)
    except Exception:
        pass
    return getattr(view_type, 'value__', view_type)


def is_supported_view_type(view_type):
    value = _view_type_to_int(view_type)
    return value in _SUPPORTED_VIEW_TYPES


def flip_instances(instances):
    for inst in instances or []:
        if getattr(inst, 'CanFlipWorkPlane', False):
            inst.IsWorkPlaneFlipped = not inst.IsWorkPlaneFlipped
