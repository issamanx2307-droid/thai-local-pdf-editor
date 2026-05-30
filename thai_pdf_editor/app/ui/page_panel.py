# -*- coding: utf-8 -*-
"""Left page list panel."""

import sys
from collections.abc import Callable
from tkinter import Listbox, Scrollbar

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import LISTBOX_FONT, PAGE_LIST_MIN_HEIGHT, PAGE_PANEL_WIDTH, TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import (
    SCROLLBAR_WIDTH,
    ctk_scroll_units_with_remainder,
    event_wheel_scroll_units_with_remainder,
)
from thai_pdf_editor.app.ui.theme import COLORS, PANEL_PAD, icon_label, make_button, panel_style


class PagePanel(ctk.CTkScrollableFrame):
    """Page list and page-operation buttons."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_select_page: Callable[[int], None],
        on_move_up: Callable[[], None],
        on_move_down: Callable[[], None],
        on_duplicate_page: Callable[[], None],
        on_rotate_left: Callable[[], None],
        on_rotate_right: Callable[[], None],
        on_delete_page: Callable[[], None],
        on_extract_page: Callable[[], None],
        on_edit_form: Callable[[], None],
        on_replace_text: Callable[[], None],
        on_import_fonts: Callable[[], None],
        on_manage_pending_overlays: Callable[[], None],
        on_export_jpg: Callable[[], None],
        on_batch_jpg: Callable[[], None],
        on_open_qa_checklist: Callable[[], None],
    ) -> None:
        super().__init__(master, width=PAGE_PANEL_WIDTH, **panel_style())
        self.grid_rowconfigure(1, weight=1, minsize=PAGE_LIST_MIN_HEIGHT)
        self.grid_columnconfigure((0, 1), weight=1)
        self.on_select_page = on_select_page
        self._listed_total_pages: int | None = None
        self._selected_page_index: int | None = None
        self._refreshing = False
        self._button_states: dict[str, str] = {}
        self._list_wheel_remainder = 0.0
        self._ctk_wheel_remainder_x = 0.0
        self._ctk_wheel_remainder_y = 0.0

        title_row = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        title_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=PANEL_PAD, pady=(12, 6))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_row,
            text=icon_label("split", "รายการหน้า"),
            anchor="w",
            font=TITLE_FONT,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(title_row, text="⋮", width=24, text_color=COLORS["muted"], font=TITLE_FONT).grid(
            row=0,
            column=1,
            sticky="e",
        )

        self.listbox = Listbox(
            self,
            exportselection=False,
            height=18,
            font=LISTBOX_FONT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["primary"],
            background=COLORS["surface_soft"],
            foreground=COLORS["text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            disabledforeground=COLORS["muted"],
        )
        self.listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(PANEL_PAD, 0), pady=6)
        self.page_scroll = Scrollbar(self, orient="vertical", command=self.listbox.yview, width=SCROLLBAR_WIDTH)
        self.page_scroll.grid(row=1, column=2, sticky="ns", padx=(0, PANEL_PAD), pady=6)
        self.listbox.configure(yscrollcommand=self.page_scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self._handle_select)
        self._bind_page_list_mouse_wheel()

        self.move_up_button = make_button(self, text="ขึ้น", icon_name="up", command=on_move_up, width=108)
        self.move_up_button.grid(row=2, column=0, padx=(PANEL_PAD, 4), pady=4, sticky="ew")
        self.move_down_button = make_button(self, text="ลง", icon_name="down", command=on_move_down, width=108)
        self.move_down_button.grid(row=2, column=1, padx=(4, PANEL_PAD), pady=4, sticky="ew")

        self.duplicate_button = make_button(self, text="ทำซ้ำหน้า", icon_name="copy", command=on_duplicate_page)
        self.duplicate_button.grid(row=3, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.rotate_left_button = make_button(
            self,
            text="หมุนซ้าย",
            icon_name="rotate_left",
            command=on_rotate_left,
        )
        self.rotate_left_button.grid(row=4, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")
        self.rotate_right_button = make_button(
            self,
            text="หมุนขวา",
            icon_name="rotate_right",
            command=on_rotate_right,
        )
        self.rotate_right_button.grid(row=5, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.delete_button = make_button(
            self,
            text="ลบหน้า",
            icon_name="delete",
            command=on_delete_page,
            variant="danger",
        )
        self.delete_button.grid(row=6, column=0, columnspan=3, padx=PANEL_PAD, pady=(4, 12), sticky="ew")

        self.extract_button = make_button(self, text="แยกหน้านี้", icon_name="extract", command=on_extract_page)
        self.extract_button.grid(row=7, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.form_button = make_button(self, text="แก้ฟอร์ม PDF", icon_name="form", command=on_edit_form)
        self.form_button.grid(row=8, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.replace_text_button = make_button(
            self,
            text="แก้ข้อความเดิม",
            icon_name="text",
            command=on_replace_text,
        )
        self.replace_text_button.grid(row=9, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.import_fonts_button = make_button(self, text="หา/โหลดฟอนต์", icon_name="font", command=on_import_fonts)
        self.import_fonts_button.grid(row=10, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.pending_overlays_button = make_button(
            self,
            text="รายการที่วางแล้ว",
            icon_name="shape",
            command=on_manage_pending_overlays,
        )
        self.pending_overlays_button.grid(row=11, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.export_jpg_button = make_button(self, text="ส่งออก JPG", icon_name="image", command=on_export_jpg)
        self.export_jpg_button.grid(row=12, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.batch_jpg_button = make_button(self, text="Batch JPG", icon_name="copy", command=on_batch_jpg)
        self.batch_jpg_button.grid(row=13, column=0, columnspan=3, padx=PANEL_PAD, pady=4, sticky="ew")

        self.qa_checklist_button = make_button(self, text="ตรวจงาน", icon_name="check", command=on_open_qa_checklist)
        self.qa_checklist_button.grid(row=14, column=0, columnspan=3, padx=PANEL_PAD, pady=(4, 12), sticky="ew")

    def refresh(self, total_pages: int, current_page_index: int) -> None:
        """Refresh listbox items and selection."""
        self._refreshing = True
        try:
            rebuilt = self._refresh_page_items(total_pages)
            self._refresh_page_selection(total_pages, current_page_index, force_scroll=rebuilt)
        finally:
            self._refreshing = False

        has_document = total_pages > 0
        self._set_button_state(self.move_up_button, "move_up", "normal" if current_page_index > 0 else "disabled")
        self._set_button_state(
            self.move_down_button,
            "move_down",
            "normal" if has_document and current_page_index < total_pages - 1 else "disabled",
        )
        page_action_state = "normal" if has_document else "disabled"
        self._set_button_state(self.rotate_left_button, "rotate_left", page_action_state)
        self._set_button_state(self.rotate_right_button, "rotate_right", page_action_state)
        self._set_button_state(self.duplicate_button, "duplicate", page_action_state)
        self._set_button_state(self.delete_button, "delete", "normal" if total_pages > 1 else "disabled")
        self._set_button_state(self.extract_button, "extract", page_action_state)
        self._set_button_state(self.form_button, "form", page_action_state)
        self._set_button_state(self.replace_text_button, "replace_text", page_action_state)
        self._set_button_state(self.import_fonts_button, "import_fonts", page_action_state)
        self._set_button_state(self.pending_overlays_button, "pending_overlays", page_action_state)
        self._set_button_state(self.export_jpg_button, "export_jpg", page_action_state)
        self._set_button_state(self.batch_jpg_button, "batch_jpg", "normal")
        self._set_button_state(self.qa_checklist_button, "qa_checklist", "normal")

    def reset_page_cache(self) -> None:
        """Force the page list to rebuild on the next refresh."""
        self._listed_total_pages = None
        self._selected_page_index = None

    def selected_page_index(self) -> int | None:
        """Return the currently highlighted page row, if any."""
        if self.listbox["state"] == "disabled":
            return None
        selection = self.listbox.curselection()
        if not selection:
            return None
        return int(selection[0])

    def _refresh_page_items(self, total_pages: int) -> bool:
        if self._listed_total_pages == total_pages:
            return False
        self.listbox.configure(state="normal")
        self.listbox.delete(0, "end")
        if total_pages:
            for index in range(total_pages):
                self.listbox.insert("end", f"หน้า {index + 1}")
        else:
            self.listbox.insert("end", "ยังไม่มีหน้า")
            self.listbox.insert("end", "เปิด PDF เพื่อแสดงหน้า")
            self.listbox.configure(state="disabled")
        self._listed_total_pages = total_pages
        self._selected_page_index = None
        return True

    def _refresh_page_selection(self, total_pages: int, current_page_index: int, *, force_scroll: bool) -> None:
        if not total_pages:
            self._selected_page_index = None
            return
        selection = tuple(int(index) for index in self.listbox.curselection())
        selection_changed = self._selected_page_index != current_page_index
        if selection_changed or selection != (current_page_index,):
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(current_page_index)
        self.listbox.activate(current_page_index)
        if force_scroll or selection_changed or not self._is_page_index_visible(current_page_index):
            self.listbox.see(current_page_index)
        self._selected_page_index = current_page_index

    def _is_page_index_visible(self, page_index: int) -> bool:
        total_items = self.listbox.size()
        if total_items <= 0:
            return False
        first_fraction, last_fraction = self.listbox.yview()
        first_visible = int(first_fraction * total_items)
        last_visible = max(first_visible, int(last_fraction * total_items) - 1)
        return first_visible <= page_index <= last_visible

    def _set_button_state(self, button: ctk.CTkButton, key: str, state: str) -> None:
        if self._button_states.get(key) == state:
            return
        button.configure(state=state)
        self._button_states[key] = state

    def _handle_select(self, _event: object) -> None:
        if self._refreshing:
            return
        selection = self.listbox.curselection()
        if selection and self.listbox["state"] != "disabled":
            self.on_select_page(int(selection[0]))

    def _bind_page_list_mouse_wheel(self) -> None:
        for widget in (self.listbox, self.page_scroll):
            widget.bind("<Enter>", self._focus_scroll_widget)
            widget.bind("<MouseWheel>", self._handle_mouse_wheel)
            widget.bind("<Button-4>", self._handle_mouse_wheel)
            widget.bind("<Button-5>", self._handle_mouse_wheel)

    def _focus_scroll_widget(self, event: object) -> None:
        event.widget.focus_set()

    def _handle_mouse_wheel(self, event: object) -> str:
        units, self._list_wheel_remainder = event_wheel_scroll_units_with_remainder(
            event,
            remainder=self._list_wheel_remainder,
        )
        if units:
            self.listbox.yview_scroll(units, "units")
        return "break"

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
