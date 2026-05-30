# -*- coding: utf-8 -*-
"""Tests for unsaved-change confirmation guard."""

from thai_pdf_editor.app.ui.dirty_guard import UNSAVED_CHANGES_MESSAGE, can_discard_unsaved_changes


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
