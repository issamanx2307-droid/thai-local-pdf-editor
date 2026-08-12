# -*- coding: utf-8 -*-
"""Tests for opening password-protected PDFs."""

from pathlib import Path

import fitz
import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import PdfPasswordRequiredError
from thai_pdf_editor.app.core.pdf_document import PdfDocument


def create_encrypted_sample_pdf(path: Path, *, user_password: str = "secret123", pages: int = 2) -> Path:
    """Create a small user-password-protected PDF for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    for page_number in range(1, pages + 1):
        page = document.new_page(width=300, height=420)
        page.insert_text((36, 64), f"ทดสอบ {page_number}", fontsize=14)
    document.save(
        str(path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-" + user_password,
        user_pw=user_password,
        permissions=fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY,
    )
    document.close()
    return path


def test_open_password_protected_pdf_without_password_raises(tmp_path) -> None:
    """Opening an encrypted PDF without a password asks for one."""
    sample_path = tmp_path / "มีรหัสผ่าน.pdf"
    create_encrypted_sample_pdf(sample_path)

    state = DocumentState()
    document = PdfDocument(state)

    with pytest.raises(PdfPasswordRequiredError) as exc_info:
        document.open(sample_path)

    assert exc_info.value.detail == "password_required"
    assert not document.is_open
    assert not state.has_document


def test_open_password_protected_pdf_with_wrong_password_raises(tmp_path) -> None:
    """Opening an encrypted PDF with the wrong password is rejected clearly."""
    sample_path = tmp_path / "มีรหัสผ่านผิด.pdf"
    create_encrypted_sample_pdf(sample_path, user_password="secret123")

    state = DocumentState()
    document = PdfDocument(state)

    with pytest.raises(PdfPasswordRequiredError) as exc_info:
        document.open(sample_path, password="wrong-password")

    assert exc_info.value.detail == "wrong_password"
    assert not document.is_open
    assert not state.has_document


def test_open_password_protected_pdf_with_correct_password_succeeds(tmp_path) -> None:
    """Opening an encrypted PDF with the correct password loads normally."""
    sample_path = tmp_path / "มีรหัสผ่านถูก.pdf"
    create_encrypted_sample_pdf(sample_path, user_password="secret123", pages=3)

    state = DocumentState()
    document = PdfDocument(state)
    document.open(sample_path, password="secret123")

    try:
        assert document.is_open
        assert state.has_document
        assert state.total_pages == 3
    finally:
        document.close()


def test_open_password_protected_pdf_after_failed_attempt_can_retry(tmp_path) -> None:
    """A failed password attempt does not prevent a subsequent correct retry."""
    sample_path = tmp_path / "ลองใหม่.pdf"
    create_encrypted_sample_pdf(sample_path, user_password="right-pass")

    state = DocumentState()
    document = PdfDocument(state)

    with pytest.raises(PdfPasswordRequiredError):
        document.open(sample_path, password="wrong-pass")

    document.open(sample_path, password="right-pass")
    try:
        assert document.is_open
        assert state.has_document
    finally:
        document.close()


def test_worker_open_pdf_reports_password_required_error_type(tmp_path) -> None:
    """A password-protected PDF should surface a typed, retryable error to the UI."""
    from thai_pdf_editor.app.worker import PdfWorkerSession
    from thai_pdf_editor.app.worker_contract import COMMAND_BATCH, COMMAND_CLOSE_DOCUMENT, COMMAND_OPEN_PDF

    source_path = create_encrypted_sample_pdf(tmp_path / "ป้องกันรหัสผ่าน.pdf", user_password="secret123")
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        no_password = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        assert no_password["ok"] is False
        assert no_password["error"]["type"] == "PdfPasswordRequiredError"
        assert no_password["error"]["detail"] == "password_required"

        wrong_password = session.handle(
            {"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path), "password": "nope"}}
        )
        assert wrong_password["ok"] is False
        assert wrong_password["error"]["type"] == "PdfPasswordRequiredError"
        assert wrong_password["error"]["detail"] == "wrong_password"

        correct_password = session.handle(
            {"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path), "password": "secret123"}}
        )
        assert correct_password["ok"] is True
        assert correct_password["state"]["has_document"] is True

        batch_response = session.handle(
            {
                "command": COMMAND_BATCH,
                "commands": [
                    {"command": COMMAND_CLOSE_DOCUMENT},
                    {"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}},
                ],
            }
        )
        assert batch_response["ok"] is False
        assert batch_response["responses"][-1]["error"]["type"] == "PdfPasswordRequiredError"
    finally:
        session.close()
