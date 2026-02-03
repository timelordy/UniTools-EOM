# -*- coding: utf-8 -*-

import os
import io
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOCKET_DIRS = [
    os.path.join(ROOT, 'EOMTemplateTools.extension', 'EOM.tab', '04_Розетки.panel'),
    os.path.join(ROOT, 'EOMTemplateTools.extension', 'Разработка.tab', '04_Розетки.panel'),
]


def _iter_socket_files():
    for base in SOCKET_DIRS:
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for name in files:
                if not name.lower().endswith('.py'):
                    continue
                yield os.path.join(root, name)


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


class TestSocketMojibake(unittest.TestCase):
    def test_socket_plugins_are_valid_utf8(self):
        offenders = []
        for path in _iter_socket_files():
            reason = _check_utf8(path)
            if reason:
                offenders.append("{0} ({1})".format(os.path.relpath(path, ROOT), reason))
        if offenders:
            self.fail("Socket plugin scripts must be UTF-8 without NUL/invalid chars:\n- " + "\n- ".join(offenders))


if __name__ == '__main__':
    unittest.main()
