# -*- coding: utf-8 -*-
"""Tests for local UI layout settings."""

from pathlib import Path

from thai_pdf_editor.app.core.layout_settings import LayoutSettings, load_layout_settings, save_layout_settings
from thai_pdf_editor.app.ui.theme import (
    PAGE_PANEL_DEFAULT_WIDTH,
    PAGE_PANEL_MAX_WIDTH,
    PAGE_PANEL_MIN_WIDTH,
    TOOL_PANEL_DEFAULT_WIDTH,
    TOOL_PANEL_MAX_WIDTH,
    TOOL_PANEL_MIN_WIDTH,
)


def test_layout_settings_round_trip_tool_panel_width(tmp_path: Path) -> None:
    """Tool panel width should persist as UTF-8 JSON."""
    settings_path = tmp_path / "layout.json"

    save_layout_settings(LayoutSettings(tool_panel_width=410, page_panel_width=300), settings_path)

    loaded = load_layout_settings(settings_path)
    assert loaded.tool_panel_width == 410
    assert loaded.page_panel_width == 300
    assert "tool_panel_width" in settings_path.read_text(encoding="utf-8")
    assert "page_panel_width" in settings_path.read_text(encoding="utf-8")


def test_layout_settings_clamps_invalid_or_out_of_range_width(tmp_path: Path) -> None:
    """Bad local layout JSON falls back to usable widths."""
    settings_path = tmp_path / "layout.json"

    save_layout_settings(LayoutSettings(tool_panel_width=9999), settings_path)
    assert load_layout_settings(settings_path).tool_panel_width == TOOL_PANEL_MAX_WIDTH

    settings_path.write_text('{"tool_panel_width": 1, "page_panel_width": 1}', encoding="utf-8")
    loaded = load_layout_settings(settings_path)
    assert loaded.tool_panel_width == TOOL_PANEL_MIN_WIDTH
    assert loaded.page_panel_width == PAGE_PANEL_MIN_WIDTH

    settings_path.write_text('{"tool_panel_width": "bad", "page_panel_width": "bad"}', encoding="utf-8")
    loaded = load_layout_settings(settings_path)
    assert loaded.tool_panel_width == TOOL_PANEL_DEFAULT_WIDTH
    assert loaded.page_panel_width == PAGE_PANEL_DEFAULT_WIDTH


def test_layout_settings_clamps_page_panel_width(tmp_path: Path) -> None:
    """The left page panel should also stay in a useful range."""
    settings_path = tmp_path / "layout.json"

    save_layout_settings(LayoutSettings(page_panel_width=9999), settings_path)

    assert load_layout_settings(settings_path).page_panel_width == PAGE_PANEL_MAX_WIDTH
