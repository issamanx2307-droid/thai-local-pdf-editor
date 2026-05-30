# -*- coding: utf-8 -*-
"""Tests for Milestone 2 page operations."""

import hashlib

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.models.geometry import PdfRect

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_rotate_page_keeps_page_count(tmp_path) -> None:
    """Rotate a page without changing total page count."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=2)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).rotate_current_page(90)

    assert state.total_pages == 2
    assert document.get_page(0).rotation == 90
    assert state.dirty is True
    document.close()


def test_delete_page_reduces_page_count(tmp_path) -> None:
    """Delete the current page and reduce page count."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=3)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).delete_current_page()

    assert state.total_pages == 2
    assert document.raw.page_count == 2
    document.close()


def test_move_page_down_updates_selection(tmp_path) -> None:
    """Move the first page down and keep selection on moved page."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=3)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).move_current_page(1)

    assert state.current_page_index == 1
    assert state.total_pages == 3
    document.close()


def test_duplicate_page_inserts_copy_after_current_page(tmp_path) -> None:
    """Duplicate the current page and select the inserted copy."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=2)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).duplicate_current_page()

    assert state.total_pages == 3
    assert state.current_page_index == 1
    assert document.raw.page_count == 3
    assert document.raw.load_page(0).get_text() == document.raw.load_page(1).get_text()
    assert state.dirty is True
    document.close()


def test_save_after_duplicate_keeps_original_pdf_unchanged(tmp_path) -> None:
    """Save As persists duplicated pages without modifying the source PDF."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=2)
    original_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).duplicate_current_page()
    output_path = SaveManager().save_as(document.raw, state, tmp_path / "sample_duplicated.pdf")

    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == original_hash
    with fitz.open(str(output_path)) as output:
        assert output.page_count == 3
    document.close()


def test_crop_page_changes_current_page_view(tmp_path) -> None:
    """Crop the current page to the selected rectangle."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).crop_current_page(PdfRect(50, 60, 250, 360))

    page = document.raw.load_page(0)
    assert round(page.rect.width) == 200
    assert round(page.rect.height) == 300
    assert state.dirty is True
    document.close()


def test_save_after_crop_keeps_original_pdf_unchanged(tmp_path) -> None:
    """Save As persists crop changes without modifying the source PDF."""
    sample_path = create_sample_pdf(tmp_path / "sample.pdf", pages=1)
    original_hash = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path)

    PageOperations(document, state).crop_current_page(PdfRect(40, 50, 240, 350))
    output_path = SaveManager().save_as(document.raw, state, tmp_path / "sample_cropped.pdf")

    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == original_hash
    with fitz.open(str(output_path)) as output:
        assert round(output.load_page(0).rect.width) == 200
        assert round(output.load_page(0).rect.height) == 300
    document.close()
