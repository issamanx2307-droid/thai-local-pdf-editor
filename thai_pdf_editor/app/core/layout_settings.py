# -*- coding: utf-8 -*-
"""Local layout settings for the desktop UI."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from thai_pdf_editor.app.config import LAYOUT_SETTINGS_PATH
from thai_pdf_editor.app.ui.theme import PAGE_PANEL_DEFAULT_WIDTH, TOOL_PANEL_DEFAULT_WIDTH, clamp_page_panel_width, clamp_tool_panel_width


@dataclass(frozen=True)
class LayoutSettings:
    """User-facing layout preferences persisted locally."""

    tool_panel_width: int = TOOL_PANEL_DEFAULT_WIDTH
    page_panel_width: int = PAGE_PANEL_DEFAULT_WIDTH


def load_layout_settings(path: Path = LAYOUT_SETTINGS_PATH) -> LayoutSettings:
    """Load saved layout settings from UTF-8 JSON."""
    if not path.exists():
        return LayoutSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return LayoutSettings()
    if not isinstance(data, dict):
        return LayoutSettings()
    return LayoutSettings(
        tool_panel_width=_read_width(data.get("tool_panel_width"), TOOL_PANEL_DEFAULT_WIDTH, clamp_tool_panel_width),
        page_panel_width=_read_width(data.get("page_panel_width"), PAGE_PANEL_DEFAULT_WIDTH, clamp_page_panel_width),
    )


def save_layout_settings(settings: LayoutSettings, path: Path = LAYOUT_SETTINGS_PATH) -> None:
    """Persist layout settings as local UTF-8 JSON."""
    clean_settings = LayoutSettings(
        tool_panel_width=clamp_tool_panel_width(settings.tool_panel_width),
        page_panel_width=clamp_page_panel_width(settings.page_panel_width),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(clean_settings), ensure_ascii=False, indent=2), encoding="utf-8")


def _read_width(value: object, fallback: int, clamp: Callable[[int], int]) -> int:
    try:
        return clamp(int(value))
    except (TypeError, ValueError):
        return fallback
