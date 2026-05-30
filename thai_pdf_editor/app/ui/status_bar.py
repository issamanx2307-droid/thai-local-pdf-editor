# -*- coding: utf-8 -*-
"""Status bar widget."""

import customtkinter as ctk

from thai_pdf_editor.app.constants import CREATOR_CREDIT, DEFAULT_STATUS
from thai_pdf_editor.app.ui.fonts import STATUS_FONT
from thai_pdf_editor.app.ui.theme import COLORS, RADIUS_PANEL


class StatusBar(ctk.CTkFrame):
    """Bottom status bar — status message / creator credit / page+zoom indicator."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(
            master,
            height=38,
            fg_color=COLORS["surface"],
            corner_radius=RADIUS_PANEL,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Status message (left)
        self._status_var = ctk.StringVar(value=DEFAULT_STATUS)
        self.label = ctk.CTkLabel(
            self,
            textvariable=self._status_var,
            anchor="w",
            font=STATUS_FONT,
            text_color=COLORS["text"],
        )
        self.label.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=5)

        # Creator credit (centre)
        self.credit_label = ctk.CTkLabel(
            self,
            text=CREATOR_CREDIT,
            anchor="center",
            font=STATUS_FONT,
            text_color=COLORS["muted"],
        )
        self.credit_label.grid(row=0, column=1, sticky="ew", padx=8, pady=5)

        # Page + zoom pill (right) — styled as a subtle badge
        self.document_label = ctk.CTkLabel(
            self,
            text="หน้า —  |  —%",
            anchor="e",
            font=STATUS_FONT,
            text_color=COLORS["muted"],
            fg_color=COLORS["surface_soft"],
            corner_radius=4,
            padx=10,
        )
        self.document_label.grid(row=0, column=2, sticky="e", padx=(8, 10), pady=5)

    def set_status(self, message: str) -> None:
        """Update the displayed status message."""
        self._status_var.set(message)

    def set_document_state(self, current_page: int, total_pages: int, zoom: float) -> None:
        """Update the right-side page and zoom indicator."""
        if total_pages:
            self.document_label.configure(
                text=f"หน้า {current_page} / {total_pages}   │   {round(zoom * 100)}%"
            )
        else:
            self.document_label.configure(text="หน้า —   │   —%")
