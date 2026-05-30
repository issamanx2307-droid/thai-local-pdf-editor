# -*- coding: utf-8 -*-
"""Tests for basic pending overlay undo/redo."""

from pathlib import Path

import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.undo_redo import (
    can_redo_pending,
    can_undo_pending,
    redo_last_pending,
    undo_last_pending,
)
from thai_pdf_editor.app.core.overlay_operations import create_rectangle_operation
from thai_pdf_editor.app.models.geometry import PdfRect

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_undo_pending_overlay_removes_latest_operation() -> None:
    """Undo removes the latest pending overlay and updates dirty state."""
    state = DocumentState()
    operation = create_rectangle_operation(page_index=0, rect=PdfRect(10, 10, 80, 80), color="#111111", line_width=2)
    state.current_file_path = state.working_copy_path = Path(__file__)
    state.total_pages = 1
    state.record_operation(operation, pending=True)

    undone = undo_last_pending(state)

    assert undone == operation
    assert state.pending_operations == []
    assert state.undo_stack == []
    assert state.redo_stack == [operation]
    assert state.dirty is False
    assert can_undo_pending(state) is False
    assert can_redo_pending(state) is True


def test_redo_pending_overlay_restores_operation() -> None:
    """Redo restores an undone pending overlay."""
    state = DocumentState()
    operation = create_rectangle_operation(page_index=0, rect=PdfRect(10, 10, 80, 80), color="#111111", line_width=2)
    state.current_file_path = state.working_copy_path = Path(__file__)
    state.total_pages = 1
    state.record_operation(operation, pending=True)
    undo_last_pending(state)

    redone = redo_last_pending(state)

    assert redone == operation
    assert state.pending_operations == [operation]
    assert state.undo_stack == [operation]
    assert state.redo_stack == []
    assert state.dirty is True


def test_undo_does_not_apply_to_committed_page_operation(tmp_path) -> None:
    """Page operations that mutate the working PDF are not undone by the basic overlay undo."""
    source_path = create_sample_pdf(tmp_path / "sample.pdf", pages=2)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    PageOperations(document, state).rotate_current_page(90)

    assert can_undo_pending(state) is False
    with pytest.raises(InvalidOperationError):
        undo_last_pending(state)
    document.close()
