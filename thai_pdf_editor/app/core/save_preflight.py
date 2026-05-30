# -*- coding: utf-8 -*-
"""Build Save As preflight summaries."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation

OPERATION_LABELS = {
    OperationType.ROTATE_PAGE: "หมุนหน้า",
    OperationType.DELETE_PAGE: "ลบหน้า",
    OperationType.MOVE_PAGE: "ย้ายหน้า",
    OperationType.DUPLICATE_PAGE: "ทำซ้ำหน้า",
    OperationType.CROP_PAGE: "Crop หน้า",
    OperationType.UPDATE_METADATA: "แก้ข้อมูลไฟล์",
    OperationType.UPDATE_FORM_FIELDS: "แก้ฟอร์ม PDF",
    OperationType.ADD_TEXT: "ข้อความ",
    OperationType.ADD_IMAGE: "รูป/ลายเซ็นภาพ",
    OperationType.DRAW_RECTANGLE: "กล่อง",
    OperationType.HIGHLIGHT: "Highlight",
    OperationType.REDACT: "ลบ/ปิดทับข้อมูลถาวร",
    OperationType.REPLACE_TEXT: "แก้ข้อความเดิม",
}

REDACTION_TYPES = {OperationType.REDACT, OperationType.REPLACE_TEXT}


def build_save_preflight_message(state: DocumentState) -> str:
    """Return a Thai confirmation message for Save As."""
    pending_counts = _operation_counts(state.pending_operations)
    applied_counts = _operation_counts(state.applied_operations)
    redaction_count = sum(1 for operation in state.pending_operations if operation.type in REDACTION_TYPES)
    lines = ["สรุปก่อนบันทึกเป็นไฟล์ใหม่", ""]

    if pending_counts:
        lines.append("รายการที่รอเขียนตอน Save As:")
        lines.extend(_count_lines(pending_counts))
    else:
        lines.append("รายการที่รอเขียนตอน Save As: ไม่มี")

    if applied_counts:
        lines.append("")
        lines.append("รายการที่แก้ใน working copy แล้ว:")
        lines.extend(_count_lines(applied_counts))

    if redaction_count:
        lines.append("")
        lines.append(f"คำเตือน: มี redaction/แก้ข้อความเดิม {redaction_count} รายการ")
        lines.append("เมื่อบันทึกแล้วข้อมูลเดิมในไฟล์ปลายทางจะกู้คืนไม่ได้")

    lines.append("")
    lines.append("ต้องการบันทึกต่อหรือไม่")
    return "\n".join(lines)


def build_save_preflight_details(state: DocumentState) -> list[str]:
    """Return page-level Save As details for review before writing output."""
    details: list[str] = []
    details.extend(_operation_detail_lines("รอ Save As", state.pending_operations))
    details.extend(_operation_detail_lines("แก้ใน working copy แล้ว", state.applied_operations))
    return details or ["ไม่มีรายการเปลี่ยนแปลง"]


def has_save_preflight_items(state: DocumentState) -> bool:
    """Return True when Save As should show a preflight summary."""
    return bool(state.pending_operations or state.applied_operations)


def _operation_counts(operations: list[object]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for operation in operations:
        if isinstance(operation, PdfOperation):
            counter[OPERATION_LABELS.get(operation.type, str(operation.type))] += 1
    return counter


def _count_lines(counts: Counter[str]) -> list[str]:
    return [f"- {label}: {count} รายการ" for label, count in sorted(counts.items())]


def _operation_detail_lines(section: str, operations: list[object]) -> list[str]:
    lines: list[str] = []
    for operation in operations:
        if not isinstance(operation, PdfOperation):
            continue
        label = OPERATION_LABELS.get(operation.type, str(operation.type))
        lines.append(f"{section}: หน้า {operation.page_index + 1} - {label}{_payload_detail(operation)}")
    return lines


def _payload_detail(operation: PdfOperation) -> str:
    payload = operation.payload
    if operation.type == OperationType.ADD_TEXT:
        return f" - {_short_text(str(payload.get('text', '')))}"
    if operation.type == OperationType.REPLACE_TEXT:
        return f" - ค้นหา {_short_text(str(payload.get('search_text', '')))}"
    if operation.type == OperationType.ADD_IMAGE:
        return f" - {Path(str(payload.get('image_path', ''))).name}"
    if operation.type == OperationType.ROTATE_PAGE:
        return f" - {payload.get('degrees')} องศา"
    if operation.type == OperationType.MOVE_PAGE:
        return f" - จากหน้า {int(payload.get('from', 0)) + 1} ไปหน้า {int(payload.get('to', 0)) + 1}"
    if operation.type == OperationType.DUPLICATE_PAGE:
        return f" - จากหน้า {int(payload.get('source_page', 0)) + 1}"
    if operation.type == OperationType.UPDATE_FORM_FIELDS:
        changed_xrefs = payload.get("changed_xrefs", [])
        if isinstance(changed_xrefs, list):
            return f" - {len(changed_xrefs)} field"
        after_values = payload.get("after", {})
        return f" - {len(after_values) if isinstance(after_values, dict) else 0} field"
    if operation.type == OperationType.UPDATE_METADATA:
        after = payload.get("after", {})
        if isinstance(after, dict):
            changed = [key for key, value in after.items() if value]
            return f" - {', '.join(changed) if changed else 'metadata'}"
    return ""


def _short_text(text: str, limit: int = 36) -> str:
    clean_text = " ".join(text.split())
    if len(clean_text) <= limit:
        return f'"{clean_text}"'
    return f'"{clean_text[: limit - 3]}..."'
