# -*- coding: utf-8 -*-
"""Page-level PDF operations."""

import logging
import shutil
from pathlib import Path

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError, PdfSaveError
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.models.geometry import PdfRect
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation
from thai_pdf_editor.app.utils.path_utils import make_temp_output_path
from thai_pdf_editor.app.utils.validation import require_page_index
from thai_pdf_editor.app.utils.validation import require_pdf_path

LOGGER = logging.getLogger("thai_pdf_editor.page_operations")


class PageOperations:
    """Apply simple page operations to the working PDF document."""

    def __init__(self, document: PdfDocument, state: DocumentState) -> None:
        self.document = document
        self.state = state

    def rotate_current_page(self, degrees: int) -> PdfOperation:
        """Rotate the current page by degrees."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        page = self.document.get_page(page_index)
        page.set_rotation((page.rotation + degrees) % 360)

        operation = PdfOperation(
            type=OperationType.ROTATE_PAGE,
            page_index=page_index,
            payload={"degrees": degrees},
        )
        self.state.rotation_map[page_index] = page.rotation
        self.state.record_operation(operation)
        LOGGER.info("rotated page index=%s degrees=%s", page_index, degrees)
        return operation

    def delete_current_page(self) -> PdfOperation:
        """Delete the current page from the working document."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        if self.state.total_pages <= 1:
            raise InvalidOperationError("ไม่สามารถลบหน้าสุดท้ายของเอกสารได้")

        self.document.raw.delete_page(page_index)
        operation = PdfOperation(
            type=OperationType.DELETE_PAGE,
            page_index=page_index,
            payload={"deleted_page": page_index},
            irreversible=True,
        )
        self.document.refresh_page_count()
        self.state.deleted_pages.add(page_index)
        self.state.record_operation(operation)
        LOGGER.info("deleted page index=%s", page_index)
        return operation

    def move_current_page(self, delta: int) -> PdfOperation:
        """Move the current page up or down by one position."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        target_index = page_index + delta
        if not 0 <= target_index < self.state.total_pages:
            raise InvalidOperationError("ไม่สามารถย้ายหน้าเกินขอบเขตเอกสารได้")

        self.document.raw.move_page(page_index, target_index)
        self.state.set_current_page(target_index)
        operation = PdfOperation(
            type=OperationType.MOVE_PAGE,
            page_index=target_index,
            payload={"from": page_index, "to": target_index},
        )
        self.document.refresh_page_count()
        self.state.set_current_page(target_index)
        self.state.record_operation(operation)
        LOGGER.info("moved page from=%s to=%s", page_index, target_index)
        return operation

    def duplicate_current_page(self) -> PdfOperation:
        """Duplicate the current page and select the new copy."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        duplicated_index = page_index + 1

        temporary_document = fitz.open()
        try:
            temporary_document.insert_pdf(self.document.raw, from_page=page_index, to_page=page_index)
            self.document.raw.insert_pdf(temporary_document, start_at=duplicated_index)
        finally:
            temporary_document.close()

        operation = PdfOperation(
            type=OperationType.DUPLICATE_PAGE,
            page_index=duplicated_index,
            payload={"source_page": page_index, "duplicated_page": duplicated_index},
        )
        self.document.refresh_page_count()
        self.state.set_current_page(duplicated_index)
        self.state.record_operation(operation)
        LOGGER.info("duplicated page source=%s duplicated=%s", page_index, duplicated_index)
        return operation

    def crop_current_page(self, rect: PdfRect) -> PdfOperation:
        """Crop the current page to the selected rectangle."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        page = self.document.get_page(page_index)
        page_rect = page.rect
        crop_rect = fitz.Rect(
            max(page_rect.x0, rect.x0),
            max(page_rect.y0, rect.y0),
            min(page_rect.x1, rect.x1),
            min(page_rect.y1, rect.y1),
        )
        if crop_rect.width < 20 or crop_rect.height < 20:
            raise InvalidOperationError("พื้นที่ crop เล็กเกินไป กรุณาลากพื้นที่ใหม่")

        before_cropbox = tuple(page.cropbox)
        page.set_cropbox(crop_rect)
        operation = PdfOperation(
            type=OperationType.CROP_PAGE,
            page_index=page_index,
            payload={
                "before_cropbox": before_cropbox,
                "after_cropbox": tuple(crop_rect),
            },
        )
        self.state.record_operation(operation)
        LOGGER.info("cropped page index=%s rect=%s", page_index, tuple(crop_rect))
        return operation

    def extract_current_page(self, destination_path: Path) -> Path:
        """Extract the current page to a new PDF file."""
        page_index = self.state.current_page_index
        require_page_index(page_index, self.state.total_pages)
        destination_path = _ensure_pdf_suffix(destination_path)
        temp_output_path = make_temp_output_path(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        output = fitz.open()
        try:
            output.insert_pdf(self.document.raw, from_page=page_index, to_page=page_index)
            output.save(str(temp_output_path), garbage=4, deflate=True)
            output.close()
            _verify_pdf(temp_output_path)
            shutil.copy2(temp_output_path, destination_path)
        except Exception as exc:
            LOGGER.exception("extract page failed destination=%s", destination_path)
            raise PdfSaveError("แยกหน้า PDF ไม่สำเร็จ", detail=str(exc)) from exc
        finally:
            if not output.is_closed:
                output.close()
            if temp_output_path.exists():
                temp_output_path.unlink(missing_ok=True)
        LOGGER.info("extracted page index=%s destination=%s", page_index, destination_path)
        return destination_path


def merge_pdfs(source_paths: list[Path], destination_path: Path) -> Path:
    """Merge multiple PDF files into a new PDF safely."""
    if len(source_paths) < 2:
        raise InvalidOperationError("กรุณาเลือก PDF อย่างน้อย 2 ไฟล์สำหรับรวม")
    for source_path in source_paths:
        require_pdf_path(source_path)

    destination_path = _ensure_pdf_suffix(destination_path)
    temp_output_path = make_temp_output_path(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    output = fitz.open()
    try:
        for source_path in source_paths:
            with fitz.open(str(source_path)) as source:
                output.insert_pdf(source)
        output.save(str(temp_output_path), garbage=4, deflate=True)
        output.close()
        _verify_pdf(temp_output_path)
        shutil.copy2(temp_output_path, destination_path)
    except Exception as exc:
        LOGGER.exception("merge pdf failed destination=%s", destination_path)
        raise PdfSaveError("รวมไฟล์ PDF ไม่สำเร็จ", detail=str(exc)) from exc
    finally:
        if not output.is_closed:
            output.close()
        if temp_output_path.exists():
            temp_output_path.unlink(missing_ok=True)
    LOGGER.info("merged pdfs count=%s destination=%s", len(source_paths), destination_path)
    return destination_path


def _ensure_pdf_suffix(path: Path) -> Path:
    if path.suffix.lower() != ".pdf":
        return path.with_suffix(".pdf")
    return path


def _verify_pdf(path: Path) -> None:
    with fitz.open(str(path)) as document:
        if document.page_count <= 0:
            raise PdfSaveError("ไฟล์ PDF ที่สร้างไม่มีหน้า")
