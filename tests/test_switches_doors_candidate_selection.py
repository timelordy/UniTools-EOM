# -*- coding: utf-8 -*-
"""Regression tests for switch candidate selection in ВыключателиУДверей."""

import os
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))
DOMAIN_DIR = os.path.join(
    ROOT,
    "EOMTemplateTools.extension",
    "EOM.tab",
    "03_ЩитыВыключатели.panel",
    "ВыключателиУДверей.pushbutton",
)
if DOMAIN_DIR not in sys.path:
    sys.path.insert(0, DOMAIN_DIR)


import adapters_switches  # noqa: E402  pylint: disable=wrong-import-position
import domain  # noqa: E402  pylint: disable=wrong-import-position


def test_prefer_farther_candidate_prefers_meaningfully_farther_point():
    current = domain.mm_to_ft(550)
    new = domain.mm_to_ft(720)

    assert adapters_switches.prefer_farther_candidate(current, new) is True


def test_prefer_farther_candidate_ignores_near_equal_distance_within_tolerance():
    current = domain.mm_to_ft(700)
    # +10mm is below default 20mm tolerance
    new = domain.mm_to_ft(710)

    assert adapters_switches.prefer_farther_candidate(current, new) is False


def test_prefer_farther_candidate_accepts_first_candidate_when_current_missing():
    new = domain.mm_to_ft(650)

    assert adapters_switches.prefer_farther_candidate(None, new) is True
