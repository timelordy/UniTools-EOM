# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


from unibim import knk_core  # noqa: E402


class TestKnkCore(unittest.TestCase):
    def test_shortest_path_prefers_shorter(self):
        # Graph: A-B-C (1+1) vs A-D-C (5+5)
        edges = [
            ((0, 0, 0), (1, 0, 0), "e1"),
            ((1, 0, 0), (2, 0, 0), "e2"),
            ((0, 0, 0), (0, 5, 0), "e3"),
            ((0, 5, 0), (2, 0, 0), "e4"),
        ]
        graph = knk_core.build_graph(edges)
        length, used = knk_core.shortest_path(graph, (0, 0, 0), (2, 0, 0))
        self.assertAlmostEqual(length, 2.0, places=6)
        self.assertEqual(set(used), {"e1", "e2"})

    def test_snap_to_nearest_node(self):
        edges = [
            ((0, 0, 0), (10, 0, 0), "e1"),
        ]
        graph = knk_core.build_graph(edges)
        length, used = knk_core.shortest_path(graph, (0.1, 0.0, 0.0), (9.9, 0.0, 0.0))
        self.assertAlmostEqual(length, 10.0, places=6)
        self.assertEqual(set(used), {"e1"})


if __name__ == '__main__':
    unittest.main()
