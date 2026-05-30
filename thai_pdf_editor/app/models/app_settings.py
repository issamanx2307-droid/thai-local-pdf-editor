# -*- coding: utf-8 -*-
"""User-configurable app settings."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppSettings:
    """Simple runtime settings used by the UI."""

    ui_font_family: str = "Tahoma"
    selected_pdf_font_path: Path | None = None
    selected_image_path: Path | None = None
    default_text_size: int = 16
    default_shape_width: int = 180
    default_shape_height: int = 60
