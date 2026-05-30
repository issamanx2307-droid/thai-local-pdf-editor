# -*- coding: utf-8 -*-
"""Tests for the font import QA workflow."""

from pathlib import Path

from scripts.font_import_qa import THAI_NO_DATA_MESSAGE, run_font_import_qa


def test_font_import_qa_controlled_sample_passes(tmp_path: Path) -> None:
    """The controlled QA sample must scan, import, and report blank PDFs clearly."""
    report = run_font_import_qa(tmp_path / "font_import_qa", include_workspace_pdfs=False)
    sample = report["sample"]

    assert report["passed"] is True
    assert sample["font_count"] > 0
    assert sample["resolved_count"] > 0
    assert Path(sample["selected_font_path"]).exists()
    assert THAI_NO_DATA_MESSAGE in report["blank_pdf_error"]
