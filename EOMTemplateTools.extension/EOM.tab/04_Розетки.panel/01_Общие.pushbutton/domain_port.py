# -*- coding: utf-8 -*-
"""Domain port for socket-related helper operations.

Keeps domain logic decoupled from direct ``socket_utils`` dependency.
"""

try:
    import socket_utils as _socket_utils
except ImportError:
    import os
    import sys

    lib_path = os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        ),
        'lib'
    )
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    import socket_utils as _socket_utils


class SocketDomainPort(object):
    """Small domain-facing contract over low-level socket helpers."""

    def __init__(self, impl_module=None):
        impl = impl_module or _socket_utils

        # Bind low-level operations as overrideable attributes.
        self._compile_patterns = impl._compile_patterns
        self._match_any = impl._match_any
        self._room_text = impl._room_text
        self._room_is_wc = impl._room_is_wc
        self._get_room_outer_boundary_segments = impl._get_room_outer_boundary_segments
        self._is_wall_element = impl._is_wall_element
        self._is_room_outer_boundary_segment = impl._is_room_outer_boundary_segment
        self._is_curtain_wall = impl._is_curtain_wall
        self._is_facade_wall = impl._is_facade_wall
        self._is_structural_wall = impl._is_structural_wall
        self._is_monolith_wall = impl._is_monolith_wall
        self._get_wall_openings_cached = impl._get_wall_openings_cached
        self._project_dist_on_curve_xy_ft = impl._project_dist_on_curve_xy_ft
        self._merge_intervals = impl._merge_intervals
        self._invert_intervals = impl._invert_intervals
        self._dist_xy = impl._dist_xy

    def compile_patterns(self, patterns):
        return self._compile_patterns(patterns)

    def match_any(self, regex_list, text):
        return self._match_any(regex_list, text)

    def room_text(self, room):
        return self._room_text(room)

    def room_is_wc(self, room, rules):
        return self._room_is_wc(room, rules)

    def get_room_outer_boundary_segments(self, room, boundary_opts):
        return self._get_room_outer_boundary_segments(room, boundary_opts)

    def is_wall_element(self, elem):
        return self._is_wall_element(elem)

    def is_room_outer_boundary_segment(self, link_doc, room, curve, probe_mm=200.0):
        return self._is_room_outer_boundary_segment(link_doc, room, curve, probe_mm=probe_mm)

    def is_curtain_wall(self, wall):
        return self._is_curtain_wall(wall)

    def is_facade_wall(self, wall, patterns_rx=None):
        return self._is_facade_wall(wall, patterns_rx=patterns_rx)

    def is_structural_wall(self, wall):
        return self._is_structural_wall(wall)

    def is_monolith_wall(self, wall, patterns_rx=None):
        return self._is_monolith_wall(wall, patterns_rx=patterns_rx)

    def get_wall_openings_cached(self, link_doc, wall, cache):
        return self._get_wall_openings_cached(link_doc, wall, cache)

    def project_dist_on_curve_xy_ft(self, curve, seg_len_ft, point_xyz, tol_ft, end_extension_ft=None):
        return self._project_dist_on_curve_xy_ft(
            curve,
            seg_len_ft,
            point_xyz,
            tol_ft,
            end_extension_ft=end_extension_ft,
        )

    def merge_intervals(self, intervals, lo, hi):
        return self._merge_intervals(intervals, lo, hi)

    def invert_intervals(self, blocked, lo, hi):
        return self._invert_intervals(blocked, lo, hi)

    def dist_xy(self, p1, p2):
        return self._dist_xy(p1, p2)


DEFAULT_SOCKET_DOMAIN_PORT = SocketDomainPort()
