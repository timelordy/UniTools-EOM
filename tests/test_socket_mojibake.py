# -*- coding: utf-8 -*-

import os
import io
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOCKET_DIRS = [
    os.path.join(ROOT, 'EOMTemplateTools.extension', 'EOM.tab', '04_Розетки.panel'),
    os.path.join(ROOT, 'EOMTemplateTools.extension', 'Разработка.tab', '04_Розетки.panel'),
]

# Characters that commonly appear when UTF-8 Russian text is mis-decoded
# as CP1251 and then saved as UTF-8.
MOJIBAKE_CHARS = u"ЃЌЊЉЍЎЏЂђѓќњљћџўєіїґ"


def _iter_socket_files():
    for base in SOCKET_DIRS:
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for name in files:
                if not name.lower().endswith('.py'):
                    continue
                yield os.path.join(root, name)


def _has_mojibake(text):
    return any(ch in text for ch in MOJIBAKE_CHARS)


class TestSocketMojibake(unittest.TestCase):
    def test_no_mojibake_in_socket_plugins(self):
        offenders = []
        for path in _iter_socket_files():
            try:
                with io.open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
            except Exception:
                continue
            if _has_mojibake(data):
                offenders.append(os.path.relpath(path, ROOT))
        if offenders:
            self.fail("Mojibake detected in socket plugins:\n- " + "\n- ".join(offenders))


if __name__ == '__main__':
    unittest.main()
