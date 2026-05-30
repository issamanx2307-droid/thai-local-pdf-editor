# -*- coding: utf-8 -*-
"""Document metadata operations."""

from __future__ import annotations

import logging

import fitz

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation

LOGGER = logging.getLogger("thai_pdf_editor.metadata_operations")

EDITABLE_METADATA_FIELDS = ("title", "author", "subject", "keywords")


def editable_metadata(document: fitz.Document) -> dict[str, str]:
    """Return metadata fields exposed in the UI."""
    metadata = document.metadata or {}
    return {field: str(metadata.get(field) or "") for field in EDITABLE_METADATA_FIELDS}


def update_metadata(document: fitz.Document, state: DocumentState, updates: dict[str, str]) -> PdfOperation:
    """Update safe editable metadata fields on the working document."""
    if not state.has_document:
        raise InvalidOperationError("ยังไม่ได้เปิดไฟล์ PDF")

    cleaned_updates = {
        field: str(updates.get(field, "")).strip()
        for field in EDITABLE_METADATA_FIELDS
        if field in updates
    }
    if not cleaned_updates:
        raise InvalidOperationError("ไม่มีข้อมูล metadata ให้บันทึก")

    before = editable_metadata(document)
    after = {**before, **cleaned_updates}
    if after == before:
        raise InvalidOperationError("metadata ไม่มีการเปลี่ยนแปลง")

    metadata = dict(document.metadata or {})
    metadata.update(after)
    document.set_metadata(metadata)

    operation = PdfOperation(
        type=OperationType.UPDATE_METADATA,
        page_index=state.current_page_index,
        payload={"before": before, "after": after},
    )
    state.record_operation(operation)
    LOGGER.info("updated metadata fields=%s", sorted(cleaned_updates))
    return operation
