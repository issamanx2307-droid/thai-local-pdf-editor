# -*- coding: utf-8 -*-
"""Page and overlay placement window actions."""

from __future__ import annotations

from pathlib import Path

from thai_pdf_editor.app.core.overlay_operations import (
    create_highlight_operation,
    create_image_operation,
    create_redact_operation,
    create_rectangle_operation,
    create_text_operation,
)
from thai_pdf_editor.app.core.signature_operations import create_visual_signature_image
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.ui.dialogs import (
    ask_font_path,
    ask_image_path,
    ask_save_pdf_path,
    ask_visual_signature_options,
    confirm,
    show_info,
)


class PageOverlayActionsMixin:
    """Actions for page operations and pending overlay placement."""

    def move_page_up(self) -> None:
        """Move the selected page up."""
        self._run_page_operation(lambda: self.page_operations.move_current_page(-1), "ย้ายหน้าขึ้นแล้ว")

    def move_page_down(self) -> None:
        """Move the selected page down."""
        self._run_page_operation(lambda: self.page_operations.move_current_page(1), "ย้ายหน้าลงแล้ว")

    def rotate_left(self) -> None:
        """Rotate the selected page left."""
        self._run_page_operation(lambda: self.page_operations.rotate_current_page(-90), "หมุนหน้าซ้ายแล้ว")

    def rotate_right(self) -> None:
        """Rotate the selected page right."""
        self._run_page_operation(lambda: self.page_operations.rotate_current_page(90), "หมุนหน้าขวาแล้ว")

    def duplicate_page(self) -> None:
        """Duplicate the selected page after itself."""
        self._run_page_operation(self.page_operations.duplicate_current_page, "ทำซ้ำหน้าแล้ว")

    def delete_page(self) -> None:
        """Delete the selected page after confirmation."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        if not confirm("ต้องการลบหน้าที่เลือกหรือไม่"):
            return
        self._run_page_operation(self.page_operations.delete_current_page, "ลบหน้าแล้ว")

    def extract_current_page(self) -> None:
        """Extract the selected page to a new PDF."""
        if not self.doc_state.has_document or self.doc_state.current_file_path is None:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        page_number = self.doc_state.current_page_index + 1
        default_path = self.doc_state.current_file_path.with_name(
            f"{self.doc_state.current_file_path.stem}_page_{page_number}.pdf"
        )
        path_text = ask_save_pdf_path(default_path)
        if not path_text:
            return

        def action() -> None:
            extracted_path = self.page_operations.extract_current_page(Path(path_text))
            self.status_bar.set_status(f"แยกหน้าสำเร็จ: {extracted_path.name}")
            show_info("แยกหน้า PDF สำเร็จ")

        self._run_user_action(action)

    def choose_font(self) -> None:
        """Choose a font file for PDF text insertion."""
        path_text = ask_font_path()
        if path_text:
            self.tool_panel.set_font_path(Path(path_text))
            self.status_bar.set_status("เลือกฟอนต์แล้ว")

    def choose_image(self) -> None:
        """Choose an image or visual signature file."""
        path_text = ask_image_path()
        if path_text:
            self.tool_panel.set_image_path(Path(path_text))
            self.status_bar.set_status("เลือกรูปภาพแล้ว")

    def create_simple_signature(self) -> None:
        """Create a local visual signature image from typed text."""
        options = ask_visual_signature_options(self)
        if options is None:
            return

        def action() -> None:
            placement_width = int(options["placement_width"])
            image_path = create_visual_signature_image(
                str(options["text"]),
                font_path=self.tool_panel.selected_font_path,
                width_px=placement_width * 4,
            )
            self.tool_panel.set_image_path(image_path)
            self.tool_panel.set_image_width(placement_width)
            if self.doc_state.has_document:
                self.activate_tool("image")
                self.status_bar.set_status("สร้างลายเซ็นภาพแล้ว คลิกตำแหน่งที่ต้องการวาง")
            else:
                self.status_bar.set_status("สร้างลายเซ็นภาพแล้ว เปิด PDF แล้วกดวางรูปเพื่อใช้งาน")

        self._run_user_action(action)

    def activate_tool(self, tool_name: str) -> None:
        """Activate an overlay tool for the next canvas click or drag."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("กรุณาเปิดไฟล์ PDF ก่อน")
            self.tool_panel.set_active_tool(None)
            return
        if tool_name == "redact" and not confirm(
            "การลบข้อมูลถาวรจะไม่สามารถกู้คืนได้ ควรบันทึกเป็นไฟล์ใหม่"
        ):
            return
        self.doc_state.selected_tool = tool_name
        tool_labels = {
            "text": "เพิ่มข้อความ",
            "image": "เพิ่มรูป/ลายเซ็นภาพ",
            "rectangle": "วาดกล่อง",
            "highlight": "Highlight",
            "crop": "Crop หน้า",
            "redact": "ลบ/ปิดทับข้อมูลถาวร",
        }
        self.tool_panel.set_active_tool(tool_labels.get(tool_name, tool_name))
        messages = {
            "text": "คลิกตำแหน่งที่ต้องการวางข้อความ",
            "image": "คลิกตำแหน่งที่ต้องการวางรูป",
            "rectangle": "ลากพื้นที่เพื่อวาดกล่อง",
            "highlight": "ลากพื้นที่เพื่อทำ highlight",
            "crop": "ลากพื้นที่ที่ต้องการเก็บไว้บนหน้า PDF",
            "redact": "ลากพื้นที่เพื่อลบ/ปิดทับข้อมูลถาวร",
        }
        self.status_bar.set_status(messages.get(tool_name, "เลือกเครื่องมือแล้ว"))

    def handle_canvas_click(self, point: PdfPoint) -> None:
        """Handle a canvas click for active text/image/shape tools."""
        self._run_user_action(lambda: self._handle_canvas_click(point))

    def _handle_canvas_click(self, point: PdfPoint) -> None:
        if self.doc_state.selected_tool == "text":
            self._add_text_overlay(point)
        elif self.doc_state.selected_tool == "image":
            self._add_image_overlay(point)
        elif self.doc_state.selected_tool in {"rectangle", "highlight", "redact"}:
            rect = PdfRect(
                point.x,
                point.y,
                point.x + self.settings.default_shape_width,
                point.y + self.settings.default_shape_height,
            )
            self.handle_canvas_rect(rect)

    def handle_canvas_rect(self, rect: PdfRect) -> None:
        """Handle a canvas drag rectangle for shape tools."""
        self._run_user_action(lambda: self._handle_canvas_rect(rect))

    def _handle_canvas_rect(self, rect: PdfRect) -> None:
        if self.doc_state.selected_tool == "rectangle":
            color, line_width = self.tool_panel.shape_options()
            operation = create_rectangle_operation(
                page_index=self.doc_state.current_page_index,
                rect=rect,
                color=color,
                line_width=line_width,
            )
            self._record_overlay(operation, "เพิ่มกล่องแล้ว")
        elif self.doc_state.selected_tool == "highlight":
            color, _line_width = self.tool_panel.shape_options()
            operation = create_highlight_operation(
                page_index=self.doc_state.current_page_index,
                rect=rect,
                color=color,
            )
            self._record_overlay(operation, "เพิ่ม highlight แล้ว")
        elif self.doc_state.selected_tool == "redact":
            operation = create_redact_operation(page_index=self.doc_state.current_page_index, rect=rect)
            self._record_overlay(operation, "เพิ่มพื้นที่ลบถาวรแล้ว")
        elif self.doc_state.selected_tool == "crop":
            self._run_page_operation(lambda: self.page_operations.crop_current_page(rect), "Crop หน้าแล้ว")

    def _add_text_overlay(self, point: PdfPoint) -> None:
        text, font_size, color, font_path = self.tool_panel.text_options()
        operation = create_text_operation(
            page_index=self.doc_state.current_page_index,
            point=point,
            text=text,
            font_size=font_size,
            color=color,
            font_path=font_path,
        )
        self._record_overlay(operation, "เพิ่มข้อความแล้ว")

    def _add_image_overlay(self, point: PdfPoint) -> None:
        image_path, width = self.tool_panel.image_options()
        if image_path is None:
            self.status_bar.set_status("กรุณาเลือกรูปภาพก่อน")
            return
        operation = create_image_operation(
            page_index=self.doc_state.current_page_index,
            point=point,
            image_path=image_path,
            width=width,
        )
        self._record_overlay(operation, "เพิ่มรูปภาพแล้ว")

    def _record_overlay(self, operation: object, success_message: str) -> None:
        self.doc_state.record_operation(operation, pending=True)
        self.renderer.clear_cache()
        self.render_current_page()
        self.status_bar.set_status(success_message)

    def _run_page_operation(self, operation: object, success_message: str) -> None:
        def action() -> None:
            self._sync_page_operation_target_from_list()
            operation()
            self.renderer.clear_cache()
            self.render_current_page()
            self.status_bar.set_status(success_message)

        self._run_user_action(action)

    def _sync_page_operation_target_from_list(self) -> None:
        selected_page_index = self.page_panel.selected_page_index()
        if selected_page_index is None:
            return
        if not 0 <= selected_page_index < self.doc_state.total_pages:
            return
        if selected_page_index != self.doc_state.current_page_index:
            self.doc_state.set_current_page(selected_page_index)
