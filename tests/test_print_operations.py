# -*- coding: utf-8 -*-
"""Tests for PDF print dispatch."""

from pathlib import Path

import pytest

from thai_pdf_editor.app.core import print_operations
from thai_pdf_editor.app.core.errors import PdfPrintError


def test_print_pdf_prefers_sumatra_when_available(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Sumatra remains the first-choice print engine when available."""
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    sumatra = tmp_path / "SumatraPDF.exe"
    sumatra.write_text("stub", encoding="utf-8")
    calls: list[tuple[Path, Path, str, int, str | None]] = []

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: sumatra)
    monkeypatch.setattr(
        print_operations,
        "_print_via_sumatra",
        lambda exe, pdf, printer, *, copies, page_spec=None: calls.append((exe, pdf, printer, copies, page_spec)),
    )
    monkeypatch.setattr(print_operations, "_spawn_gdi_print_worker", lambda *args, **kwargs: pytest.fail())
    monkeypatch.setattr(print_operations, "_print_via_shell", lambda *args, **kwargs: pytest.fail())

    print_operations.print_pdf(source, "Brother DCP-T720DW Printer", copies=2)

    assert calls == [(sumatra, source, "Brother DCP-T720DW Printer", 2, None)]


def test_print_pdf_passes_normalized_page_spec_to_sumatra(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A custom page selection is validated against the PDF and normalized."""
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    sumatra = tmp_path / "SumatraPDF.exe"
    sumatra.write_text("stub", encoding="utf-8")
    calls: list[tuple[Path, Path, str, int, str | None]] = []

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: sumatra)
    monkeypatch.setattr(print_operations, "_get_page_count", lambda _pdf: 9)
    monkeypatch.setattr(
        print_operations,
        "_print_via_sumatra",
        lambda exe, pdf, printer, *, copies, page_spec=None: calls.append((exe, pdf, printer, copies, page_spec)),
    )

    print_operations.print_pdf(source, "Brother DCP-T720DW Printer", copies=1, pages="3,1-2,8-9")

    assert calls == [(sumatra, source, "Brother DCP-T720DW Printer", 1, "1-3,8-9")]


def test_print_pdf_starts_internal_worker_without_sumatra(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A machine without a PDF print verb still gets a local print path."""
    source = tmp_path / "เอกสารไทย.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    calls: list[tuple[Path, str, int, str | None]] = []

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: None)
    monkeypatch.setattr(print_operations, "_is_windows", lambda: True)
    monkeypatch.setattr(
        print_operations,
        "_spawn_gdi_print_worker",
        lambda pdf, printer, *, copies, page_spec=None: calls.append((pdf, printer, copies, page_spec)),
    )
    monkeypatch.setattr(print_operations, "_print_via_shell", lambda *args, **kwargs: pytest.fail())

    print_operations.print_pdf(source, "Brother DCP-T720DW Printer", copies=1)

    assert calls == [(source, "Brother DCP-T720DW Printer", 1, None)]


def test_print_pdf_wraps_shell_print_association_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """WinError 1155 is shown as a Thai app error instead of a generic crash."""
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: None)
    monkeypatch.setattr(print_operations, "_is_windows", lambda: False)
    monkeypatch.setattr(
        print_operations,
        "_print_via_shell",
        lambda _pdf: (_ for _ in ()).throw(OSError(1155, "No application is associated")),
    )

    with pytest.raises(PdfPrintError) as exc_info:
        print_operations.print_pdf(source, "Brother DCP-T720DW Printer")

    assert "พิมพ์ PDF ไม่ได้" in exc_info.value.user_message


def test_print_pdf_rejects_missing_file() -> None:
    """Missing source PDFs fail before dispatching a print job."""
    with pytest.raises(PdfPrintError) as exc_info:
        print_operations.print_pdf(Path("missing.pdf"), "Brother DCP-T720DW Printer")

    assert exc_info.value.user_message == "ไม่พบไฟล์ PDF ที่ต้องการพิมพ์"


def test_fit_image_to_printable_area_preserves_aspect_ratio() -> None:
    """Rendered PDF pages are centered inside the printable page area."""
    assert print_operations._fit_image_to_printable_area(200, 100, 1000, 1000) == (0, 250, 1000, 750)
    assert print_operations._fit_image_to_printable_area(100, 200, 1000, 1000) == (250, 0, 750, 1000)


def test_parse_page_range_accepts_singles_and_ranges() -> None:
    """Mixed comma-separated singles and ranges resolve to 0-based indices."""
    assert print_operations.parse_page_range("1,3-5,8", total_pages=10) == [0, 2, 3, 4, 7]


def test_parse_page_range_deduplicates_and_sorts_out_of_order_input() -> None:
    """Overlapping and out-of-order chunks collapse into a sorted, unique list."""
    assert print_operations.parse_page_range("5, 2-3, 3-4, 1", total_pages=10) == [0, 1, 2, 3, 4]


def test_parse_page_range_rejects_blank_spec() -> None:
    """An empty page selection is treated as a user error, not 'print nothing'."""
    with pytest.raises(PdfPrintError):
        print_operations.parse_page_range("   ", total_pages=5)


def test_parse_page_range_rejects_page_beyond_document() -> None:
    """A page number past the end of the document is rejected with a Thai message."""
    with pytest.raises(PdfPrintError) as exc_info:
        print_operations.parse_page_range("1-3,9", total_pages=5)

    assert "เกินจำนวนหน้าทั้งหมด" in exc_info.value.user_message


def test_parse_page_range_rejects_backwards_range() -> None:
    """A range like '5-2' is invalid rather than silently empty."""
    with pytest.raises(PdfPrintError):
        print_operations.parse_page_range("5-2", total_pages=10)


def test_format_page_ranges_collapses_consecutive_runs() -> None:
    """Consecutive 0-based indices collapse into compact 1-based ranges."""
    assert print_operations._format_page_ranges([0, 1, 2, 4, 6, 7, 8]) == "1-3,5,7-9"
