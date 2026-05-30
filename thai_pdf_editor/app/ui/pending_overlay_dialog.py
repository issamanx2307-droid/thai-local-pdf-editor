# -*- coding: utf-8 -*-
"""Dialog for pending overlay operations before Save As."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import Listbox, Scrollbar

import customtkinter as ctk

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.pending_overlay_operations import (
    MOVE_STEP,
    RESIZE_DOWN_SCALE,
    RESIZE_UP_SCALE,
    delete_pending_operation,
    nudge_pending_operation,
    pending_operation_views,
    resize_pending_operation,
)
from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT, LISTBOX_FONT, TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import SCROLLBAR_WIDTH
from thai_pdf_editor.app.ui.theme import bind_button_depth


def show_pending_overlay_manager(
    master: ctk.CTkBaseClass,
    state: DocumentState,
    *,
    on_changed: Callable[[], None],
) -> None:
    """Show a modal pending overlay manager."""
    dialog = ctk.CTkToplevel(master)
    dialog.title("รายการที่วางแล้ว")
    dialog.geometry("620x430")
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=0)
    dialog.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="รายการที่วางแล้วก่อน Save As", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))

    listbox = Listbox(dialog, exportselection=False, height=12, font=LISTBOX_FONT)
    listbox.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=8)
    scrollbar = Scrollbar(dialog, orient="vertical", command=listbox.yview, width=SCROLLBAR_WIDTH)
    scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=8)
    listbox.configure(yscrollcommand=scrollbar.set)

    status_label = ctk.CTkLabel(dialog, text="", anchor="w", font=LABEL_FONT)
    status_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

    button_frame = ctk.CTkFrame(dialog, corner_radius=0)
    button_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 16))
    button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    selected_id: str | None = None
    current_views = []

    def selected_operation_id() -> str | None:
        selection = listbox.curselection()
        if not selection or int(selection[0]) >= len(current_views):
            return selected_id
        return current_views[int(selection[0])].id

    def refresh(keep_id: str | None = None) -> None:
        nonlocal current_views, selected_id
        current_views = pending_operation_views(state.pending_operations)
        selected_id = keep_id if keep_id in {view.id for view in current_views} else None
        listbox.configure(state="normal")
        listbox.delete(0, "end")
        for view in current_views:
            listbox.insert("end", view.label)
        if selected_id is not None:
            for index, view in enumerate(current_views):
                if view.id == selected_id:
                    listbox.selection_set(index)
                    listbox.see(index)
                    break
        elif not current_views:
            listbox.insert("end", "ยังไม่มีรายการที่วางแล้ว")
            listbox.configure(state="disabled")
        state_name = "normal" if current_views else "disabled"
        for button in action_buttons:
            button.configure(state=state_name)
        status_label.configure(text=f"ทั้งหมด {len(current_views)} รายการ")

    def run_action(action: Callable[[str], None]) -> None:
        operation_id = selected_operation_id()
        if operation_id is None:
            status_label.configure(text="กรุณาเลือกรายการก่อน")
            return
        action(operation_id)
        on_changed()
        refresh(operation_id)

    def delete_selected() -> None:
        operation_id = selected_operation_id()
        if operation_id is None:
            status_label.configure(text="กรุณาเลือกรายการก่อน")
            return
        delete_pending_operation(state, operation_id)
        on_changed()
        refresh(None)

    left_button = ctk.CTkButton(
        button_frame,
        text="ซ้าย",
        command=lambda: run_action(lambda item_id: nudge_pending_operation(state, item_id, dx=-MOVE_STEP, dy=0)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    left_button.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
    right_button = ctk.CTkButton(
        button_frame,
        text="ขวา",
        command=lambda: run_action(lambda item_id: nudge_pending_operation(state, item_id, dx=MOVE_STEP, dy=0)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    right_button.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
    up_button = ctk.CTkButton(
        button_frame,
        text="ขึ้น",
        command=lambda: run_action(lambda item_id: nudge_pending_operation(state, item_id, dx=0, dy=-MOVE_STEP)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    up_button.grid(row=0, column=2, sticky="ew", padx=6, pady=4)
    down_button = ctk.CTkButton(
        button_frame,
        text="ลง",
        command=lambda: run_action(lambda item_id: nudge_pending_operation(state, item_id, dx=0, dy=MOVE_STEP)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    down_button.grid(row=0, column=3, sticky="ew", padx=(6, 0), pady=4)

    shrink_button = ctk.CTkButton(
        button_frame,
        text="ย่อ",
        command=lambda: run_action(lambda item_id: resize_pending_operation(state, item_id, scale=RESIZE_DOWN_SCALE)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    shrink_button.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)
    grow_button = ctk.CTkButton(
        button_frame,
        text="ขยาย",
        command=lambda: run_action(lambda item_id: resize_pending_operation(state, item_id, scale=RESIZE_UP_SCALE)),
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    grow_button.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
    delete_button = ctk.CTkButton(
        button_frame,
        text="ลบรายการ",
        command=delete_selected,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    delete_button.grid(row=1, column=2, sticky="ew", padx=6, pady=4)
    close_button = ctk.CTkButton(
        button_frame,
        text="ปิด",
        command=dialog.destroy,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    close_button.grid(row=1, column=3, sticky="ew", padx=(6, 0), pady=4)

    action_buttons = [
        left_button,
        right_button,
        up_button,
        down_button,
        shrink_button,
        grow_button,
        delete_button,
    ]
    for button in action_buttons[:-1]:
        bind_button_depth(button, "secondary")
    bind_button_depth(delete_button, "danger")
    bind_button_depth(close_button, "secondary")

    refresh()
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
