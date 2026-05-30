# -*- coding: utf-8 -*-
"""Path helpers with Thai path support."""

from pathlib import Path
from uuid import uuid4

from thai_pdf_editor.app.config import REQUIRED_DIRS, TEMP_DIR


def ensure_app_dirs() -> None:
    """Create local data and asset directories."""
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def normalize_path(value: str | Path) -> Path:
    """Return a resolved Path without requiring it to already exist."""
    return Path(value).expanduser()


def make_working_copy_path(source_path: Path) -> Path:
    """Create a unique working-copy path in data/temp."""
    ensure_app_dirs()
    suffix = source_path.suffix or ".pdf"
    return TEMP_DIR / f"{source_path.stem}_{uuid4().hex}_working{suffix}"


def make_temp_output_path(destination_path: Path) -> Path:
    """Create a unique temp output path for safe save operations."""
    ensure_app_dirs()
    suffix = destination_path.suffix or ".pdf"
    return TEMP_DIR / f"{destination_path.stem}_{uuid4().hex}_output{suffix}"


def default_edited_path(source_path: Path) -> Path:
    """Return the default Save As path next to the source PDF."""
    return source_path.with_name(f"{source_path.stem}_edited.pdf")
