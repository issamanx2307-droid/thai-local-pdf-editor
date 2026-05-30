# -*- coding: utf-8 -*-
"""Tests for safe existing-text replacement."""

import fitz
import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.core.text_edit_operations import (
    TEXT_REPLACE_SCOPE_ALL,
    TEXT_REPLACE_SCOPE_CURRENT,
    create_replace_text_operations,
    resolve_text_replace_page_indices,
)
from thai_pdf_editor.app.models.operations import OperationType
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_replace_existing_text_removes_old_text_and_writes_new_text(tmp_path) -> None:
    """Replacement uses real redaction before placing the new text."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1, text_prefix="OLD TEXT")
    output_path = tmp_path / "replaced.pdf"
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    operations = create_replace_text_operations(
        document.raw,
        page_indices=[0],
        search_text="OLD TEXT",
        replacement_text="NEW TEXT",
        font_size=14,
        color="#111111",
        font_path=font_path,
    )
    for operation in operations:
        state.record_operation(operation, pending=True)

    SaveManager().save_as(document.raw, state, output_path)

    with fitz.open(str(output_path)) as saved:
        text = saved[0].get_text()
    assert "OLD TEXT" not in text
    assert "NEW TEXT" in text
    document.close()


def test_replace_text_scope_resolution() -> None:
    """Current-page and all-page scopes resolve deterministically."""
    assert resolve_text_replace_page_indices(TEXT_REPLACE_SCOPE_CURRENT, 1, 3) == [1]
    assert resolve_text_replace_page_indices(TEXT_REPLACE_SCOPE_ALL, 1, 3) == [0, 1, 2]


def test_replace_text_fails_when_search_text_is_missing(tmp_path) -> None:
    """The user should get a clear error instead of a silent no-op."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1, text_prefix="VISIBLE")
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    with pytest.raises(InvalidOperationError):
        create_replace_text_operations(
            document.raw,
            page_indices=[0],
            search_text="MISSING",
            replacement_text="NEW",
            font_size=14,
            color="#111111",
            font_path=font_path,
        )
    document.close()


def test_replace_text_operation_is_pending_redaction_plus_overlay(tmp_path) -> None:
    """Replacement remains a pending operation until Save As is used."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1, text_prefix="OLD TEXT")
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    operations = create_replace_text_operations(
        document.raw,
        page_indices=[0],
        search_text="OLD TEXT",
        replacement_text="NEW",
        font_size=14,
        color="#111111",
        font_path=font_path,
    )

    assert operations
    assert operations[0].type == OperationType.REPLACE_TEXT
    assert operations[0].irreversible is True
    assert state.pending_operations == []
    document.close()
