# -*- coding: utf-8 -*-
"""Tests for editing existing PDF form fields."""

from pathlib import Path

import fitz
import pytest

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.form_operations import editable_form_fields, update_form_fields
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.save_manager import SaveManager


def test_update_existing_text_and_checkbox_fields_then_save_as(tmp_path: Path) -> None:
    """Existing text fields and checkboxes can be edited through Save As."""
    source_path = _create_form_pdf(tmp_path / "แบบฟอร์ม.pdf")
    original_bytes = source_path.read_bytes()
    output_path = tmp_path / "แบบฟอร์ม_กรอกแล้ว.pdf"
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    fields = editable_form_fields(document.raw)

    assert [(field.name, field.value) for field in fields] == [("customer_name", ""), ("accepted", False)]
    updates = {fields[0].xref: "Somchai", fields[1].xref: True}
    update_form_fields(document.raw, state, updates)

    assert state.dirty is True
    SaveManager().save_as(document.raw, state, output_path)
    document.close()

    assert source_path.read_bytes() == original_bytes
    with fitz.open(str(output_path)) as saved:
        saved_fields = editable_form_fields(saved)
    assert [(field.name, field.value) for field in saved_fields] == [("customer_name", "Somchai"), ("accepted", True)]


def test_update_form_fields_rejects_no_changes(tmp_path: Path) -> None:
    """No-op form updates return a Thai user-facing error."""
    source_path = _create_form_pdf(tmp_path / "form.pdf")
    state = DocumentState()
    document = PdfDocument(state)
    document.open(source_path)
    fields = editable_form_fields(document.raw)

    with pytest.raises(InvalidOperationError) as exc_info:
        update_form_fields(document.raw, state, {fields[0].xref: ""})

    assert exc_info.value.user_message == "ข้อมูลฟอร์มไม่มีการเปลี่ยนแปลง"
    document.close()


def _create_form_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page(width=360, height=240)
    page.insert_text((40, 45), "Customer name", fontsize=11)
    text_widget = fitz.Widget()
    text_widget.field_name = "customer_name"
    text_widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    text_widget.field_value = ""
    text_widget.rect = fitz.Rect(40, 56, 250, 82)
    text_widget.border_color = (0, 0, 0)
    text_widget.border_width = 1
    page.add_widget(text_widget)

    page.insert_text((40, 120), "Accepted", fontsize=11)
    checkbox_widget = fitz.Widget()
    checkbox_widget.field_name = "accepted"
    checkbox_widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    checkbox_widget.field_value = False
    checkbox_widget.rect = fitz.Rect(110, 108, 130, 128)
    checkbox_widget.border_color = (0, 0, 0)
    checkbox_widget.border_width = 1
    page.add_widget(checkbox_widget)

    document.save(str(path))
    document.close()
    return path
