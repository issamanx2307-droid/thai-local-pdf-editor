# -*- coding: utf-8 -*-
"""Validation helpers for local files."""

from pathlib import Path

from thai_pdf_editor.app.core.errors import InvalidOperationError, PdfOpenError


def require_pdf_path(path: Path) -> None:
    """Validate an existing PDF path."""
    if not path.exists():
        raise PdfOpenError("ไม่พบไฟล์ PDF ที่เลือก")
    if not path.is_file():
        raise PdfOpenError("เส้นทางที่เลือกไม่ใช่ไฟล์ PDF")
    if path.suffix.lower() != ".pdf":
        raise PdfOpenError("กรุณาเลือกไฟล์นามสกุล .pdf")


def require_page_index(page_index: int, total_pages: int) -> None:
    """Validate a zero-based page index."""
    if total_pages <= 0:
        raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")
    if not 0 <= page_index < total_pages:
        raise InvalidOperationError("เลขหน้าที่เลือกไม่ถูกต้อง")
