# -*- coding: utf-8 -*-
"""Run repeatable QA for PDF font inspection and font import."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thai_pdf_editor.app.config import DATA_DIR, IMPORTED_FONT_DIR, LOG_DIR
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.font_importer import import_fonts_for_document, scan_pdf_font_usage
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

QA_ROOT = DATA_DIR / "qa" / "font_import_qa"
PHASE7_QA_ROOT = DATA_DIR / "qa" / "phase7_qa"
REPORT_PATH = LOG_DIR / "font_import_qa_report.json"
THAI_NO_DATA_MESSAGE = "ไม่สามารถหาข้อมูลได้"


def run_font_import_qa(
    base_dir: Path = QA_ROOT,
    *,
    include_workspace_pdfs: bool = True,
) -> dict[str, Any]:
    """Create controlled PDFs, run font import checks, and return a report."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    base_dir.mkdir(parents=True, exist_ok=True)
    sample_dir = base_dir / "เอกสารฟอนต์"
    sample_dir.mkdir(parents=True, exist_ok=True)

    font_path = _qa_font_path()
    sample_pdf = sample_dir / "ตัวอย่างฟอนต์.pdf"
    blank_pdf = sample_dir / "ไม่มีข้อความ.pdf"
    _create_text_pdf(sample_pdf, font_path)
    _create_blank_pdf(blank_pdf)

    sample_report = _inspect_controlled_sample(sample_pdf)
    blank_pdf_error = _inspect_blank_pdf(blank_pdf)
    workspace_reports = _inspect_workspace_pdfs(base_dir) if include_workspace_pdfs else []
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qa_font_path": str(font_path),
        "sample_pdf": str(sample_pdf),
        "blank_pdf": str(blank_pdf),
        "sample": sample_report,
        "blank_pdf_error": blank_pdf_error,
        "workspace_pdfs": workspace_reports,
        "passed": sample_report["resolved_count"] > 0 and THAI_NO_DATA_MESSAGE in blank_pdf_error,
    }
    _write_report(report)
    return report


def _qa_font_path() -> Path:
    imported_sarabun = IMPORTED_FONT_DIR / "Sarabun-Regular.ttf"
    if imported_sarabun.exists() and imported_sarabun.stat().st_size > 0:
        return imported_sarabun

    thai_font = first_existing_thai_font()
    if thai_font is not None:
        return thai_font

    raise InvalidOperationError("ไม่พบฟอนต์ไทยสำหรับสร้าง PDF ทดสอบ")


def _create_text_pdf(pdf_path: Path, font_path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=420, height=300)
    page.insert_text(
        (48, 80),
        "ทดสอบฟอนต์ไทย PDF 123",
        fontname="ThaiQaFont",
        fontfile=str(font_path),
        fontsize=20,
        color=(0, 0, 0),
    )
    page.insert_text(
        (48, 120),
        "ข้อความนี้ใช้ตรวจการนำเข้าฟอนต์",
        fontname="ThaiQaFont",
        fontfile=str(font_path),
        fontsize=18,
        color=(0, 0, 0),
    )
    document.save(str(pdf_path))
    document.close()


def _create_blank_pdf(pdf_path: Path) -> None:
    document = fitz.open()
    document.new_page(width=240, height=160)
    document.save(str(pdf_path))
    document.close()


def _inspect_controlled_sample(pdf_path: Path) -> dict[str, Any]:
    with fitz.open(str(pdf_path)) as document:
        usages = scan_pdf_font_usage(document)
        summary = import_fonts_for_document(document, allow_download=True)

    imported_paths = [str(result.imported_path) for result in summary.results if result.imported_path is not None]
    return {
        "font_count": len(usages),
        "fonts": [_usage_report(usage) for usage in usages],
        "result_statuses": [result.status for result in summary.results],
        "resolved_count": len(imported_paths),
        "selected_font_path": str(summary.selected_font_path),
        "imported_paths": imported_paths,
    }


def _inspect_blank_pdf(pdf_path: Path) -> str:
    with fitz.open(str(pdf_path)) as document:
        try:
            import_fonts_for_document(document, allow_download=False)
        except InvalidOperationError as exc:
            return str(exc)
    raise InvalidOperationError("PDF ว่างควรแจ้งว่าไม่สามารถหาข้อมูลฟอนต์ได้")


def _inspect_workspace_pdfs(base_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    if not PHASE7_QA_ROOT.exists():
        return reports

    base_resolved = base_dir.resolve()
    for pdf_path in sorted(PHASE7_QA_ROOT.rglob("*.pdf")):
        if _is_inside(pdf_path.resolve(), base_resolved):
            continue
        reports.append(_inspect_pdf_best_effort(pdf_path))
    return reports


def _inspect_pdf_best_effort(pdf_path: Path) -> dict[str, Any]:
    try:
        with fitz.open(str(pdf_path)) as document:
            usages = scan_pdf_font_usage(document)
            if not usages:
                return {"path": str(pdf_path), "font_count": 0, "resolved_count": 0, "error": THAI_NO_DATA_MESSAGE}
            summary = import_fonts_for_document(document, allow_download=True)
    except Exception as exc:
        return {"path": str(pdf_path), "font_count": 0, "resolved_count": 0, "error": str(exc)}

    return {
        "path": str(pdf_path),
        "font_count": len(usages),
        "resolved_count": sum(1 for result in summary.results if result.imported_path is not None),
        "selected_font_path": str(summary.selected_font_path),
        "fonts": [_usage_report(usage) for usage in usages[:5]],
    }


def _usage_report(usage: Any) -> dict[str, Any]:
    return {
        "pdf_name": usage.pdf_name,
        "normalized_name": usage.normalized_name,
        "pages": list(usage.pages),
        "spans": usage.spans,
        "characters": usage.characters,
        "from_text_layer": usage.from_text_layer,
    }


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PDF font import QA")
    parser.add_argument(
        "--skip-workspace-pdfs",
        action="store_true",
        help="only run the controlled sample checks",
    )
    args = parser.parse_args()
    report = run_font_import_qa(include_workspace_pdfs=not args.skip_workspace_pdfs)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
