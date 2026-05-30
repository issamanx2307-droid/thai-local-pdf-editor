# -*- coding: utf-8 -*-
"""QA report for search, recent files, Save As preflight, and checklist helpers."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.overlay_operations import create_redact_operation, create_text_operation
from thai_pdf_editor.app.core.pdf_search import scaled_search_rect, search_pdf_text
from thai_pdf_editor.app.core.recent_files import add_recent_file, clear_recent_files, load_recent_files, remove_recent_file
from thai_pdf_editor.app.core.save_preflight import build_save_preflight_details, build_save_preflight_message
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.ui.qa_checklist_dialog import checklist_items_for_document
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

QA_DIR = PROJECT_ROOT / "data" / "qa" / "phase43_ui_qa" / "เอกสารไทย"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
REPORT_PATH = LOG_DIR / "phase43_ui_qa_report.json"


def run_phase43_ui_qa() -> dict[str, object]:
    """Run non-GUI QA for the latest UI helper workflows."""
    QA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = QA_DIR / "ค้นหา_recent_preflight.pdf"
    settings_path = QA_DIR / "recent_files.json"
    _create_search_pdf(pdf_path)

    with fitz.open(str(pdf_path)) as document:
        search_results = search_pdf_text(document, "Phase43")
    scaled_rect = scaled_search_rect(search_results[0].rect, 1.5)

    recent_after_add = add_recent_file(pdf_path, settings_path)
    recent_after_remove = remove_recent_file(pdf_path, settings_path)
    add_recent_file(pdf_path, settings_path)
    clear_recent_files(settings_path)
    recent_after_clear = load_recent_files(settings_path)

    preflight_state = _build_preflight_state(pdf_path)
    preflight_message = build_save_preflight_message(preflight_state)
    preflight_details = build_save_preflight_details(preflight_state)
    checklist_items = checklist_items_for_document(has_document=True, dirty=True)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(pdf_path),
        "search_result_count": len(search_results),
        "scaled_highlight_rect": scaled_rect,
        "recent_after_add": [str(path) for path in recent_after_add],
        "recent_after_remove_count": len(recent_after_remove),
        "recent_after_clear_count": len(recent_after_clear),
        "preflight_has_redaction_warning": "กู้คืนไม่ได้" in preflight_message,
        "preflight_detail_count": len(preflight_details),
        "preflight_details": preflight_details,
        "checklist_count": len(checklist_items),
        "checklist_mentions_redaction": any("redaction" in item for item in checklist_items),
        "passed": False,
    }
    report["passed"] = _report_passed(report)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)
    return report


def _create_search_pdf(path: Path) -> None:
    font_path = first_existing_thai_font()
    if font_path is None:
        raise RuntimeError("ไม่พบฟอนต์ไทยสำหรับสร้าง PDF ทดสอบ")
    document = fitz.open()
    page = document.new_page(width=360, height=260)
    page.insert_text(
        (40, 80),
        "Phase43 ค้นหา recent preflight checklist",
        fontfile=str(font_path),
        fontname="phase43_font",
        fontsize=16,
    )
    document.save(str(path))
    document.close()


def _build_preflight_state(pdf_path: Path) -> DocumentState:
    font_path = first_existing_thai_font()
    if font_path is None:
        raise RuntimeError("ไม่พบฟอนต์ไทยสำหรับ preflight QA")
    state = DocumentState()
    state.load_document(pdf_path, pdf_path, 1)
    state.record_operation(
        create_text_operation(
            page_index=0,
            point=PdfPoint(30, 40),
            text="ตรวจงาน",
            font_size=16,
            color="#111111",
            font_path=font_path,
        ),
        pending=True,
    )
    state.record_operation(create_redact_operation(page_index=0, rect=PdfRect(20, 20, 80, 45)), pending=True)
    return state


def _report_passed(report: dict[str, object]) -> bool:
    return (
        report["search_result_count"] == 1
        and len(report["recent_after_add"]) == 1
        and report["recent_after_remove_count"] == 0
        and report["recent_after_clear_count"] == 0
        and bool(report["preflight_has_redaction_warning"])
        and int(report["preflight_detail_count"]) >= 2
        and int(report["checklist_count"]) >= 8
        and bool(report["checklist_mentions_redaction"])
    )


def main() -> None:
    report = run_phase43_ui_qa()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
