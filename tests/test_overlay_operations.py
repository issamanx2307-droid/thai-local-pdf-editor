# -*- coding: utf-8 -*-
"""Tests for Milestone 3 overlay operations."""

from pathlib import Path

import fitz
from PIL import Image

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.overlay_operations import (
    create_highlight_operation,
    create_image_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_add_thai_text_overlay_with_selected_font_and_save(tmp_path) -> None:
    """Thai text overlay is written when a Thai font file is selected."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1)
    output_path = tmp_path / "ข้อความไทย.pdf"

    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    operation = create_text_operation(
        page_index=0,
        point=PdfPoint(40, 100),
        text="ทดสอบข้อความไทย",
        font_size=18,
        color="#111111",
        font_path=font_path,
    )
    state.record_operation(operation, pending=True)

    SaveManager().save_as(document.raw, state, output_path)

    with fitz.open(str(output_path)) as saved:
        assert "ทดสอบข้อความไทย" in saved[0].get_text()
    document.close()


def test_add_image_rectangle_and_highlight_operations_save(tmp_path) -> None:
    """Image, rectangle, and highlight overlays save without corrupting output."""
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1)
    image_path = tmp_path / "ลายเซ็น.png"
    Image.new("RGBA", (80, 30), (20, 90, 200, 180)).save(image_path)
    output_path = tmp_path / "with_overlays.pdf"

    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    for operation in [
        create_image_operation(page_index=0, point=PdfPoint(40, 120), image_path=image_path, width=80),
        create_rectangle_operation(page_index=0, rect=PdfRect(30, 40, 140, 100), color="#d32f2f", line_width=2),
        create_highlight_operation(page_index=0, rect=PdfRect(35, 150, 180, 190), color="#fff176"),
    ]:
        state.record_operation(operation, pending=True)

    SaveManager().save_as(document.raw, state, output_path)

    with fitz.open(str(output_path)) as saved:
        assert saved.page_count == 1
    document.close()


def test_renderer_previews_pending_overlay(tmp_path) -> None:
    """Renderer draws pending overlays into preview image."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    operation = create_text_operation(
        page_index=0,
        point=PdfPoint(30, 80),
        text="ไทย",
        font_size=16,
        color="#d32f2f",
        font_path=Path(font_path),
    )
    state.record_operation(operation, pending=True)

    rendered = PdfRenderer().render_page(
        document.raw,
        state.working_copy_path,
        0,
        1.0,
        state.dirty_version,
        state.pending_operations,
    )

    assert rendered.image.getbbox() is not None
    document.close()
