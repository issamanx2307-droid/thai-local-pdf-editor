# -*- coding: utf-8 -*-
"""Read and update existing PDF form fields."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation

LOGGER = logging.getLogger("thai_pdf_editor.form_operations")

SUPPORTED_FORM_TYPES = {
    fitz.PDF_WIDGET_TYPE_TEXT,
    fitz.PDF_WIDGET_TYPE_CHECKBOX,
}


@dataclass(frozen=True)
class FormField:
    """Editable PDF form field exposed by the app."""

    xref: int
    page_index: int
    name: str
    field_type: int
    field_type_label: str
    value: str | bool

    @property
    def is_checkbox(self) -> bool:
        """Return True when this form field is a checkbox."""
        return self.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX


def editable_form_fields(document: fitz.Document) -> list[FormField]:
    """Return supported existing form fields in document order."""
    fields: list[FormField] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        for widget in page.widgets() or []:
            if widget.field_type not in SUPPORTED_FORM_TYPES:
                continue
            name = str(widget.field_name or f"field_{widget.xref}")
            fields.append(
                FormField(
                    xref=int(widget.xref),
                    page_index=page_index,
                    name=name,
                    field_type=int(widget.field_type),
                    field_type_label=_field_type_label(widget),
                    value=_field_value(widget),
                )
            )
    return fields


def update_form_fields(
    document: fitz.Document,
    state: DocumentState,
    updates: dict[int, str | bool],
) -> PdfOperation:
    """Update existing text fields and checkboxes on the working PDF."""
    if not state.has_document:
        raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")
    if not updates:
        raise InvalidOperationError("ไม่มีข้อมูลฟอร์มให้บันทึก")

    before: dict[int, str | bool] = {}
    after: dict[int, str | bool] = {}
    changed_xrefs: list[int] = []
    normalized_updates = {int(xref): value for xref, value in updates.items()}

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        for widget in page.widgets() or []:
            xref = int(widget.xref)
            if widget.field_type not in SUPPORTED_FORM_TYPES or xref not in normalized_updates:
                continue
            old_value = _field_value(widget)
            new_value = _normalize_value(widget, normalized_updates[xref])
            before[xref] = old_value
            after[xref] = new_value
            if old_value == new_value:
                continue
            widget.field_value = _widget_value(widget, new_value)
            widget.update()
            changed_xrefs.append(xref)

    if not changed_xrefs:
        raise InvalidOperationError("ข้อมูลฟอร์มไม่มีการเปลี่ยนแปลง")

    try:
        document.need_appearances(True)
    except Exception:
        LOGGER.debug("could not set need_appearances flag", exc_info=True)

    operation = PdfOperation(
        type=OperationType.UPDATE_FORM_FIELDS,
        page_index=state.current_page_index,
        payload={
            "changed_xrefs": changed_xrefs,
            "before": before,
            "after": after,
        },
    )
    state.record_operation(operation)
    LOGGER.info("updated form fields count=%s", len(changed_xrefs))
    return operation


def _field_type_label(widget: fitz.Widget) -> str:
    if widget.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
        return "ข้อความ"
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        return "checkbox"
    return str(widget.field_type_string or "ไม่รองรับ")


def _field_value(widget: fitz.Widget) -> str | bool:
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        return str(widget.field_value) == str(widget.on_state())
    return str(widget.field_value or "")


def _normalize_value(widget: fitz.Widget, value: str | bool) -> str | bool:
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on", "checked"}
    return str(value)


def _widget_value(widget: fitz.Widget, value: str | bool) -> str:
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        return str(widget.on_state()) if bool(value) else "Off"
    return str(value)
