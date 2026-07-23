# -*- coding: utf-8 -*-
"""Print dialog: choose printer and number of copies.

Printer discovery runs in a background thread so the dialog opens
instantly without freezing the main UI thread.
"""

from __future__ import annotations

import threading

import customtkinter as ctk

from thai_pdf_editor.app.core.print_operations import get_default_printer, list_printers
from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, ENTRY_FONT, LABEL_FONT, TITLE_FONT
from thai_pdf_editor.app.ui.theme import COLORS, RADIUS_PANEL, bind_button_depth

_NO_PRINTER_LABEL = "(ไม่พบเครื่องปริ้นท์)"
_LOADING_LABEL = "กำลังโหลดเครื่องปริ้นท์ ..."


_SCOPE_ALL = "all"
_SCOPE_CURRENT = "current"
_SCOPE_CUSTOM = "custom"


def ask_print_options(
    master: ctk.CTkBaseClass,
    *,
    total_pages: int,
    current_page: int | None = None,
) -> dict[str, object] | None:
    """Show a modal print dialog.

    The dialog opens immediately. Printer discovery runs in a background
    thread; the dropdown updates automatically when results are ready.

    *current_page*, if given, is the 1-based number of the page currently
    shown on screen — it enables the "current page" scope option.

    Returns ``{"printer": str, "copies": int, "pages": str | None}`` on
    confirm (``pages`` is ``None`` for "print every page"), or ``None`` on
    cancel.
    """
    result: dict[str, object] | None = None

    dialog = ctk.CTkToplevel(master)
    dialog.title("พิมพ์เอกสาร")
    dialog.resizable(False, False)
    dialog.transient(master)
    dialog.grab_set()
    dialog.configure(fg_color=COLORS["app_bg"])

    # ── outer card ──────────────────────────────────────────────────────────
    card = ctk.CTkFrame(
        dialog,
        fg_color=COLORS["surface"],
        corner_radius=RADIUS_PANEL,
        border_width=1,
        border_color=COLORS["border"],
    )
    card.pack(padx=20, pady=20, fill="both", expand=True)
    card.grid_columnconfigure(1, weight=1)

    # ── heading ─────────────────────────────────────────────────────────────
    ctk.CTkLabel(
        card,
        text="  พิมพ์เอกสาร",
        font=TITLE_FONT,
        text_color=COLORS["text"],
        anchor="w",
    ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 14))

    # ── printer picker ───────────────────────────────────────────────────────
    ctk.CTkLabel(
        card, text="เครื่องปริ้นท์ :", font=LABEL_FONT, text_color=COLORS["text"],
    ).grid(row=1, column=0, sticky="w", padx=(16, 8), pady=6)

    printer_var = ctk.StringVar(value=_LOADING_LABEL)
    printer_menu = ctk.CTkOptionMenu(
        card,
        variable=printer_var,
        values=[_LOADING_LABEL],
        width=300,
        font=ENTRY_FONT,
        fg_color=COLORS["surface_soft"],
        button_color=COLORS["border"],          # muted while loading
        button_hover_color=COLORS["border"],
        text_color=COLORS["muted"],
        state="disabled",
    )
    printer_menu.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=6)

    # ── copies ───────────────────────────────────────────────────────────────
    ctk.CTkLabel(
        card, text="จำนวนชุด :", font=LABEL_FONT, text_color=COLORS["text"],
    ).grid(row=2, column=0, sticky="w", padx=(16, 8), pady=6)

    copies_var = ctk.StringVar(value="1")
    ctk.CTkEntry(
        card,
        textvariable=copies_var,
        width=70,
        font=ENTRY_FONT,
        justify="center",
        border_color=COLORS["border"],
    ).grid(row=2, column=1, sticky="w", padx=(0, 16), pady=6)

    # ── page range ───────────────────────────────────────────────────────────
    ctk.CTkLabel(
        card, text="หน้าที่จะพิมพ์ :", font=LABEL_FONT, text_color=COLORS["text"],
    ).grid(row=3, column=0, sticky="nw", padx=(16, 8), pady=6)

    scope_var = ctk.StringVar(value=_SCOPE_ALL)
    scope_frame = ctk.CTkFrame(card, fg_color="transparent")
    scope_frame.grid(row=3, column=1, sticky="w", padx=(0, 16), pady=6)

    range_entry_var = ctk.StringVar(value="")
    range_entry = ctk.CTkEntry(
        card,
        textvariable=range_entry_var,
        width=180,
        font=ENTRY_FONT,
        placeholder_text="เช่น 1-3,5,8",
        border_color=COLORS["border"],
        state="disabled",
    )

    def _on_scope_changed() -> None:
        range_entry.configure(state="normal" if scope_var.get() == _SCOPE_CUSTOM else "disabled")

    ctk.CTkRadioButton(
        scope_frame, text=f"ทั้งหมด ({total_pages} หน้า)", variable=scope_var,
        value=_SCOPE_ALL, font=ENTRY_FONT, text_color=COLORS["text"],
        command=_on_scope_changed,
    ).pack(anchor="w", pady=(0, 4))

    if current_page is not None:
        ctk.CTkRadioButton(
            scope_frame, text=f"หน้าปัจจุบัน ({current_page})", variable=scope_var,
            value=_SCOPE_CURRENT, font=ENTRY_FONT, text_color=COLORS["text"],
            command=_on_scope_changed,
        ).pack(anchor="w", pady=(0, 4))

    ctk.CTkRadioButton(
        scope_frame, text="กำหนดเอง :", variable=scope_var,
        value=_SCOPE_CUSTOM, font=ENTRY_FONT, text_color=COLORS["text"],
        command=_on_scope_changed,
    ).pack(anchor="w")

    # ── custom range entry ──────────────────────────────────────────────────
    range_entry.grid(row=4, column=1, sticky="w", padx=(0, 16), pady=(0, 6))

    # ── divider ──────────────────────────────────────────────────────────────
    ctk.CTkFrame(card, height=1, fg_color=COLORS["border"]).grid(
        row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 0),
    )

    # ── action buttons ───────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(card, fg_color="transparent")
    btn_row.grid(row=6, column=0, columnspan=2, sticky="e", padx=16, pady=14)

    def on_cancel() -> None:
        dialog.destroy()

    def _resolve_pages() -> str | None:
        """Return the pages spec to send, or a sentinel meaning 'invalid'."""
        scope = scope_var.get()
        if scope == _SCOPE_ALL:
            return None
        if scope == _SCOPE_CURRENT:
            return str(current_page) if current_page is not None else None
        custom_text = range_entry_var.get().strip()
        return custom_text or ""

    def on_print() -> None:
        nonlocal result
        chosen = printer_var.get()
        if chosen in (_NO_PRINTER_LABEL, _LOADING_LABEL):
            return
        if scope_var.get() == _SCOPE_CUSTOM and not range_entry_var.get().strip():
            range_entry.configure(border_color=COLORS.get("error", "#d64545"))
            return
        raw = copies_var.get().strip()
        copies = int(raw) if raw.isdigit() and int(raw) >= 1 else 1
        result = {"printer": chosen, "copies": copies, "pages": _resolve_pages()}
        dialog.destroy()

    cancel_button = ctk.CTkButton(
        btn_row,
        text="ยกเลิก",
        command=on_cancel,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        text_color=COLORS["primary"],
        border_width=1,
        border_color=COLORS["border"],
        width=90,
    )
    bind_button_depth(cancel_button, "secondary")
    cancel_button.pack(side="left", padx=(0, 8))

    print_button = ctk.CTkButton(
        btn_row,
        text="  พิมพ์",
        command=on_print,
        height=BUTTON_HEIGHT,
        font=BUTTON_FONT,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="#ffffff",
        width=100,
        state="disabled",               # enabled after printers load
    )
    bind_button_depth(print_button, "primary")
    print_button.pack(side="left")

    # ── centre over parent ───────────────────────────────────────────────────
    dialog.update_idletasks()
    pw, ph = master.winfo_width(), master.winfo_height()
    px, py = master.winfo_rootx(), master.winfo_rooty()
    dw, dh = dialog.winfo_width(), dialog.winfo_height()
    dialog.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    # ── background printer discovery ─────────────────────────────────────────
    def _discover() -> None:
        """Run WMI queries off the main thread."""
        printers = list_printers()
        default = get_default_printer()
        # Re-enter Tk on the main thread safely via after()
        try:
            dialog.after(0, lambda: _apply_printers(printers, default))
        except Exception:  # noqa: BLE001
            pass  # dialog was closed before thread finished — ignore

    def _apply_printers(printers: list[str], default: str) -> None:
        """Update the dropdown on the main thread once discovery is done."""
        try:
            dialog.winfo_exists()          # raises TclError if dialog is gone
        except Exception:  # noqa: BLE001
            return

        if printers:
            initial = default if default in printers else printers[0]
        else:
            printers = [_NO_PRINTER_LABEL]
            initial = _NO_PRINTER_LABEL

        printer_menu.configure(
            values=printers,
            fg_color=COLORS["surface_soft"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            state="normal",
        )
        printer_var.set(initial)

        if initial != _NO_PRINTER_LABEL:
            print_button.configure(state="normal")

    threading.Thread(target=_discover, daemon=True).start()

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.bind("<Escape>", lambda _e: on_cancel())
    dialog.wait_window()
    return result
