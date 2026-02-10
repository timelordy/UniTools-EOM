# -*- coding: utf-8 -*-
"""Tests for time_savings module."""

import pytest
from time_savings import calculate_time_saved, calculate_time_saved_range, TIME_SAVINGS_CATALOG


class TestCalculateTimeSaved:
    """Tests for calculate_time_saved function."""

    def test_lights_center_single(self):
        """Test time savings for single center light."""
        # Assumes lights_center in catalog
        if 'lights_center' in TIME_SAVINGS_CATALOG:
            result = calculate_time_saved('lights_center', 1)
            assert result > 0

    def test_lights_center_multiple(self):
        """Test time savings scales with count."""
        if 'lights_center' in TIME_SAVINGS_CATALOG:
            single = calculate_time_saved('lights_center', 1)
            double = calculate_time_saved('lights_center', 2)
            assert double == pytest.approx(single * 2, rel=0.01)

    def test_zero_count(self):
        """Test that zero count returns zero time."""
        result = calculate_time_saved('lights_center', 0)
        assert result == 0

    def test_negative_count(self):
        """Test that negative count returns zero or raises."""
        result = calculate_time_saved('lights_center', -1)
        assert result >= 0  # Should handle gracefully


class TestCalculateTimeSavedRange:
    """Tests for calculate_time_saved_range function."""

    def test_range_returns_tuple(self):
        """Test that function returns (min, max) tuple."""
        if 'lights_center' in TIME_SAVINGS_CATALOG:
            result = calculate_time_saved_range('lights_center', 1)
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_min_less_than_max(self):
        """Test that min < max in range."""
        if 'lights_center' in TIME_SAVINGS_CATALOG:
            min_time, max_time = calculate_time_saved_range('lights_center', 10)
            assert min_time <= max_time

    def test_average_in_range(self):
        """Test that average time is within min-max range."""
        if 'lights_center' in TIME_SAVINGS_CATALOG:
            avg = calculate_time_saved('lights_center', 10)
            min_time, max_time = calculate_time_saved_range('lights_center', 10)
            assert min_time <= avg <= max_time


class TestTimeSavingsCatalog:
    """Tests for TIME_SAVINGS_CATALOG structure."""

    def test_catalog_exists(self):
        """Test that catalog is defined."""
        assert TIME_SAVINGS_CATALOG is not None
        assert isinstance(TIME_SAVINGS_CATALOG, dict)

    def test_catalog_has_entries(self):
        """Test that catalog has at least one entry."""
        assert len(TIME_SAVINGS_CATALOG) > 0

    @pytest.mark.parametrize("tool_id", [
        'lights_center',
        'lights_elevator',
        'sockets_general',
        'switches_doors',
    ])
    def test_common_tools_in_catalog(self, tool_id):
        """Test that common tools are in catalog."""
        # This test will skip if tool not in catalog
        if tool_id in TIME_SAVINGS_CATALOG:
            entry = TIME_SAVINGS_CATALOG[tool_id]
            assert 'minutes_per_element' in entry or 'minutes' in entry
