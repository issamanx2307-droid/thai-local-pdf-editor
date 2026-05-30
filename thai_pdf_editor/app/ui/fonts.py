# -*- coding: utf-8 -*-
"""Readable font settings for Thai desktop controls."""

from __future__ import annotations

import tkinter.font as tkfont

from thai_pdf_editor.app.utils.font_utils import preferred_ui_font

UI_FONT_FAMILY = preferred_ui_font()

TITLE_FONT      = (UI_FONT_FAMILY, 15, "bold")
LABEL_FONT      = (UI_FONT_FAMILY, 14)
STATUS_FONT     = (UI_FONT_FAMILY, 12)
BUTTON_FONT     = (UI_FONT_FAMILY, 14, "bold")
ENTRY_FONT      = (UI_FONT_FAMILY, 14)
MENU_FONT       = (UI_FONT_FAMILY, 13)
CANVAS_MESSAGE_FONT = (UI_FONT_FAMILY, 17, "bold")
LISTBOX_FONT    = (UI_FONT_FAMILY, 12)
TOOLBAR_GROUP_FONT  = (UI_FONT_FAMILY, 11, "bold")
CANVAS_TITLE_FONT   = (UI_FONT_FAMILY, 20, "bold")
CANVAS_HINT_FONT    = (UI_FONT_FAMILY, 14)

BUTTON_HEIGHT   = 38
ENTRY_HEIGHT    = 36
# Keep the ribbon frame content-driven; fixed height becomes oversized on high-DPI Windows.
TOOLBAR_HEIGHT  = 1
TOOL_PANEL_WIDTH  = 330
PAGE_PANEL_WIDTH  = 255
PAGE_LIST_MIN_HEIGHT = 220

BUTTON_HORIZONTAL_PADDING = 40
BUTTON_ESTIMATED_CHAR_WIDTH = 9
MIN_BUTTON_WIDTH = 96


def readable_button_width(label: str, *, minimum: int = MIN_BUTTON_WIDTH) -> int:
    """Return a conservative button width for Thai text labels."""
    return max(minimum, BUTTON_HORIZONTAL_PADDING + len(label) * BUTTON_ESTIMATED_CHAR_WIDTH)


def configure_tk_default_fonts() -> None:
    """Apply Thai-capable defaults to built-in Tk widgets."""
    font_settings = {
        "TkDefaultFont": (12, "normal"),
        "TkTextFont":    (12, "normal"),
        "TkMenuFont":    (12, "normal"),
        "TkHeadingFont": (13, "bold"),
        "TkTooltipFont": (11, "normal"),
    }
    for font_name, (size, weight) in font_settings.items():
        try:
            tkfont.nametofont(font_name).configure(family=UI_FONT_FAMILY, size=size, weight=weight)
        except tkfont.TclError:
            continue
