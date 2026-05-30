# -*- coding: utf-8 -*-
"""Repeatable QA for pending overlay delete, move, resize, and Save As."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thai_pdf_editor.app.config import DATA_DIR, LOG_DIR
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.overlay_operations import (
    create_highlight_operation,
    create_image_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.pending_overlay_operations import (
    delete_pending_operation,
    nudge_pending_operation,
    pending_operation_views,
    resize_pending_operation,
)
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.core.signature_operations import create_visual_signature_image
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

QA_ROOT = DATA_DIR / "qa" / "overlay_edit_qa"
REPORT_PATH = LOG_DIR / "overlay_edit_qa_report.json"
QA_TEXT = "ข้อความหลังย้าย"
DELETED_TEXT = "ข้อความที่ควรถูกลบก่อนบันทึก"


def run_overlay_edit_qa(base_dir: Path = QA_ROOT) -> dict[str, Any]:
    """Run overlay edit QA and write a structured report."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    sample_dir = base_dir / "เอกสาร overlay"
    sample_dir.mkdir(parents=True, exist_ok=True)
    source_path = sample_dir / "ต้นฉบับ.pdf"
    output_path = sample_dir / "ผลลัพธ์_overlay.pdf"
    font_path = first_existing_thai_font()
    if font_path is None:
        raise RuntimeError("ไม่พบฟอนต์ไทยสำหรับ QA")

    _create_source_pdf(source_path, font_path)
    source_hash_before = _sha256(source_path)
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)

    signature_path = create_visual_signature_image("ลายเซ็น QA", output_dir=sample_dir, font_path=font_path, width_px=520)
    text_operation = create_text_operation(
        page_index=0,
        point=PdfPoint(48, 130),
        text=QA_TEXT,
        font_size=16,
        color="#111111",
        font_path=font_path,
    )
    delete_candidate = create_text_operation(
        page_index=0,
        point=PdfPoint(48, 170),
        text=DELETED_TEXT,
        font_size=14,
        color="#d32f2f",
        font_path=font_path,
    )
    image_operation = create_image_operation(page_index=0, point=PdfPoint(48, 210), image_path=signature_path, width=130)
    rectangle_operation = create_rectangle_operation(
        page_index=0,
        rect=PdfRect(220, 120, 330, 180),
        color="#d32f2f",
        line_width=2,
    )
    highlight_operation = create_highlight_operation(
        page_index=0,
        rect=PdfRect(48, 72, 260, 96),
        color="#fff176",
    )

    for operation in [text_operation, delete_candidate, image_operation, rectangle_operation, highlight_operation]:
        state.record_operation(operation, pending=True)

    pending_before = pending_operation_views(state.pending_operations)
    delete_pending_operation(state, delete_candidate.id)
    nudge_pending_operation(state, text_operation.id, dx=12, dy=8)
    nudge_pending_operation(state, image_operation.id, dx=20, dy=-10)
    resize_pending_operation(state, image_operation.id, scale=1.1)
    resize_pending_operation(state, rectangle_operation.id, scale=0.8)
    pending_after = pending_operation_views(state.pending_operations)
    SaveManager().save_as(document.raw, state, output_path)
    document.close()

    source_hash_after = _sha256(source_path)
    saved_checks = _inspect_saved_pdf(output_path)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path),
        "output_path": str(output_path),
        "signature_path": str(signature_path),
        "pending_before": len(pending_before),
        "pending_after_edit": len(pending_after),
        "source_unchanged": source_hash_before == source_hash_after,
        "text_x_after_nudge": text_operation.payload["x"],
        "image_width_after_resize": image_operation.payload["width"],
        **saved_checks,
    }
    report["passed"] = (
        report["source_unchanged"]
        and report["thai_text_found"]
        and report["deleted_text_absent"]
        and report["image_found"]
        and report["pending_before"] == 5
        and report["pending_after_edit"] == 4
    )
    _write_report(report)
    return report


def _create_source_pdf(path: Path, font_path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=420, height=595)
    page.insert_text(
        fitz.Point(48, 72),
        "เอกสารทดสอบจัดการรายการที่วางแล้ว",
        fontsize=18,
        fontfile=str(font_path),
        fontname="qa_overlay_font",
    )
    page.insert_text(fitz.Point(48, 110), "Original marker", fontsize=12)
    document.save(str(path))
    document.close()


def _inspect_saved_pdf(path: Path) -> dict[str, Any]:
    with fitz.open(str(path)) as document:
        text = "\n".join(page.get_text() for page in document)
        images = sum(len(page.get_images()) for page in document)
        return {
            "saved_page_count": document.page_count,
            "thai_text_found": QA_TEXT in text,
            "deleted_text_absent": DELETED_TEXT not in text,
            "image_found": images > 0,
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pending overlay edit QA")
    parser.parse_args()
    report = run_overlay_edit_qa()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
