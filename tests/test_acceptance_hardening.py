# -*- coding: utf-8 -*-
"""Acceptance-level hardening tests."""

import os
import stat

import pytest

from thai_pdf_editor.app.config import APP_LOG_PATH, TEMP_DIR
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import PdfOpenError
from thai_pdf_editor.app.core.overlay_operations import create_text_operation
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.models.geometry import PdfPoint
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_invalid_pdf_returns_thai_error_without_crashing(tmp_path) -> None:
    """Invalid PDFs raise an app error with a Thai user message."""
    invalid_path = tmp_path / "ไฟล์เสีย_acceptance_unique.pdf"
    invalid_path.write_text("not a pdf", encoding="utf-8")
    state = DocumentState()
    document = PdfDocument(state)

    with pytest.raises(PdfOpenError) as exc_info:
        document.open(invalid_path)

    assert "เปิดไฟล์ PDF ไม่สำเร็จ" == exc_info.value.user_message
    assert not list(TEMP_DIR.glob("ไฟล์เสีย_acceptance_unique_*_working.pdf"))


def test_close_removes_working_copy(tmp_path) -> None:
    """Closing a PDF cleans up its temp working copy."""
    source_path = create_sample_pdf(tmp_path / "ต้นฉบับ.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    working_copy_path = state.working_copy_path
    assert working_copy_path is not None and working_copy_path.exists()

    document.close()

    assert not working_copy_path.exists()


def test_close_removes_working_copy_for_read_only_source(tmp_path) -> None:
    """Read-only source metadata must not leave undeletable temp PDFs."""
    source_path = create_sample_pdf(tmp_path / "readonly_source.pdf", pages=1)
    os.chmod(source_path, stat.S_IREAD)
    state = DocumentState()
    document = PdfDocument(state)
    working_copy_path = None

    try:
        document.open(source_path)
        working_copy_path = state.working_copy_path
        assert working_copy_path is not None and working_copy_path.exists()

        document.close()

        assert not working_copy_path.exists()
    finally:
        os.chmod(source_path, stat.S_IWRITE | stat.S_IREAD)
        if working_copy_path is not None and working_copy_path.exists():
            working_copy_path.chmod(0o666)
            working_copy_path.unlink()


def test_save_as_then_reopen_keeps_saved_text_visible_in_document(tmp_path) -> None:
    """After Save As, reopening the saved file preserves overlay content."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    source_path = create_sample_pdf(tmp_path / "ต้นฉบับ.pdf", pages=1)
    output_path = tmp_path / "ผลลัพธ์.pdf"
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    operation = create_text_operation(
        page_index=0,
        point=PdfPoint(40, 120),
        text="ข้อความหลังบันทึก",
        font_size=16,
        color="#111111",
        font_path=font_path,
    )
    state.record_operation(operation, pending=True)

    saved_path = SaveManager().save_as(document.raw, state, output_path)
    document.open(saved_path)

    assert "ข้อความหลังบันทึก" in document.raw[0].get_text()
    assert not state.pending_operations
    document.close()


def test_logging_path_and_temp_dir_exist() -> None:
    """Runtime dirs required by acceptance criteria exist."""
    logger = setup_logging()
    logger.info("acceptance hardening log entry")

    assert APP_LOG_PATH.exists()
    assert TEMP_DIR.exists()
