# -*- coding: utf-8 -*-
"""Manage pending overlay operations before Save As."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation

MOVE_STEP = 5.0
RESIZE_UP_SCALE = 1.1
RESIZE_DOWN_SCALE = 0.9
MIN_SIZE = 2.0

PENDING_OVERLAY_TYPES = {
    OperationType.ADD_TEXT,
    OperationType.ADD_IMAGE,
    OperationType.DRAW_RECTANGLE,
    OperationType.HIGHLIGHT,
    OperationType.REDACT,
    OperationType.REPLACE_TEXT,
}

TYPE_LABELS = {
    OperationType.ADD_TEXT: "ข้อความ",
    OperationType.ADD_IMAGE: "รูป/ลายเซ็นภาพ",
    OperationType.DRAW_RECTANGLE: "กล่อง",
    OperationType.HIGHLIGHT: "Highlight",
    OperationType.REDACT: "ลบถาวร",
    OperationType.REPLACE_TEXT: "แก้ข้อความเดิม",
}


@dataclass(frozen=True)
class PendingOperationView:
    """Display data for one pending overlay operation."""

    id: str
    label: str
    page_index: int
    type_label: str


def pending_operation_views(operations: list[PdfOperation]) -> list[PendingOperationView]:
    """Return list-ready labels for pending overlay operations."""
    views: list[PendingOperationView] = []
    for index, operation in enumerate(_pending_overlays(operations), start=1):
        type_label = TYPE_LABELS.get(operation.type, str(operation.type))
        detail = _operation_detail(operation)
        label = f"{index}. หน้า {operation.page_index + 1} - {type_label}"
        if detail:
            label = f"{label}: {detail}"
        views.append(
            PendingOperationView(
                id=operation.id,
                label=label,
                page_index=operation.page_index,
                type_label=type_label,
            )
        )
    return views


def delete_pending_operation(state: DocumentState, operation_id: str) -> PdfOperation:
    """Delete a pending overlay operation by id."""
    operation = _pop_pending_operation(state.pending_operations, operation_id)
    _remove_from_stack(state.undo_stack, operation_id)
    _remove_from_stack(state.redo_stack, operation_id)
    _refresh_dirty_state(state)
    return operation


def nudge_pending_operation(state: DocumentState, operation_id: str, *, dx: float, dy: float) -> PdfOperation:
    """Move a pending overlay operation by a small PDF-point offset."""
    operation = _find_pending_operation(state.pending_operations, operation_id)
    payload = operation.payload
    if operation.type in {OperationType.ADD_TEXT, OperationType.ADD_IMAGE}:
        payload["x"] = max(0.0, float(payload["x"]) + float(dx))
        payload["y"] = max(0.0, float(payload["y"]) + float(dy))
    elif operation.type in {
        OperationType.DRAW_RECTANGLE,
        OperationType.HIGHLIGHT,
        OperationType.REDACT,
        OperationType.REPLACE_TEXT,
    }:
        payload["rect"] = _move_rect(payload["rect"], dx, dy)
    else:
        raise InvalidOperationError("รายการนี้ยังไม่รองรับการย้าย")
    _mark_pending_changed(state)
    return operation


def resize_pending_operation(state: DocumentState, operation_id: str, *, scale: float) -> PdfOperation:
    """Resize a pending overlay operation around its current center or anchor."""
    operation = _find_pending_operation(state.pending_operations, operation_id)
    payload = operation.payload
    if operation.type == OperationType.ADD_TEXT:
        payload["font_size"] = max(1, int(round(float(payload["font_size"]) * float(scale))))
    elif operation.type == OperationType.ADD_IMAGE:
        payload["width"] = max(MIN_SIZE, float(payload["width"]) * float(scale))
        payload["height"] = max(MIN_SIZE, float(payload["height"]) * float(scale))
    elif operation.type in {
        OperationType.DRAW_RECTANGLE,
        OperationType.HIGHLIGHT,
        OperationType.REDACT,
        OperationType.REPLACE_TEXT,
    }:
        payload["rect"] = _scale_rect(payload["rect"], scale)
        if operation.type == OperationType.REPLACE_TEXT and "font_size" in payload:
            payload["font_size"] = max(1, int(round(float(payload["font_size"]) * float(scale))))
    else:
        raise InvalidOperationError("รายการนี้ยังไม่รองรับการปรับขนาด")
    _mark_pending_changed(state)
    return operation


def _pending_overlays(operations: list[PdfOperation]) -> list[PdfOperation]:
    return [operation for operation in operations if operation.type in PENDING_OVERLAY_TYPES]


def _operation_detail(operation: PdfOperation) -> str:
    payload = operation.payload
    if operation.type == OperationType.ADD_TEXT:
        return _short_text(str(payload.get("text", "")))
    if operation.type == OperationType.REPLACE_TEXT:
        return _short_text(str(payload.get("text", "")) or "แทนที่ข้อความ")
    if operation.type == OperationType.ADD_IMAGE:
        return Path(str(payload.get("image_path", ""))).name
    return ""


def _short_text(value: str, limit: int = 24) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return f"{clean[:limit - 3]}..."


def _find_pending_operation(operations: list[PdfOperation], operation_id: str) -> PdfOperation:
    for operation in operations:
        if operation.id == operation_id and operation.type in PENDING_OVERLAY_TYPES:
            return operation
    raise InvalidOperationError("ไม่พบรายการที่เลือก")


def _pop_pending_operation(operations: list[PdfOperation], operation_id: str) -> PdfOperation:
    for index, operation in enumerate(operations):
        if operation.id == operation_id and operation.type in PENDING_OVERLAY_TYPES:
            return operations.pop(index)
    raise InvalidOperationError("ไม่พบรายการที่เลือก")


def _remove_from_stack(stack: list[object], operation_id: str) -> None:
    stack[:] = [operation for operation in stack if getattr(operation, "id", None) != operation_id]


def _move_rect(payload: object, dx: float, dy: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = _rect_values(payload)
    width = x1 - x0
    height = y1 - y0
    new_x0 = max(0.0, x0 + float(dx))
    new_y0 = max(0.0, y0 + float(dy))
    return (new_x0, new_y0, new_x0 + width, new_y0 + height)


def _scale_rect(payload: object, scale: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = _rect_values(payload)
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2
    half_width = max(MIN_SIZE / 2, ((x1 - x0) * float(scale)) / 2)
    half_height = max(MIN_SIZE / 2, ((y1 - y0) * float(scale)) / 2)
    return (
        max(0.0, center_x - half_width),
        max(0.0, center_y - half_height),
        center_x + half_width,
        center_y + half_height,
    )


def _rect_values(payload: object) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = payload
    return (float(x0), float(y0), float(x1), float(y1))


def _mark_pending_changed(state: DocumentState) -> None:
    state.dirty = True
    state.bump_version()


def _refresh_dirty_state(state: DocumentState) -> None:
    state.dirty = bool(state.pending_operations or state.applied_operations)
    state.bump_version()
