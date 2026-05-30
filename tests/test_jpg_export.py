# -*- coding: utf-8 -*-
"""Tests for exporting PDF pages to JPG files."""

import json
from pathlib import Path

from PIL import Image

from thai_pdf_editor.app.core.document_state import DocumentState
import pytest

from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.export_operations import batch_export_pdfs_as_jpg, export_pdf_as_jpg, resolve_jpg_page_indices
from thai_pdf_editor.app.core.overlay_operations import create_redact_operation
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.models.geometry import PdfRect

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_export_pdf_as_jpg_creates_one_file_per_page_with_thai_path(tmp_path: Path) -> None:
    """Export every PDF page to a separate JPG without modifying the source PDF."""
    source_path = create_sample_pdf(tmp_path / "เอกสารไทย.pdf", pages=3)
    original_bytes = source_path.read_bytes()
    output_dir = tmp_path / "ภาพส่งออก"
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    output_paths = export_pdf_as_jpg(document.raw, state, output_dir, dpi=96)

    assert len(output_paths) == 3
    assert [path.name for path in output_paths] == [
        "เอกสารไทย_page_0001.jpg",
        "เอกสารไทย_page_0002.jpg",
        "เอกสารไทย_page_0003.jpg",
    ]
    for output_path in output_paths:
        assert output_path.exists()
        with Image.open(output_path) as image:
            assert image.format == "JPEG"
            assert image.width > 0
            assert image.height > 0
    assert source_path.read_bytes() == original_bytes
    assert state.dirty is False
    document.close()


def test_export_pdf_as_jpg_can_export_current_page_with_requested_dpi(tmp_path: Path) -> None:
    """Current-page export writes only the selected page at the requested DPI."""
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=3)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    state.set_current_page(1)

    page_indices = resolve_jpg_page_indices("current", state.current_page_index, state.total_pages)
    output_paths = export_pdf_as_jpg(
        document.raw,
        state,
        tmp_path / "jpg",
        page_indices=page_indices,
        dpi=144,
        quality=80,
    )

    assert len(output_paths) == 1
    assert output_paths[0].name == "source_page_0002.jpg"
    with Image.open(output_paths[0]) as image:
        assert image.size == (600, 840)
    document.close()


def test_resolve_jpg_page_indices_supports_all_and_rejects_invalid_scope() -> None:
    """UI export scope values are resolved before calling the exporter."""
    assert resolve_jpg_page_indices("all", 1, 3) is None
    assert resolve_jpg_page_indices("current", 1, 3) == [1]
    with pytest.raises(InvalidOperationError):
        resolve_jpg_page_indices("selected", 1, 3)


def test_export_pdf_as_jpg_does_not_overwrite_existing_files(tmp_path: Path) -> None:
    """Existing JPG files in the destination folder are preserved."""
    source_path = create_sample_pdf(tmp_path / "source.pdf", pages=1)
    output_dir = tmp_path / "jpg"
    output_dir.mkdir()
    existing_path = output_dir / "source_page_0001.jpg"
    existing_path.write_bytes(b"existing")
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    output_paths = export_pdf_as_jpg(document.raw, state, output_dir, page_indices=[0], dpi=72)

    assert len(output_paths) == 1
    assert output_paths[0].name == "source_page_0001_2.jpg"
    assert existing_path.read_bytes() == b"existing"
    document.close()


def test_export_pdf_as_jpg_includes_pending_redaction_preview(tmp_path: Path) -> None:
    """Pending redaction operations are applied to the exported JPG copy."""
    source_path = create_sample_pdf(tmp_path / "redact.pdf", pages=1)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    operation = create_redact_operation(page_index=0, rect=PdfRect(20, 20, 100, 100))
    state.record_operation(operation, pending=True)

    output_paths = export_pdf_as_jpg(document.raw, state, tmp_path / "jpg", dpi=72)

    with Image.open(output_paths[0]) as image:
        red, green, blue = image.convert("RGB").getpixel((30, 30))
    assert (red, green, blue) == (0, 0, 0)
    assert state.dirty is True
    document.close()


def test_batch_export_pdfs_as_jpg_writes_report_and_continues_after_failure(tmp_path: Path) -> None:
    """Batch JPG exports valid PDFs and records failed inputs without stopping."""
    first_path = create_sample_pdf(tmp_path / "หนึ่ง.pdf", pages=2)
    second_path = create_sample_pdf(tmp_path / "สอง.pdf", pages=1)
    invalid_path = tmp_path / "เสีย.pdf"
    invalid_path.write_text("not a pdf", encoding="utf-8")
    first_bytes = first_path.read_bytes()
    second_bytes = second_path.read_bytes()

    report = batch_export_pdfs_as_jpg(
        [first_path, invalid_path, second_path],
        tmp_path / "batch_output",
        dpi=72,
        quality=70,
    )

    assert report["total_sources"] == 3
    assert report["succeeded"] == 2
    assert report["failed"] == 1
    report_path = Path(str(report["report_path"]))
    assert report_path.exists()
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["succeeded"] == 2
    assert saved_report["failed"] == 1
    output_paths = [
        Path(path)
        for item in saved_report["items"]
        if item["status"] == "succeeded"
        for path in item["output_paths"]
    ]
    assert [path.name for path in output_paths] == [
        "หนึ่ง_page_0001.jpg",
        "หนึ่ง_page_0002.jpg",
        "สอง_page_0001.jpg",
    ]
    for output_path in output_paths:
        with Image.open(output_path) as image:
            assert image.format == "JPEG"
            assert image.width > 0
            assert image.height > 0
    failed_items = [item for item in saved_report["items"] if item["status"] == "failed"]
    assert len(failed_items) == 1
    assert "ส่งออก JPG ไม่สำเร็จ" in failed_items[0]["error"]
    assert first_path.read_bytes() == first_bytes
    assert second_path.read_bytes() == second_bytes
