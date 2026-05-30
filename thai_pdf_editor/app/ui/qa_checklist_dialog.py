# -*- coding: utf-8 -*-
"""Manual QA checklist dialog."""

from __future__ import annotations

from collections.abc import Sequence
from tkinter import BooleanVar

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT, TITLE_FONT


DEFAULT_QA_CHECKLIST = (
    "เปิดไฟล์ผลลัพธ์หลัง Save As แล้วดู preview อีกครั้ง",
    "ยืนยันว่าไฟล์ต้นฉบับยังเปิดได้และไม่ได้ถูกเขียนทับ",
    "ถ้ามี redaction ให้ค้นหาข้อความเดิมในไฟล์ปลายทางว่าไม่เหลือ",
    "ตรวจข้อความไทยและฟอนต์ไทยบนหน้าที่แก้ไข",
    "ตรวจรูปภาพ/ลายเซ็นภาพว่าตำแหน่งและขนาดถูกต้อง",
    "ตรวจฟอร์มและ metadata ถ้ามีการแก้ไข",
    "ตรวจ path ภาษาไทยของไฟล์ปลายทางและโฟลเดอร์ส่งออก",
    "เก็บไฟล์ต้นฉบับและไฟล์ผลลัพธ์แยกชื่อกันเสมอ",
)


def checklist_items_for_document(*, has_document: bool, dirty: bool) -> list[str]:
    """Return manual QA checklist items with current document context."""
    items = list(DEFAULT_QA_CHECKLIST)
    if not has_document:
        items.insert(0, "ยังไม่ได้เปิด PDF: เปิดไฟล์ก่อนเริ่มตรวจงาน")
    elif dirty:
        items.insert(0, "มีงานที่ยังไม่ได้ Save As: บันทึกเป็นไฟล์ใหม่ก่อนตรวจไฟล์ผลลัพธ์")
    else:
        items.insert(0, "เอกสารปัจจุบันไม่มีงานค้างใน state แล้ว")
    return items


def show_qa_checklist_dialog(master: ctk.CTkBaseClass, items: Sequence[str]) -> None:
    """Show a local manual QA checklist."""
    dialog = ctk.CTkToplevel(master)
    dialog.title("ตรวจงานก่อนส่ง")
    dialog.geometry("680x520")
    dialog.minsize(680, 520)
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="ตรวจงานก่อนส่ง", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

    frame = ctk.CTkScrollableFrame(dialog)
    frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
    frame.grid_columnconfigure(0, weight=1)

    for row_index, item in enumerate(items):
        checkbox = ctk.CTkCheckBox(frame, text=item, variable=BooleanVar(value=False), font=LABEL_FONT)
        checkbox.grid(row=row_index, column=0, sticky="ew", padx=4, pady=6)

    close_button = ctk.CTkButton(dialog, text="ปิดหน้าต่าง", command=dialog.destroy, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    close_button.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.wait_window()
