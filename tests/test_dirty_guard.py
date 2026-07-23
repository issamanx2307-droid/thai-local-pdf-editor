# -*- coding: utf-8 -*-
"""Tests for unsaved-change confirmation guard."""

from thai_pdf_editor.app.ui.dirty_guard import (
    UNSAVED_CHANGES_MESSAGE,
    can_discard_unsaved_changes,
    resolve_close_action,
)


def test_clean_document_does_not_ask_for_confirmation() -> None:
    """Clean state can continue without opening a dialog."""
    called = False

    def confirm_callback(_message: str) -> bool:
        nonlocal called
        called = True
        return False

    assert can_discard_unsaved_changes(False, confirm_callback) is True
    assert called is False


def test_dirty_document_can_continue_when_user_confirms() -> None:
    """Dirty state continues only when the user accepts the warning."""
    messages: list[str] = []

    def confirm_callback(message: str) -> bool:
        messages.append(message)
        return True

    assert can_discard_unsaved_changes(True, confirm_callback) is True
    assert messages == [UNSAVED_CHANGES_MESSAGE]


def test_dirty_document_blocks_when_user_cancels() -> None:
    """Dirty state blocks destructive navigation when the user cancels."""
    assert can_discard_unsaved_changes(True, lambda _message: False) is False


def test_close_action_clean_document_closes_without_prompting() -> None:
    """A clean document closes immediately without opening the save dialog."""
    called = False

    def confirm_callback() -> str:
        nonlocal called
        called = True
        return "cancel"

    assert resolve_close_action(False, confirm_callback) == "close"
    assert called is False


def test_close_action_dirty_document_save_choice() -> None:
    """Choosing 'save' triggers the save-then-close flow."""
    assert resolve_close_action(True, lambda: "save") == "save_then_close"


def test_close_action_dirty_document_discard_choice() -> None:
    """Choosing 'discard' closes without saving."""
    assert resolve_close_action(True, lambda: "discard") == "close"


def test_close_action_dirty_document_cancel_choice() -> None:
    """Choosing 'cancel' keeps the window open."""
    assert resolve_close_action(True, lambda: "cancel") == "stay"
