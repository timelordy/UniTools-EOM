# -*- coding: utf-8 -*-

import unittest

from unibim.panel_info_utils import build_param_names, count_module_stats


class TestPanelInfoUtils(unittest.TestCase):
    def test_build_param_names_defaults(self):
        data = build_param_names([])
        self.assertEqual(data["Units"], u"ADSK_Единица измерения")
        self.assertEqual(data["Manufacturer"], u"ADSK_Завод-изготовитель")
        self.assertEqual(data["Name"], u"ADSK_Наименование")
        self.assertEqual(data["TypeMark"], u"ADSK_Марка")

    def test_build_param_names_overrides(self):
        settings = [
            "Param_name_0_for_Param_Names_Storage", "U",
            "Param_name_1_for_Param_Names_Storage", "M",
            "Param_name_3_for_Param_Names_Storage", "T",
        ]
        data = build_param_names(settings)
        self.assertEqual(data["Units"], "U")
        self.assertEqual(data["Manufacturer"], "M")
        self.assertEqual(data["TypeMark"], "T")

    def test_count_module_stats(self):
        stats = count_module_stats(list(range(13)))
        self.assertEqual(stats["count_device"], 13)
        self.assertEqual(stats["count0p"], 1)
        self.assertEqual(stats["count1p"], 1)
        self.assertEqual(stats["count12p"], 1)
        self.assertEqual(stats["all_modules"], 78)

    def test_count_module_stats_default_to_three(self):
        stats = count_module_stats([99])
        self.assertEqual(stats["count3p"], 1)
        self.assertEqual(stats["all_modules"], 3)


if __name__ == "__main__":
    unittest.main()
