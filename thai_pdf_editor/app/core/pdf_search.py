# -*- coding: utf-8 -*-
"""Text-layer PDF search helpers."""

from __future__ import annotations

from dataclasses import dataclass

import fitz

from thai_pdf_editor.app.core.errors import InvalidOperationError


@dataclass(frozen=True)
class PdfSearchResult:
    """One text-layer search match in a PDF."""

    page_index: int
    match_index: int
    rect: tuple[float, float, float, float]
    label: str


def search_pdf_text(document: fitz.Document, query: str) -> list[PdfSearchResult]:
    """Search PDF text layer only; OCR/image text is intentionally unsupported."""
    clean_query = str(query or "").strip()
    if not clean_query:
        raise InvalidOperationError("กรุณากรอกข้อความที่ต้องการค้นหา")

    results: list[PdfSearchResult] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        matches = page.search_for(clean_query)
        for match_index, rect in enumerate(matches, start=1):
            results.append(
                PdfSearchResult(
                    page_index=page_index,
                    match_index=match_index,
                    rect=(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
                    label=f"หน้า {page_index + 1} - พบครั้งที่ {match_index}",
                )
            )
    if not results:
        raise InvalidOperationError("ไม่พบข้อความที่ค้นหาใน text layer ของ PDF")
    return results


def next_search_index(current_index: int, total_results: int) -> int:
    """Return the next search-result index with wraparound."""
    if total_results <= 0:
        raise InvalidOperationError("ยังไม่มีผลการค้นหา")
    return (current_index + 1) % total_results


def previous_search_index(current_index: int, total_results: int) -> int:
    """Return the previous search-result index with wraparound."""
    if total_results <= 0:
        raise InvalidOperationError("ยังไม่มีผลการค้นหา")
    return (current_index - 1) % total_results


def scaled_search_rect(rect: tuple[float, float, float, float], zoom: float) -> tuple[float, float, float, float]:
    """Scale a PDF search rectangle into preview-canvas coordinates."""
    safe_zoom = max(float(zoom), 0.01)
    x0, y0, x1, y1 = rect
    return (x0 * safe_zoom, y0 * safe_zoom, x1 * safe_zoom, y1 * safe_zoom)
