# -*- coding: utf-8 -*-
"""Document metadata, form, font, pending-overlay, and undo actions."""

from __future__ import annotations

from thai_pdf_editor.app.core.form_operations import editable_form_fields, update_form_fields
from thai_pdf_editor.app.core.font_importer import format_font_import_summary, import_fonts_for_document
from thai_pdf_editor.app.core.metadata_operations import editable_metadata, update_metadata
from thai_pdf_editor.app.core.text_edit_operations import (
    create_replace_text_operations,
    resolve_text_replace_page_indices,
)
from thai_pdf_editor.app.core.undo_redo import redo_last_pending, undo_last_pending
from thai_pdf_editor.app.ui.dialogs import (
    ask_form_field_values,
    ask_metadata_values,
    ask_replace_text_options,
    show_info,
)
from thai_pdf_editor.app.ui.pending_overlay_dialog import show_pending_overlay_manager


class DocumentEditActionsMixin:
    """Actions for document fields, metadata, font import, and pending operation management."""

    def edit_form_fields(self) -> None:
        """Edit supported existing PDF form fields."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        fields = editable_form_fields(self.document.raw)
        if not fields:
            self.status_bar.set_status("ไม่พบฟอร์ม PDF ที่รองรับ")
            show_info("ไม่พบ text field หรือ checkbox ที่แก้ไขได้ใน PDF นี้")
            return
        updates = ask_form_field_values(self, fields)
        if updates is None:
            return

        def action() -> None:
            update_form_fields(self.document.raw, self.doc_state, updates)
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status("แก้ฟอร์มแล้ว กรุณาบันทึกเป็นไฟล์ใหม่")

        self._run_user_action(action)

    def replace_existing_text(self) -> None:
        """Find existing text and safely replace it in the pending Save As output."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        _text, default_font_size, color, font_path = self.tool_panel.text_options()
        options = ask_replace_text_options(
            self,
            current_page=self.doc_state.display_page_number,
            total_pages=self.doc_state.total_pages,
            default_font_size=default_font_size,
        )
        if options is None:
            return

        def action() -> None:
            page_indices = resolve_text_replace_page_indices(
                str(options["page_scope"]),
                self.doc_state.current_page_index,
                self.doc_state.total_pages,
            )
            operations = create_replace_text_operations(
                self.document.raw,
                page_indices=page_indices,
                search_text=str(options["search_text"]),
                replacement_text=str(options["replacement_text"]),
                font_size=int(options["font_size"]),
                color=color,
                font_path=font_path,
            )
            for operation in operations:
                self.doc_state.record_operation(operation, pending=True)
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status(
                f"เตรียมแก้ข้อความเดิม {len(operations)} ตำแหน่งแล้ว กรุณาบันทึกเป็นไฟล์ใหม่"
            )

        self._run_user_action(action)

    def import_fonts_from_pdf(self) -> None:
        """Scan PDF font names and import a matching or similar font for editing."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return

        def action() -> None:
            self.status_bar.set_status("กำลังค้นหาและนำเข้าฟอนต์จาก PDF...")
            summary = import_fonts_for_document(self.document.raw, allow_download=True)
            self.tool_panel.set_font_path(summary.selected_font_path)
            self.status_bar.set_status(f"นำเข้าฟอนต์แล้ว: {summary.selected_font_path.name}")
            show_info(format_font_import_summary(summary))

        self._run_user_action(action)

    def manage_pending_overlays(self) -> None:
        """Open a manager for pending overlays before Save As."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        show_pending_overlay_manager(self, self.doc_state, on_changed=self._pending_overlays_changed)

    def _pending_overlays_changed(self) -> None:
        self.renderer.clear_cache()
        self.render_current_page()
        self.status_bar.set_status("ปรับรายการที่วางแล้ว กรุณาบันทึกเป็นไฟล์ใหม่")

    def undo_pending_operation(self) -> None:
        """Undo the latest pending overlay operation."""
        def action() -> None:
            undo_last_pending(self.doc_state)
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status("ย้อนกลับคำสั่งล่าสุดแล้ว")

        self._run_user_action(action)

    def redo_pending_operation(self) -> None:
        """Redo the latest pending overlay operation."""
        def action() -> None:
            redo_last_pending(self.doc_state)
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status("ทำซ้ำคำสั่งล่าสุดแล้ว")

        self._run_user_action(action)

    def edit_metadata(self) -> None:
        """Edit PDF metadata on the working copy."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        updates = ask_metadata_values(self, editable_metadata(self.document.raw))
        if updates is None:
            return

        def action() -> None:
            update_metadata(self.document.raw, self.doc_state, updates)
            self.status_bar.set_status("แก้ไขข้อมูลไฟล์แล้ว กรุณาบันทึกเป็นไฟล์ใหม่")

        self._run_user_action(action)
