# -*- coding: utf-8 -*-

# Комментарий для авто-размещенных элементов
COMMENT_TAG_DEFAULT = "AUTO_EOM"
COMMENT_SUFFIX = ":STORAGE"

# Высоты размещения (мм)
DEFAULT_PANEL_HEIGHT_MM = 1700  # Щиток
DEFAULT_SWITCH_HEIGHT_MM = 900  # Выключатель
DEFAULT_LIGHT_HEIGHT_MM = 2700  # Светильник (от уровня помещения)

# Дедупликация
DEFAULT_DEDUPE_MM = 300

# Размеры батча
BATCH_SIZE = 25

# Паттерны для поиска кладовых
DEFAULT_STORAGE_ROOM_PATTERNS = [
    "клад",
    "хранил",
    "кладов",
    "storage"
]

# Валидация
DEFAULT_VALIDATE_MATCH_TOL_MM = 2000
DEFAULT_VALIDATE_HEIGHT_TOL_MM = 20
DEFAULT_VALIDATE_WALL_DIST_MM = 100
