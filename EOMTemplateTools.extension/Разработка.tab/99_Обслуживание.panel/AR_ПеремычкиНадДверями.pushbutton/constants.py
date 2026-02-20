# -*- coding: utf-8 -*-

from utils_units import mm_to_ft

# Tag stored in element Comments for de-duplication.
PLACEHOLDER_TAG = "UT_AR_LINTEL"

# Preferred lintel families (as shown in AR library / file names).
# Matching is done against both Family.Name and Type.Name (with and without ".rfa").
PREFERRED_LINTEL_NAMES = (
    u"180_Перемычка ПБ",
    u"180_Перемычка_ПБ",
    u"180_Перемычка.ПБ.0001",
    u"180_Перемычка.ПБ.0002",
    u"180_Перемычка.ПБ.0003",
    u"180_Перемычка_ПБ.0001",
    u"180_Перемычка_ПБ.0002",
    u"180_Перемычка_ПБ.0003",
)
LINTEL_NAME_PREFIX = u"180_Перемычка"

# Candidate parameter names for symbol dimensions.
LINTEL_LENGTH_PARAM_NAMES = (
    u"Длина",
    "Length",
    "L",
)
LINTEL_WIDTH_PARAM_NAMES = (
    u"Ширина",
    "Width",
    "B",
    "b",
    u"Толщина",
)

# Allowed mismatch on width (for symbol selection)
WIDTH_MATCH_TOLERANCE_MM = 30

# Optional family name to use if a placeholder family exists in the model.
PLACEHOLDER_FAMILY_NAME = "UT_AR_LINTEL_PLACEHOLDER"
PLACEHOLDER_TYPE_NAME = "Default"

# Geometry defaults (mm)
LINTEL_WIDTH_MM = 120
LINTEL_HEIGHT_MM = 140
LINTEL_BEARING_MM = 100

# Logic thresholds
DOUBLE_LINTEL_WALL_MM = 200  # 240 mm walls -> 2 lintels

# Fallback opening width
DEFAULT_OPENING_WIDTH_MM = 900

# Derived defaults (ft)
LINTEL_WIDTH_FT = mm_to_ft(LINTEL_WIDTH_MM)
LINTEL_HEIGHT_FT = mm_to_ft(LINTEL_HEIGHT_MM)
LINTEL_BEARING_FT = mm_to_ft(LINTEL_BEARING_MM)
DEFAULT_OPENING_WIDTH_FT = mm_to_ft(DEFAULT_OPENING_WIDTH_MM)
