# -*- coding: utf-8 -*-
"""Tests for Thai font preference."""

from pathlib import Path

from thai_pdf_editor.app.core.overlay_operations import create_text_operation
from thai_pdf_editor.app.models.geometry import PdfPoint
from thai_pdf_editor.app.utils.font_utils import PREFERRED_THAI_FONT_PATH, first_existing_thai_font


def test_requested_thai_font_is_preferred_when_available() -> None:
    """The user-provided THSarabunNew font is preferred when present."""
    if PREFERRED_THAI_FONT_PATH.exists():
        assert first_existing_thai_font() == PREFERRED_THAI_FONT_PATH


def test_text_operation_uses_default_thai_font_when_not_selected() -> None:
    """Text overlay falls back to the preferred Thai font when no font is selected."""
    operation = create_text_operation(
        page_index=0,
        point=PdfPoint(10, 10),
        text="ทดสอบ",
        font_size=16,
        color="#111111",
        font_path=None,
    )

    assert Path(str(operation.payload["font_path"])) == first_existing_thai_font()
