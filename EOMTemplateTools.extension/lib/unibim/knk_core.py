# -*- coding: utf-8 -*-

import math


def _dist(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )


def _node_key(pt, precision=6):
    return (round(pt[0], precision), round(pt[1], precision), round(pt[2], precision))


def build_graph(edges):
    """
    Build adjacency list graph.
    edges: list of (p1, p2, element_id)
    Returns dict node -> list of (neighbor, length, element_id)
    """
    graph = {}
    for p1, p2, eid in edges:
        n1 = _node_key(p1)
        n2 = _node_key(p2)
        length = _dist(n1, n2)
        graph.setdefault(n1, []).append((n2, length, eid))
        graph.setdefault(n2, []).append((n1, length, eid))
    return graph


def _nearest_node(graph, point):
    if not graph:
        return None
    target = _node_key(point)
    best = None
    best_d = None
    for node in graph.keys():
        d = _dist(node, target)
        if best_d is None or d < best_d:
            best = node
            best_d = d
    return best


def shortest_path(graph, start, end):
    """
    Dijkstra shortest path.
    Returns (length, used_element_ids)
    """
    if not graph:
        return 0.0, []
    s = _nearest_node(graph, start)
    t = _nearest_node(graph, end)
    if s is None or t is None:
        return 0.0, []

    dist = {s: 0.0}
    prev = {}
    visited = set()
    queue = [(0.0, s)]

    while queue:
        queue.sort(key=lambda x: x[0])
        d, node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node == t:
            break
        for neigh, w, eid in graph.get(node, []):
            if neigh in visited:
                continue
            nd = d + w
            if neigh not in dist or nd < dist[neigh]:
                dist[neigh] = nd
                prev[neigh] = (node, eid)
                queue.append((nd, neigh))

    if t not in dist:
        return 0.0, []

    # reconstruct
    used = []
    cur = t
    while cur != s and cur in prev:
        cur, eid = prev[cur]
        used.append(eid)
    used.reverse()
    return dist[t], used
