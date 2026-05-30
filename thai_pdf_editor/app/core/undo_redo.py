# -*- coding: utf-8 -*-
"""Basic undo/redo for pending overlay operations."""

from __future__ import annotations

from typing import Any

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError


def can_undo_pending(state: DocumentState) -> bool:
    """Return True when the latest operation is a pending overlay."""
    return bool(state.undo_stack and _operation_in_list(state.undo_stack[-1], state.pending_operations))


def can_redo_pending(state: DocumentState) -> bool:
    """Return True when a pending overlay can be restored."""
    return bool(state.redo_stack)


def undo_last_pending(state: DocumentState) -> Any:
    """Undo the latest pending overlay operation."""
    if not state.undo_stack:
        raise InvalidOperationError("ไม่มีคำสั่งให้ย้อนกลับ")
    operation = state.undo_stack[-1]
    if not _operation_in_list(operation, state.pending_operations):
        raise InvalidOperationError("คำสั่งล่าสุดยังไม่รองรับการย้อนกลับในรุ่นนี้")

    state.undo_stack.pop()
    _remove_operation(operation, state.pending_operations)
    state.redo_stack.append(operation)
    _refresh_dirty_state(state)
    return operation


def redo_last_pending(state: DocumentState) -> Any:
    """Restore the latest undone pending overlay operation."""
    if not state.redo_stack:
        raise InvalidOperationError("ไม่มีคำสั่งให้ทำซ้ำ")

    operation = state.redo_stack.pop()
    state.pending_operations.append(operation)
    state.undo_stack.append(operation)
    state.dirty = True
    state.bump_version()
    return operation


def _operation_in_list(operation: Any, operations: list[Any]) -> bool:
    operation_id = getattr(operation, "id", None)
    return any(candidate is operation or getattr(candidate, "id", None) == operation_id for candidate in operations)


def _remove_operation(operation: Any, operations: list[Any]) -> None:
    operation_id = getattr(operation, "id", None)
    for index in range(len(operations) - 1, -1, -1):
        candidate = operations[index]
        if candidate is operation or getattr(candidate, "id", None) == operation_id:
            del operations[index]
            return
    raise InvalidOperationError("ไม่พบคำสั่งที่ต้องการย้อนกลับ")


def _refresh_dirty_state(state: DocumentState) -> None:
    state.dirty = bool(state.pending_operations or state.applied_operations)
    state.bump_version()
