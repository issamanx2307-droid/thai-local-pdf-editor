# -*- coding: utf-8 -*-
"""Font lookup helpers for Thai UI and PDF text insertion."""

from pathlib import Path

WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
PREFERRED_THAI_FONT_PATH = Path("D:/ฟอนท์ไทย/THSarabunNew.ttf")
THAI_UI_FONT_FALLBACKS = ("Tahoma", "Leelawadee UI", "Segoe UI")
THAI_PDF_FONT_FILES = ("tahoma.ttf", "leelawui.ttf", "segoeui.ttf")


def first_existing_thai_font() -> Path | None:
    """Return the preferred Thai-capable font file."""
    if PREFERRED_THAI_FONT_PATH.exists():
        return PREFERRED_THAI_FONT_PATH
    if not WINDOWS_FONT_DIR.exists():
        return None
    for filename in THAI_PDF_FONT_FILES:
        candidate = WINDOWS_FONT_DIR / filename
        if candidate.exists():
            return candidate
    return None


def preferred_ui_font() -> str:
    """Return a Thai-capable UI font family name."""
    return THAI_UI_FONT_FALLBACKS[0]
