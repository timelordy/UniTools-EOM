# -*- coding: utf-8 -*-

# Config
SOCKET_FAMILY_NAME = "TSL_EF_т_СТ_в_IP20_Рзт_1P+N+PE"
OFFSET_FROM_CORNER_MM = 250  # Distance from the inner corner along the partition wall
OFFSET_FROM_CEILING_MM = 300 # Distance down from the ceiling/wall top
SEARCH_RADIUS_MM = 4000      # Search radius to find walls near basket
PERP_TOLERANCE = 0.3         # Dot product tolerance for perpendicular check

# Limits
MAX_BASKETS = 2000

# Keywords
BASKET_KW = [u"корзин", u"basket", u"кондиц", u"конденс", u"нб_", u"nar_blok"]
BALCONY_KW = [u"балкон", u"лоджия", u"balcony", u"loggia", u"terrace", u"терраса", u"веранда", u"cold", u"холод"]
EXTERIOR_WALL_KW = [u"фасад", u"наружн", u"exterior", u"facade", u"curtain", u"витраж", u"utepl", u"утепл"]

# Parameter to mark created elements
PARAM_COMMENTS = "AUTO_EOM_AC_SOCKET"
