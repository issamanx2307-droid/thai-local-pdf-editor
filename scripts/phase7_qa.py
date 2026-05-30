# -*- coding: utf-8 -*-
"""Repeatable Phase 7 QA workflow for real PDF user flows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thai_pdf_editor.app.config import LOG_DIR
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.export_operations import export_pdf_as_jpg
from thai_pdf_editor.app.core.form_operations import editable_form_fields, update_form_fields
from thai_pdf_editor.app.core.overlay_operations import (
    create_highlight_operation,
    create_image_operation,
    create_rectangle_operation,
    create_redact_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.page_operations import PageOperations, merge_pdfs
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

SECRET_TEXT = "SECRET DATA"
THAI_OVERLAY_TEXT = "ข้อความภาษาไทย QA"
FORM_TEXT_FIELD_NAME = "customer_name"
FORM_CHECKBOX_FIELD_NAME = "accepted"
FORM_TEXT_VALUE = "สมชาย ทดสอบ"


def run_phase7_qa(base_dir: Path, *, include_gui: bool = False) -> dict[str, Any]:
    """Run Phase 7 QA and return a structured report."""
    setup_logging()
    base_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = base_dir / "เอกสารลูกค้า"
    source_path = qa_dir / "ใบเสนอราคา.pdf"
    output_path = qa_dir / "ใบเสนอราคา_edited.pdf"
    extract_path = qa_dir / "แยกหน้า.pdf"
    merge_path = qa_dir / "รวมไฟล์.pdf"
    jpg_dir = qa_dir / "ส่งออก_jpg"
    image_path = qa_dir / "ลายเซ็น.png"
    form_source_path = qa_dir / "แบบฟอร์ม.pdf"
    form_output_path = qa_dir / "แบบฟอร์ม_กรอกแล้ว.pdf"

    font_path = first_existing_thai_font()
    if font_path is None:
        raise RuntimeError("ไม่พบฟอนต์ไทยสำหรับ QA")

    _create_qa_pdf(source_path, font_path)
    _create_signature_image(image_path)
    _create_form_pdf(form_source_path, font_path)
    source_hash = _sha256(source_path)
    form_source_hash = _sha256(form_source_path)

    state = DocumentState()
    document = PdfDocument(state)
    renderer = PdfRenderer()
    page_ops = PageOperations(document, state)
    document.open(source_path)

    renderer.render_page(document.raw, state.working_copy_path, 0, 1.0, state.dirty_version)
    state.set_current_page(1)
    page_ops.rotate_current_page(90)
    state.set_current_page(2)
    page_ops.move_current_page(-1)
    state.set_current_page(state.total_pages - 1)
    page_ops.delete_current_page()
    state.set_current_page(0)

    redaction_rect = document.raw[0].search_for(SECRET_TEXT)[0]
    operations = [
        create_text_operation(
            page_index=0,
            point=PdfPoint(48, 180),
            text=THAI_OVERLAY_TEXT,
            font_size=18,
            color="#111111",
            font_path=font_path,
        ),
        create_image_operation(page_index=0, point=PdfPoint(48, 220), image_path=image_path, width=120),
        create_rectangle_operation(page_index=0, rect=PdfRect(40, 260, 200, 320), color="#d32f2f", line_width=2),
        create_highlight_operation(page_index=0, rect=PdfRect(40, 330, 220, 365), color="#fff176"),
        create_redact_operation(
            page_index=0,
            rect=PdfRect(redaction_rect.x0, redaction_rect.y0, redaction_rect.x1, redaction_rect.y1),
        ),
    ]
    for operation in operations:
        state.record_operation(operation, pending=True)

    renderer.render_page(document.raw, state.working_copy_path, 0, 1.25, state.dirty_version, state.pending_operations)
    SaveManager().save_as(document.raw, state, output_path)
    document.close()

    saved_checks = _inspect_saved_pdf(output_path)
    output_hash_before_jpg = _sha256(output_path)

    jpg_state = DocumentState()
    jpg_document = PdfDocument(jpg_state)
    jpg_document.open(output_path)
    jpg_paths = export_pdf_as_jpg(jpg_document.raw, jpg_state, jpg_dir, dpi=96)
    jpg_document.close()
    jpg_checks = _inspect_jpg_files(jpg_paths)

    form_state = DocumentState()
    form_document = PdfDocument(form_state)
    form_document.open(form_source_path)
    form_updates = _form_updates_for_qa(form_document.raw)
    update_form_fields(form_document.raw, form_state, form_updates)
    form_dirty_after_update = form_state.dirty
    SaveManager().save_as(form_document.raw, form_state, form_output_path)
    form_document.close()
    form_checks = _inspect_form_pdf(form_output_path)

    extract_state = DocumentState()
    extract_document = PdfDocument(extract_state)
    extract_document.open(output_path)
    PageOperations(extract_document, extract_state).extract_current_page(extract_path)
    extract_document.close()

    merge_pdfs([output_path, extract_path], merge_path)
    if include_gui:
        _run_gui_smoke(output_path)

    report = {
        "source_path": str(source_path),
        "output_path": str(output_path),
        "extract_path": str(extract_path),
        "merge_path": str(merge_path),
        "jpg_dir": str(jpg_dir),
        "jpg_paths": [str(path) for path in jpg_paths],
        "form_source_path": str(form_source_path),
        "form_output_path": str(form_output_path),
        "source_unchanged": _sha256(source_path) == source_hash,
        "form_source_unchanged": _sha256(form_source_path) == form_source_hash,
        "output_unchanged_after_jpg_export": _sha256(output_path) == output_hash_before_jpg,
        "saved_page_count": saved_checks["page_count"],
        "thai_text_found": saved_checks["thai_text_found"],
        "secret_removed": saved_checks["secret_removed"],
        "image_found": saved_checks["image_found"],
        "jpg_export_count": len(jpg_paths),
        "jpg_images_valid": jpg_checks["images_valid"],
        "jpg_first_size": jpg_checks["first_size"],
        "form_dirty_after_update": form_dirty_after_update,
        "form_field_count": form_checks["field_count"],
        "form_text_value_saved": form_checks["text_value_saved"],
        "form_checkbox_value_saved": form_checks["checkbox_value_saved"],
        "extract_page_count": _page_count(extract_path),
        "merge_page_count": _page_count(merge_path),
        "gui_smoke_ok": True,
    }
    _assert_report(report)
    _write_report(report)
    return report


def _create_qa_pdf(path: Path, font_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    for index in range(4):
        page = document.new_page(width=420, height=595)
        page.insert_text(
            fitz.Point(42, 64),
            f"เอกสารทดสอบหน้า {index + 1}",
            fontsize=14,
            fontfile=str(font_path),
            fontname="qa_thai_font",
        )
        page.insert_text(fitz.Point(42, 118), f"Page marker {index + 1}", fontsize=12)
        if index == 0:
            page.insert_text(fitz.Point(42, 150), SECRET_TEXT, fontsize=16)
    document.save(str(path))
    document.close()


def _create_signature_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (240, 80), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.line((18, 48, 80, 22, 142, 54, 220, 28), fill=(20, 90, 180, 230), width=5)
    draw.rectangle((8, 8, 232, 72), outline=(20, 90, 180, 120), width=2)
    image.save(path)


def _create_form_pdf(path: Path, font_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page(width=420, height=260)
    page.insert_text(
        fitz.Point(42, 42),
        "แบบฟอร์มทดสอบ",
        fontsize=16,
        fontfile=str(font_path),
        fontname="qa_form_thai_font",
    )
    page.insert_text(fitz.Point(42, 82), "Customer name", fontsize=11)
    text_widget = fitz.Widget()
    text_widget.field_name = FORM_TEXT_FIELD_NAME
    text_widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    text_widget.field_value = ""
    text_widget.rect = fitz.Rect(42, 94, 270, 124)
    text_widget.border_color = (0, 0, 0)
    text_widget.border_width = 1
    page.add_widget(text_widget)

    page.insert_text(fitz.Point(42, 162), "Accepted", fontsize=11)
    checkbox_widget = fitz.Widget()
    checkbox_widget.field_name = FORM_CHECKBOX_FIELD_NAME
    checkbox_widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    checkbox_widget.field_value = False
    checkbox_widget.rect = fitz.Rect(112, 148, 134, 170)
    checkbox_widget.border_color = (0, 0, 0)
    checkbox_widget.border_width = 1
    page.add_widget(checkbox_widget)

    document.save(str(path))
    document.close()


def _inspect_saved_pdf(path: Path) -> dict[str, Any]:
    with fitz.open(str(path)) as document:
        text = "\n".join(page.get_text() for page in document).replace("\xa0", " ")
        images = sum(len(page.get_images()) for page in document)
        return {
            "page_count": document.page_count,
            "thai_text_found": THAI_OVERLAY_TEXT in text,
            "secret_removed": SECRET_TEXT not in text,
            "image_found": images > 0,
        }


def _form_updates_for_qa(document: fitz.Document) -> dict[int, str | bool]:
    fields = editable_form_fields(document)
    updates: dict[int, str | bool] = {}
    for field in fields:
        if field.name == FORM_TEXT_FIELD_NAME:
            updates[field.xref] = FORM_TEXT_VALUE
        elif field.name == FORM_CHECKBOX_FIELD_NAME:
            updates[field.xref] = True
    return updates


def _inspect_form_pdf(path: Path) -> dict[str, Any]:
    with fitz.open(str(path)) as document:
        values = {field.name: field.value for field in editable_form_fields(document)}
    return {
        "field_count": len(values),
        "text_value_saved": values.get(FORM_TEXT_FIELD_NAME) == FORM_TEXT_VALUE,
        "checkbox_value_saved": values.get(FORM_CHECKBOX_FIELD_NAME) is True,
    }


def _inspect_jpg_files(paths: list[Path]) -> dict[str, Any]:
    first_size: tuple[int, int] | None = None
    images_valid = True
    for index, path in enumerate(paths):
        try:
            with Image.open(path) as image:
                images_valid = images_valid and image.format == "JPEG" and image.width > 0 and image.height > 0
                if index == 0:
                    first_size = (image.width, image.height)
        except Exception:
            images_valid = False
    return {"images_valid": images_valid, "first_size": first_size}


def _run_gui_smoke(path: Path) -> None:
    from thai_pdf_editor.app.main import create_app

    app = create_app(smoke_test=False)
    errors: list[BaseException] = []

    def exercise_window() -> None:
        try:
            app._open_pdf_path(path)
            app.next_page()
            app.previous_page()
            app.zoom_in()
            app.zoom_out()
        except BaseException as exc:
            errors.append(exc)
        finally:
            app.quit()

    app.after(100, exercise_window)
    app.mainloop()
    try:
        app.destroy()
    except Exception:
        pass
    if errors:
        raise errors[0]


def _page_count(path: Path) -> int:
    with fitz.open(str(path)) as document:
        return document.page_count


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_report(report: dict[str, Any]) -> None:
    expected = {
        "source_unchanged": True,
        "form_source_unchanged": True,
        "output_unchanged_after_jpg_export": True,
        "saved_page_count": 3,
        "thai_text_found": True,
        "secret_removed": True,
        "image_found": True,
        "jpg_export_count": 3,
        "jpg_images_valid": True,
        "form_dirty_after_update": True,
        "form_field_count": 2,
        "form_text_value_saved": True,
        "form_checkbox_value_saved": True,
        "extract_page_count": 1,
        "merge_page_count": 4,
        "gui_smoke_ok": True,
    }
    failures = {key: report.get(key) for key, value in expected.items() if report.get(key) != value}
    if failures:
        raise AssertionError(f"Phase 7 QA failed: {failures}")


def _write_report(report: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report_path = LOG_DIR / "phase7_qa_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    """Run Phase 7 QA from the command line."""
    parser = argparse.ArgumentParser(description="Run Phase 7 QA workflow")
    parser.add_argument("--base-dir", type=Path, default=Path("data/qa/phase7_qa"))
    parser.add_argument("--include-gui", action="store_true")
    args = parser.parse_args()
    report = run_phase7_qa(args.base_dir, include_gui=args.include_gui)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
