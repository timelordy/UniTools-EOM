# -*- coding: utf-8 -*-
"""Tests for utils_units module."""

import pytest
from utils_units import mm_to_ft, ft_to_mm, MM_PER_FOOT


class TestMmToFt:
    """Tests for mm_to_ft conversion function."""

    def test_standard_conversion(self):
        """Test standard mm to feet conversion."""
        result = mm_to_ft(304.8)
        assert result == pytest.approx(1.0, rel=1e-9)

    def test_zero(self):
        """Test conversion of zero."""
        assert mm_to_ft(0) == 0.0

    def test_negative(self):
        """Test conversion of negative values."""
        result = mm_to_ft(-304.8)
        assert result == pytest.approx(-1.0, rel=1e-9)

    def test_none_input(self):
        """Test that None input returns None."""
        assert mm_to_ft(None) is None

    def test_string_input(self):
        """Test that string numbers are converted."""
        result = mm_to_ft("304.8")
        assert result == pytest.approx(1.0, rel=1e-9)


class TestFtToMm:
    """Tests for ft_to_mm conversion function."""

    def test_standard_conversion(self):
        """Test standard feet to mm conversion."""
        result = ft_to_mm(1.0)
        assert result == pytest.approx(304.8, rel=1e-9)

    def test_zero(self):
        """Test conversion of zero."""
        assert ft_to_mm(0) == 0.0

    def test_none_input(self):
        """Test that None input returns None."""
        assert ft_to_mm(None) is None


class TestRoundTrip:
    """Tests for round-trip conversions."""

    def test_mm_to_ft_to_mm(self):
        """Test that converting mm -> ft -> mm returns original value."""
        original = 1234.5
        converted = ft_to_mm(mm_to_ft(original))
        assert converted == pytest.approx(original, rel=1e-9)

    def test_ft_to_mm_to_ft(self):
        """Test that converting ft -> mm -> ft returns original value."""
        original = 12.345
        converted = mm_to_ft(ft_to_mm(original))
        assert converted == pytest.approx(original, rel=1e-9)
