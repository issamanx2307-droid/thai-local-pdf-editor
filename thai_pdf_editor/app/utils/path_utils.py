# -*- coding: utf-8 -*-
"""Path helpers with Thai path support."""

import logging
import time
from pathlib import Path
from uuid import uuid4

from thai_pdf_editor.app.config import REQUIRED_DIRS, TEMP_DIR

LOGGER = logging.getLogger("thai_pdf_editor.path_utils")

# Working-copy files older than this many seconds are considered orphaned.
_WORKING_COPY_MAX_AGE_SECONDS = 3600  # 1 hour


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


def cleanup_temp_files() -> None:
    """Remove orphaned working-copy and output files left by crashed sessions.

    Only files directly inside TEMP_DIR whose names end with ``_working.*``
    or ``_output.*`` and that are older than ``_WORKING_COPY_MAX_AGE_SECONDS``
    are removed.  Sub-directories (e.g. react_bridge_*) are intentionally
    left untouched.
    """
    if not TEMP_DIR.exists():
        return
    cutoff = time.time() - _WORKING_COPY_MAX_AGE_SECONDS
    removed = 0
    for candidate in TEMP_DIR.iterdir():
        if not candidate.is_file():
            continue
        name = candidate.stem  # filename without extension
        if not (name.endswith("_working") or name.endswith("_output")):
            continue
        try:
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                removed += 1
        except OSError:
            LOGGER.warning("could not remove temp file path=%s", candidate)
    if removed:
        LOGGER.info("startup temp cleanup removed %d orphaned file(s)", removed)
