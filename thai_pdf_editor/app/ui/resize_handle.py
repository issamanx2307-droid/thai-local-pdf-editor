# -*- coding: utf-8 -*-
"""Resizable divider for the PDF viewer and side tool panel."""

from collections.abc import Callable

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import LABEL_FONT
from thai_pdf_editor.app.ui.theme import COLORS, RESIZER_WIDTH, bind_button_depth


class ResizeHandle(ctk.CTkFrame):
    """Vertical drag handle used to resize or collapse the right panel."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_drag: Callable[[int], None],
        on_toggle: Callable[[], None],
        expanded_button_text: str = ">",
        collapsed_button_text: str = "<",
        expanded_grip_text: str = "<>\n<>\n<>",
        collapsed_grip_text: str = ">\n>\n>",
    ) -> None:
        super().__init__(
            master,
            width=RESIZER_WIDTH,
            fg_color=COLORS["surface_muted"],
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
            cursor="sb_h_double_arrow",
        )
        self.grid_propagate(False)
        self._on_drag = on_drag
        self._on_toggle = on_toggle
        self._last_root_x: int | None = None
        self._expanded_button_text = expanded_button_text
        self._collapsed_button_text = collapsed_button_text
        self._expanded_grip_text = expanded_grip_text
        self._collapsed_grip_text = collapsed_grip_text

        self.toggle_button = ctk.CTkButton(
            self,
            text=self._expanded_button_text,
            width=20,
            height=28,
            command=on_toggle,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#ffffff",
            corner_radius=5,
            font=LABEL_FONT,
        )
        bind_button_depth(self.toggle_button, "primary")
        self.toggle_button.place(relx=0.5, y=14, anchor="n")

        self.label = ctk.CTkLabel(
            self,
            text=self._expanded_grip_text,
            font=LABEL_FONT,
            text_color=COLORS["primary"],
            cursor="sb_h_double_arrow",
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")
        for widget in (self, self.label):
            widget.bind("<ButtonPress-1>", self._start_drag, add="+")
            widget.bind("<B1-Motion>", self._drag, add="+")
            widget.bind("<ButtonRelease-1>", self._end_drag, add="+")
            widget.bind("<Double-Button-1>", self._toggle, add="+")

    def set_collapsed(self, collapsed: bool) -> None:
        """Update visible handle text for collapsed/expanded state."""
        self.toggle_button.configure(text=self._collapsed_button_text if collapsed else self._expanded_button_text)
        self.label.configure(text=self._collapsed_grip_text if collapsed else self._expanded_grip_text)

    def _start_drag(self, event: object) -> str:
        self._last_root_x = int(event.x_root)
        return "break"

    def _drag(self, event: object) -> str:
        if self._last_root_x is None:
            self._last_root_x = int(event.x_root)
            return "break"
        root_x = int(event.x_root)
        delta = root_x - self._last_root_x
        self._last_root_x = root_x
        if delta:
            self._on_drag(delta)
        return "break"

    def _end_drag(self, _event: object) -> str:
        self._last_root_x = None
        return "break"

    def _toggle(self, _event: object) -> str:
        self._on_toggle()
        return "break"
