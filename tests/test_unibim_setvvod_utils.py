# -*- coding: utf-8 -*-

import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim import setvvod_utils  # noqa: E402


class TestSetVvodUtils(unittest.TestCase):
    def test_format_cable_basic(self):
        res = setvvod_utils.format_cable(
            mark='ВВГ',
            kolvo_zhil=3,
            kolvo_luchey=0,
            kolvo_provodnikov=0,
            kolvo_provodnikov_pe=0,
            sechenie=2.5,
            sechenie_pe=0.0,
            dlina=10,
        )
        self.assertEqual(res, 'ВВГ 3х2.5; L=10')

    def test_format_cable_rays(self):
        res = setvvod_utils.format_cable(
            mark='ВВГ',
            kolvo_zhil=3,
            kolvo_luchey=2,
            kolvo_provodnikov=0,
            kolvo_provodnikov_pe=0,
            sechenie=2.5,
            sechenie_pe=0.0,
            dlina=10,
        )
        self.assertEqual(res, 'ВВГ 2х(3х2.5); L=10')

    def test_format_cable_with_pe(self):
        res = setvvod_utils.format_cable(
            mark='ВВГнг',
            kolvo_zhil=3,
            kolvo_luchey=0,
            kolvo_provodnikov=2,
            kolvo_provodnikov_pe=1,
            sechenie=2.5,
            sechenie_pe=1.5,
            dlina=10,
        )
        self.assertEqual(res, 'ВВГнг 2(3х2.5)+1х1.5; L=10')

    def test_format_cable_multi_rays_with_pe(self):
        res = setvvod_utils.format_cable(
            mark='ВВГнг',
            kolvo_zhil=3,
            kolvo_luchey=2,
            kolvo_provodnikov=2,
            kolvo_provodnikov_pe=1,
            sechenie=2.5,
            sechenie_pe=1.5,
            dlina=10,
        )
        self.assertEqual(res, 'ВВГнг 2х2(3х2.5)+1х1.5; L=10')


if __name__ == '__main__':
    unittest.main()
