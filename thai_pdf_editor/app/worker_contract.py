# -*- coding: utf-8 -*-
"""JSON-safe contract helpers for the future React desktop shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import AppError

COMMAND_BATCH = "batch"
COMMAND_ADD_TEXT_OVERLAY = "add_text_overlay"
COMMAND_ADD_HIGHLIGHT_OVERLAY = "add_highlight_overlay"
COMMAND_ADD_IMAGE_OVERLAY = "add_image_overlay"
COMMAND_CLOSE_DOCUMENT = "close_document"
COMMAND_CREATE_VISUAL_SIGNATURE = "create_visual_signature"
COMMAND_DELETE_PAGE = "delete_page"
COMMAND_DRAW_RECTANGLE_OVERLAY = "draw_rectangle_overlay"
COMMAND_DUPLICATE_PAGE = "duplicate_page"
COMMAND_GO_TO_PAGE = "go_to_page"
COMMAND_MOVE_PAGE = "move_page"
COMMAND_OPEN_PDF = "open_pdf"
COMMAND_RENDER_PAGE = "render_page"
COMMAND_SAVE_COPY = "save_copy"
COMMAND_SEARCH_TEXT = "search_text"


def state_payload(state: DocumentState) -> dict[str, Any]:
    """Return the document state shape React can consume."""
    return {
        "has_document": state.has_document,
        "current_file_path": _path_text(state.current_file_path),
        "working_copy_path": _path_text(state.working_copy_path),
        "total_pages": state.total_pages,
        "current_page_index": state.current_page_index,
        "display_page_number": state.display_page_number,
        "zoom_level": state.zoom_level,
        "dirty": state.dirty,
        "selected_page_indices": list(state.selected_page_indices),
        "selected_tool": state.selected_tool,
    }


def success_response(command: str, state: DocumentState, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a successful worker response."""
    return {
        "ok": True,
        "command": command,
        "state": state_payload(state),
        "payload": payload or {},
    }


def error_response(command: str, state: DocumentState, exc: Exception) -> dict[str, Any]:
    """Build an error response safe for a Thai UI to display."""
    if isinstance(exc, AppError):
        message = exc.user_message
        detail = exc.detail
    else:
        message = "ไม่สามารถทำรายการได้"
        detail = str(exc)
    return {
        "ok": False,
        "command": command,
        "state": state_payload(state),
        "error": {
            "type": exc.__class__.__name__,
            "message": message,
            "detail": detail,
        },
    }


def _path_text(path: Path | None) -> str | None:
    return str(path) if path is not None else None
