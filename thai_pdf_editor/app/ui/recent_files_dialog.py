# -*- coding: utf-8 -*-
"""Recent PDF files dialog."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import Listbox, Scrollbar

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT, LISTBOX_FONT, TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import SCROLLBAR_WIDTH
from thai_pdf_editor.app.ui.theme import bind_button_depth


def show_recent_files_dialog(
    master: ctk.CTkBaseClass,
    recent_paths: list[Path],
    *,
    on_open_path: Callable[[Path], None],
    on_remove_path: Callable[[Path], list[Path]],
    on_clear: Callable[[], None],
) -> None:
    """Show recent PDF paths and open the selected one."""
    paths = list(recent_paths)
    dialog = ctk.CTkToplevel(master)
    dialog.title("ไฟล์ล่าสุด")
    dialog.geometry("720x460")
    dialog.minsize(720, 460)
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=0)
    dialog.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="ไฟล์ PDF ล่าสุด", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))

    listbox = Listbox(dialog, exportselection=False, height=10, font=LISTBOX_FONT)
    listbox.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=8)
    scrollbar = Scrollbar(dialog, orient="vertical", command=listbox.yview, width=SCROLLBAR_WIDTH)
    scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=8)
    listbox.configure(yscrollcommand=scrollbar.set)

    path_label = ctk.CTkLabel(dialog, text="เลือกไฟล์เพื่อดู path เต็ม", anchor="w", font=LABEL_FONT)
    path_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 4))

    status_label = ctk.CTkLabel(dialog, text="", anchor="w", font=LABEL_FONT)
    status_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

    button_frame = ctk.CTkFrame(dialog, corner_radius=0)
    button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 16))
    button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def refresh_list(selected_index: int | None = None) -> None:
        listbox.configure(state="normal")
        listbox.delete(0, "end")
        for path in paths:
            listbox.insert("end", str(path))
        if not paths:
            listbox.insert("end", "ยังไม่มีไฟล์ล่าสุด")
            listbox.configure(state="disabled")
            open_button.configure(state="disabled")
            remove_button.configure(state="disabled")
            clear_button.configure(state="disabled")
            path_label.configure(text="ไม่มีไฟล์ล่าสุด")
        else:
            open_button.configure(state="normal")
            remove_button.configure(state="normal")
            clear_button.configure(state="normal")
            if selected_index is not None:
                safe_index = max(0, min(selected_index, len(paths) - 1))
                listbox.selection_set(safe_index)
                listbox.see(safe_index)
                path_label.configure(text=str(paths[safe_index]))
        status_label.configure(text=f"ทั้งหมด {len(paths)} ไฟล์")

    def open_selected() -> None:
        selection = listbox.curselection()
        if not selection:
            status_label.configure(text="กรุณาเลือกไฟล์ก่อน")
            return
        selected_path = paths[int(selection[0])]
        dialog.destroy()
        on_open_path(selected_path)

    def remove_selected() -> None:
        nonlocal paths
        selection = listbox.curselection()
        if not selection:
            status_label.configure(text="กรุณาเลือกไฟล์ก่อน")
            return
        selected_index = int(selection[0])
        paths = on_remove_path(paths[selected_index])
        refresh_list(selected_index)

    def clear_all() -> None:
        nonlocal paths
        on_clear()
        paths = []
        refresh_list()

    def show_selected_path(_event: object) -> None:
        selection = listbox.curselection()
        if selection and paths:
            path_label.configure(text=str(paths[int(selection[0])]))

    listbox.bind("<Double-Button-1>", lambda _event: open_selected())
    listbox.bind("<<ListboxSelect>>", show_selected_path)
    open_button = ctk.CTkButton(
        button_frame,
        text="เปิดไฟล์ที่เลือก",
        command=open_selected,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    open_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    remove_button = ctk.CTkButton(
        button_frame,
        text="ลบรายการ",
        command=remove_selected,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    remove_button.grid(row=0, column=1, sticky="ew", padx=8)
    clear_button = ctk.CTkButton(
        button_frame,
        text="ล้างทั้งหมด",
        command=clear_all,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    clear_button.grid(row=0, column=2, sticky="ew", padx=8)
    close_button = ctk.CTkButton(
        button_frame,
        text="ปิดหน้าต่าง",
        command=dialog.destroy,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    close_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))

    bind_button_depth(open_button, "primary")
    bind_button_depth(remove_button, "danger")
    bind_button_depth(clear_button, "warning")
    bind_button_depth(close_button, "secondary")

    refresh_list()
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    listbox.bind("<Return>", lambda _event: open_selected())
    listbox.bind("<Delete>", lambda _event: remove_selected())
    dialog.wait_window()
