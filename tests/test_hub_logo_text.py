# -*- coding: utf-8 -*-
"""Static checks for Hub header logo text and order."""

from pathlib import Path


def _read_app():
    root = Path(__file__).resolve().parents[1]
    app_path = root / "EOMHub" / "frontend" / "src" / "App.tsx"
    return app_path.read_text(encoding="utf-8")


def test_logo_text_is_unitools():
    content = _read_app()
    assert "UniTools" in content


def test_logo_text_before_icon():
    content = _read_app()
    text_idx = content.find('className="logo-text"')
    icon_idx = content.find('className="logo-icon"')
    assert text_idx != -1 and icon_idx != -1
    assert text_idx < icon_idx
