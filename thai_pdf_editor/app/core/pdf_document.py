# -*- coding: utf-8 -*-
"""PDF document wrapper around PyMuPDF."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import PdfOpenError
from thai_pdf_editor.app.utils.path_utils import make_working_copy_path
from thai_pdf_editor.app.utils.validation import require_pdf_path

LOGGER = logging.getLogger("thai_pdf_editor.pdf_document")


class PdfDocument:
    """Owns the currently open PyMuPDF document and working copy."""

    def __init__(self, state: DocumentState) -> None:
        self.state = state
        self._doc: fitz.Document | None = None

    @property
    def raw(self) -> fitz.Document:
        """Return the loaded PyMuPDF document."""
        if self._doc is None:
            raise PdfOpenError("ยังไม่ได้เปิดไฟล์ PDF")
        return self._doc

    @property
    def is_open(self) -> bool:
        """Return True when a document is loaded."""
        return self._doc is not None

    def open(self, source_path: Path) -> None:
        """Open a PDF from disk and create a safe working copy."""
        require_pdf_path(source_path)
        self.close()
        working_copy_path = make_working_copy_path(source_path)

        try:
            shutil.copyfile(source_path, working_copy_path)
            document = fitz.open(str(working_copy_path))
        except Exception as exc:
            if working_copy_path.exists():
                working_copy_path.unlink(missing_ok=True)
            LOGGER.exception("failed to open pdf path=%s", source_path)
            raise PdfOpenError("เปิดไฟล์ PDF ไม่สำเร็จ", detail=str(exc)) from exc

        if document.page_count <= 0:
            document.close()
            raise PdfOpenError("ไฟล์ PDF ไม่มีหน้าให้แสดง")

        self._doc = document
        self.state.load_document(source_path, working_copy_path, document.page_count)
        LOGGER.info("opened pdf path=%s pages=%s", source_path, document.page_count)

    def close(self) -> None:
        """Close the current document and clear state."""
        working_copy_path = self.state.working_copy_path
        if self._doc is not None:
            self._doc.close()
        self._doc = None
        if working_copy_path and working_copy_path.exists():
            _remove_working_copy(working_copy_path)
        self.state.reset()

    def get_page(self, page_index: int) -> fitz.Page:
        """Return a page by zero-based index."""
        if not 0 <= page_index < self.raw.page_count:
            raise PdfOpenError("เลขหน้าที่เลือกไม่ถูกต้อง")
        return self.raw.load_page(page_index)

    def refresh_page_count(self) -> None:
        """Sync state page count with the loaded document."""
        self.state.total_pages = self.raw.page_count
        self.state.page_order = list(range(self.raw.page_count))
        self.state.clamp_current_page()


def _remove_working_copy(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        try:
            path.chmod(0o666)
            path.unlink()
        except OSError:
            LOGGER.warning("could not remove working copy path=%s", path)
    except OSError:
        LOGGER.warning("could not remove working copy path=%s", path)
