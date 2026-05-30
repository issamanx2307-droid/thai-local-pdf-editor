# -*- coding: utf-8 -*-
"""Tests for Milestone 4 redaction, extract, and merge."""

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.overlay_operations import create_redact_operation
from thai_pdf_editor.app.core.page_operations import PageOperations, merge_pdfs
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_real_redaction_removes_text_from_saved_pdf(tmp_path) -> None:
    """Redaction uses PyMuPDF redaction APIs and removes underlying text."""
    source_path = tmp_path / "secret.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((50, 100), "SECRET DATA", fontsize=18)
    document.save(str(source_path))
    document.close()

    state = DocumentState()
    pdf_document = PdfDocument(state)
    pdf_document.open(source_path)
    rect = pdf_document.raw[0].search_for("SECRET DATA")[0]
    operation = create_redact_operation(page_index=0, rect=rect)
    state.record_operation(operation, pending=True)
    output_path = tmp_path / "redacted.pdf"

    SaveManager().save_as(pdf_document.raw, state, output_path)

    with fitz.open(str(output_path)) as redacted:
        assert "SECRET DATA" not in redacted[0].get_text()
    pdf_document.close()


def test_extract_current_page_creates_single_page_pdf(tmp_path) -> None:
    """Extract current page to a new one-page PDF."""
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=3)
    output_path = tmp_path / "แยกหน้า.pdf"
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    state.set_current_page(1)

    PageOperations(document, state).extract_current_page(output_path)

    with fitz.open(str(output_path)) as extracted:
        assert extracted.page_count == 1
    document.close()


def test_merge_pdfs_creates_combined_page_count(tmp_path) -> None:
    """Merge PDFs and preserve expected page count."""
    first = create_sample_pdf(tmp_path / "หนึ่ง.pdf", pages=2)
    second = create_sample_pdf(tmp_path / "สอง.pdf", pages=3)
    output_path = tmp_path / "รวม.pdf"

    merge_pdfs([first, second], output_path)

    with fitz.open(str(output_path)) as merged:
        assert merged.page_count == 5
