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
    calls: list[tuple[Path, Path, str, int]] = []

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: sumatra)
    monkeypatch.setattr(
        print_operations,
        "_print_via_sumatra",
        lambda exe, pdf, printer, *, copies: calls.append((exe, pdf, printer, copies)),
    )
    monkeypatch.setattr(print_operations, "_spawn_gdi_print_worker", lambda *args, **kwargs: pytest.fail())
    monkeypatch.setattr(print_operations, "_print_via_shell", lambda *args, **kwargs: pytest.fail())

    print_operations.print_pdf(source, "Brother DCP-T720DW Printer", copies=2)

    assert calls == [(sumatra, source, "Brother DCP-T720DW Printer", 2)]


def test_print_pdf_starts_internal_worker_without_sumatra(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A machine without a PDF print verb still gets a local print path."""
    source = tmp_path / "เอกสารไทย.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    calls: list[tuple[Path, str, int]] = []

    monkeypatch.setattr(print_operations, "_find_sumatra", lambda: None)
    monkeypatch.setattr(print_operations, "_is_windows", lambda: True)
    monkeypatch.setattr(
        print_operations,
        "_spawn_gdi_print_worker",
        lambda pdf, printer, *, copies: calls.append((pdf, printer, copies)),
    )
    monkeypatch.setattr(print_operations, "_print_via_shell", lambda *args, **kwargs: pytest.fail())

    print_operations.print_pdf(source, "Brother DCP-T720DW Printer", copies=1)

    assert calls == [(source, "Brother DCP-T720DW Printer", 1)]


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
