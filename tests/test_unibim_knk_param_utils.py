# -*- coding: utf-8 -*-

import unittest

from unibim.knk_param_utils import get_knk_param_names


class TestKnkParamUtils(unittest.TestCase):
    def test_defaults(self):
        data = get_knk_param_names([])
        self.assertEqual(data["KnkCircuitNumber"], u"TSL_КНК_Номер цепи")
        self.assertEqual(data["KnkCableTrayOccupancy"], u"TSL_КНК_Заполняемость лотка (%)")

    def test_overrides(self):
        settings = [
            "Param_name_24_for_Param_Names_Storage", "C1",
            "Param_name_26_for_Param_Names_Storage", "O1",
            "Param_name_47_for_Param_Names_Storage", "EM1",
        ]
        data = get_knk_param_names(settings)
        self.assertEqual(data["KnkCircuitNumber"], "C1")
        self.assertEqual(data["KnkCableTrayOccupancy"], "O1")
        self.assertEqual(data["KnkCircuitNumberEM"], "EM1")


if __name__ == "__main__":
    unittest.main()
