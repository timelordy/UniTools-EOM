# -*- coding: utf-8 -*-

COMMENT_TAG_DEFAULT = 'AUTO_EOM'
COMMENT_SUFFIX = ':SHDUP'

DEFAULT_SHDUP_HEIGHT_MM = 300
DEFAULT_DEDUPE_MM = 300

DEFAULT_VALIDATE_MATCH_TOL_MM = 2000
DEFAULT_VALIDATE_HEIGHT_TOL_MM = 20
DEFAULT_VALIDATE_WALL_DIST_MM = 150
DEFAULT_VALIDATE_BETWEEN_PAD_MM = 100

DEFAULT_BATH_PATTERNS = [u'ванн', u'санузел', u'туалет', u'уборная', u'постирочная', u'моп']

SINK_KEYWORDS_DEFAULT = [u'раков', u'умыв', u'sink', u'washbasin', u'мойк', u'basin', u'lavatory']
TUB_KEYWORDS_DEFAULT = [u'ванн', u'bath', u'tub', u'jacuzzi', u'джакузи']
TOILET_KEYWORDS_DEFAULT = [u'унитаз', u'toilet', u'wc', u'closet', u'биде', u'bidet']

SHDUP_KEYWORDS = [u'шдуп', u'shdup', u'пс_кр']

BATCH_SIZE = 25
