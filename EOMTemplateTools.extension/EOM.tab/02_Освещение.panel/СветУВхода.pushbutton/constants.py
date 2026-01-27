# -*- coding: utf-8 -*-

OUTSIDE_DEFAULT_PATTERNS = [
    u'улиц', u'наруж', u'внеш', u'street', u'outside', u'exterior'
]

ROOF_DEFAULT_PATTERNS = [
    u'кровл', u'roof'
]

ENTRANCE_DOOR_DEFAULT_PATTERNS = [
    u'вход', u'входн', u'entry', u'entrance', u'тамбур', u'вестиб'
]

ROOF_EXIT_DOOR_DEFAULT_PATTERNS = [
    u'кровл', u'roof', u'выход на кровлю'
]

ENTRANCE_INSIDE_ROOM_DEFAULT_PATTERNS = [
    u'тамбур', u'вестиб', u'холл', u'лестн', u'корид', u'подъезд',
    u'hall', u'corridor', u'lobby', u'stair', u'тбо'
]

ENTRANCE_PUBLIC_ROOM_DEFAULT_PATTERNS = [
    u'внеквартир', u'корид', u'холл', u'лестн', u'лифтов', u'тамбур',
    u'вестиб', u'подъезд', u'тбо', u'lobby', u'stair'
]

APARTMENT_ROOM_DEFAULT_PATTERNS = [
    u'квартир', u'прихож', u'кухн', u'спальн', u'гостин', u'комнат',
    u'жил', u'детск', u'кабин', u'клад', u'гардер', u'сан', u'с/у',
    u'ванн', u'душ', u'wc', u'toilet', u'bath', u'bedroom', u'living'
]

ENTRANCE_LEVEL_DEFAULT_PATTERNS = [
    u'э1', u'±0.000', u'+0.000', u'0.000', u'перв'
]

LIGHT_STRONG_KEYWORDS = [u'свет', u'light', u'lighting', u'светиль', u'lamp', u'lum']
LIGHT_EXTERIOR_KEYWORDS = [u'наруж', u'outdoor', u'exterior', u'фасад', u'wall']
LIGHT_NEGATIVE_KEYWORDS = [u'авар', u'emerg', u'emergency', u'exit', u'табло', u'указ', u'эвак']
