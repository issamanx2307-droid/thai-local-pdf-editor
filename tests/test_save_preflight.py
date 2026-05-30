# -*- coding: utf-8 -*-
"""Tests for Save As preflight summaries."""

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.overlay_operations import create_redact_operation, create_text_operation
from thai_pdf_editor.app.core.save_preflight import (
    build_save_preflight_details,
    build_save_preflight_message,
    has_save_preflight_items,
)
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font


def test_save_preflight_summarizes_pending_and_warns_redaction() -> None:
    """Preflight should show pending counts and warn for destructive redaction."""
    font_path = first_existing_thai_font()
    assert font_path is not None
    state = DocumentState()
    state.record_operation(
        create_text_operation(
            page_index=0,
            point=PdfPoint(10, 20),
            text="ทดสอบ",
            font_size=16,
            color="#111111",
            font_path=font_path,
        ),
        pending=True,
    )
    state.record_operation(create_redact_operation(page_index=0, rect=PdfRect(10, 10, 50, 30)), pending=True)

    message = build_save_preflight_message(state)

    assert has_save_preflight_items(state) is True
    assert "ข้อความ: 1 รายการ" in message
    assert "ลบ/ปิดทับข้อมูลถาวร: 1 รายการ" in message
    assert "กู้คืนไม่ได้" in message
    assert build_save_preflight_details(state) == [
        'รอ Save As: หน้า 1 - ข้อความ - "ทดสอบ"',
        "รอ Save As: หน้า 1 - ลบ/ปิดทับข้อมูลถาวร",
    ]


def test_save_preflight_can_be_skipped_when_nothing_changed() -> None:
    """Clean state does not need a Save As preflight dialog."""
    assert has_save_preflight_items(DocumentState()) is False
    assert build_save_preflight_details(DocumentState()) == ["ไม่มีรายการเปลี่ยนแปลง"]


def test_save_preflight_counts_updated_form_fields() -> None:
    """Form-edit details should report the number of changed PDF fields."""
    state = DocumentState()
    state.record_operation(
        PdfOperation(
            type=OperationType.UPDATE_FORM_FIELDS,
            page_index=0,
            payload={
                "changed_xrefs": [101, 102],
                "before": {101: "old-a", 102: "old-b"},
                "after": {101: "new-a", 102: "new-b"},
            },
        )
    )

    details = build_save_preflight_details(state)

    assert len(details) == 1
    assert "แก้ฟอร์ม PDF - 2 field" in details[0]
