# -*- coding: utf-8 -*-
"""Right tool panel for overlay and document tools."""

import sys
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import ENTRY_FONT, ENTRY_HEIGHT, LABEL_FONT, MENU_FONT, TOOL_PANEL_WIDTH
from thai_pdf_editor.app.ui.scrolling import ctk_scroll_units_with_remainder
from thai_pdf_editor.app.ui.theme import (
    COLORS,
    PANEL_PAD,
    RADIUS_CONTROL,
    icon_label,
    make_button,
    make_section,
    panel_style,
)


class ToolPanel(ctk.CTkScrollableFrame):
    """Overlay tool controls with grouped editor sections."""

    COLOR_OPTIONS = {
        "ดำ": "#111111",
        "แดง": "#d32f2f",
        "น้ำเงิน": "#1565c0",
        "เหลือง": "#fff176",
    }

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_choose_font: Callable[[], None],
        on_choose_image: Callable[[], None],
        on_create_signature: Callable[[], None],
        on_text_tool: Callable[[], None],
        on_image_tool: Callable[[], None],
        on_rectangle_tool: Callable[[], None],
        on_highlight_tool: Callable[[], None],
        on_crop_tool: Callable[[], None],
        on_redact_tool: Callable[[], None],
        on_edit_metadata: Callable[[], None],
    ) -> None:
        super().__init__(master, width=TOOL_PANEL_WIDTH, **panel_style())
        self.grid_columnconfigure(0, weight=1)
        self.selected_font_path: Path | None = None
        self.selected_image_path: Path | None = None
        self._document_tool_buttons: list[ctk.CTkButton] = []
        self._ctk_wheel_remainder_x = 0.0
        self._ctk_wheel_remainder_y = 0.0
        entry_style = {
            "height": ENTRY_HEIGHT,
            "font": ENTRY_FONT,
            "border_color": COLORS["border"],
            "corner_radius": RADIUS_CONTROL,
        }
        menu_style = {
            "font": MENU_FONT,
            "dropdown_font": MENU_FONT,
            "button_color": COLORS["primary"],
            "button_hover_color": COLORS["primary_hover"],
            "fg_color": COLORS["surface_soft"],
            "text_color": COLORS["text"],
        }

        header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=PANEL_PAD, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=icon_label("shape", "เครื่องมือ"),
            anchor="w",
            font=(LABEL_FONT[0], 15, "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="⌄", width=20, font=LABEL_FONT, text_color=COLORS["muted"]).grid(
            row=0,
            column=1,
            sticky="e",
        )

        self.active_tool_label = ctk.CTkLabel(
            self,
            text="เครื่องมือที่ใช้: ไม่มี",
            anchor="w",
            font=LABEL_FONT,
            text_color=COLORS["muted"],
            fg_color=COLORS["surface_soft"],
            corner_radius=RADIUS_CONTROL,
        )
        self.active_tool_label.grid(row=1, column=0, sticky="ew", padx=PANEL_PAD, pady=(0, 8))

        text_section = make_section(self, title="ข้อความ", icon_name="text", row=2)
        self.text_entry = ctk.CTkEntry(text_section, placeholder_text="ข้อความ", **entry_style)
        self.text_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        text_option_row = ctk.CTkFrame(text_section, fg_color="transparent", corner_radius=0)
        text_option_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        text_option_row.grid_columnconfigure(0, weight=1)
        text_option_row.grid_columnconfigure(2, weight=1)
        self.text_size_entry = ctk.CTkEntry(text_option_row, placeholder_text="ขนาด", width=82, **entry_style)
        self.text_size_entry.insert(0, "16")
        self.text_size_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.text_color_swatch = ctk.CTkLabel(
            text_option_row,
            text="",
            width=28,
            height=28,
            fg_color=self.COLOR_OPTIONS["ดำ"],
            corner_radius=4,
        )
        self.text_color_swatch.grid(row=0, column=1, padx=(0, 6))
        self.text_color_menu = ctk.CTkOptionMenu(
            text_option_row,
            values=list(self.COLOR_OPTIONS),
            width=116,
            command=lambda _value: self._sync_color_swatches(),
            **menu_style,
        )
        self.text_color_menu.set("ดำ")
        self.text_color_menu.grid(row=0, column=2, sticky="ew")

        self.font_label = ctk.CTkLabel(
            text_section,
            text="ฟอนต์: ค่าเริ่มต้น",
            anchor="w",
            font=LABEL_FONT,
            text_color=COLORS["muted"],
        )
        self.font_label.grid(row=3, column=0, sticky="ew", pady=(0, 6))

        self.font_button = make_button(
            text_section,
            text="เลือกฟอนต์ไทย",
            icon_name="font",
            command=on_choose_font,
            variant="secondary",
        )
        self.font_button.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        self.text_button = make_button(
            text_section,
            text="วางข้อความ",
            icon_name="text",
            command=on_text_tool,
            variant="primary",
        )
        self.text_button.grid(row=5, column=0, sticky="ew")

        image_section = make_section(self, title="รูปภาพ / ลายเซ็น", icon_name="image", row=3)
        self.image_label = ctk.CTkLabel(
            image_section,
            text="รูป: ยังไม่ได้เลือก",
            anchor="w",
            font=LABEL_FONT,
            text_color=COLORS["muted"],
        )
        self.image_label.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.image_button = make_button(
            image_section,
            text="เลือกรูป/ลายเซ็นภาพ",
            icon_name="image",
            command=on_choose_image,
            variant="primary",
        )
        self.image_button.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.create_signature_button = make_button(
            image_section,
            text="สร้างลายเซ็นภาพ",
            icon_name="signature",
            command=on_create_signature,
            variant="secondary",
        )
        self.create_signature_button.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        image_place_row = ctk.CTkFrame(image_section, fg_color="transparent", corner_radius=0)
        image_place_row.grid(row=4, column=0, sticky="ew")
        image_place_row.grid_columnconfigure(0, weight=1)
        image_place_row.grid_columnconfigure(1, weight=1)
        self.image_width_entry = ctk.CTkEntry(image_place_row, placeholder_text="ความกว้างรูป", **entry_style)
        self.image_width_entry.insert(0, "140")
        self.image_width_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.place_image_button = make_button(
            image_place_row,
            text="วางรูป",
            icon_name="image",
            command=on_image_tool,
            variant="primary",
        )
        self.place_image_button.grid(row=0, column=1, sticky="ew")

        shape_section = make_section(self, title="รูปทรง", icon_name="shape", row=4)
        shape_option_row = ctk.CTkFrame(shape_section, fg_color="transparent", corner_radius=0)
        shape_option_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        shape_option_row.grid_columnconfigure(2, weight=1)
        self.shape_color_swatch = ctk.CTkLabel(
            shape_option_row,
            text="",
            width=28,
            height=28,
            fg_color=self.COLOR_OPTIONS["แดง"],
            corner_radius=4,
        )
        self.shape_color_swatch.grid(row=0, column=0, padx=(0, 6))
        self.shape_color_menu = ctk.CTkOptionMenu(
            shape_option_row,
            values=list(self.COLOR_OPTIONS),
            width=120,
            command=lambda _value: self._sync_color_swatches(),
            **menu_style,
        )
        self.shape_color_menu.set("แดง")
        self.shape_color_menu.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.line_width_entry = ctk.CTkEntry(shape_option_row, placeholder_text="หนา", width=74, **entry_style)
        self.line_width_entry.insert(0, "2")
        self.line_width_entry.grid(row=0, column=2, sticky="ew")
        self.rectangle_button = make_button(
            shape_section,
            text="วาดกล่อง",
            icon_name="shape",
            command=on_rectangle_tool,
            variant="primary",
        )
        self.rectangle_button.grid(row=2, column=0, sticky="ew")

        highlight_section = make_section(self, title="ไฮไลต์", icon_name="highlight", row=5)
        self.highlight_button = make_button(
            highlight_section,
            text="Highlight",
            icon_name="highlight",
            command=on_highlight_tool,
            variant="warning",
        )
        self.highlight_button.grid(row=1, column=0, sticky="ew")

        crop_section = make_section(self, title="ครอบหน้า", icon_name="crop", row=6)
        self.crop_button = make_button(
            crop_section,
            text="Crop หน้า",
            icon_name="crop",
            command=on_crop_tool,
            variant="secondary",
        )
        self.crop_button.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.redact_button = make_button(
            crop_section,
            text="ลบ/ปิดทับข้อมูลถาวร",
            icon_name="redact",
            command=on_redact_tool,
            variant="danger",
        )
        self.redact_button.grid(row=2, column=0, sticky="ew")

        info_section = make_section(self, title="ข้อมูลเอกสาร", icon_name="info", row=7)
        self.metadata_button = make_button(
            info_section,
            text="ดูข้อมูลเอกสาร",
            icon_name="info",
            command=on_edit_metadata,
            variant="secondary",
        )
        self.metadata_button.grid(row=1, column=0, sticky="ew")

        self._document_tool_buttons = [
            self.text_button,
            self.place_image_button,
            self.rectangle_button,
            self.highlight_button,
            self.crop_button,
            self.redact_button,
            self.metadata_button,
        ]
        self.set_document_loaded(False)

    def set_font_path(self, path: Path) -> None:
        """Display the selected font path."""
        self.selected_font_path = path
        self.font_label.configure(text=f"ฟอนต์: {path.name}")

    def set_image_path(self, path: Path) -> None:
        """Display the selected image path."""
        self.selected_image_path = path
        self.image_label.configure(text=f"รูป: {path.name}")

    def set_image_width(self, width: int) -> None:
        """Set the default PDF placement width for selected images."""
        self.image_width_entry.delete(0, "end")
        self.image_width_entry.insert(0, str(max(1, int(width))))

    def set_active_tool(self, tool_label: str | None) -> None:
        """Display the currently selected overlay tool."""
        label = tool_label if tool_label else "ไม่มี"
        self.active_tool_label.configure(text=f"เครื่องมือที่ใช้: {label}")

    def set_document_loaded(self, is_loaded: bool) -> None:
        """Enable overlay placement only when a PDF document is open."""
        state = "normal" if is_loaded else "disabled"
        for button in self._document_tool_buttons:
            button.configure(state=state)
        if not is_loaded:
            self.set_active_tool(None)

    def _mouse_wheel_all(self, event: object) -> None:
        if not self.check_if_master_is_canvas(event.widget):
            return
        delta = int(getattr(event, "delta", 0) or 0)
        if self._shift_pressed:
            if self._parent_canvas.xview() != (0.0, 1.0):
                units, self._ctk_wheel_remainder_x = ctk_scroll_units_with_remainder(
                    delta,
                    platform_name=sys.platform,
                    remainder=getattr(self, "_ctk_wheel_remainder_x", 0.0),
                )
                if units:
                    self._parent_canvas.xview("scroll", units, "units")
        elif self._parent_canvas.yview() != (0.0, 1.0):
            units, self._ctk_wheel_remainder_y = ctk_scroll_units_with_remainder(
                delta,
                platform_name=sys.platform,
                remainder=getattr(self, "_ctk_wheel_remainder_y", 0.0),
            )
            if units:
                self._parent_canvas.yview("scroll", units, "units")

    def text_options(self) -> tuple[str, int, str, Path | None]:
        """Return current text overlay options."""
        return (
            self.text_entry.get(),
            self._int_value(self.text_size_entry.get(), 16),
            self.COLOR_OPTIONS.get(self.text_color_menu.get(), "#111111"),
            self.selected_font_path,
        )

    def image_options(self) -> tuple[Path | None, int]:
        """Return current image overlay options."""
        return (self.selected_image_path, self._int_value(self.image_width_entry.get(), 140))

    def shape_options(self) -> tuple[str, int]:
        """Return current shape options."""
        return (
            self.COLOR_OPTIONS.get(self.shape_color_menu.get(), "#d32f2f"),
            self._int_value(self.line_width_entry.get(), 2),
        )

    def _sync_color_swatches(self) -> None:
        self.text_color_swatch.configure(fg_color=self.COLOR_OPTIONS.get(self.text_color_menu.get(), "#111111"))
        self.shape_color_swatch.configure(fg_color=self.COLOR_OPTIONS.get(self.shape_color_menu.get(), "#d32f2f"))

    def _int_value(self, value: str, fallback: int) -> int:
        try:
            return max(1, int(value))
        except ValueError:
            return fallback
