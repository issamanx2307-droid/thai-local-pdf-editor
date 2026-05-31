# -*- coding: utf-8 -*-
"""Final local acceptance checks for the Thai PDF editor."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.release_qa import build_static_report
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font
from thai_pdf_editor.app.worker import PdfWorkerSession
from thai_pdf_editor.app.worker_contract import (
    COMMAND_BATCH_EXPORT_JPG,
    COMMAND_EXPORT_JPG,
    COMMAND_LIST_METADATA,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
    COMMAND_REPLACE_TEXT,
    COMMAND_SAVE_COPY,
    COMMAND_UPDATE_METADATA,
)

QA_DIR = PROJECT_ROOT / "data" / "qa" / "final_acceptance" / "เอกสารไทย"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
REPORT_PATH = LOG_DIR / "final_acceptance_report.json"


def run_final_acceptance() -> dict[str, object]:
    """Run a local acceptance pass without adding new user-facing features."""
    setup_logging()
    QA_DIR.mkdir(parents=True, exist_ok=True)
    source_path = QA_DIR / "acceptance_ภาษาไทย.pdf"
    _create_pdf(source_path)
    source_hash_before = _sha256(source_path)

    state = DocumentState()
    document = PdfDocument(state)
    renderer = PdfRenderer()
    page_ops = PageOperations(document, state)
    try:
        document.open(source_path)
        first_render = renderer.render_page(document.raw, state.working_copy_path, 0, 1.0, state.dirty_version)
        state.set_current_page(1)
        second_render = renderer.render_page(document.raw, state.working_copy_path, 1, 1.25, state.dirty_version)
        page_ops.rotate_current_page(90)
        page_ops.duplicate_current_page()
        page_ops.delete_current_page()
        final_page_count = state.total_pages
    finally:
        document.close()

    source_hash_after = _sha256(source_path)
    worker_report = _run_worker_acceptance(source_path)
    static_report = build_static_report(PROJECT_ROOT)
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    roadmap_text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()
    checklist_text = (PROJECT_ROOT / "V1_ACCEPTANCE_CHECKLIST.md").read_text(encoding="utf-8").lower()

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path),
        "opened_pdf": True,
        "preview_rendered": first_render.image.width > 0 and first_render.image.height > 0,
        "zoom_rendered": second_render.image.width > first_render.image.width,
        "page_navigation_checked": state.current_page_index >= 0,
        "page_operations_checked": final_page_count == 2,
        "source_unchanged": source_hash_before == source_hash_after,
        "worker_acceptance": worker_report,
        "app_log_exists": (LOG_DIR / "app.log").exists(),
        "static_clean": _static_clean(static_report),
        "readme_install_run_present": "## ติดตั้ง" in readme_text and "python run_app.py" in readme_text,
        "roadmap_41_44_present": all(f"phase {phase}" in roadmap_text for phase in (41, 42, 43, 44)),
        "v1_checklist_present": all(
            marker in checklist_text
            for marker in (
                "local-only",
                "core function qa",
                "real pdf acceptance",
                "ui completion",
                "packaging",
            )
        ),
        "passed": False,
    }
    report["passed"] = all(
        bool(report[key])
        for key in (
            "opened_pdf",
            "preview_rendered",
            "zoom_rendered",
            "page_navigation_checked",
            "page_operations_checked",
            "source_unchanged",
            "v1_checklist_present",
            "app_log_exists",
            "static_clean",
            "readme_install_run_present",
            "roadmap_41_44_present",
        )
    ) and bool(worker_report["passed"])
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)
    return report


def _create_pdf(path: Path) -> None:
    font_path = first_existing_thai_font()
    if font_path is None:
        raise RuntimeError("ไม่พบฟอนต์ไทยสำหรับ final acceptance")
    document = fitz.open()
    for index in range(2):
        page = document.new_page(width=360, height=260)
        page.insert_text(
            (40, 80),
            f"Final acceptance หน้า {index + 1} ภาษาไทย",
            fontfile=str(font_path),
            fontname=f"acceptance_font_{index}",
            fontsize=16,
        )
    document.save(str(path))
    document.close()


def _run_worker_acceptance(source_path: Path) -> dict[str, object]:
    preview_dir = QA_DIR / "worker_previews"
    jpg_dir = QA_DIR / "worker_jpg"
    batch_jpg_dir = QA_DIR / "worker_batch_jpg"
    saved_path = QA_DIR / "worker_saved.pdf"
    session = PdfWorkerSession(preview_dir=preview_dir)
    try:
        opened = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        metadata_updated = session.handle(
            {
                "command": COMMAND_UPDATE_METADATA,
                "payload": {"updates": {"title": "Final Worker Acceptance", "author": "Thai PDF Editor QA"}},
            }
        )
        metadata_listed = session.handle({"command": COMMAND_LIST_METADATA})
        replaced = session.handle(
            {
                "command": COMMAND_REPLACE_TEXT,
                "payload": {
                    "search_text": "Final acceptance",
                    "replacement_text": "Worker accepted",
                    "page_scope": "current",
                    "font_size": 14,
                },
            }
        )
        saved = session.handle({"command": COMMAND_SAVE_COPY, "payload": {"destination_path": str(saved_path)}})
        exported = session.handle(
            {
                "command": COMMAND_EXPORT_JPG,
                "payload": {"destination_dir": str(jpg_dir), "page_scope": "current", "dpi": 72, "quality": 80},
            }
        )
        batch_exported = session.handle(
            {
                "command": COMMAND_BATCH_EXPORT_JPG,
                "payload": {
                    "source_paths": [str(source_path), str(saved_path)],
                    "destination_dir": str(batch_jpg_dir),
                    "dpi": 72,
                    "quality": 80,
                },
            }
        )
    finally:
        session.close()

    metadata = metadata_listed.get("payload", {}).get("metadata", {}) if metadata_listed.get("ok") else {}
    saved_text = _pdf_text(saved_path) if saved_path.exists() else ""
    report = {
        "opened": opened.get("ok") is True,
        "rendered": rendered.get("ok") is True and Path(str(rendered.get("payload", {}).get("preview_path", ""))).exists(),
        "metadata_updated": metadata_updated.get("ok") is True and metadata.get("title") == "Final Worker Acceptance",
        "replace_text_pending": replaced.get("ok") is True and replaced.get("payload", {}).get("operation_count") == 1,
        "saved_copy_exists": saved.get("ok") is True and saved_path.exists(),
        "saved_copy_contains_replacement": "Worker accepted" in saved_text,
        "single_jpg_count": exported.get("ok") is True and exported.get("payload", {}).get("count") == 1,
        "batch_jpg_count": batch_exported.get("ok") is True and batch_exported.get("payload", {}).get("count") == 4,
        "batch_jpg_report_exists": Path(str(batch_exported.get("payload", {}).get("report_path", ""))).exists(),
    }
    report["passed"] = all(bool(value) for value in report.values())
    return report


def _pdf_text(path: Path) -> str:
    with fitz.open(str(path)) as document:
        return "\n".join(page.get_text() for page in document)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _static_clean(report: dict[str, object]) -> bool:
    return (
        report["source_files_over_line_limit"] == []
        and report["mojibake_files"] == []
        and report["missing_required_paths"] == []
    )


def main() -> None:
    report = run_final_acceptance()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
