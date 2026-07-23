# -*- coding: utf-8 -*-
"""PDF page rendering for preview images."""

import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from thai_pdf_editor.app.constants import PREVIEW_CACHE_SIZE
from thai_pdf_editor.app.core.errors import PdfRenderError
from thai_pdf_editor.app.core.overlay_operations import render_overlay_preview
from thai_pdf_editor.app.models.operations import PdfOperation


@dataclass
class RenderedPage:
    """Rendered PDF preview image with source page dimensions."""

    image: Image.Image
    page_width: float
    page_height: float


class PdfRenderer:
    """Render PDF pages to Pillow images with a thread-safe LRU cache."""

    def __init__(self, cache_size: int = PREVIEW_CACHE_SIZE) -> None:
        self.cache_size = cache_size
        self._cache: OrderedDict[tuple[str, int, float, int], RenderedPage] = OrderedDict()
        self._cache_lock = threading.Lock()
        # PyMuPDF (MuPDF) is not safe for concurrent calls on the same
        # fitz.Document from multiple threads. Foreground renders happen on
        # the Tk main thread while prefetch runs on background threads —
        # this lock serializes all actual page-load/pixmap calls between them.
        self._fitz_lock = threading.Lock()

    def clear_cache(self) -> None:
        """Clear all cached preview images."""
        with self._cache_lock:
            self._cache.clear()

    def render_page(
        self,
        document: fitz.Document,
        working_copy_path: Path | None,
        page_index: int,
        zoom: float,
        dirty_version: int,
        pending_operations: list[PdfOperation] | None = None,
    ) -> RenderedPage:
        """Render a PDF page at the requested zoom level (main thread)."""
        cache_key = (str(working_copy_path or ""), page_index, zoom, dirty_version)

        with self._cache_lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return self._cache[cache_key]

        try:
            with self._fitz_lock:
                page = document.load_page(page_index)
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_width = page.rect.width
                page_height = page.rect.height
        except Exception as exc:
            raise PdfRenderError("แสดงตัวอย่าง PDF ไม่สำเร็จ", detail=str(exc)) from exc

        if pending_operations:
            image = render_overlay_preview(image, pending_operations, page_index=page_index, zoom=zoom)

        rendered = RenderedPage(image=image, page_width=page_width, page_height=page_height)
        with self._cache_lock:
            self._cache[cache_key] = rendered
            self._cache.move_to_end(cache_key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
        return rendered

    def prefetch_page(
        self,
        document: fitz.Document,
        working_copy_path: Path | None,
        page_index: int,
        zoom: float,
        dirty_version: int,
        pending_operations: list[PdfOperation] | None = None,
    ) -> None:
        """Render and cache a page in a background thread.

        Uses the same live in-memory ``document`` the main thread renders
        from (rather than reopening the working copy from disk), so unsaved
        edits such as rotation are reflected correctly. Because PyMuPDF is
        not safe for concurrent calls against a single fitz.Document, every
        actual page-load/pixmap call is serialized with the main thread via
        ``_fitz_lock``.

        Failures are intentionally silent — this is best-effort only.
        """
        cache_key = (str(working_copy_path or ""), page_index, zoom, dirty_version)
        with self._cache_lock:
            if cache_key in self._cache:
                return  # already cached, nothing to do

        try:
            with self._fitz_lock:
                if not 0 <= page_index < document.page_count:
                    return
                page = document.load_page(page_index)
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_width = page.rect.width
                page_height = page.rect.height
        except Exception:
            return

        if pending_operations:
            image = render_overlay_preview(image, pending_operations, page_index=page_index, zoom=zoom)

        rendered = RenderedPage(image=image, page_width=page_width, page_height=page_height)
        with self._cache_lock:
            if cache_key not in self._cache:  # double-check under lock
                self._cache[cache_key] = rendered
                self._cache.move_to_end(cache_key)
                while len(self._cache) > self.cache_size:
                    self._cache.popitem(last=False)
