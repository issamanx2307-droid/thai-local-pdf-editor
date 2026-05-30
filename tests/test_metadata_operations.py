# -*- coding: utf-8 -*-
"""Tests for PDF metadata editing."""

import hashlib

import fitz
import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.metadata_operations import editable_metadata, update_metadata
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_update_metadata_marks_document_dirty(tmp_path) -> None:
    """Metadata updates are tracked as dirty document operations."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    update_metadata(
        document.raw,
        state,
        {
            "title": "ใบเสนอราคา",
            "author": "ทีมเอกสาร",
            "subject": "ทดสอบ metadata",
            "keywords": "PDF,ภาษาไทย",
        },
    )

    metadata = editable_metadata(document.raw)
    assert metadata["title"] == "ใบเสนอราคา"
    assert metadata["author"] == "ทีมเอกสาร"
    assert state.dirty is True
    assert state.applied_operations[-1].payload["after"]["keywords"] == "PDF,ภาษาไทย"
    document.close()


def test_save_metadata_as_keeps_original_pdf_unchanged(tmp_path) -> None:
    """Save As writes metadata to the new file without mutating the source."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=1)
    original_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    update_metadata(document.raw, state, {"title": "เอกสารภาษาไทย", "author": "ผู้ทดสอบ"})
    output_path = SaveManager().save_as(document.raw, state, tmp_path / "metadata_output.pdf")

    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == original_hash
    with fitz.open(str(output_path)) as output:
        assert output.metadata["title"] == "เอกสารภาษาไทย"
        assert output.metadata["author"] == "ผู้ทดสอบ"
    document.close()


def test_update_metadata_rejects_no_change(tmp_path) -> None:
    """Submitting unchanged metadata should not mark the document dirty."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    with pytest.raises(InvalidOperationError):
        update_metadata(document.raw, state, editable_metadata(document.raw))

    assert state.dirty is False
    document.close()
