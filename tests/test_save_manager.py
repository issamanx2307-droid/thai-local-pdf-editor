# -*- coding: utf-8 -*-
"""Tests for safe Save As behavior."""

from hashlib import sha256

import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import PdfSaveError
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def _file_hash(path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_save_as_creates_new_file_without_modifying_source(tmp_path) -> None:
    """Save As writes a new file and keeps the source bytes unchanged."""
    source_path = create_sample_pdf(tmp_path / "ต้นฉบับ.pdf", pages=2)
    original_hash = _file_hash(source_path)
    output_path = tmp_path / "ผลลัพธ์" / "ต้นฉบับ_edited.pdf"

    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    PageOperations(document, state).rotate_current_page(90)

    SaveManager().save_as(document.raw, state, output_path)

    assert output_path.exists()
    assert _file_hash(source_path) == original_hash
    assert state.dirty is False
    document.close()


def test_save_as_rejects_original_path(tmp_path) -> None:
    """Save As refuses to overwrite the original file path."""
    source_path = create_sample_pdf(tmp_path / "ต้นฉบับ.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    with pytest.raises(PdfSaveError):
        SaveManager().save_as(document.raw, state, source_path)

    document.close()
