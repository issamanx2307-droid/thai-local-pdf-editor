# -*- coding: utf-8 -*-
"""Milestone 1 smoke tests."""

import importlib

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.logging_config import setup_logging

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_core_imports() -> None:
    """Important modules import without side effects."""
    for module_name in [
        "thai_pdf_editor.app.main",
        "thai_pdf_editor.app.ui.main_window",
        "thai_pdf_editor.app.core.pdf_document",
        "thai_pdf_editor.app.core.pdf_renderer",
    ]:
        importlib.import_module(module_name)


def test_logging_file_is_created() -> None:
    """App logging writes to data/logs/app.log."""
    logger = setup_logging()
    logger.info("test log entry")
    from thai_pdf_editor.app.config import APP_LOG_PATH

    assert APP_LOG_PATH.exists()


def test_open_and_render_sample_pdf_with_thai_path(tmp_path) -> None:
    """Open and render a sample PDF stored under a Thai path."""
    sample_path = tmp_path / "เอกสารลูกค้า" / "ใบเสนอราคา.pdf"
    create_sample_pdf(sample_path, pages=2)

    state = DocumentState()
    document = PdfDocument(state)
    renderer = PdfRenderer()
    document.open(sample_path)

    rendered = renderer.render_page(
        document.raw,
        state.working_copy_path,
        state.current_page_index,
        state.zoom_level,
        state.dirty_version,
    )

    assert state.total_pages == 2
    assert rendered.image.width > 0
    assert rendered.image.height > 0
    document.close()


def test_renderer_cache_reuses_rendered_page_on_cache_hit(tmp_path) -> None:
    """Repeated preview renders should not copy the cached Pillow image."""
    sample_path = tmp_path / "เอกสารไทย" / "cache-test.pdf"
    create_sample_pdf(sample_path, pages=1)

    state = DocumentState()
    document = PdfDocument(state)
    renderer = PdfRenderer()
    document.open(sample_path)

    first = renderer.render_page(
        document.raw,
        state.working_copy_path,
        0,
        state.zoom_level,
        state.dirty_version,
    )
    second = renderer.render_page(
        document.raw,
        state.working_copy_path,
        0,
        state.zoom_level,
        state.dirty_version,
    )

    assert second is first
    assert second.image is first.image
    document.close()


def test_prefetch_uses_live_document_not_stale_disk_copy(tmp_path) -> None:
    """Prefetch must reflect in-memory-only edits (e.g. rotation), not the on-disk copy.

    Regression test for a bug where prefetch_page() reopened the working
    copy from disk on every background call. Since edits like rotation are
    only applied to the live in-memory fitz.Document (and not flushed to
    disk until Save), the stale disk-based prefetch could poison the LRU
    cache and make the edit appear to vanish when navigating back to the
    page.
    """
    sample_path = tmp_path / "หมุนหน้า" / "rotate-test.pdf"
    create_sample_pdf(sample_path, pages=2)

    state = DocumentState()
    document = PdfDocument(state)
    renderer = PdfRenderer()
    document.open(sample_path)

    before = renderer.render_page(
        document.raw,
        state.working_copy_path,
        0,
        state.zoom_level,
        state.dirty_version,
    )

    # Rotate page 0 in-memory only — this is NOT written to the working
    # copy file on disk (that only happens on Save).
    page = document.get_page(0)
    page.set_rotation((page.rotation + 90) % 360)
    state.bump_version()

    # Simulate the background prefetch that fires when the user navigates
    # away with next/previous.
    renderer.prefetch_page(
        document.raw,
        state.working_copy_path,
        0,
        state.zoom_level,
        state.dirty_version,
    )

    # Navigating back to page 0 must show the rotation, not a stale
    # unrotated image poisoned into the cache by prefetch.
    after = renderer.render_page(
        document.raw,
        state.working_copy_path,
        0,
        state.zoom_level,
        state.dirty_version,
    )

    assert (after.image.width, after.image.height) == (before.image.height, before.image.width)
    document.close()
