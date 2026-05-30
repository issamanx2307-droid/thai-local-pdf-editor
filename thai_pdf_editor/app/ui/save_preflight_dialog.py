# -*- coding: utf-8 -*-
"""Save As preflight confirmation dialog."""

from __future__ import annotations

from tkinter import Listbox, Scrollbar

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT, LISTBOX_FONT, TITLE_FONT
from thai_pdf_editor.app.ui.scrolling import SCROLLBAR_WIDTH
from thai_pdf_editor.app.ui.theme import bind_button_depth


def ask_save_preflight_confirmation(master: ctk.CTkBaseClass, *, summary: str, details: list[str]) -> bool:
    """Show Save As summary and detailed operation list before writing output."""
    confirmed = False
    dialog = ctk.CTkToplevel(master)
    dialog.title("ตรวจสอบก่อนบันทึก")
    dialog.geometry("720x560")
    dialog.minsize(720, 560)
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=0)
    dialog.grid_rowconfigure(3, weight=1)

    title = ctk.CTkLabel(dialog, text="ตรวจสอบก่อนบันทึกเป็นไฟล์ใหม่", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))

    summary_box = ctk.CTkTextbox(dialog, height=170, font=LABEL_FONT, wrap="word")
    summary_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=8)
    summary_box.insert("1.0", summary)
    summary_box.configure(state="disabled")

    detail_label = ctk.CTkLabel(dialog, text="รายละเอียดตามหน้า", anchor="w", font=LABEL_FONT)
    detail_label.grid(row=2, column=0, columnspan=2, sticky="new", padx=16, pady=(4, 0))

    listbox = Listbox(dialog, exportselection=False, height=10, font=LISTBOX_FONT)
    listbox.grid(row=3, column=0, sticky="nsew", padx=(16, 0), pady=8)
    scrollbar = Scrollbar(dialog, orient="vertical", command=listbox.yview, width=SCROLLBAR_WIDTH)
    scrollbar.grid(row=3, column=1, sticky="ns", padx=(0, 16), pady=8)
    listbox.configure(yscrollcommand=scrollbar.set)
    for line in details:
        listbox.insert("end", line)

    button_frame = ctk.CTkFrame(dialog, corner_radius=0)
    button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 16))
    button_frame.grid_columnconfigure((0, 1), weight=1)

    def accept() -> None:
        nonlocal confirmed
        confirmed = True
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(button_frame, text="บันทึกต่อ", command=accept, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    cancel_button = ctk.CTkButton(
        button_frame,
        text="ยกเลิกและกลับไปแก้",
        command=cancel,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    cancel_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    bind_button_depth(save_button, "primary")
    bind_button_depth(cancel_button, "secondary")

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.bind("<Escape>", lambda _event: cancel())
    dialog.wait_window()
    return confirmed
