# -*- coding: utf-8 -*-

import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim import knk_switch  # noqa: E402


class TestKnkSwitch(unittest.TestCase):
    def test_to_roman_basic(self):
        self.assertEqual(knk_switch.to_roman(0), '')
        self.assertEqual(knk_switch.to_roman(1), 'I')
        self.assertEqual(knk_switch.to_roman(2), 'II')
        self.assertEqual(knk_switch.to_roman(4), 'IV')
        self.assertEqual(knk_switch.to_roman(9), 'IX')
        self.assertEqual(knk_switch.to_roman(10), 'X')
        self.assertEqual(knk_switch.to_roman(14), 'XIV')
        self.assertEqual(knk_switch.to_roman(40), 'XL')
        self.assertEqual(knk_switch.to_roman(90), 'XC')
        self.assertEqual(knk_switch.to_roman(400), 'CD')
        self.assertEqual(knk_switch.to_roman(900), 'CM')
        self.assertEqual(knk_switch.to_roman(1000), 'M')

    def test_assign_switch_codes_basic(self):
        segments = [
            {
                'base_id': 100,
                'light_ids': [1, 2],
                'device_ids': [10, 11],
            },
            {
                'base_id': 100,
                'light_ids': [3],
                'device_ids': [],
            },
        ]
        result = knk_switch.assign_switch_codes(segments)
        self.assertEqual(result['light_codes'][1], 'I')
        self.assertEqual(result['light_codes'][2], 'I')
        self.assertEqual(result['light_codes'][3], 'II')
        self.assertEqual(result['switch_codes'][10], 'I')
        self.assertEqual(result['switch_codes'][11], 'I')
        self.assertEqual(result['switch_codes'][100], 'II')

    def test_assign_switch_codes_extend_existing(self):
        segments = [
            {
                'base_id': 100,
                'light_ids': [1],
                'device_ids': [],
            },
            {
                'base_id': 100,
                'light_ids': [2],
                'device_ids': [10],
            },
        ]
        result = knk_switch.assign_switch_codes(segments)
        self.assertEqual(result['light_codes'][1], 'I')
        self.assertEqual(result['light_codes'][2], 'II')
        self.assertEqual(result['switch_codes'][10], 'I,II')
        self.assertNotIn(100, result['switch_codes'])

    def test_assign_switch_codes_skip_no_lights(self):
        segments = [
            {
                'base_id': 100,
                'light_ids': [],
                'device_ids': [10],
            }
        ]
        result = knk_switch.assign_switch_codes(segments)
        self.assertEqual(result['light_codes'], {})
        self.assertEqual(result['switch_codes'], {})


if __name__ == '__main__':
    unittest.main()
