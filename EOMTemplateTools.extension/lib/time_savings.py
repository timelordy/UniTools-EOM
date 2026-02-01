# -*- coding: utf-8 -*-

"""Time-saved reporting for EOM tools.

Estimates time saved based on manual placement rate and actual element count.

`MANUAL_TIME_PER_ITEM` values can be:
- float: fixed minutes per unit
- (min, max): range of minutes per unit
"""


# Manual placement time estimates (minutes per element/room).
# NOTE: keep Python 2.7 compatibility (pyRevit/IronPython).
MANUAL_TIME_PER_ITEM = {
    # 01. Розетки (бытовые): ~4 sockets/room, 5–7 min total
    'sockets_general': (1.25, 1.75),
    # 02. Кухня блок: 4 sockets total, 5–7 min total
    'kitchen_block': (1.25, 1.75),
    # 05/06/07: mostly 1 element per room
    'wet_zones': (1.0, 3.0),
    'low_voltage': (1.0, 3.0),
    'switches_doors': (1.0, 3.0),
    'lights_center': (1.0, 3.0),
    'shdup': (1.0, 3.0),
    # Свет в лифтах: per shaft (not per placed light)
    'lights_elevator': (10.0, 10.0),
    # Щит над дверью: per apartment
    'panel_door': (7.0, 7.0),

    # Other tools (kept for compatibility)
    'lights_entrance': (1.0, 3.0),
    'entrance_numbering': (10.0, 10.0),
    'storage_equipment': (15.0, 15.0),
    'panels_mop': (5.0, 5.0),
}


# Backward-compatible key aliases used by some scripts
TOOL_KEY_ALIASES = {
    'switches': 'switches_doors',
    'sockets_wet': 'wet_zones',
    'sockets_low_voltage': 'low_voltage',
}


DEFAULT_TIME_PER_ITEM = 0.5

# Session storage for element counts
_session_counts = {}


def set_element_count(tool_key, count):
    """Store the number of elements created for time calculation."""
    key = normalize_tool_key(tool_key)
    try:
        _session_counts[key] = int(count or 0)
    except Exception:
        _session_counts[key] = 0


def get_element_count(tool_key):
    """Get stored element count."""
    key = normalize_tool_key(tool_key)
    try:
        return int(_session_counts.get(key, 0) or 0)
    except Exception:
        return 0


def normalize_tool_key(tool_key):
    """Return canonical tool key (handles legacy aliases)."""
    try:
        return TOOL_KEY_ALIASES.get(tool_key, tool_key)
    except Exception:
        return tool_key


def get_manual_time_per_item_range(tool_key):
    """Return (min, max) minutes per unit."""
    key = normalize_tool_key(tool_key)
    v = MANUAL_TIME_PER_ITEM.get(key, None)
    if v is None:
        return float(DEFAULT_TIME_PER_ITEM), float(DEFAULT_TIME_PER_ITEM)
    try:
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return float(v[0]), float(v[1])
    except Exception:
        pass
    try:
        fv = float(v)
        return fv, fv
    except Exception:
        return float(DEFAULT_TIME_PER_ITEM), float(DEFAULT_TIME_PER_ITEM)


def calculate_time_saved_range(tool_key, count=None):
    """Calculate (min, max) time saved in minutes based on element count."""
    if count is None:
        count = get_element_count(tool_key)
    try:
        cnt = int(count or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        return 0.0, 0.0

    rate_min, rate_max = get_manual_time_per_item_range(tool_key)
    return cnt * float(rate_min), cnt * float(rate_max)


def calculate_time_saved(tool_key, count=None):
    """Calculate time saved in minutes based on element count."""
    mn, mx = calculate_time_saved_range(tool_key, count)
    if mn <= 0 and mx <= 0:
        return 0.0
    return (float(mn) + float(mx)) / 2.0


def _format_minutes(minutes):
    try:
        minutes = float(minutes)
    except Exception:
        minutes = 0.0

    if minutes <= 0:
        return None

    if minutes < 1:
        return u'меньше минуты'
    elif minutes < 60:
        mins = int(round(minutes))
        if mins <= 0:
            return u'меньше минуты'
        if mins == 1:
            return u'~1 минута'
        # 2-4 minutes: "минуты", else "минут"
        if mins < 5:
            return u'~{0} минуты'.format(mins)
        return u'~{0} минут'.format(mins)
    else:
        hours = minutes / 60.0
        if hours < 2:
            return u'~{0:.1f} час'.format(hours)
        return u'~{0:.1f} часов'.format(hours)


def format_time_saved(tool_key, count=None):
    """Format time saved as human-readable string."""
    minutes = calculate_time_saved(tool_key, count)
    return _format_minutes(minutes)


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

    mn, mx = calculate_time_saved_range(tool_key, saved_count)
    range_str = None
    try:
        if abs(float(mx) - float(mn)) > 1e-6:
            range_str = u'диапазон: {0}–{1}'.format(_format_minutes(mn), _format_minutes(mx))
    except Exception:
        range_str = None

    msg = u'Сэкономлено времени: **{0}**'.format(time_str)
    if range_str:
        msg += u' ({0})'.format(range_str)
    msg += u' (создано элементов: {0})'.format(saved_count)
    
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
