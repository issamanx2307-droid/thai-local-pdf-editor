# -*- coding: utf-8 -*-
"""Safe existing-text replacement helpers."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import fitz

from thai_pdf_editor.app.core.errors import FontError, InvalidOperationError
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font
from thai_pdf_editor.app.utils.validation import require_page_index

TEXT_REPLACE_SCOPE_ALL = "all"
TEXT_REPLACE_SCOPE_CURRENT = "current"
TEXT_REPLACE_FILL_COLOR = "#ffffff"
TEXT_REPLACE_PADDING = 1.25


def resolve_text_replace_page_indices(page_scope: str, current_page_index: int, total_pages: int) -> list[int]:
    """Resolve the text-replacement scope to concrete page indices."""
    if page_scope == TEXT_REPLACE_SCOPE_ALL:
        return list(range(total_pages))
    if page_scope == TEXT_REPLACE_SCOPE_CURRENT:
        require_page_index(current_page_index, total_pages)
        return [current_page_index]
    raise InvalidOperationError("ตัวเลือกหน้าสำหรับแก้ข้อความไม่ถูกต้อง")


def create_replace_text_operations(
    document: fitz.Document,
    *,
    page_indices: Sequence[int],
    search_text: str,
    replacement_text: str,
    font_size: int,
    color: str,
    font_path: Path | None,
) -> list[PdfOperation]:
    """Create pending operations that redact found text and place replacement text."""
    needle = search_text.strip()
    if not needle:
        raise InvalidOperationError("กรุณากรอกข้อความเดิมที่ต้องการค้นหา")
    if document.page_count <= 0:
        raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")

    resolved_font = font_path or first_existing_thai_font()
    if replacement_text.strip() and (resolved_font is None or not resolved_font.exists()):
        raise FontError("ไม่พบฟอนต์ภาษาไทย กรุณาเลือกไฟล์ .ttf ก่อนแก้ข้อความ")

    operations: list[PdfOperation] = []
    for page_index in page_indices:
        require_page_index(page_index, document.page_count)
        page = document.load_page(page_index)
        for rect in page.search_for(needle):
            replacement_rect = _expanded_rect(page.rect, fitz.Rect(rect))
            operations.append(
                PdfOperation(
                    type=OperationType.REPLACE_TEXT,
                    page_index=page_index,
                    payload={
                        "rect": _rect_payload(replacement_rect),
                        "search_text": needle,
                        "text": replacement_text,
                        "font_size": int(font_size),
                        "color": color or "#111111",
                        "font_path": str(resolved_font) if resolved_font is not None else "",
                        "fill": TEXT_REPLACE_FILL_COLOR,
                    },
                    irreversible=True,
                )
            )

    if not operations:
        raise InvalidOperationError("ไม่พบข้อความเดิมในหน้าที่เลือก")
    return operations


def _expanded_rect(page_rect: fitz.Rect, rect: fitz.Rect) -> fitz.Rect:
    return fitz.Rect(
        max(page_rect.x0, rect.x0 - TEXT_REPLACE_PADDING),
        max(page_rect.y0, rect.y0 - TEXT_REPLACE_PADDING),
        min(page_rect.x1, rect.x1 + TEXT_REPLACE_PADDING),
        min(page_rect.y1, rect.y1 + TEXT_REPLACE_PADDING),
    )


def _rect_payload(rect: fitz.Rect) -> tuple[float, float, float, float]:
    return (rect.x0, rect.y0, rect.x1, rect.y1)
