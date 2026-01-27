# -*- coding: utf-8 -*-

DEFAULT_SPACING_MM = 3000
DEFAULT_HEIGHT_MM = 300
AVOID_DOOR_MM = 300
AVOID_RADIATOR_MM = 500
DEDUPE_MM = 300
BATCH_SIZE = 25

COMMENT_TAG_DEFAULT = 'AUTO_EOM'
COMMENT_SUFFIX = ':SOCKET_GENERAL'

# Default regex patterns
DEFAULT_HALLWAY_PATTERNS = [u'корид', u'холл', u'corridor', u'hall', u'прихожая', u'вестибюль']
DEFAULT_WET_PATTERNS = [u'ванная', u'санузел', u'сан. узел', u'туалет', u'уборная', u'bath', u'toilet', u'wc', u'restroom', u'shower', u'душевая']
DEFAULT_KITCHEN_PATTERNS = [u'кухн', u'kitchen', u'столов']
DEFAULT_EXCLUDE_PATTERNS = [u'лоджия', u'балкон', u'loggia', u'balcony', u'терраса', u'terrace']

DEFAULT_APARTMENT_PATTERNS = [u'жилая', u'комната', u'спальня', u'гостиная', u'bed', u'living', u'room', u'apartment', u'квартир', u'кабинет']
DEFAULT_PUBLIC_PATTERNS = [u'моп', u'лестни', u'лифт', u'тамбур', u'технич', u'кладов', u'электро', u'itp', u'pump', u'roof', u'lobby']
