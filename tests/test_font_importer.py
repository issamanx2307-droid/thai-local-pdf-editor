# -*- coding: utf-8 -*-
"""Tests for PDF font inspection and import."""

from pathlib import Path

import fitz
import pytest

from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.font_importer import (
    FontImportResult,
    FontImportSummary,
    PdfFontUsage,
    download_font,
    format_font_import_summary,
    import_fonts_for_document,
    normalize_font_name,
    resolve_and_import_font,
    scan_pdf_font_usage,
)

from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_scan_pdf_font_usage_reads_text_layer_fonts(tmp_path: Path) -> None:
    """Font names should come from the PDF text layer when available."""
    pdf_path = create_sample_pdf(tmp_path / "font-source.pdf", pages=1, text_prefix="FONT TEST")

    with fitz.open(str(pdf_path)) as document:
        usages = scan_pdf_font_usage(document)

    assert usages
    assert usages[0].from_text_layer is True
    assert usages[0].characters > 0


def test_resolve_and_import_font_copies_matching_local_font(tmp_path: Path) -> None:
    """A matching local font should be copied into the imported-font directory."""
    local_dir = tmp_path / "local"
    imported_dir = tmp_path / "imported"
    local_dir.mkdir()
    source_font = local_dir / "arial.ttf"
    source_font.write_bytes(b"fake local font")

    result = resolve_and_import_font(
        "ArialMT",
        allow_download=False,
        imported_dir=imported_dir,
        search_dirs=(local_dir,),
    )

    assert result.status == "local_exact"
    assert result.imported_path == imported_dir / "arial.ttf"
    assert result.imported_path.read_bytes() == b"fake local font"


def test_resolve_and_import_font_downloads_similar_known_font(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If an exact local font is missing, a known similar free font can be downloaded."""
    imported_dir = tmp_path / "imported"

    def fake_download(_url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"\x00\x01\x00\x00" + b"0" * 2048)
        return destination

    monkeypatch.setattr("thai_pdf_editor.app.core.font_importer.download_font", fake_download)

    result = resolve_and_import_font(
        "ABCDEE+THSarabunNew",
        allow_download=True,
        imported_dir=imported_dir,
        search_dirs=(tmp_path / "empty",),
    )

    assert result.status == "downloaded_similar"
    assert result.resolved_family == "Sarabun"
    assert result.imported_path is not None
    assert result.imported_path.exists()


def test_import_fonts_for_document_reports_no_data_for_blank_pdf(tmp_path: Path) -> None:
    """Blank or image-only PDFs without font data should produce a clear error."""
    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page(width=200, height=200)
    document.save(str(pdf_path))
    document.close()

    with fitz.open(str(pdf_path)) as opened:
        with pytest.raises(InvalidOperationError, match="ไม่สามารถหาข้อมูลได้"):
            import_fonts_for_document(
                opened,
                allow_download=False,
                imported_dir=tmp_path / "imported",
                search_dirs=(tmp_path / "empty",),
            )


def test_normalize_font_name_removes_subset_prefix() -> None:
    """Subset prefixes in PDFs should not block matching."""
    assert normalize_font_name("ABCDEE+THSarabunNew") == "thsarabunnew"


def test_download_font_rejects_non_font_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Downloaded data must look like a font before being stored."""
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not a font"

    monkeypatch.setattr("thai_pdf_editor.app.core.font_importer.urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(InvalidOperationError):
        download_font("https://example.invalid/font.ttf", tmp_path / "font.ttf")


def test_format_font_import_summary_shows_pdf_font_names_and_status(tmp_path: Path) -> None:
    """The UI report should explain what PDF fonts were found and how they resolved."""
    selected_font = tmp_path / "THSarabunNew.ttf"
    selected_font.write_bytes(b"font")
    summary = FontImportSummary(
        usages=(
            PdfFontUsage(
                pdf_name="ABCDEE+THSarabunNew",
                normalized_name="thsarabunnew",
                pages=(1, 2),
                spans=3,
                characters=42,
                from_text_layer=True,
            ),
            PdfFontUsage(
                pdf_name="MissingFont",
                normalized_name="missingfont",
                pages=(2,),
                spans=1,
                characters=5,
                from_text_layer=True,
            ),
        ),
        results=(
            FontImportResult(
                pdf_font_name="ABCDEE+THSarabunNew",
                status="local_exact",
                resolved_family="THSarabunNew",
                imported_path=selected_font,
                source_path=selected_font,
            ),
            FontImportResult(
                pdf_font_name="MissingFont",
                status="unresolved",
                message="ไม่พบฟอนต์ตรงกันหรือฟอนต์ใกล้เคียง",
            ),
        ),
        selected_font_path=selected_font,
    )

    report = format_font_import_summary(summary)

    assert "ชื่อฟอนต์ใน PDF: THSarabunNew" in report
    assert "สถานะ: พบฟอนต์ตรงกันในเครื่อง" in report
    assert "ไฟล์ที่ใช้: THSarabunNew.ttf" in report
    assert "ยังหาหรือโหลดไม่ได้: 1 รายการ" in report
