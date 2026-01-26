# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_occupancy_utils import (  # noqa: E402
    compute_occupancy_percent,
    match_cable_db,
    parse_cable_db,
)


class TestKnkOccupancyUtils(unittest.TestCase):
    def test_parse_cable_db(self):
        text5 = "<<@@>>".join([
            "CableA<<&&>>CableB",
            "3<<&&>>4",
            "1.5<<&&>>2.5",
            "10<<&&>>20",
            "5<<&&>>7",
            "100<<&&>>200",
        ])
        raw = "X&&??&&{0}&&??&&MARK".format(text5)
        items = parse_cable_db(raw)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["mark"], "MARK")
        self.assertEqual(items[0]["name"], "CableA")
        self.assertEqual(items[0]["count_of_veins"], 3)
        self.assertAlmostEqual(items[0]["cross_section"], 1.5)
        self.assertAlmostEqual(items[0]["diameter"], 5.0)

    def test_match_cable_db_prefers_66(self):
        cable = {"mark": "M1", "count_of_veins": 3, "cross_section": 1.5}
        db = [
            {"mark": "M1", "count_of_veins": 3, "cross_section": 1.5, "name": "A 66", "diameter": 10.0},
            {"mark": "M1", "count_of_veins": 3, "cross_section": 1.5, "name": "A 04", "diameter": 5.0},
        ]
        matched = match_cable_db(cable, db)
        self.assertEqual(matched["name"], "A 66")

    def test_compute_occupancy(self):
        percent = compute_occupancy_percent([10, 10], 100, 200)
        self.assertEqual(percent, 1)


if __name__ == "__main__":
    unittest.main()
