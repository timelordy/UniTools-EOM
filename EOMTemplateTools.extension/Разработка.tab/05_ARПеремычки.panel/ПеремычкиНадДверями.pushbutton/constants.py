# -*- coding: utf-8 -*-

from utils_units import mm_to_ft

# Tag stored in element Comments for de-duplication.
PLACEHOLDER_TAG = "UT_AR_LINTEL"

# Preferred lintel family/type (optional exact match).
# Leave empty to use keyword-based auto-detection.
LINTEL_FAMILY_PB = "180_Перемычка_ПБ"
LINTEL_FAMILY_PA = "180_Перемычка_ПА"
LINTEL_FAMILY_PA_ALT = "180_Перемычка ПА"
# Backward-compatible alias used by older code paths.
LINTEL_FAMILY_NAME = LINTEL_FAMILY_PB
LINTEL_FAMILY_NAMES = (
    LINTEL_FAMILY_PB,
    LINTEL_FAMILY_PA,
    LINTEL_FAMILY_PA_ALT,
)
LINTEL_TYPE_NAME = ""
LINTEL_SYMBOL_KEYWORDS = ("перемыч", "пб", "па", "lintel")
PREFER_SYMBOL_WITH_120 = False
LINTEL_LENGTH_PARAM_NAMES = ("ADSK_Размер_Длина", "Длина", "Length", "L")
LINTEL_LENGTH_PICK_TOLERANCE_MM = 5.0

# Legacy placeholder symbol lookup.
PLACEHOLDER_FAMILY_NAME = "UT_AR_LINTEL_PLACEHOLDER"
PLACEHOLDER_TYPE_NAME = "Default"
ALLOW_DIRECTSHAPE_FALLBACK = False

# Geometry defaults (mm)
LINTEL_WIDTH_MM = 120
LINTEL_HEIGHT_MM = 140
LINTEL_BEARING_MM = 100
LINTEL_GAP_ABOVE_OPENING_MM = 0
LINTEL_TABLE_TOLERANCE_MM = 30.0
LINTEL_MARK_EXACT_NORMALIZE = True

# Do not force cut/join between lintel and host wall.
# This avoids "Instance(s) ... not cutting anything" warnings on loadable PB types.
LINTEL_JOIN_WITH_WALL = False

# Static table is intentionally empty.
# Actual type sizing is read directly from the loaded family types
# (Ширина проема, ADSK_Размер_Длина, ADSK_Размер_Высота и др.).
LINTEL_SELECTION_TABLE = ()

# Wall filtering logic:
# - ceramic walls -> table 1 marks (1ПБ/2ПБ/3ПБ)
# - silicate walls -> table 4 marks (8ПБ/9ПБ/10ПБ)
# - pgp walls (80 mm) -> rebar lintels from family 180_Перемычка_ПА
# - supported wall classes: 80 (PGP), 120 and 250 mm (brick)
# - if wall thickness class > 120 mm -> instance flag "2 шт" ON
# - if wall thickness class == 120 mm -> instance flag "1 шт" ON
PGP_WALL_KEYWORDS = ("пгп",)
SILICATE_WALL_KEYWORDS = ("силикат",)
CERAMIC_WALL_KEYWORDS = ("керамич",)
CERAMIC_MARK_PREFIXES = ("1ПБ", "2ПБ", "3ПБ")
SILICATE_MARK_PREFIXES = ("8ПБ", "9ПБ", "10ПБ")

WALL_DOUBLE_THRESHOLD_MM = 120.0
WALL_THICKNESS_TOLERANCE_MM = 20.0

# Compatibility constants (used by legacy helpers).
PGP_80_MARKERS = ("80",)
PGP_80_MM = 80.0
# PGP rods are picked by the shortest feasible support at both sides of opening.
# `PGP_MIN_BEARING_MM` is the hard minimum, `PGP_TARGET_BEARING_MM` is desired trim.
PGP_BEARING_MM = 150.0
PGP_MIN_BEARING_MM = 90.0
PGP_TARGET_BEARING_MM = 100.0
# Table: lintels from rebar for PGP (GOST 34028-2016), sorted ascending by length.
PGP_REBAR_LENGTHS_MM = (
    1090.0,
    1110.0,
    1150.0,
    1165.0,
    1200.0,
    1210.0,
    1800.0,
    2240.0,
    2300.0,
    2310.0,
    2350.0,
)
SILICATE_120_MARKERS = ("120",)
SILICATE_250_MARKERS = ("250",)
SILICATE_120_MM = 120.0
SILICATE_250_MM = 250.0
SILICATE_THICKNESS_TOLERANCE_MM = WALL_THICKNESS_TOLERANCE_MM
LINTEL_FAMILY_BY_WALL_MM = {
    80: LINTEL_FAMILY_PA,
    120: LINTEL_FAMILY_PB,
    250: LINTEL_FAMILY_PB,
}
SILICATE_STRICT_NAME_ONLY = False

# Fallback opening width
DEFAULT_OPENING_WIDTH_MM = 900

# Debug output controls
DEBUG_PRINT_PER_DOOR_LIMIT = 1000000

# Debug plan view controls (created/updated after script run)
DEBUG_CREATE_PLAN_AT_END = False
DEBUG_PLAN_NAME = "UT_AR_Перемычки_Отладка"
DEBUG_PLAN_VERTICAL_MARGIN_MM = 200.0
DEBUG_PLAN_MIN_RANGE_MM = 400.0
DEBUG_PLAN_OPEN_AFTER_CREATE = True

# Derived defaults (ft)
LINTEL_WIDTH_FT = mm_to_ft(LINTEL_WIDTH_MM)
LINTEL_HEIGHT_FT = mm_to_ft(LINTEL_HEIGHT_MM)
LINTEL_BEARING_FT = mm_to_ft(LINTEL_BEARING_MM)
LINTEL_GAP_ABOVE_OPENING_FT = mm_to_ft(LINTEL_GAP_ABOVE_OPENING_MM)
DEFAULT_OPENING_WIDTH_FT = mm_to_ft(DEFAULT_OPENING_WIDTH_MM)
