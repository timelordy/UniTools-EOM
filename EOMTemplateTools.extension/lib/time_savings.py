# -*- coding: utf-8 -*-

"""Time-saved reporting for EOM tools.

Estimates time saved based on manual placement rate and actual element count.
"""

# Manual placement time estimates (minutes per element/room)
MANUAL_TIME_PER_ITEM = {
    'sockets_general': 0.5,        # 0.5 min per socket
    'sockets_kitchen_unit': 0.5,
    'sockets_kitchen_general': 0.5,
    'sockets_ac': 0.3,
    'sockets_wet': 0.3,
    'sockets_low_voltage': 0.3,
    'switches': 0.3,
    'lights_room': 0.3,
    'shdup': 0.5,
    'lights_lift_shaft': 2.0,
    'lights_entrance_doors': 0.5,
    'lights_pk': 1.0,
    'panels_shk_apartment': 7.0,
    'panels_mop': 5.0,
    'storage_equipment': 15.0,
    'entrance_numbering': 10.0,
}

# Session storage for element counts
_session_counts = {}


def set_element_count(tool_key, count):
    """Store the number of elements created for time calculation."""
    _session_counts[tool_key] = count


def get_element_count(tool_key):
    """Get stored element count."""
    return _session_counts.get(tool_key, 0)


def calculate_time_saved(tool_key, count=None):
    """Calculate time saved in minutes based on element count."""
    if count is None:
        count = get_element_count(tool_key)
    if count <= 0:
        return 0
    rate = MANUAL_TIME_PER_ITEM.get(tool_key, 0.5)
    return count * rate


def format_time_saved(tool_key, count=None):
    """Format time saved as human-readable string."""
    minutes = calculate_time_saved(tool_key, count)
    if minutes <= 0:
        return None
    if minutes < 1:
        return u'меньше минуты'
    elif minutes < 60:
        mins = int(round(minutes))
        if mins == 1:
            return u'~1 минута'
        elif mins < 5:
            return u'~{0} минуты'.format(mins)
        else:
            return u'~{0} минут'.format(mins)
    else:
        hours = minutes / 60.0
        if hours < 2:
            return u'~{0:.1f} час'.format(hours)
        else:
            return u'~{0:.1f} часов'.format(hours)


def report(output, tool_key, count=None):
    """Report time saved to output.
    
    Args:
        output: pyRevit output object with print_md method
        tool_key: Tool identifier (e.g., 'sockets_general')
        count: Number of elements created. If None, uses stored count.
    """
    if count is not None:
        set_element_count(tool_key, count)
    
    saved_count = get_element_count(tool_key)
    time_str = format_time_saved(tool_key, saved_count)
    
    if not time_str:
        return False
    
    msg = u'Сэкономлено времени: **{0}** (создано элементов: {1})'.format(time_str, saved_count)
    
    try:
        if output is not None and hasattr(output, 'print_md'):
            output.print_md(msg)
        else:
            from utils_revit import alert
            alert(msg, title='EOM Template Tools', warn_icon=False)
    except Exception:
        try:
            from utils_revit import get_logger
            get_logger().info(msg)
        except Exception:
            pass
    return True


# Backwards-compatible alias
report_time_saved = report
