# -*- coding: utf-8 -*-
"""Tests for pending overlay management before Save As."""

from pathlib import Path

import pytest
from PIL import Image

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.overlay_operations import (
    create_image_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.pending_overlay_operations import (
    delete_pending_operation,
    nudge_pending_operation,
    pending_operation_views,
    resize_pending_operation,
)
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font


def test_pending_operation_views_label_overlay_items(tmp_path: Path) -> None:
    """Pending overlay items should be readable in the manager list."""
    state = DocumentState()
    operation = create_text_operation(
        page_index=1,
        point=PdfPoint(10, 20),
        text="ข้อความที่วางแล้ว",
        font_size=16,
        color="#111111",
        font_path=_font_path(),
    )
    state.record_operation(operation, pending=True)

    views = pending_operation_views(state.pending_operations)

    assert len(views) == 1
    assert views[0].id == operation.id
    assert "หน้า 2" in views[0].label
    assert "ข้อความ" in views[0].label


def test_delete_pending_operation_removes_it_from_state_and_undo_stack(tmp_path: Path) -> None:
    """Deleting a selected pending overlay should remove stale undo references."""
    state = DocumentState()
    operation = create_rectangle_operation(page_index=0, rect=PdfRect(10, 10, 50, 50), color="#d32f2f", line_width=2)
    state.record_operation(operation, pending=True)

    removed = delete_pending_operation(state, operation.id)

    assert removed.id == operation.id
    assert state.pending_operations == []
    assert state.undo_stack == []
    assert state.dirty is False


def test_nudge_and_resize_pending_image_operation(tmp_path: Path) -> None:
    """Image and visual signature overlays can be moved and resized before Save As."""
    image_path = tmp_path / "ลายเซ็นภาพ.png"
    Image.new("RGBA", (100, 40), (20, 90, 200, 180)).save(image_path)
    state = DocumentState()
    operation = create_image_operation(page_index=0, point=PdfPoint(40, 120), image_path=image_path, width=100)
    state.record_operation(operation, pending=True)
    version_before = state.dirty_version

    nudge_pending_operation(state, operation.id, dx=5, dy=-10)
    resize_pending_operation(state, operation.id, scale=1.1)

    assert operation.payload["x"] == 45
    assert operation.payload["y"] == 110
    assert float(operation.payload["width"]) > 100
    assert state.dirty is True
    assert state.dirty_version > version_before


def test_nudge_and_resize_pending_rectangle_operation() -> None:
    """Shape overlays should update their rectangle payloads safely."""
    state = DocumentState()
    operation = create_rectangle_operation(page_index=0, rect=PdfRect(10, 20, 60, 80), color="#d32f2f", line_width=2)
    state.record_operation(operation, pending=True)

    nudge_pending_operation(state, operation.id, dx=10, dy=5)
    assert operation.payload["rect"] == (20.0, 25.0, 70.0, 85.0)

    resize_pending_operation(state, operation.id, scale=0.5)
    x0, y0, x1, y1 = operation.payload["rect"]
    assert x1 - x0 == pytest.approx(25.0)
    assert y1 - y0 == pytest.approx(30.0)


def test_missing_pending_operation_reports_clear_error() -> None:
    """Unknown selected ids should not silently do nothing."""
    with pytest.raises(InvalidOperationError, match="ไม่พบรายการ"):
        delete_pending_operation(DocumentState(), "missing")


def _font_path() -> Path:
    font_path = first_existing_thai_font()
    assert font_path is not None
    return font_path
