# -*- coding: utf-8 -*-
"""Unsaved-change guard helpers for UI workflows."""

from collections.abc import Callable

UNSAVED_CHANGES_MESSAGE = "ไฟล์มีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก ต้องการทิ้งการเปลี่ยนแปลงและทำต่อหรือไม่"


def can_discard_unsaved_changes(is_dirty: bool, confirm_callback: Callable[[str], bool]) -> bool:
    """Return True when it is safe to continue past unsaved changes."""
    if not is_dirty:
        return True
    return confirm_callback(UNSAVED_CHANGES_MESSAGE)


def resolve_close_action(is_dirty: bool, confirm_callback: Callable[[], str]) -> str:
    """Decide what should happen when the user tries to close the app.

    ``confirm_callback`` should return "save", "discard", or "cancel"
    (matching ``dialogs.confirm_save_before_close``). Returns one of:
      - "close": no unsaved changes, close immediately.
      - "save_then_close": run the save flow, then close only if it succeeded.
      - "stay": keep the window open (user cancelled or chose to keep editing).
    """
    if not is_dirty:
        return "close"
    choice = confirm_callback()
    if choice == "discard":
        return "close"
    if choice == "save":
        return "save_then_close"
    return "stay"
