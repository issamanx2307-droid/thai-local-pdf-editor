# -*- coding: utf-8 -*-
"""Tests for text-layer PDF search."""

from pathlib import Path

import fitz
import pytest

from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.pdf_search import (
    next_search_index,
    previous_search_index,
    scaled_search_rect,
    search_pdf_text,
)
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font


def test_search_pdf_text_finds_text_layer_matches(tmp_path: Path) -> None:
    """Search should use the PDF text layer and return page labels."""
    pdf_path = tmp_path / "ค้นหา.pdf"
    font_path = first_existing_thai_font()
    assert font_path is not None
    document = fitz.open()
    page = document.new_page(width=300, height=220)
    page.insert_text((40, 80), "ค้นหา คำนี้", fontfile=str(font_path), fontname="qa_search_font", fontsize=16)
    document.save(str(pdf_path))
    document.close()

    with fitz.open(str(pdf_path)) as opened:
        results = search_pdf_text(opened, "คำนี้")

    assert len(results) == 1
    assert results[0].page_index == 0
    assert results[0].label == "หน้า 1 - พบครั้งที่ 1"


def test_search_pdf_text_reports_no_match(tmp_path: Path) -> None:
    """Missing text should raise a clear Thai error."""
    pdf_path = tmp_path / "empty.pdf"
    document = fitz.open()
    document.new_page(width=200, height=200)
    document.save(str(pdf_path))
    document.close()

    with fitz.open(str(pdf_path)) as opened:
        with pytest.raises(InvalidOperationError, match="ไม่พบข้อความ"):
            search_pdf_text(opened, "ไม่มีคำนี้")


def test_search_navigation_wraps() -> None:
    """Next and previous search navigation should wrap around."""
    assert next_search_index(0, 2) == 1
    assert next_search_index(1, 2) == 0
    assert previous_search_index(0, 2) == 1
    assert previous_search_index(1, 2) == 0


def test_scaled_search_rect_uses_preview_zoom() -> None:
    """Search highlight rectangles should scale with the preview zoom."""
    assert scaled_search_rect((10, 20, 30, 40), 1.5) == (15, 30, 45, 60)
    assert scaled_search_rect((10, 20, 30, 40), 0) == (0.1, 0.2, 0.3, 0.4)
