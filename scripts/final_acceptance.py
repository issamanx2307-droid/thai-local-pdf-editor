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
    static_report = build_static_report(PROJECT_ROOT)
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    roadmap_text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path),
        "opened_pdf": True,
        "preview_rendered": first_render.image.width > 0 and first_render.image.height > 0,
        "zoom_rendered": second_render.image.width > first_render.image.width,
        "page_navigation_checked": state.current_page_index >= 0,
        "page_operations_checked": final_page_count == 2,
        "source_unchanged": source_hash_before == source_hash_after,
        "app_log_exists": (LOG_DIR / "app.log").exists(),
        "static_clean": _static_clean(static_report),
        "readme_install_run_present": "## ติดตั้ง" in readme_text and "python run_app.py" in readme_text,
        "roadmap_41_44_present": all(f"phase {phase}" in roadmap_text for phase in (41, 42, 43, 44)),
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
            "app_log_exists",
            "static_clean",
            "readme_install_run_present",
            "roadmap_41_44_present",
        )
    )
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
