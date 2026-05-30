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
