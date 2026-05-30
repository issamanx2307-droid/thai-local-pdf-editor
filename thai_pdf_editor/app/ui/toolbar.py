# -*- coding: utf-8 -*-
"""Top ribbon toolbar for document commands and navigation."""

from collections.abc import Callable

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import ENTRY_FONT, ENTRY_HEIGHT, LABEL_FONT, TOOLBAR_GROUP_FONT, TOOLBAR_HEIGHT
from thai_pdf_editor.app.ui.theme import (
    COLORS,
    RADIUS_PANEL,
    RIBBON_BUTTON_HEIGHT,
    bind_button_depth,
    icon_label,
    ribbon_button_style,
)


class Toolbar(ctk.CTkFrame):
    """Top action toolbar grouped like a desktop ribbon."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_open: Callable[[], None],
        on_open_recent: Callable[[], None],
        on_save_as: Callable[[], None],
        on_search: Callable[[], None],
        on_undo: Callable[[], None],
        on_redo: Callable[[], None],
        on_merge_pdfs: Callable[[], None],
        on_edit_metadata: Callable[[], None],
        on_prev: Callable[[], None],
        on_next: Callable[[], None],
        on_zoom_in: Callable[[], None],
        on_zoom_out: Callable[[], None],
        on_fit_width: Callable[[], None],
        on_fit_height: Callable[[], None],
        on_go_to_page: Callable[[int], None],
        on_usage_guide: Callable[[], None],
        on_reset_layout: Callable[[], None],
        on_print: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            height=TOOLBAR_HEIGHT,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS_PANEL,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.on_go_to_page = on_go_to_page
        for column in range(16):
            self.grid_columnconfigure(column, weight=0)
        self.grid_columnconfigure(16, weight=1)

        col = 0
        file_group = self._group("ไฟล์", col); col += 1
        self.open_button   = self._ribbon_button(file_group, "เปิดไฟล์", "open",   on_open,         "primary", 0)
        self.recent_button = self._ribbon_button(file_group, "ล่าสุด",   "recent", on_open_recent,  "secondary", 1)
        self.save_button   = self._ribbon_button(file_group, "บันทึก",   "save",   on_save_as,      "secondary", 2)
        self.print_button  = self._ribbon_button(file_group, "พิมพ์",    "print",  on_print,        "secondary", 3)
        self._sep(col); col += 1

        edit_group = self._group("แก้ไข", col); col += 1
        self.undo_button = self._ribbon_button(edit_group, "ย้อนกลับ", "undo", on_undo, "secondary", 0)
        self.redo_button = self._ribbon_button(edit_group, "ทำซ้ำ",    "redo", on_redo, "secondary", 1)
        self._sep(col); col += 1

        page_group = self._group("จัดการหน้า", col); col += 1
        self.merge_button = self._ribbon_button(page_group, "รวม PDF", "merge", on_merge_pdfs, "secondary", 0)
        self._sep(col); col += 1

        info_group = self._group("ข้อมูล", col); col += 1
        self.metadata_button = self._ribbon_button(info_group, "ข้อมูล", "info", on_edit_metadata, "secondary", 0)
        self._sep(col); col += 1

        search_group = self._group("ค้นหา", col); col += 1
        self.search_button = self._ribbon_button(search_group, "ค้นหา", "search", on_search, "secondary", 0)
        self._sep(col); col += 1

        view_group = self._group("มุมมอง", col); col += 1
        self.zoom_out_button = self._ribbon_button(view_group, "ซูม−", "zoom_out", on_zoom_out, "secondary", 0)
        self.zoom_label = ctk.CTkLabel(
            view_group,
            text="100%",
            width=64,
            height=34,
            fg_color=COLORS["surface_soft"],
            corner_radius=6,
            font=LABEL_FONT,
            text_color=COLORS["text"],
        )
        self.zoom_label.grid(row=1, column=1, padx=5, pady=(2, 4))
        self.zoom_in_button = self._ribbon_button(view_group, "ซูม+", "zoom_in", on_zoom_in, "secondary", 2)
        self.fit_width_button = self._ribbon_button(
            view_group, "พอดีกว้าง", "fit_width", on_fit_width, "secondary", 3, width=100,
        )
        self.fit_height_button = self._ribbon_button(
            view_group, "พอดีบน-ล่าง", "fit_height", on_fit_height, "secondary", 4, width=122,
        )
        self._sep(col); col += 1

        nav_group = self._group("ไปที่หน้า", col); col += 1
        self.prev_button = self._ribbon_button(nav_group, "ก่อน", "prev", on_prev, "secondary", 0)
        self.page_entry = ctk.CTkEntry(
            nav_group,
            width=58,
            height=38,
            justify="center",
            font=ENTRY_FONT,
            border_color=COLORS["border"],
        )
        self.page_entry.grid(row=1, column=1, padx=(5, 3), pady=(2, 4))
        self.page_entry.bind("<Return>", self._go_to_page)
        self.page_label = ctk.CTkLabel(nav_group, text="/ 0", width=30, font=LABEL_FONT, text_color=COLORS["muted"])
        self.page_label.grid(row=1, column=2, padx=(0, 5), pady=(2, 4))
        self.next_button = self._ribbon_button(nav_group, "ถัด", "next", on_next, "secondary", 3)
        self._sep(col); col += 1

        help_group = self._group("ช่วยเหลือ", col)
        self.usage_guide_button = self._ribbon_button(
            help_group, "คู่มือ", "help", on_usage_guide, "secondary", 0, width=80,
        )
        self.reset_layout_button = self._ribbon_button(
            help_group, "คืนค่าหน้าจอ", "reset", on_reset_layout, "secondary", 1, width=108,
        )

    def _group(self, title: str, column: int) -> ctk.CTkFrame:
        group = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        group.grid(row=0, column=column, sticky="nw", padx=(8 if column == 0 else 2, 2), pady=(2, 2))
        ctk.CTkLabel(
            group, text=title,
            font=TOOLBAR_GROUP_FONT,
            text_color=COLORS["muted"],
        ).grid(row=0, column=0, columnspan=8, sticky="ew", pady=(0, 0))
        return group

    def _sep(self, column: int) -> None:
        """Insert a 1-px hairline vertical separator at *column*."""
        ctk.CTkFrame(
            self,
            width=1,
            height=RIBBON_BUTTON_HEIGHT + 18,
            fg_color=COLORS["border"],
            corner_radius=0,
        ).grid(row=0, column=column, sticky="n", padx=2, pady=10)

    def _ribbon_button(
        self,
        master: ctk.CTkBaseClass,
        label: str,
        icon_name: str,
        command: Callable[[], None],
        variant: str,
        column: int,
        width: int | None = None,
    ) -> ctk.CTkButton:
        options = ribbon_button_style(variant)
        if width is not None:
            options["width"] = width
        button = ctk.CTkButton(
            master,
            text=icon_label(icon_name, label, stacked=True),
            command=command,
            **options,
        )
        button.grid(row=1, column=column, padx=3, pady=(1, 2))
        return bind_button_depth(button, variant)

    def set_document_state(
        self,
        current_page: int,
        total_pages: int,
        zoom: float,
        *,
        can_undo: bool,
        can_redo: bool,
    ) -> None:
        """Sync navigation labels with document state."""
        has_document = total_pages > 0
        self.page_entry.configure(state="normal")
        self.page_entry.delete(0, "end")
        if total_pages:
            self.page_entry.insert(0, str(current_page))
        self.page_label.configure(text=f"/ {total_pages}")
        self.zoom_label.configure(text=f"{round(zoom * 100)}%")
        self.save_button.configure(state="normal" if has_document else "disabled")
        self.print_button.configure(state="normal" if has_document else "disabled")
        self.search_button.configure(state="normal" if has_document else "disabled")
        self.undo_button.configure(state="normal" if can_undo else "disabled")
        self.redo_button.configure(state="normal" if can_redo else "disabled")
        self.metadata_button.configure(state="normal" if has_document else "disabled")
        self.prev_button.configure(state="normal" if current_page > 1 else "disabled")
        self.next_button.configure(state="normal" if has_document and current_page < total_pages else "disabled")
        self.page_entry.configure(state="normal" if has_document else "disabled")
        self.zoom_out_button.configure(state="normal" if has_document else "disabled")
        self.zoom_in_button.configure(state="normal" if has_document else "disabled")
        self.fit_width_button.configure(state="normal" if has_document else "disabled")
        self.fit_height_button.configure(state="normal" if has_document else "disabled")

    def _go_to_page(self, _event: object) -> None:
        raw_value = self.page_entry.get().strip()
        if not raw_value.isdigit():
            return
        self.on_go_to_page(int(raw_value) - 1)
