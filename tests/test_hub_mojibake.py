# -*- coding: utf-8 -*-

import os
import io
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HUB_SCRIPT = os.path.join(
    ROOT,
    'EOMTemplateTools.extension',
    'EOM.tab',
    '01_Хаб.panel',
    'Hub.pushbutton',
    'script.py',
)


def _check_utf8(path):
    try:
        with io.open(path, 'rb') as f:
            data = f.read()
    except Exception:
        return "read_failed"
    if b'\x00' in data:
        return "contains_nul_bytes"
    try:
        text = data.decode('utf-8', 'replace')
    except Exception:
        return "decode_failed"
    if u'\ufffd' in text:
        return "invalid_utf8"
    return None


class TestHubMojibake(unittest.TestCase):
    def test_hub_script_is_valid_utf8(self):
        if not os.path.isfile(HUB_SCRIPT):
            self.skipTest("Hub script not found")
        reason = _check_utf8(HUB_SCRIPT)
        if reason:
            self.fail("Hub script must be UTF-8 without NUL/invalid chars: {0}".format(reason))


if __name__ == '__main__':
    unittest.main()
