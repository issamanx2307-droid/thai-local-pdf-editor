# -*- coding: utf-8 -*-
"""Tests for page navigation keyboard shortcut helpers."""

from thai_pdf_editor.app.ui.keyboard_shortcuts import (
    NAVIGATION_SHORTCUTS,
    is_text_input_class,
    is_text_input_widget,
)


class FakeWidget:
    """Small stand-in for Tk widgets used by shortcut guards."""

    def __init__(self, class_name: str) -> None:
        self._class_name = class_name

    def winfo_class(self) -> str:
        return self._class_name


def test_navigation_shortcuts_cover_common_page_keys() -> None:
    """Page shortcuts should use Tk keysyms for PageUp/PageDown/Home/End."""
    assert NAVIGATION_SHORTCUTS == {
        "previous_page": "<Prior>",
        "next_page": "<Next>",
        "first_page": "<Home>",
        "last_page": "<End>",
    }


def test_text_input_classes_keep_normal_key_behavior() -> None:
    """Entry and Text-like widgets should not be hijacked by navigation keys."""
    assert is_text_input_class("Entry")
    assert is_text_input_class("TEntry")
    assert is_text_input_class("CTkEntry")
    assert is_text_input_class("Text")
    assert is_text_input_class("CTkTextbox")
    assert not is_text_input_class("Canvas")
    assert not is_text_input_class("Listbox")
    assert not is_text_input_class("Button")


def test_text_input_widget_guard_handles_missing_or_broken_widgets() -> None:
    """Shortcut guards should be defensive around non-Tk objects."""
    assert is_text_input_widget(FakeWidget("Entry"))
    assert not is_text_input_widget(FakeWidget("Canvas"))
    assert not is_text_input_widget(None)
