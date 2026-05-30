# -*- coding: utf-8 -*-
"""Safe Save As workflow for PDF output."""

import logging
import shutil
from pathlib import Path

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import PdfSaveError
from thai_pdf_editor.app.core.overlay_operations import apply_overlay_operations, apply_redaction_operations
from thai_pdf_editor.app.utils.path_utils import make_temp_output_path

LOGGER = logging.getLogger("thai_pdf_editor.save_manager")


class SaveManager:
    """Persist the working PDF through a temp file before final copy."""

    def save_as(self, document: fitz.Document, state: DocumentState, destination_path: Path) -> Path:
        """Save to a new PDF path without damaging the source file."""
        if not state.has_document:
            raise PdfSaveError("ยังไม่ได้เปิดไฟล์ PDF")
        destination_path = destination_path.expanduser()
        if destination_path.suffix.lower() != ".pdf":
            destination_path = destination_path.with_suffix(".pdf")
        if state.current_file_path and destination_path.resolve() == state.current_file_path.resolve():
            raise PdfSaveError("กรุณาเลือกชื่อไฟล์ใหม่ ห้ามบันทึกทับไฟล์ต้นฉบับ")

        has_pending = bool(state.pending_operations)
        temp_base_path = make_temp_output_path(destination_path.with_name(f"{destination_path.stem}_base.pdf"))
        temp_output_path = make_temp_output_path(destination_path) if has_pending else None
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            document.save(str(temp_base_path), garbage=4, deflate=True)
            if has_pending:
                # Two-pass: apply overlays/redactions on a fresh GC-compressed copy
                with fitz.open(str(temp_base_path)) as output_document:
                    apply_redaction_operations(output_document, state.pending_operations)
                    apply_overlay_operations(output_document, state.pending_operations)
                    output_document.save(str(temp_output_path), garbage=4, deflate=True)
                self._verify_pdf(temp_output_path)
                shutil.copy2(temp_output_path, destination_path)
            else:
                # Single-pass: no pending operations — skip re-open and second save
                self._verify_pdf(temp_base_path)
                shutil.copy2(temp_base_path, destination_path)
        except Exception as exc:
            LOGGER.exception("safe save failed destination=%s", destination_path)
            raise PdfSaveError("บันทึกไฟล์ PDF ไม่สำเร็จ ไฟล์ต้นฉบับยังไม่ถูกแก้ไข", detail=str(exc)) from exc
        finally:
            temp_base_path.unlink(missing_ok=True)
            if temp_output_path and temp_output_path.exists():
                temp_output_path.unlink(missing_ok=True)

        state.mark_saved()
        LOGGER.info("saved pdf destination=%s passes=%s", destination_path, 2 if has_pending else 1)
        return destination_path

    def _verify_pdf(self, path: Path) -> None:
        """Reopen a temp output PDF before copying to the final path."""
        try:
            with fitz.open(str(path)) as document:
                if document.page_count <= 0:
                    raise PdfSaveError("ไฟล์ PDF ที่บันทึกไม่มีหน้า")
        except PdfSaveError:
            raise
        except Exception as exc:
            raise PdfSaveError("ตรวจสอบไฟล์ PDF ที่บันทึกไม่สำเร็จ", detail=str(exc)) from exc
