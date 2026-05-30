# -*- coding: utf-8 -*-
"""Dialog for searching PDF text layer."""

from __future__ import annotations

from collections.abc import Callable
from tkinter import Listbox, Scrollbar, StringVar

import customtkinter as ctk

from thai_pdf_editor.app.core.errors import AppError
from thai_pdf_editor.app.core.pdf_search import PdfSearchResult
from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, ENTRY_FONT, ENTRY_HEIGHT, LABEL_FONT, LISTBOX_FONT, TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import SCROLLBAR_WIDTH
from thai_pdf_editor.app.ui.theme import bind_button_depth


def show_text_search_dialog(
    master: ctk.CTkBaseClass,
    *,
    initial_query: str,
    on_search: Callable[[str], list[PdfSearchResult]],
    on_select: Callable[[int], None],
    on_previous: Callable[[], int],
    on_next: Callable[[], int],
    on_close: Callable[[], None] | None = None,
) -> None:
    """Show a modal text-layer search dialog."""
    dialog = ctk.CTkToplevel(master)
    dialog.title("ค้นหาข้อความ")
    dialog.geometry("560x420")
    dialog.minsize(560, 420)
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)
    dialog.grid_rowconfigure(2, weight=1)

    query_var = StringVar(value=initial_query)
    results: list[PdfSearchResult] = []

    title = ctk.CTkLabel(dialog, text="ค้นหาข้อความใน PDF", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=3, sticky="ew", padx=16, pady=(16, 8))

    query_label = ctk.CTkLabel(dialog, text="ข้อความ", anchor="w", font=LABEL_FONT)
    query_label.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=6)
    query_entry = ctk.CTkEntry(dialog, textvariable=query_var, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    query_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=6)
    search_button = ctk.CTkButton(dialog, text="ค้นหา", height=BUTTON_HEIGHT, font=BUTTON_FONT)
    search_button.grid(row=1, column=2, sticky="ew", padx=(0, 16), pady=6)

    listbox = Listbox(dialog, exportselection=False, height=12, font=LISTBOX_FONT)
    listbox.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(16, 0), pady=8)
    scrollbar = Scrollbar(dialog, orient="vertical", command=listbox.yview, width=SCROLLBAR_WIDTH)
    scrollbar.grid(row=2, column=2, sticky="ns", padx=(0, 16), pady=8)
    listbox.configure(yscrollcommand=scrollbar.set)

    status_label = ctk.CTkLabel(dialog, text="ค้นจาก text layer เท่านั้น", anchor="w", font=LABEL_FONT)
    status_label.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

    button_frame = ctk.CTkFrame(dialog, corner_radius=0)
    button_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(4, 16))
    button_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def select_index(index: int) -> None:
        if not 0 <= index < len(results):
            return
        listbox.selection_clear(0, "end")
        listbox.selection_set(index)
        listbox.see(index)
        on_select(index)
        status_label.configure(text=f"เลือกผลลัพธ์ {index + 1}/{len(results)}")

    def refresh_results(new_results: list[PdfSearchResult]) -> None:
        nonlocal results
        results = new_results
        listbox.configure(state="normal")
        listbox.delete(0, "end")
        for result in results:
            listbox.insert("end", result.label)
        state = "normal" if results else "disabled"
        prev_button.configure(state=state)
        next_button.configure(state=state)
        if results:
            select_index(0)

    def run_search() -> None:
        try:
            refresh_results(on_search(query_var.get()))
            status_label.configure(text=f"พบ {len(results)} รายการ")
        except AppError as exc:
            results.clear()
            listbox.delete(0, "end")
            listbox.insert("end", exc.user_message)
            listbox.configure(state="disabled")
            prev_button.configure(state="disabled")
            next_button.configure(state="disabled")
            status_label.configure(text=exc.user_message)

    def select_from_list(_event: object) -> None:
        selection = listbox.curselection()
        if selection:
            select_index(int(selection[0]))

    def previous_result() -> None:
        select_index(on_previous())

    def next_result() -> None:
        select_index(on_next())

    search_button.configure(command=run_search)
    query_entry.bind("<Return>", lambda _event: run_search())
    listbox.bind("<<ListboxSelect>>", select_from_list)
    listbox.bind("<Double-Button-1>", select_from_list)

    prev_button = ctk.CTkButton(button_frame, text="ก่อนหน้า", command=previous_result, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    prev_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    next_button = ctk.CTkButton(button_frame, text="ถัดไป", command=next_result, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    next_button.grid(row=0, column=1, sticky="ew", padx=8)
    def close() -> None:
        if on_close is not None:
            on_close()
        dialog.destroy()

    close_button = ctk.CTkButton(button_frame, text="ปิดหน้าต่าง", command=close, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    close_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

    bind_button_depth(search_button, "primary")
    for button in (prev_button, next_button, close_button):
        bind_button_depth(button, "secondary")

    prev_button.configure(state="disabled")
    next_button.configure(state="disabled")
    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.bind("<Escape>", lambda _event: close())
    query_entry.focus_set()
    dialog.wait_window()
