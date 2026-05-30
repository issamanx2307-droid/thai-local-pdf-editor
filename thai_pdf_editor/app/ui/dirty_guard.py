# -*- coding: utf-8 -*-
"""Unsaved-change guard helpers for UI workflows."""

from collections.abc import Callable

UNSAVED_CHANGES_MESSAGE = "ไฟล์มีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก ต้องการทิ้งการเปลี่ยนแปลงและทำต่อหรือไม่"


def can_discard_unsaved_changes(is_dirty: bool, confirm_callback: Callable[[str], bool]) -> bool:
    """Return True when it is safe to continue past unsaved changes."""
    if not is_dirty:
        return True
    return confirm_callback(UNSAVED_CHANGES_MESSAGE)
