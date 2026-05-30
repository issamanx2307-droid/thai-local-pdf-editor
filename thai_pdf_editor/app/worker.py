# -*- coding: utf-8 -*-
"""Local JSON worker for the future React desktop shell."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thai_pdf_editor.app.config import TEMP_DIR
from thai_pdf_editor.app.constants import DEFAULT_ZOOM
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.overlay_operations import (
    DEFAULT_HIGHLIGHT_COLOR,
    DEFAULT_SHAPE_COLOR,
    DEFAULT_TEXT_COLOR,
    create_highlight_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.core.pdf_search import search_pdf_text
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.worker_contract import (
    COMMAND_ADD_HIGHLIGHT_OVERLAY,
    COMMAND_ADD_TEXT_OVERLAY,
    COMMAND_BATCH,
    COMMAND_CLOSE_DOCUMENT,
    COMMAND_DELETE_PAGE,
    COMMAND_DRAW_RECTANGLE_OVERLAY,
    COMMAND_DUPLICATE_PAGE,
    COMMAND_GO_TO_PAGE,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
    COMMAND_SAVE_COPY,
    COMMAND_SEARCH_TEXT,
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
            if command == COMMAND_MOVE_PAGE:
                return self._move_page(payload)
            if command == COMMAND_DUPLICATE_PAGE:
                return self._duplicate_page(payload)
            if command == COMMAND_DELETE_PAGE:
                return self._delete_page(payload)
            if command == COMMAND_SEARCH_TEXT:
                return self._search_text(payload)
            if command == COMMAND_ADD_TEXT_OVERLAY:
                return self._add_text_overlay(payload)
            if command == COMMAND_DRAW_RECTANGLE_OVERLAY:
                return self._draw_rectangle_overlay(payload)
            if command == COMMAND_ADD_HIGHLIGHT_OVERLAY:
                return self._add_highlight_overlay(payload)
            if command == COMMAND_SAVE_COPY:
                return self._save_copy(payload)
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
        self.renderer.clear_cache()
        self.document.open(Path(path_text))
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
                "image_width": rendered.image.width,
                "image_height": rendered.image.height,
                "page_width": rendered.page_width,
                "page_height": rendered.page_height,
            },
        )

    def _go_to_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_document()
        page_index = _int_payload(payload, "page_index", self.state.current_page_index)
        self._set_current_page_or_raise(page_index)
        return success_response(COMMAND_GO_TO_PAGE, self.state)

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


def _int_payload(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    return int(value)


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
