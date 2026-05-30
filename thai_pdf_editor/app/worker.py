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
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.worker_contract import (
    COMMAND_BATCH,
    COMMAND_CLOSE_DOCUMENT,
    COMMAND_GO_TO_PAGE,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
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

    def _preview_path(self, *, page_index: int, zoom: float) -> Path:
        stem = Path(str(self.state.current_file_path or "document")).stem
        safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48]
        zoom_label = int(round(zoom * 100))
        return self.preview_dir / f"{safe_stem}_p{page_index + 1:04d}_z{zoom_label}_v{self.state.dirty_version}.png"


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


if __name__ == "__main__":
    raise SystemExit(main())
