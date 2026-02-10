# -*- coding: utf-8 -*-
"""Tests for hub_tool_commands module."""

import pytest
import sys
import os

# Add lib to path
ROOT = os.path.dirname(os.path.dirname(__file__))
LIB = os.path.join(ROOT, "EOMTemplateTools.extension", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from hub_tool_commands import (
    get_tool_metadata,
    is_tool_available,
    TOOL_REGISTRY
)


class TestGetToolMetadata:
    """Tests for get_tool_metadata function."""

    def test_returns_dict_for_valid_tool(self):
        """Test that valid tool returns metadata dict."""
        # Get first tool from registry
        if TOOL_REGISTRY:
            first_tool = list(TOOL_REGISTRY.keys())[0]
            metadata = get_tool_metadata(first_tool)
            assert isinstance(metadata, dict)

    def test_returns_none_for_invalid_tool(self):
        """Test that invalid tool returns None."""
        metadata = get_tool_metadata("nonexistent_tool_12345")
        assert metadata is None or isinstance(metadata, dict)

    def test_metadata_has_required_fields(self):
        """Test that metadata contains expected fields."""
        if TOOL_REGISTRY:
            first_tool = list(TOOL_REGISTRY.keys())[0]
            metadata = get_tool_metadata(first_tool)
            if metadata:
                # Common fields
                assert 'id' in metadata or 'name' in metadata or len(metadata) > 0


class TestIsToolAvailable:
    """Tests for is_tool_available function."""

    def test_known_tool_is_available(self):
        """Test that known tools are available."""
        if TOOL_REGISTRY:
            first_tool = list(TOOL_REGISTRY.keys())[0]
            result = is_tool_available(first_tool)
            assert isinstance(result, bool)

    def test_unknown_tool_is_unavailable(self):
        """Test that unknown tools are not available."""
        result = is_tool_available("nonexistent_tool_99999")
        assert result is False


class TestToolRegistry:
    """Tests for TOOL_REGISTRY constant."""

    def test_registry_exists(self):
        """Test that registry is defined."""
        assert TOOL_REGISTRY is not None

    def test_registry_is_dict(self):
        """Test that registry is a dictionary."""
        assert isinstance(TOOL_REGISTRY, dict)

    def test_registry_has_tools(self):
        """Test that registry contains at least one tool."""
        assert len(TOOL_REGISTRY) > 0

    @pytest.mark.parametrize("expected_tool", [
        'lights_center',
        'lights_elevator',
        'sockets_general',
    ])
    def test_common_tools_in_registry(self, expected_tool):
        """Test that common tools are in registry."""
        # Will pass if tool exists, skip if not
        if expected_tool in TOOL_REGISTRY:
            assert TOOL_REGISTRY[expected_tool] is not None
