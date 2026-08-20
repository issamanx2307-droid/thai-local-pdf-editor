# -*- coding: utf-8 -*-
"""Local JSON worker for the future React desktop shell."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from thai_pdf_editor.app.config import TEMP_DIR
from thai_pdf_editor.app.constants import DEFAULT_ZOOM
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.export_operations import (
    DEFAULT_JPG_DPI,
    DEFAULT_JPG_QUALITY,
    JPG_EXPORT_SCOPE_CURRENT,
    batch_export_pdfs_as_jpg,
    export_pdf_as_jpg,
    resolve_jpg_page_indices,
)
from thai_pdf_editor.app.core.form_operations import editable_form_fields, update_form_fields
from thai_pdf_editor.app.core.metadata_operations import editable_metadata, update_metadata
from thai_pdf_editor.app.core.overlay_operations import (
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_SHAPE_COLOR,
    DEFAULT_TEXT_COLOR,
    create_redact_operation,
    create_highlight_operation,
    create_image_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.page_operations import PageOperations, merge_pdfs
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.core.pdf_search import search_pdf_text
from thai_pdf_editor.app.core.print_operations import get_default_printer, list_printers, open_printer_queue, print_pdf
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.core.signature_operations import create_visual_signature_image
from thai_pdf_editor.app.core.text_edit_operations import (
    TEXT_REPLACE_SCOPE_CURRENT,
    create_replace_text_operations,
    resolve_text_replace_page_indices,
)
from thai_pdf_editor.app.core.undo_redo import redo_last_pending, undo_last_pending
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.worker_contract import (
    COMMAND_ADD_HIGHLIGHT_OVERLAY,
    COMMAND_ADD_IMAGE_OVERLAY,
    COMMAND_ADD_REDACTION_OVERLAY,
    COMMAND_ADD_TEXT_OVERLAY,
    COMMAND_BATCH,
    COMMAND_BATCH_EXPORT_JPG,
    COMMAND_CLOSE_DOCUMENT,
    COMMAND_CROP_PAGE,
    COMMAND_CREATE_VISUAL_SIGNATURE,
    COMMAND_DELETE_PAGE,
    COMMAND_DRAW_RECTANGLE_OVERLAY,
    COMMAND_DUPLICATE_PAGE,
    COMMAND_EXPORT_JPG,
    COMMAND_EXTRACT_PAGE,
    COMMAND_GO_TO_PAGE,
    COMMAND_LIST_FORM_FIELDS,
    COMMAND_LIST_METADATA,
    COMMAND_LIST_PRINTERS,
    COMMAND_MERGE_PDFS,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_OPEN_PRINTER_QUEUE,
    COMMAND_PRINT_PDF,
    COMMAND_RENDER_PAGE,
    COMMAND_REDO_PENDING,
    COMMAND_REPLACE_TEXT,
    COMMAND_ROTATE_PAGE,
    COMMAND_SAVE_COPY,
    COMMAND_SEARCH_TEXT,
    COMMAND_UNDO_PENDING,
    COMMAND_UPDATE_FORM_FIELDS,
    COMMAND_UPDATE_METADATA,
    error_response,
    state_payload,
    success_response,
)


class PdfWorkerSession:
    """Stateful local PDF worker used by CLI tests and future React IPC."""

    def __init__(self, *, preview_dir: Path | None = None) -> None:
        self.state = DocumentState()
        self.document = PdfDocument(self.state)
        self.renderer = PdfRenderer()
        self.page_operations = PageOperations(self.document, self.state)
        self.save_manager = SaveManager()
        self.preview_dir = preview_dir or TEMP_DIR / "react_worker_previews"
        self.preview_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        """Close the open document and clean up the working copy."""
        self.document.close()

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle one command request and return a JSON-safe response."""
        command = str(request.get("command", ""))
        if command == COMMAND_BATCH:
            return self._handle_batch(request)
        try:
            payload = request.get("payload") or {}
            if command == COMMAND_OPEN_PDF:
                return self._open_pdf(payload)
            if command == COMMAND_RENDER_PAGE:
                return self._render_page(payload)
            if command == COMMAND_GO_TO_PAGE:
                return self._go_to_page(payload)
            if command == COMMAND_LIST_METADATA:
                return self._list_metadata()
            if command == COMMAND_UPDATE_METADATA:
                return self._update_metadata(payload)
            if command == COMMAND_LIST_FORM_FIELDS:
                return self._list_form_fields()
            if command == COMMAND_UPDATE_FORM_FIELDS:
                return self._update_form_fields(payload)
            if command == COMMAND_LIST_PRINTERS:
                return self._list_printers()
            if command == COMMAND_OPEN_PRINTER_QUEUE:
                return self._open_printer_queue(payload)
            if command == COMMAND_MERGE_PDFS:
                return self._merge_pdfs(payload)
            if command == COMMAND_MOVE_PAGE:
                return self._move_page(payload)
            if command == COMMAND_ROTATE_PAGE:
                return self._rotate_page(payload)
            if command == COMMAND_DUPLICATE_PAGE:
                return self._duplicate_page(payload)
            if command == COMMAND_EXTRACT_PAGE:
                return self._extract_page(payload)
            if command == COMMAND_DELETE_PAGE:
                return self._delete_page(payload)
            if command == COMMAND_SEARCH_TEXT:
                return self._search_text(payload)
            if command == COMMAND_REPLACE_TEXT:
                return self._replace_text(payload)
            if command == COMMAND_ADD_TEXT_OVERLAY:
                return self._add_text_overlay(payload)
            if command == COMMAND_DRAW_RECTANGLE_OVERLAY:
                return self._draw_rectangle_overlay(payload)
            if command == COMMAND_ADD_HIGHLIGHT_OVERLAY:
                return self._add_highlight_overlay(payload)
            if command == COMMAND_ADD_REDACTION_OVERLAY:
                return self._add_redaction_overlay(payload)
            if command == COMMAND_ADD_IMAGE_OVERLAY:
                return self._add_image_overlay(payload)
            if command == COMMAND_CREATE_VISUAL_SIGNATURE:
                return self._create_visual_signature(payload)
            if command == COMMAND_CROP_PAGE:
                return self._crop_page(payload)
            if command == COMMAND_EXPORT_JPG:
                return self._export_jpg(payload)
            if command == COMMAND_BATCH_EXPORT_JPG:
                return self._batch_export_jpg(payload)
            if command == COMMAND_SAVE_COPY:
                return self._save_copy(payload)
            if command == COMMAND_PRINT_PDF:
                return self._print_pdf(payload)
            if command == COMMAND_UNDO_PENDING:
                return self._undo_pending()
            if command == COMMAND_REDO_PENDING:
                return self._redo_pending()
            if command == COMMAND_CLOSE_DOCUMENT:
                return self._close_document()
            raise InvalidOperationError("คำสั่ง worker ไม่ถูกต้อง", detail=f"unknown command: {command}")
        except Exception as exc:
            return error_response(command, self.state, exc)

    def _handle_batch(self, request: dict[str, Any]) -> dict[str, Any]:
        commands = request.get("commands") or []
        responses = []
        for item in commands:
            if not isinstance(item, dict):
                responses.append(error_response(COMMAND_BATCH, self.state, InvalidOperationError("คำสั่ง worker ไม่ถูกต้อง")))
                continue
            responses.append(self.handle(item))
            if responses[-1].get("ok") is False:
                break
        return {
            "ok": all(response.get("ok") is True for response in responses),
            "command": COMMAND_BATCH,
            "state": state_payload(self.state),
            "responses": responses,
        }

    def _open_pdf(self, payload: dict[str, Any]) -> dict[str, Any]:
        path_text = str(payload.get("path") or "")
        if not path_text:
            raise InvalidOperationError("กรุณาเลือกไฟล์ PDF")
        password_text = str(payload.get("password") or "").strip() or None
        self.renderer.clear_cache()
        self.document.open(Path(path_text), password=password_text)
        return success_response(COMMAND_OPEN_PDF, self.state, {"path": str(self.state.current_file_path)})

    def _render_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        page_index = _int_payload(payload, "page_index", self.state.current_page_index)
        zoom = _float_payload(payload, "zoom", self.state.zoom_level or DEFAULT_ZOOM)
        self._set_current_page_or_raise(page_index)
        self.state.zoom_level = round(zoom, 2)
        rendered = self.renderer.render_page(
            self.document.raw,
            self.state.working_copy_path,
            self.state.current_page_index,
            self.state.zoom_level,
            self.state.dirty_version,
            self.state.pending_operations,
        )
        preview_path = self._preview_path(page_index=self.state.current_page_index, zoom=self.state.zoom_level)
        rendered.image.save(preview_path)
        return success_response(
            COMMAND_RENDER_PAGE,
            self.state,
            {
                "preview_path": str(preview_path),
                "image_width": rendered.logical_width,
                "image_height": rendered.logical_height,
                "page_width": rendered.page_width,
                "page_height": rendered.page_height,
            },
        )

    def _go_to_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        page_index = _int_payload(payload, "page_index", self.state.current_page_index)
        self._set_current_page_or_raise(page_index)
        return success_response(COMMAND_GO_TO_PAGE, self.state)

    def _list_metadata(self) -> dict[str, Any]:
        self._require_document()
        return success_response(
            COMMAND_LIST_METADATA,
            self.state,
            {
                "metadata": editable_metadata(self.document.raw),
            },
        )

    def _update_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        raw_updates = payload.get("updates") or payload.get("metadata") or {}
        if not isinstance(raw_updates, dict):
            raise InvalidOperationError("ข้อมูล metadata ไม่ถูกต้อง")
        operation = update_metadata(self.document.raw, self.state, raw_updates)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_UPDATE_METADATA,
            self.state,
            {
                "operation_id": operation.id,
                "metadata": editable_metadata(self.document.raw),
            },
        )

    def _list_form_fields(self) -> dict[str, Any]:
        self._require_document()
        fields = editable_form_fields(self.document.raw)
        return success_response(
            COMMAND_LIST_FORM_FIELDS,
            self.state,
            {
                "fields": [
                    {
                        "xref": field.xref,
                        "page_index": field.page_index,
                        "name": field.name,
                        "field_type": field.field_type,
                        "field_type_label": field.field_type_label,
                        "value": field.value,
                        "is_checkbox": field.is_checkbox,
                    }
                    for field in fields
                ],
            },
        )

    def _update_form_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        raw_updates = payload.get("updates") or {}
        if not isinstance(raw_updates, dict):
            raise InvalidOperationError("ข้อมูลฟอร์มไม่ถูกต้อง")
        updates = {int(xref): value for xref, value in raw_updates.items()}
        operation = update_form_fields(self.document.raw, self.state, updates)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_UPDATE_FORM_FIELDS,
            self.state,
            {
                "operation_id": operation.id,
                "changed_xrefs": list(operation.payload.get("changed_xrefs", [])),
                "fields": [
                    {
                        "xref": field.xref,
                        "page_index": field.page_index,
                        "name": field.name,
                        "field_type": field.field_type,
                        "field_type_label": field.field_type_label,
                        "value": field.value,
                        "is_checkbox": field.is_checkbox,
                    }
                    for field in editable_form_fields(self.document.raw)
                ],
            },
        )

    def _list_printers(self) -> dict[str, Any]:
        printers = list_printers()
        default_printer = get_default_printer()
        return success_response(
            COMMAND_LIST_PRINTERS,
            self.state,
            {
                "printers": printers,
                "default_printer": default_printer,
            },
        )

    def _merge_pdfs(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_paths = payload.get("source_paths") or []
        if not isinstance(raw_paths, list):
            raise InvalidOperationError("กรุณาเลือก PDF อย่างน้อย 2 ไฟล์สำหรับรวม")
        source_paths = [Path(str(path_text)) for path_text in raw_paths if str(path_text).strip()]
        destination_text = str(payload.get("destination_path") or "").strip()
        destination_path = Path(destination_text) if destination_text else self._default_merge_output_path(source_paths)

        merged_path = merge_pdfs(source_paths, destination_path)
        self.renderer.clear_cache()
        self.document.open(merged_path)
        return success_response(
            COMMAND_MERGE_PDFS,
            self.state,
            {
                "destination_path": str(merged_path),
                "file_name": merged_path.name,
                "source_count": len(source_paths),
            },
        )

    def _print_pdf(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        printer_name = str(payload.get("printer_name") or "").strip()
        copies = max(1, min(99, _int_payload(payload, "copies", 1)))
        pages_text = str(payload.get("pages") or "").strip() or None
        source_path = self.state.working_copy_path or self.state.current_file_path
        if source_path is None:
            raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")

        print_pdf(source_path, printer_name, copies=copies, pages=pages_text)
        return success_response(
            COMMAND_PRINT_PDF,
            self.state,
            {
                "printer_name": printer_name,
                "copies": copies,
                "pages": pages_text,
                "source_path": str(source_path),
            },
        )

    def _open_printer_queue(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Open the selected printer's Windows queue without requiring a PDF."""
        printer_name = str(payload.get("printer_name") or "").strip()
        open_printer_queue(printer_name)
        return success_response(
            COMMAND_OPEN_PRINTER_QUEUE,
            self.state,
            {"printer_name": printer_name},
        )

    def _undo_pending(self) -> dict[str, Any]:
        self._require_document()
        operation = undo_last_pending(self.state)
        page_index = int(getattr(operation, "page_index", self.state.current_page_index))
        if 0 <= page_index < self.state.total_pages:
            self.state.set_current_page(page_index)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_UNDO_PENDING,
            self.state,
            {
                "operation_id": getattr(operation, "id", ""),
                "page_index": getattr(operation, "page_index", self.state.current_page_index),
                "pending_count": len(self.state.pending_operations),
            },
        )

    def _redo_pending(self) -> dict[str, Any]:
        self._require_document()
        operation = redo_last_pending(self.state)
        page_index = int(getattr(operation, "page_index", self.state.current_page_index))
        if 0 <= page_index < self.state.total_pages:
            self.state.set_current_page(page_index)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_REDO_PENDING,
            self.state,
            {
                "operation_id": getattr(operation, "id", ""),
                "page_index": getattr(operation, "page_index", self.state.current_page_index),
                "pending_count": len(self.state.pending_operations),
            },
        )

    def _move_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))
        before_index = self.state.current_page_index
        delta = _int_payload(payload, "delta", 0)
        if delta not in (-1, 1):
            raise InvalidOperationError("คำสั่งย้ายหน้าต้องเป็นขึ้นหรือลง")
        operation = self.page_operations.move_current_page(delta)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_MOVE_PAGE,
            self.state,
            {
                "from_page_index": before_index,
                "to_page_index": self.state.current_page_index,
                "operation_id": operation.id,
            },
        )

    def _rotate_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))
        degrees = _int_payload(payload, "degrees", 90)
        if degrees not in (-90, 90, 180):
            raise InvalidOperationError("คำสั่งหมุนหน้าต้องเป็น -90, 90 หรือ 180 องศา")
        before_rotation = self.document.get_page(self.state.current_page_index).rotation
        operation = self.page_operations.rotate_current_page(degrees)
        after_rotation = self.document.get_page(self.state.current_page_index).rotation
        self.renderer.clear_cache()
        return success_response(
            COMMAND_ROTATE_PAGE,
            self.state,
            {
                "page_index": self.state.current_page_index,
                "degrees": degrees,
                "before_rotation": before_rotation,
                "after_rotation": after_rotation,
                "operation_id": operation.id,
            },
        )

    def _duplicate_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))
        operation = self.page_operations.duplicate_current_page()
        self.renderer.clear_cache()
        return success_response(
            COMMAND_DUPLICATE_PAGE,
            self.state,
            {
                "source_page_index": operation.payload.get("source_page"),
                "duplicated_page_index": operation.payload.get("duplicated_page"),
                "operation_id": operation.id,
            },
        )

    def _extract_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        destination_text = str(payload.get("destination_path") or "").strip()
        destination_path = Path(destination_text) if destination_text else self._default_extract_output_path()
        extracted_path = self.page_operations.extract_current_page(destination_path)
        return success_response(
            COMMAND_EXTRACT_PAGE,
            self.state,
            {
                "destination_path": str(extracted_path),
                "file_name": extracted_path.name,
                "page_index": self.state.current_page_index,
            },
        )

    def _delete_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))
        operation = self.page_operations.delete_current_page()
        self.renderer.clear_cache()
        return success_response(
            COMMAND_DELETE_PAGE,
            self.state,
            {
                "deleted_page_index": operation.payload.get("deleted_page"),
                "operation_id": operation.id,
            },
        )

    def _search_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        query = str(payload.get("query") or "").strip()
        results = search_pdf_text(self.document.raw, query)
        self._set_current_page_or_raise(results[0].page_index)
        return success_response(
            COMMAND_SEARCH_TEXT,
            self.state,
            {
                "query": query,
                "count": len(results),
                "results": [
                    {
                        "page_index": result.page_index,
                        "match_index": result.match_index,
                        "rect": list(result.rect),
                        "label": result.label,
                    }
                    for result in results
                ],
            },
        )

    def _replace_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        page_scope = str(payload.get("page_scope") or TEXT_REPLACE_SCOPE_CURRENT)
        page_indices = resolve_text_replace_page_indices(
            page_scope,
            self.state.current_page_index,
            self.state.total_pages,
        )
        font_path_text = str(payload.get("font_path") or "").strip()
        operations = create_replace_text_operations(
            self.document.raw,
            page_indices=page_indices,
            search_text=str(payload.get("search_text") or ""),
            replacement_text=str(payload.get("replacement_text") or ""),
            font_size=max(6, min(96, _int_payload(payload, "font_size", 16))),
            color=_color_payload(payload.get("color"), DEFAULT_TEXT_COLOR),
            font_path=Path(font_path_text) if font_path_text else None,
        )
        for operation in operations:
            self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_REPLACE_TEXT,
            self.state,
            {
                "operation_ids": [operation.id for operation in operations],
                "operation_count": len(operations),
                "page_indices": list(page_indices),
                "pending_count": len(self.state.pending_operations),
            },
        )

    def _add_text_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        page = self.document.raw.load_page(self.state.current_page_index)
        default_x = max(24.0, min(48.0, page.rect.width - 96.0))
        default_y = max(32.0, min(72.0, page.rect.height - 48.0))
        font_size = max(6, min(96, _int_payload(payload, "font_size", 16)))
        operation = create_text_operation(
            page_index=self.state.current_page_index,
            point=PdfPoint(
                _float_payload(payload, "x", default_x),
                _float_payload(payload, "y", default_y),
            ),
            text=str(payload.get("text") or ""),
            font_size=font_size,
            color=_color_payload(payload.get("color"), DEFAULT_TEXT_COLOR),
            font_path=None,
        )
        operation.validate(self.state.total_pages)
        self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_ADD_TEXT_OVERLAY,
            self.state,
            {
                "operation_id": operation.id,
                "page_index": operation.page_index,
                "text": operation.payload.get("text"),
            },
        )

    def _draw_rectangle_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        operation = create_rectangle_operation(
            page_index=self.state.current_page_index,
            rect=self._overlay_rect(payload),
            color=_color_payload(payload.get("color"), DEFAULT_SHAPE_COLOR),
            line_width=max(1.0, min(24.0, _float_payload(payload, "line_width", 2.0))),
        )
        operation.validate(self.state.total_pages)
        self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return self._overlay_response(COMMAND_DRAW_RECTANGLE_OVERLAY, operation)

    def _add_highlight_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        operation = create_highlight_operation(
            page_index=self.state.current_page_index,
            rect=self._overlay_rect(payload),
            color=_color_payload(payload.get("color"), DEFAULT_HIGHLIGHT_COLOR),
        )
        operation.validate(self.state.total_pages)
        self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return self._overlay_response(COMMAND_ADD_HIGHLIGHT_OVERLAY, operation)

    def _add_redaction_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        operation = create_redact_operation(
            page_index=self.state.current_page_index,
            rect=self._overlay_rect(payload),
        )
        operation.validate(self.state.total_pages)
        self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return self._overlay_response(COMMAND_ADD_REDACTION_OVERLAY, operation)

    def _add_image_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        image_path_text = str(payload.get("image_path") or "").strip()
        if not image_path_text:
            raise InvalidOperationError("กรุณาเลือกรูปภาพหรือลายเซ็นภาพก่อนวางลง PDF")

        page = self.document.raw.load_page(self.state.current_page_index)
        width = max(8.0, min(page.rect.width - 24.0, _float_payload(payload, "width", 140.0)))
        operation = create_image_operation(
            page_index=self.state.current_page_index,
            point=PdfPoint(
                _float_payload(payload, "x", min(72.0, max(24.0, page.rect.width - width - 24.0))),
                _float_payload(payload, "y", min(220.0, max(32.0, page.rect.height - 96.0))),
            ),
            image_path=Path(image_path_text),
            width=width,
        )
        operation.validate(self.state.total_pages)
        self.state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_ADD_IMAGE_OVERLAY,
            self.state,
            {
                "operation_id": operation.id,
                "page_index": operation.page_index,
                "image_path": operation.payload.get("image_path"),
                "width": operation.payload.get("width"),
                "height": operation.payload.get("height"),
            },
        )

    def _create_visual_signature(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        width_px = max(240, min(1600, _int_payload(payload, "width_px", 720)))
        image_path = create_visual_signature_image(
            text,
            width_px=width_px,
            color=_color_payload(payload.get("color"), "#1565c0"),
        )
        return success_response(
            COMMAND_CREATE_VISUAL_SIGNATURE,
            self.state,
            {
                "image_path": str(image_path),
                "file_name": image_path.name,
            },
        )

    def _crop_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        page = self.document.raw.load_page(self.state.current_page_index)
        operation = self.page_operations.crop_current_page(_crop_rect_from_payload(page.rect, payload))
        self.renderer.clear_cache()
        return success_response(
            COMMAND_CROP_PAGE,
            self.state,
            {
                "operation_id": operation.id,
                "page_index": operation.page_index,
                "before_cropbox": list(operation.payload.get("before_cropbox", ())),
                "after_cropbox": list(operation.payload.get("after_cropbox", ())),
            },
        )

    def _export_jpg(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        selected_page_index = payload.get("selected_page_index")
        if selected_page_index is not None:
            self._set_current_page_or_raise(int(selected_page_index))

        page_scope = str(payload.get("page_scope") or JPG_EXPORT_SCOPE_CURRENT)
        page_indices = resolve_jpg_page_indices(page_scope, self.state.current_page_index, self.state.total_pages)
        destination_text = str(payload.get("destination_dir") or "").strip()
        destination_dir = Path(destination_text) if destination_text else self._default_jpg_export_dir()
        output_paths = export_pdf_as_jpg(
            self.document.raw,
            self.state,
            destination_dir,
            page_indices=page_indices,
            dpi=_int_payload(payload, "dpi", DEFAULT_JPG_DPI),
            quality=_int_payload(payload, "quality", DEFAULT_JPG_QUALITY),
        )
        return success_response(
            COMMAND_EXPORT_JPG,
            self.state,
            {
                "destination_dir": str(destination_dir),
                "output_paths": [str(path) for path in output_paths],
                "file_names": [path.name for path in output_paths],
                "count": len(output_paths),
                "page_scope": page_scope,
            },
        )

    def _batch_export_jpg(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_values = payload.get("source_paths") or []
        if not isinstance(source_values, list):
            raise InvalidOperationError("กรุณาเลือก PDF อย่างน้อย 1 ไฟล์")

        source_paths = [Path(str(value)) for value in source_values if str(value).strip()]
        destination_text = str(payload.get("destination_dir") or "").strip()
        destination_dir = Path(destination_text) if destination_text else self._default_batch_jpg_export_dir()
        report = batch_export_pdfs_as_jpg(
            source_paths,
            destination_dir,
            dpi=_int_payload(payload, "dpi", DEFAULT_JPG_DPI),
            quality=_int_payload(payload, "quality", DEFAULT_JPG_QUALITY),
        )
        output_paths = _flatten_report_output_paths(report)
        return success_response(
            COMMAND_BATCH_EXPORT_JPG,
            self.state,
            {
                **report,
                "source_count": len(source_paths),
                "output_paths": [str(path) for path in output_paths],
                "file_names": [path.name for path in output_paths],
                "count": len(output_paths),
            },
        )

    def _save_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        destination_text = str(payload.get("destination_path") or "").strip()
        destination_path = Path(destination_text) if destination_text else self._default_save_copy_path()
        saved_path = self.save_manager.save_as(self.document.raw, self.state, destination_path)
        self.renderer.clear_cache()
        return success_response(
            COMMAND_SAVE_COPY,
            self.state,
            {
                "destination_path": str(saved_path),
                "file_name": saved_path.name,
            },
        )

    def _close_document(self) -> dict[str, Any]:
        self.close()
        self.renderer.clear_cache()
        return success_response(COMMAND_CLOSE_DOCUMENT, self.state)

    def _require_document(self) -> None:
        if not self.state.has_document:
            raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")

    def _set_current_page_or_raise(self, page_index: int) -> None:
        if not 0 <= page_index < self.state.total_pages:
            raise InvalidOperationError("เลขหน้าที่เลือกไม่ถูกต้อง")
        self.state.set_current_page(page_index)

    def _overlay_rect(self, payload: dict[str, Any]) -> PdfRect:
        page = self.document.raw.load_page(self.state.current_page_index)
        default_width = min(220.0, max(80.0, page.rect.width * 0.36))
        default_height = min(96.0, max(36.0, page.rect.height * 0.11))
        default_x = min(72.0, max(24.0, page.rect.width - default_width - 24.0))
        default_y = min(160.0, max(32.0, page.rect.height - default_height - 32.0))
        x0 = _float_payload(payload, "x", default_x)
        y0 = _float_payload(payload, "y", default_y)
        width = max(8.0, _float_payload(payload, "width", default_width))
        height = max(8.0, _float_payload(payload, "height", default_height))
        x1 = min(page.rect.width - 1.0, x0 + width)
        y1 = min(page.rect.height - 1.0, y0 + height)
        return PdfRect(x0=x0, y0=y0, x1=x1, y1=y1)

    def _overlay_response(self, command: str, operation: object) -> dict[str, Any]:
        payload = getattr(operation, "payload", {})
        rect = payload.get("rect", ()) if isinstance(payload, dict) else ()
        return success_response(
            command,
            self.state,
            {
                "operation_id": getattr(operation, "id", ""),
                "page_index": getattr(operation, "page_index", self.state.current_page_index),
                "rect": list(rect),
            },
        )

    def _preview_path(self, *, page_index: int, zoom: float) -> Path:
        stem = Path(str(self.state.current_file_path or "document")).stem
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48]
        zoom_label = int(round(zoom * 100))
        return self.preview_dir / f"{safe_stem}_p{page_index + 1:04d}_z{zoom_label}_v{self.state.dirty_version}.png"

    def _default_save_copy_path(self) -> Path:
        stem = Path(str(self.state.current_file_path or "document")).stem
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48] or "document"
        output_dir = TEMP_DIR / "react_bridge_saves"
        output_dir.mkdir(parents=True, exist_ok=True)
        candidate = output_dir / f"{safe_stem}_react_saved.pdf"
        suffix = 1
        while candidate.exists():
            candidate = output_dir / f"{safe_stem}_react_saved_{suffix:03d}.pdf"
            suffix += 1
        return candidate

    def _default_merge_output_path(self, source_paths: list[Path]) -> Path:
        stem = source_paths[0].stem if source_paths else "merged"
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48] or "merged"
        output_dir = TEMP_DIR / "react_bridge_merges"
        output_dir.mkdir(parents=True, exist_ok=True)
        candidate = output_dir / f"{safe_stem}_merged.pdf"
        suffix = 1
        while candidate.exists():
            candidate = output_dir / f"{safe_stem}_merged_{suffix:03d}.pdf"
            suffix += 1
        return candidate

    def _default_extract_output_path(self) -> Path:
        stem = Path(str(self.state.current_file_path or "document")).stem
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48] or "document"
        output_dir = TEMP_DIR / "react_bridge_extracts"
        output_dir.mkdir(parents=True, exist_ok=True)
        page_label = self.state.current_page_index + 1
        candidate = output_dir / f"{safe_stem}_page_{page_label:04d}.pdf"
        suffix = 1
        while candidate.exists():
            candidate = output_dir / f"{safe_stem}_page_{page_label:04d}_{suffix:03d}.pdf"
            suffix += 1
        return candidate

    def _default_jpg_export_dir(self) -> Path:
        stem = Path(str(self.state.current_file_path or "document")).stem
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48] or "document"
        output_dir = TEMP_DIR / "react_bridge_jpg_exports" / safe_stem
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _default_batch_jpg_export_dir(self) -> Path:
        base_dir = TEMP_DIR / "react_bridge_batch_jpg_exports"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = base_dir / f"batch_{stamp}"
        suffix = 1
        while output_dir.exists():
            output_dir = base_dir / f"batch_{stamp}_{suffix:02d}"
            suffix += 1
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


def run_request(request: dict[str, Any], *, preview_dir: Path | None = None) -> dict[str, Any]:
    """Run a request in a temporary worker session."""
    session = PdfWorkerSession(preview_dir=preview_dir)
    try:
        return session.handle(request)
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for one-shot JSON requests."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Thai PDF Editor local worker")
    parser.add_argument("--request-json", help="JSON request string")
    parser.add_argument("--request-file", help="Path to a UTF-8 JSON request file")
    parser.add_argument("--preview-dir", help="Directory for rendered preview images")
    args = parser.parse_args(argv)

    request = _load_request(args)
    response = run_request(request, preview_dir=Path(args.preview_dir) if args.preview_dir else None)
    print(json.dumps(response, ensure_ascii=False))
    return 0 if response.get("ok") else 1


def _load_request(args: argparse.Namespace) -> dict[str, Any]:
    if args.request_json:
        return json.loads(args.request_json)
    if args.request_file:
        return json.loads(Path(args.request_file).read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def _crop_rect_from_payload(page_rect: Any, payload: dict[str, Any]) -> PdfRect:
    if any(key in payload for key in ("x", "y", "width", "height")):
        x0 = _float_payload(payload, "x", float(page_rect.x0))
        y0 = _float_payload(payload, "y", float(page_rect.y0))
        width = max(20.0, _float_payload(payload, "width", float(page_rect.width)))
        height = max(20.0, _float_payload(payload, "height", float(page_rect.height)))
        return PdfRect(x0=x0, y0=y0, x1=x0 + width, y1=y0 + height)

    margin_percent = max(0.0, min(45.0, _float_payload(payload, "margin_percent", 8.0)))
    margin_x = float(page_rect.width) * margin_percent / 100.0
    margin_y = float(page_rect.height) * margin_percent / 100.0
    return PdfRect(
        x0=float(page_rect.x0) + margin_x,
        y0=float(page_rect.y0) + margin_y,
        x1=float(page_rect.x1) - margin_x,
        y1=float(page_rect.y1) - margin_y,
    )


def _int_payload(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    return int(value)


def _flatten_report_output_paths(report: dict[str, object]) -> list[Path]:
    items = report.get("items")
    if not isinstance(items, list):
        return []

    output_paths: list[Path] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paths = item.get("output_paths")
        if not isinstance(paths, list):
            continue
        output_paths.extend(Path(str(path)) for path in paths if str(path).strip())
    return output_paths


def _float_payload(payload: dict[str, Any], key: str, default: float) -> float:
    value = payload.get(key, default)
    return float(value)


def _color_payload(value: object, default: str) -> str:
    clean = str(value or default).strip().lstrip("#")
    if len(clean) == 6 and all(char in "0123456789abcdefABCDEF" for char in clean):
        return f"#{clean}"
    return default


if __name__ == "__main__":
    raise SystemExit(main())
