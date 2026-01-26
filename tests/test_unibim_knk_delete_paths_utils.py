import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim.knk_delete_paths_utils import PATH_NAME_TOKEN, is_knk_path_name  # noqa: E402


class TestKnkDeletePathsUtils(unittest.TestCase):
    def test_is_knk_path_name_true_when_token_present(self):
        name = "prefix " + PATH_NAME_TOKEN + " suffix"
        self.assertTrue(is_knk_path_name(name))

    def test_is_knk_path_name_false_when_missing(self):
        self.assertFalse(is_knk_path_name("Other name"))

    def test_is_knk_path_name_false_for_empty(self):
        self.assertFalse(is_knk_path_name(""))
        self.assertFalse(is_knk_path_name(None))


if __name__ == '__main__':
    unittest.main()
