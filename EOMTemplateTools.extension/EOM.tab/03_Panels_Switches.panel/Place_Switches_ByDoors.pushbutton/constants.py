# -*- coding: utf-8 -*-

SWITCH_HEIGHT_MM = 900
OUTLET_HEIGHT_MM = 300  # Высота розетки от пола
# Distance from door jamb to switch center (СП 31-110-2003 recommends 100-200mm)
JAMB_OFFSET_MM = 150
COMMENT_TAG = u"AUTO_EOM:SWITCH"
COMMENT_TAG_OUTLET = u"AUTO_EOM:OUTLET"

SWITCH_1G_TYPE_ID = 2010333
SWITCH_2G_TYPE_ID = 2015166
OUTLET_TYPE_ID = 2010333  # TODO: заменить на реальный ID розетки

WET_ROOMS = [u"ванная", u"душ", u"туа", u"сану", u"сан.", u"с/у", u"wc"]
TWO_GANG_ROOMS = [u"спальн", u"кабине", u"детск", u"гостин"]
CORRIDOR_ROOMS = [u"коридо", u"холл", u"прихо", u"тамбур", u"вестиб"]
SKIP_ROOMS = [u"балкон", u"лоджи", u"терра", u"гараж", u"кладо", u"подсоб"]

# Паттерны для определения входной двери (в имени типа)
# ДМ = Дверь Металлическая (входная в квартиру)
ENTRANCE_DOOR_PATTERNS = [u"вход", u"наруж", u"металл", u"стальн", u"двп", u"дв_вх", u"дм_"]
