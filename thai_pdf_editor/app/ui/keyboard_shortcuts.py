# -*- coding: utf-8 -*-
"""Keyboard shortcut helpers for the desktop UI."""

from __future__ import annotations

from typing import Any

NAVIGATION_SHORTCUTS = {
    "previous_page": "<Prior>",
    "next_page": "<Next>",
    "first_page": "<Home>",
    "last_page": "<End>",
}

TEXT_INPUT_CLASS_MARKERS = ("entry", "text")


def is_text_input_class(class_name: str) -> bool:
    """Return whether a Tk widget class should keep normal text-editing keys."""
    normalized = class_name.strip().lower()
    return any(marker in normalized for marker in TEXT_INPUT_CLASS_MARKERS)


def is_text_input_widget(widget: Any) -> bool:
    """Return whether a Tk widget looks like a text input."""
    if widget is None or not hasattr(widget, "winfo_class"):
        return False
    try:
        class_name = str(widget.winfo_class())
    except Exception:
        return False
    return is_text_input_class(class_name)


def is_text_input_event(event: object) -> bool:
    """Return whether a Tk event originated from a text input widget."""
    return is_text_input_widget(getattr(event, "widget", None))
