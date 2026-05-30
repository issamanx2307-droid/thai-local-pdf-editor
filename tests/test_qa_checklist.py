# -*- coding: utf-8 -*-
"""Tests for the manual QA checklist content."""

from thai_pdf_editor.app.ui.qa_checklist_dialog import checklist_items_for_document


def test_qa_checklist_warns_when_document_has_unsaved_work() -> None:
    """Manual QA checklist should reflect dirty document state."""
    items = checklist_items_for_document(has_document=True, dirty=True)

    assert items[0].startswith("มีงานที่ยังไม่ได้ Save As")
    assert any("redaction" in item for item in items)
    assert any("ฟอนต์ไทย" in item for item in items)


def test_qa_checklist_warns_when_no_pdf_is_open() -> None:
    """Checklist should guide the user to open a PDF first."""
    assert checklist_items_for_document(has_document=False, dirty=False)[0].startswith("ยังไม่ได้เปิด PDF")
