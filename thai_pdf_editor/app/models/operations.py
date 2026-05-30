# -*- coding: utf-8 -*-
"""Operation models for page and overlay changes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from thai_pdf_editor.app.core.errors import InvalidOperationError


class OperationType(str, Enum):
    """Supported operation types."""

    ROTATE_PAGE = "rotate_page"
    DELETE_PAGE = "delete_page"
    MOVE_PAGE = "move_page"
    DUPLICATE_PAGE = "duplicate_page"
    CROP_PAGE = "crop_page"
    UPDATE_METADATA = "update_metadata"
    UPDATE_FORM_FIELDS = "update_form_fields"
    ADD_TEXT = "add_text"
    ADD_IMAGE = "add_image"
    DRAW_RECTANGLE = "draw_rectangle"
    HIGHLIGHT = "highlight"
    REDACT = "redact"
    REPLACE_TEXT = "replace_text"
    EXTRACT_PAGES = "extract_pages"
    MERGE_PDFS = "merge_pdfs"


@dataclass
class PdfOperation:
    """Generic PDF operation with payload data."""

    type: OperationType
    page_index: int
    payload: dict[str, object] = field(default_factory=dict)
    irreversible: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self, total_pages: int) -> None:
        """Validate that this operation targets an existing page."""
        if total_pages <= 0:
            raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")
        if not 0 <= self.page_index < total_pages:
            raise InvalidOperationError("เลขหน้าที่เลือกไม่ถูกต้อง")

    def undo(self) -> None:
        """Placeholder for operation-specific undo support."""
        if self.irreversible:
            raise InvalidOperationError("คำสั่งนี้ไม่สามารถย้อนกลับได้")
