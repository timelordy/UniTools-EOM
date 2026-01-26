# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.cable_param_utils import get_cable_param_names  # noqa: E402


class TestCableParamUtils(unittest.TestCase):
    def test_defaults_when_empty(self):
        names = get_cable_param_names([])
        self.assertIn("CableLength", names)
        self.assertIn("CableLengthAdjusted", names)
        self.assertIn("CableLengthToRemoteDevice", names)
        self.assertIn("CableLayingMethod", names)

    def test_mapping_from_storage_list(self):
        settings = [
            "Param_name_20_for_Param_Names_Storage",
            "LEN_A",
            "Param_name_41_for_Param_Names_Storage",
            "LEN_REMOTE",
            "Param_name_42_for_Param_Names_Storage",
            "LEN_ADJ",
            "Param_name_30_for_Param_Names_Storage",
            "LAYING",
        ]
        names = get_cable_param_names(settings)
        self.assertEqual(names["CableLength"], "LEN_A")
        self.assertEqual(names["CableLengthToRemoteDevice"], "LEN_REMOTE")
        self.assertEqual(names["CableLengthAdjusted"], "LEN_ADJ")
        self.assertEqual(names["CableLayingMethod"], "LAYING")


if __name__ == '__main__':
    unittest.main()
