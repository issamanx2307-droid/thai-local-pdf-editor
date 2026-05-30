# -*- coding: utf-8 -*-
"""Shared visual tokens and small UI helpers for the desktop editor."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from thai_pdf_editor.app.ui.fonts import BUTTON_FONT, BUTTON_HEIGHT, LABEL_FONT, PAGE_PANEL_WIDTH, TITLE_FONT

# ── Palette ─────────────────────────────────────────────────────────────────
# "Studio Precision" — crisp shell / deep navy canvas
COLORS = {
    # Shell
    "app_bg":          "#eff2f7",   # cool near-white — slight blue cast
    "surface":         "#ffffff",
    "surface_soft":    "#f6f8fc",   # form inputs, hover targets
    "surface_muted":   "#eceff6",   # secondary areas
    # Borders
    "border":          "#d0d9e8",   # clean hairline
    "border_strong":   "#a8b8cc",   # emphasis border
    # Typography
    "text":            "#0c1a2e",   # deep navy-black — authoritative
    "muted":           "#516075",   # cool slate — secondary text
    # Canvas (PDF work area)
    "canvas":          "#18202f",   # deep navy — confident dark area
    "canvas_soft":     "#1f2a3e",   # slightly lighter canvas variant
    # Accent — primary action
    "primary":         "#2055c7",   # precise, deep blue
    "primary_hover":   "#1845a8",
    "primary_pressed": "#123a8c",
    "primary_light":   "#deeaff",   # highlight / selection background
    # Secondary control
    "secondary":       "#f0f5ff",   # blue-tinted white
    "secondary_hover": "#dde8ff",
    "secondary_pressed": "#cad8f3",
    "button_lift":     "#f8fbff",
    "button_shadow":   "#8da1bd",
    # Semantic
    "danger":          "#d92b2b",
    "danger_hover":    "#b71c1c",
    "danger_pressed":  "#8f1111",
    "warning":         "#c97000",
    "warning_hover":   "#a55c00",
    "warning_pressed": "#7e4500",
    "success":         "#15883d",
    "success_hover":   "#0f6b2e",
}

# ── Layout tokens ────────────────────────────────────────────────────────────
RADIUS_PANEL   = 10
RADIUS_CONTROL = 6
PANEL_PAD      = 12
SECTION_PAD    = 10
TOOL_BUTTON_HEIGHT    = 40
RIBBON_BUTTON_HEIGHT  = 62
RIBBON_BUTTON_WIDTH   = 60
RESIZER_WIDTH         = 22
TOOL_PANEL_MIN_WIDTH     = 260
TOOL_PANEL_DEFAULT_WIDTH = 330
TOOL_PANEL_MAX_WIDTH     = 520
PAGE_PANEL_MIN_WIDTH     = 200
PAGE_PANEL_DEFAULT_WIDTH = PAGE_PANEL_WIDTH
PAGE_PANEL_MAX_WIDTH     = 420

# ── Icon glyphs ─────────────────────────────────────────────────────────────
# Unicode symbols — Windows font fallback renders any missing glyphs cleanly.
ICON = {
    "open":         "⊕",    # circled plus — add/open
    "recent":       "≡",    # triple bar  — list
    "save":         "↓",    # down arrow   — save/export
    "undo":         "↩",    # hooked left arrow
    "redo":         "↪",    # hooked right arrow
    "merge":        "⊞",    # squared plus — combine
    "split":        "÷",    # division sign
    "info":         "▪",    # small square — metadata
    "search":       "⊙",    # circled dot  — find
    "zoom_out":     "−",    # proper minus (U+2212)
    "zoom_in":      "+",    # plus
    "fit_width":    "↔",    # left-right arrow
    "fit_height":   "↕",    # up-down arrow
    "prev":         "←",    # left arrow
    "next":         "→",    # right arrow
    "up":           "↑",
    "down":         "↓",
    "copy":         "⊚",    # circled ring operator
    "rotate_left":  "↺",    # counterclockwise arrow
    "rotate_right": "↻",    # clockwise arrow
    "delete":       "×",    # multiplication sign (U+00D7)
    "extract":      "↗",    # diagonal arrow
    "form":         "□",    # empty square
    "text":         "T",
    "font":         "A",
    "image":        "◆",    # filled diamond
    "signature":    "◇",    # white diamond
    "shape":        "▬",    # rectangle
    "highlight":    "◈",    # diamond with dot
    "crop":         "◻",    # white square
    "redact":       "■",    # black square
    "check":        "✓",    # checkmark
    "help":         "?",
    "reset":        "⊙",    # circled dot — restore
    "print":        "⎙",    # print symbol (U+2399)
}


# ── Helper functions ─────────────────────────────────────────────────────────

def icon_label(icon_name: str, label: str, *, stacked: bool = False) -> str:
    """Return a compact icon plus label string for CustomTkinter text buttons."""
    icon = ICON.get(icon_name, "")
    separator = "\n" if stacked else "  "
    return f"{icon}{separator}{label}" if icon else label


def button_depth_palette(variant: str = "secondary") -> dict[str, object]:
    """Return raised and pressed surface colors for a button variant."""
    palettes: dict[str, dict[str, object]] = {
        "primary": {
            "fg_color": COLORS["primary"],
            "hover_color": COLORS["primary_hover"],
            "pressed_fg_color": COLORS["primary_pressed"],
            "text_color": "#ffffff",
            "border_color": "#7fa4ff",
            "pressed_border_color": "#0b2867",
            "border_width": 2,
            "pressed_border_width": 1,
        },
        "danger": {
            "fg_color": COLORS["danger"],
            "hover_color": COLORS["danger_hover"],
            "pressed_fg_color": COLORS["danger_pressed"],
            "text_color": "#ffffff",
            "border_color": "#ff8a8a",
            "pressed_border_color": "#760d0d",
            "border_width": 2,
            "pressed_border_width": 1,
        },
        "warning": {
            "fg_color": COLORS["warning"],
            "hover_color": COLORS["warning_hover"],
            "pressed_fg_color": COLORS["warning_pressed"],
            "text_color": "#ffffff",
            "border_color": "#ffc56d",
            "pressed_border_color": "#6c3b00",
            "border_width": 2,
            "pressed_border_width": 1,
        },
        "secondary": {
            "fg_color": COLORS["button_lift"],
            "hover_color": COLORS["secondary_hover"],
            "pressed_fg_color": COLORS["secondary_pressed"],
            "text_color": COLORS["primary"],
            "border_color": COLORS["button_shadow"],
            "pressed_border_color": COLORS["border_strong"],
            "border_width": 2,
            "pressed_border_width": 1,
        },
    }
    return palettes.get(variant, palettes["secondary"])


def button_style(variant: str = "secondary") -> dict[str, object]:
    """Return consistent CTkButton styling for a named variant."""
    depth = button_depth_palette(variant)
    base = {
        "height":        TOOL_BUTTON_HEIGHT,
        "font":          BUTTON_FONT,
        "corner_radius": RADIUS_CONTROL,
        "border_width":  depth["border_width"],
        "border_color":  depth["border_color"],
    }
    return {**base,
        "fg_color":    depth["fg_color"],
        "hover_color": depth["hover_color"],
        "text_color":  depth["text_color"],
    }


def bind_button_depth(button: ctk.CTkButton, variant: str = "secondary") -> ctk.CTkButton:
    """Bind press/release feedback so CTk buttons feel raised and depressible."""
    depth = button_depth_palette(variant)
    raised = {
        "fg_color": depth["fg_color"],
        "border_color": depth["border_color"],
        "border_width": depth["border_width"],
    }
    pressed = {
        "fg_color": depth["pressed_fg_color"],
        "border_color": depth["pressed_border_color"],
        "border_width": depth["pressed_border_width"],
    }

    def is_disabled() -> bool:
        try:
            return button.cget("state") == "disabled"
        except Exception:  # noqa: BLE001 - custom widgets may reject cget during teardown.
            return False

    def restore() -> None:
        try:
            button.configure(**raised)
        except Exception:  # noqa: BLE001 - ignore callbacks after widget destruction.
            pass

    def press(_event: object) -> None:
        if is_disabled():
            return
        try:
            button.configure(**pressed)
        except Exception:  # noqa: BLE001
            pass

    def release(_event: object) -> None:
        try:
            button.after(45, restore)
        except Exception:  # noqa: BLE001
            restore()

    button.configure(**raised)
    button.bind("<ButtonPress-1>", press, add="+")
    button.bind("<ButtonRelease-1>", release, add="+")
    button.bind("<Leave>", release, add="+")
    setattr(button, "_thai_pdf_depth_variant", variant)
    return button


def panel_style() -> dict[str, object]:
    """Return common style for the left and right panels."""
    return {
        "fg_color":      COLORS["surface"],
        "corner_radius": RADIUS_PANEL,
        "border_width":  1,
        "border_color":  COLORS["border"],
    }


def make_section(
    master: ctk.CTkBaseClass,
    *,
    title: str,
    icon_name: str,
    row: int,
    expanded: bool = True,
) -> ctk.CTkFrame:
    """Create a titled section frame at a specific grid row."""
    section = ctk.CTkFrame(master, fg_color=COLORS["surface"], corner_radius=0)
    section.grid(row=row, column=0, sticky="ew", padx=PANEL_PAD, pady=(4, 8))
    section.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(section, fg_color="transparent", corner_radius=0)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        header,
        text=icon_label(icon_name, title),
        anchor="w",
        font=TITLE_FONT,
        text_color=COLORS["text"],
    ).grid(row=0, column=0, sticky="ew", pady=(0, 6))
    caret = "^" if expanded else "v"
    ctk.CTkLabel(header, text=caret, width=18, font=LABEL_FONT,
                 text_color=COLORS["muted"]).grid(row=0, column=1, sticky="e", pady=(0, 6))
    return section


def make_button(
    master: ctk.CTkBaseClass,
    *,
    text: str,
    command: Callable[[], None],
    icon_name: str,
    variant: str = "secondary",
    width: int | None = None,
) -> ctk.CTkButton:
    """Create a side-panel button with consistent icon and variant styling."""
    options = button_style(variant)
    if width is not None:
        options["width"] = width
    button = ctk.CTkButton(master, text=icon_label(icon_name, text), command=command, **options)
    return bind_button_depth(button, variant)


def ribbon_button_style(variant: str = "secondary") -> dict[str, object]:
    """Return button style for compact ribbon buttons."""
    options = button_style(variant)
    options.update({
        "height": RIBBON_BUTTON_HEIGHT,
        "width":  RIBBON_BUTTON_WIDTH,
        "font":   (BUTTON_FONT[0], 11, BUTTON_FONT[2]),
    })
    return options


def clamp_tool_panel_width(width: int) -> int:
    """Clamp the right tool panel to a usable resize range."""
    return max(TOOL_PANEL_MIN_WIDTH, min(TOOL_PANEL_MAX_WIDTH, int(width)))


def clamp_page_panel_width(width: int) -> int:
    """Clamp the left page panel to a usable resize range."""
    return max(PAGE_PANEL_MIN_WIDTH, min(PAGE_PANEL_MAX_WIDTH, int(width)))
