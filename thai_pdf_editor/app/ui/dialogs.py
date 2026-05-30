# -*- coding: utf-8 -*-
"""Dialog helpers for Thai user messages."""

from tkinter import BooleanVar, StringVar, filedialog, messagebox

from pathlib import Path

import customtkinter as ctk

from thai_pdf_editor.app.constants import FONT_FILE_TYPES, IMAGE_FILE_TYPES, PDF_FILE_TYPES
from thai_pdf_editor.app.core.export_operations import (
    DEFAULT_JPG_DPI,
    DEFAULT_JPG_QUALITY,
    JPG_EXPORT_SCOPE_ALL,
    JPG_EXPORT_SCOPE_CURRENT,
    MAX_JPG_DPI,
    MAX_JPG_QUALITY,
    MIN_JPG_DPI,
    MIN_JPG_QUALITY,
)
from thai_pdf_editor.app.core.form_operations import FormField
from thai_pdf_editor.app.core.text_edit_operations import TEXT_REPLACE_SCOPE_ALL, TEXT_REPLACE_SCOPE_CURRENT
from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, ENTRY_FONT, ENTRY_HEIGHT, LABEL_FONT, TITLE_FONT


def ask_open_pdf_path() -> str:
    """Ask the user to select a PDF path."""
    return filedialog.askopenfilename(title="เปิดไฟล์ PDF", filetypes=PDF_FILE_TYPES)


def ask_merge_pdf_paths() -> tuple[str, ...]:
    """Ask the user to select multiple PDFs for merging."""
    return filedialog.askopenfilenames(title="เลือก PDF สำหรับรวม", filetypes=PDF_FILE_TYPES)


def ask_batch_jpg_pdf_paths() -> tuple[str, ...]:
    """Ask the user to select PDFs for batch JPG export."""
    return filedialog.askopenfilenames(title="เลือก PDF สำหรับ Batch JPG", filetypes=PDF_FILE_TYPES)


def ask_save_pdf_path(default_path: Path) -> str:
    """Ask the user to choose a Save As PDF path."""
    return filedialog.asksaveasfilename(
        title="บันทึกเป็น",
        defaultextension=".pdf",
        filetypes=PDF_FILE_TYPES,
        initialdir=str(default_path.parent),
        initialfile=default_path.name,
    )


def ask_export_jpg_directory(default_dir: Path) -> str:
    """Ask the user to choose a destination folder for JPG export."""
    return filedialog.askdirectory(
        title="เลือกโฟลเดอร์สำหรับบันทึก JPG",
        initialdir=str(default_dir.parent),
        mustexist=False,
    )


def ask_jpg_export_options(
    master: ctk.CTkBaseClass,
    *,
    current_page: int,
    total_pages: int,
) -> dict[str, int | str] | None:
    """Ask the user for JPG export scope, DPI, and quality."""
    result: dict[str, int | str] | None = None
    all_pages_label = f"ทุกหน้า ({total_pages} หน้า)"
    current_page_label = f"หน้าปัจจุบัน ({current_page})"
    dialog = ctk.CTkToplevel(master)
    dialog.title("ตั้งค่าส่งออก JPG")
    dialog.geometry("460x300")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="ตั้งค่าส่งออก JPG", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

    scope_var = StringVar(value=all_pages_label)
    dpi_var = StringVar(value=str(DEFAULT_JPG_DPI))

    scope_label = ctk.CTkLabel(dialog, text="หน้า", anchor="w", font=LABEL_FONT)
    scope_label.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=7)
    scope_menu = ctk.CTkOptionMenu(
        dialog,
        values=[all_pages_label, current_page_label],
        variable=scope_var,
        height=ENTRY_HEIGHT,
        font=ENTRY_FONT,
        dropdown_font=ENTRY_FONT,
    )
    scope_menu.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=7)

    dpi_label = ctk.CTkLabel(dialog, text="DPI", anchor="w", font=LABEL_FONT)
    dpi_label.grid(row=2, column=0, sticky="w", padx=(16, 8), pady=7)
    dpi_menu = ctk.CTkOptionMenu(
        dialog,
        values=["96", "150", "300"],
        variable=dpi_var,
        height=ENTRY_HEIGHT,
        font=ENTRY_FONT,
        dropdown_font=ENTRY_FONT,
    )
    dpi_menu.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=7)

    quality_label = ctk.CTkLabel(dialog, text="คุณภาพ JPG", anchor="w", font=LABEL_FONT)
    quality_label.grid(row=3, column=0, sticky="w", padx=(16, 8), pady=7)
    quality_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    quality_entry.insert(0, str(DEFAULT_JPG_QUALITY))
    quality_entry.grid(row=3, column=1, sticky="ew", padx=(0, 16), pady=7)

    hint = ctk.CTkLabel(
        dialog,
        text=f"คุณภาพ {MIN_JPG_QUALITY}-{MAX_JPG_QUALITY}, DPI {MIN_JPG_DPI}-{MAX_JPG_DPI}",
        anchor="w",
        font=LABEL_FONT,
    )
    hint.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(6, 0))

    def save() -> None:
        nonlocal result
        try:
            dpi = int(dpi_var.get())
            quality = int(quality_entry.get().strip())
        except ValueError:
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอก DPI และคุณภาพ JPG เป็นตัวเลข")
            return
        if not MIN_JPG_DPI <= dpi <= MAX_JPG_DPI:
            messagebox.showerror("เกิดข้อผิดพลาด", f"ค่า DPI ต้องอยู่ระหว่าง {MIN_JPG_DPI}-{MAX_JPG_DPI}")
            return
        if not MIN_JPG_QUALITY <= quality <= MAX_JPG_QUALITY:
            messagebox.showerror(
                "เกิดข้อผิดพลาด",
                f"คุณภาพ JPG ต้องอยู่ระหว่าง {MIN_JPG_QUALITY}-{MAX_JPG_QUALITY}",
            )
            return
        result = {
            "page_scope": JPG_EXPORT_SCOPE_CURRENT
            if scope_var.get() == current_page_label
            else JPG_EXPORT_SCOPE_ALL,
            "dpi": dpi,
            "quality": quality,
        }
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(dialog, text="ส่งออก", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=5, column=0, sticky="ew", padx=(16, 8), pady=(18, 16))
    cancel_button = ctk.CTkButton(dialog, text="ยกเลิก", command=cancel, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    cancel_button.grid(row=5, column=1, sticky="ew", padx=(8, 16), pady=(18, 16))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def ask_batch_jpg_export_options(master: ctk.CTkBaseClass) -> dict[str, int] | None:
    """Ask the user for batch JPG DPI and quality."""
    result: dict[str, int] | None = None
    dialog = ctk.CTkToplevel(master)
    dialog.title("ตั้งค่า Batch JPG")
    dialog.geometry("420x240")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="ตั้งค่า Batch JPG", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

    dpi_var = StringVar(value=str(DEFAULT_JPG_DPI))
    dpi_label = ctk.CTkLabel(dialog, text="DPI", anchor="w", font=LABEL_FONT)
    dpi_label.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=7)
    dpi_menu = ctk.CTkOptionMenu(
        dialog,
        values=["96", "150", "300"],
        variable=dpi_var,
        height=ENTRY_HEIGHT,
        font=ENTRY_FONT,
        dropdown_font=ENTRY_FONT,
    )
    dpi_menu.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=7)

    quality_label = ctk.CTkLabel(dialog, text="คุณภาพ JPG", anchor="w", font=LABEL_FONT)
    quality_label.grid(row=2, column=0, sticky="w", padx=(16, 8), pady=7)
    quality_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    quality_entry.insert(0, str(DEFAULT_JPG_QUALITY))
    quality_entry.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=7)

    hint = ctk.CTkLabel(
        dialog,
        text=f"Batch นี้ export ทุกหน้าของแต่ละ PDF, คุณภาพ {MIN_JPG_QUALITY}-{MAX_JPG_QUALITY}",
        anchor="w",
        font=LABEL_FONT,
    )
    hint.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(6, 0))

    def save() -> None:
        nonlocal result
        try:
            dpi = int(dpi_var.get())
            quality = int(quality_entry.get().strip())
        except ValueError:
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอก DPI และคุณภาพ JPG เป็นตัวเลข")
            return
        if not MIN_JPG_DPI <= dpi <= MAX_JPG_DPI:
            messagebox.showerror("เกิดข้อผิดพลาด", f"ค่า DPI ต้องอยู่ระหว่าง {MIN_JPG_DPI}-{MAX_JPG_DPI}")
            return
        if not MIN_JPG_QUALITY <= quality <= MAX_JPG_QUALITY:
            messagebox.showerror(
                "เกิดข้อผิดพลาด",
                f"คุณภาพ JPG ต้องอยู่ระหว่าง {MIN_JPG_QUALITY}-{MAX_JPG_QUALITY}",
            )
            return
        result = {"dpi": dpi, "quality": quality}
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(dialog, text="ส่งออก", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=4, column=0, sticky="ew", padx=(16, 8), pady=(18, 16))
    cancel_button = ctk.CTkButton(dialog, text="ยกเลิก", command=cancel, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    cancel_button.grid(row=4, column=1, sticky="ew", padx=(8, 16), pady=(18, 16))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def ask_replace_text_options(
    master: ctk.CTkBaseClass,
    *,
    current_page: int,
    total_pages: int,
    default_font_size: int,
) -> dict[str, int | str] | None:
    """Ask the user for safe existing-text replacement options."""
    result: dict[str, int | str] | None = None
    all_pages_label = f"ทุกหน้า ({total_pages} หน้า)"
    current_page_label = f"หน้าปัจจุบัน ({current_page})"
    dialog = ctk.CTkToplevel(master)
    dialog.title("แก้ข้อความเดิม")
    dialog.geometry("560x360")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="แก้ข้อความเดิมใน PDF", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

    search_label = ctk.CTkLabel(dialog, text="ข้อความเดิม", anchor="w", font=LABEL_FONT)
    search_label.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=7)
    search_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    search_entry.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=7)

    replacement_label = ctk.CTkLabel(dialog, text="ข้อความใหม่", anchor="w", font=LABEL_FONT)
    replacement_label.grid(row=2, column=0, sticky="w", padx=(16, 8), pady=7)
    replacement_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    replacement_entry.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=7)

    scope_var = StringVar(value=current_page_label)
    scope_label = ctk.CTkLabel(dialog, text="ขอบเขต", anchor="w", font=LABEL_FONT)
    scope_label.grid(row=3, column=0, sticky="w", padx=(16, 8), pady=7)
    scope_menu = ctk.CTkOptionMenu(
        dialog,
        values=[current_page_label, all_pages_label],
        variable=scope_var,
        height=ENTRY_HEIGHT,
        font=ENTRY_FONT,
        dropdown_font=ENTRY_FONT,
    )
    scope_menu.grid(row=3, column=1, sticky="ew", padx=(0, 16), pady=7)

    size_label = ctk.CTkLabel(dialog, text="ขนาดตัวอักษร", anchor="w", font=LABEL_FONT)
    size_label.grid(row=4, column=0, sticky="w", padx=(16, 8), pady=7)
    size_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    size_entry.insert(0, str(default_font_size))
    size_entry.grid(row=4, column=1, sticky="ew", padx=(0, 16), pady=7)

    hint = ctk.CTkLabel(
        dialog,
        text="ระบบจะลบข้อความเดิมแบบถาวรในไฟล์ Save As แล้ววางข้อความใหม่ทับตำแหน่งเดิม",
        anchor="w",
        font=LABEL_FONT,
    )
    hint.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 0))

    def save() -> None:
        nonlocal result
        search_text = search_entry.get()
        if not search_text.strip():
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอกข้อความเดิมที่ต้องการค้นหา")
            return
        try:
            font_size = int(size_entry.get().strip())
        except ValueError:
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอกขนาดตัวอักษรเป็นตัวเลข")
            return
        if font_size <= 0:
            messagebox.showerror("เกิดข้อผิดพลาด", "ขนาดตัวอักษรต้องมากกว่า 0")
            return
        result = {
            "search_text": search_text,
            "replacement_text": replacement_entry.get(),
            "page_scope": TEXT_REPLACE_SCOPE_CURRENT
            if scope_var.get() == current_page_label
            else TEXT_REPLACE_SCOPE_ALL,
            "font_size": font_size,
        }
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(dialog, text="ใช้การแก้ไข", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=6, column=0, sticky="ew", padx=(16, 8), pady=(22, 16))
    cancel_button = ctk.CTkButton(dialog, text="ยกเลิก", command=cancel, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    cancel_button.grid(row=6, column=1, sticky="ew", padx=(8, 16), pady=(22, 16))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def ask_font_path() -> str:
    """Ask the user to select a Thai-capable font file."""
    return filedialog.askopenfilename(title="เลือกฟอนต์", filetypes=FONT_FILE_TYPES)


def ask_image_path() -> str:
    """Ask the user to select an image or visual signature file."""
    return filedialog.askopenfilename(title="เลือกรูปภาพ/ลายเซ็นภาพ", filetypes=IMAGE_FILE_TYPES)


def ask_visual_signature_options(master: ctk.CTkBaseClass) -> dict[str, int | str] | None:
    """Ask for simple visual signature text and PDF placement width."""
    result: dict[str, int | str] | None = None
    dialog = ctk.CTkToplevel(master)
    dialog.title("สร้างลายเซ็นภาพ")
    dialog.geometry("520x260")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="สร้างลายเซ็นภาพแบบง่าย", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

    text_label = ctk.CTkLabel(dialog, text="ข้อความลายเซ็น", anchor="w", font=LABEL_FONT)
    text_label.grid(row=1, column=0, sticky="w", padx=(16, 8), pady=7)
    text_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    text_entry.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=7)

    width_label = ctk.CTkLabel(dialog, text="ความกว้างตอนวาง", anchor="w", font=LABEL_FONT)
    width_label.grid(row=2, column=0, sticky="w", padx=(16, 8), pady=7)
    width_entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
    width_entry.insert(0, "160")
    width_entry.grid(row=2, column=1, sticky="ew", padx=(0, 16), pady=7)

    hint = ctk.CTkLabel(
        dialog,
        text="ระบบจะสร้าง PNG โปร่งใสไว้ในเครื่อง แล้วตั้งเป็นลายเซ็นภาพสำหรับวางลง PDF",
        anchor="w",
        font=LABEL_FONT,
    )
    hint.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 0))

    def save() -> None:
        nonlocal result
        signature_text = text_entry.get().strip()
        if not signature_text:
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอกข้อความลายเซ็น")
            return
        try:
            placement_width = int(width_entry.get().strip())
        except ValueError:
            messagebox.showerror("เกิดข้อผิดพลาด", "กรุณากรอกความกว้างเป็นตัวเลข")
            return
        if not 40 <= placement_width <= 600:
            messagebox.showerror("เกิดข้อผิดพลาด", "ความกว้างตอนวางต้องอยู่ระหว่าง 40-600")
            return
        result = {"text": signature_text, "placement_width": placement_width}
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(dialog, text="สร้าง", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=4, column=0, sticky="ew", padx=(16, 8), pady=(22, 16))
    cancel_button = ctk.CTkButton(dialog, text="ยกเลิก", command=cancel, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    cancel_button.grid(row=4, column=1, sticky="ew", padx=(8, 16), pady=(22, 16))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def ask_metadata_values(master: ctk.CTkBaseClass, initial_values: dict[str, str]) -> dict[str, str] | None:
    """Ask the user to edit PDF metadata fields."""
    labels = {
        "title": "ชื่อเรื่อง",
        "author": "ผู้เขียน",
        "subject": "หัวข้อ",
        "keywords": "คำค้น",
    }
    result: dict[str, str] | None = None
    dialog = ctk.CTkToplevel(master)
    dialog.title("ข้อมูลไฟล์ PDF")
    dialog.geometry("480x310")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="ข้อมูลไฟล์ PDF", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

    entries: dict[str, ctk.CTkEntry] = {}
    for row_index, (field, label_text) in enumerate(labels.items(), start=1):
        label = ctk.CTkLabel(dialog, text=label_text, anchor="w", font=LABEL_FONT)
        label.grid(row=row_index, column=0, sticky="w", padx=(16, 8), pady=6)
        entry = ctk.CTkEntry(dialog, height=ENTRY_HEIGHT, font=ENTRY_FONT)
        entry.insert(0, initial_values.get(field, ""))
        entry.grid(row=row_index, column=1, sticky="ew", padx=(0, 16), pady=6)
        entries[field] = entry

    def save() -> None:
        nonlocal result
        result = {field: entry.get() for field, entry in entries.items()}
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(dialog, text="ใช้ข้อมูลนี้", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=5, column=0, sticky="ew", padx=(16, 8), pady=(18, 16))
    cancel_button = ctk.CTkButton(dialog, text="ยกเลิก", command=cancel, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    cancel_button.grid(row=5, column=1, sticky="ew", padx=(8, 16), pady=(18, 16))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def ask_form_field_values(master: ctk.CTkBaseClass, fields: list[FormField]) -> dict[int, str | bool] | None:
    """Ask the user to edit supported existing PDF form fields."""
    result: dict[int, str | bool] | None = None
    dialog_height = min(620, max(280, 150 + len(fields) * 54))
    dialog = ctk.CTkToplevel(master)
    dialog.title("แก้ฟอร์ม PDF")
    dialog.geometry(f"560x{dialog_height}")
    dialog.resizable(False, True)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="แก้ฟอร์ม PDF ที่มีอยู่แล้ว", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

    frame = ctk.CTkScrollableFrame(dialog)
    frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
    frame.grid_columnconfigure(1, weight=1)

    controls: dict[int, ctk.CTkEntry | BooleanVar] = {}
    for row_index, field in enumerate(fields):
        label_text = f"{field.name} ({field.field_type_label})"
        label = ctk.CTkLabel(frame, text=label_text, anchor="w", font=LABEL_FONT)
        label.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=6)
        if field.is_checkbox:
            variable = BooleanVar(value=bool(field.value))
            checkbox = ctk.CTkCheckBox(frame, text="", variable=variable, width=32, font=BUTTON_FONT)
            checkbox.grid(row=row_index, column=1, sticky="w", pady=6)
            controls[field.xref] = variable
        else:
            entry = ctk.CTkEntry(frame, height=ENTRY_HEIGHT, font=ENTRY_FONT)
            entry.insert(0, str(field.value))
            entry.grid(row=row_index, column=1, sticky="ew", pady=6)
            controls[field.xref] = entry

    button_frame = ctk.CTkFrame(dialog, corner_radius=0)
    button_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
    button_frame.grid_columnconfigure((0, 1), weight=1)

    def save() -> None:
        nonlocal result
        values: dict[int, str | bool] = {}
        for xref, control in controls.items():
            if isinstance(control, BooleanVar):
                values[xref] = bool(control.get())
            else:
                values[xref] = control.get()
        result = values
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    save_button = ctk.CTkButton(button_frame, text="ใช้ข้อมูลนี้", command=save, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    save_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    cancel_button = ctk.CTkButton(
        button_frame,
        text="ยกเลิก",
        command=cancel,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
    )
    cancel_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result


def show_usage_guide_dialog(master: ctk.CTkBaseClass) -> None:
    """Show a local usage guide for the main editor workflows."""
    dialog = ctk.CTkToplevel(master)
    dialog.title("คู่มือการใช้งาน")
    dialog.geometry("680x560")
    dialog.minsize(620, 480)
    dialog.transient(master)
    dialog.grab_set()
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(dialog, text="คู่มือการใช้งาน", anchor="w", font=TITLE_FONT)
    title.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

    guide_text = """เริ่มต้น
1. กด เปิดไฟล์ หรือวางไฟล์ PDF ลงบนพื้นที่อ่าน
2. ใช้ ก่อน/ถัด หรือช่องเลขหน้าเพื่อเปลี่ยนหน้า
3. ใช้ ซูม-, ซูม+, พอดีกว้าง หรือ พอดีบน-ล่าง เพื่อปรับมุมมอง

ปรับพื้นที่อ่าน PDF
1. ลากแถบ <> ด้านขวาเพื่อย่อ/ขยายแผงเครื่องมือ
2. กด > เพื่อยุบแผงเครื่องมือขวา และกด < เพื่อเปิดกลับ
3. ลากแถบ <> ด้านซ้ายเพื่อย่อ/ขยายรายการหน้า
4. กด < เพื่อยุบรายการหน้า และกด > เพื่อเปิดกลับ

เพิ่มข้อความ รูป และลายเซ็น
1. เลือกฟอนต์ ขนาด สี หรือเลือกรูปภาพ
2. กด วางข้อความ หรือ วางรูป
3. คลิกตำแหน่งบนหน้า PDF ที่ต้องการวาง
4. กด บันทึก เพื่อ Save As เป็นไฟล์ใหม่

จัดการหน้า
1. เลือกหน้าจากรายการหน้า
2. ใช้ ขึ้น/ลง, ทำซ้ำหน้า, หมุนซ้าย/ขวา, ลบหน้า หรือ แยกหน้านี้
3. คำสั่งที่แก้ไฟล์จะมีผลกับไฟล์ใหม่เมื่อบันทึก

ฟอร์ม PDF และข้อมูลเอกสาร
1. แก้ฟอร์ม PDF รองรับ text field และ checkbox ที่มีอยู่แล้ว
2. ข้อมูลเอกสาร ใช้แก้ metadata เช่น ชื่อเรื่อง ผู้เขียน หัวข้อ และคำค้น

ข้อควรจำ
1. โปรแกรมทำงานในเครื่องแบบ local-only
2. ใช้ บันทึก เพื่อสร้างไฟล์ใหม่ ไม่เขียนทับต้นฉบับโดยตรง
3. ก่อนส่งงานให้เปิดไฟล์ผลลัพธ์ตรวจซ้ำ โดยเฉพาะ redaction และข้อความภาษาไทย
"""
    textbox = ctk.CTkTextbox(dialog, font=LABEL_FONT, wrap="word")
    textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
    textbox.insert("1.0", guide_text)
    textbox.configure(state="disabled")

    close_button = ctk.CTkButton(dialog, text="ปิด", command=dialog.destroy, height=BUTTON_HEIGHT, font=BUTTON_FONT)
    close_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()


def show_error(message: str) -> None:
    """Show a Thai error dialog."""
    messagebox.showerror("เกิดข้อผิดพลาด", message)


def show_info(message: str) -> None:
    """Show a Thai information dialog."""
    messagebox.showinfo("แจ้งเตือน", message)


def confirm(message: str) -> bool:
    """Ask for confirmation."""
    return messagebox.askyesno("ยืนยัน", message)
