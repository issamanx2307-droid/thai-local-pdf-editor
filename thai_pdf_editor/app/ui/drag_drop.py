# -*- coding: utf-8 -*-
"""Drag-and-drop support for opening PDF files."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

LOGGER = logging.getLogger("thai_pdf_editor.drag_drop")

try:
    from tkinterdnd2 import COPY, DND_FILES, TkinterDnD
except Exception:  # pragma: no cover - exercised only when dependency is missing
    COPY = "copy"
    DND_FILES = "DND_Files"
    TkinterDnD = None


def parse_dropped_paths(raw_data: str, splitlist: Callable[[str], Iterable[str]]) -> list[Path]:
    """Parse tkdnd dropped file data into paths."""
    if not raw_data:
        return []
    try:
        raw_items = list(splitlist(raw_data))
    except Exception:
        raw_items = [raw_data]
    return [_drop_item_to_path(item) for item in raw_items if str(item).strip()]


def first_pdf_path(paths: Iterable[Path]) -> Path | None:
    """Return the first dropped PDF path."""
    for path in paths:
        if path.suffix.lower() == ".pdf":
            return path
    return None


def enable_pdf_drop_target(root: Any, widgets: Iterable[Any], on_paths: Callable[[list[Path]], None]) -> bool:
    """Enable dropping PDF files onto the given Tk widgets."""
    if TkinterDnD is None:
        LOGGER.info("tkinterdnd2 is not available; drag and drop disabled")
        return False
    try:
        root.TkdndVersion = TkinterDnD._require(root)
    except Exception as exc:
        LOGGER.warning("tkdnd extension is not available; drag and drop disabled: %s", exc)
        return False

    def handle_drop(event: Any) -> str:
        paths = parse_dropped_paths(str(getattr(event, "data", "")), root.tk.splitlist)
        on_paths(paths)
        return COPY

    registered_count = 0
    for widget in widgets:
        if _register_drop_target(widget, handle_drop):
            registered_count += 1
    if registered_count == 0:
        LOGGER.warning("could not register any drag-and-drop target widgets")
        return False
    return True


def _drop_item_to_path(item: str) -> Path:
    cleaned = item.strip().strip("{}")
    if cleaned.lower().startswith("file:"):
        parsed = urlparse(cleaned)
        cleaned = unquote(parsed.path)
        if len(cleaned) >= 3 and cleaned[0] == "/" and cleaned[2] == ":":
            cleaned = cleaned[1:]
    return Path(cleaned)


def _register_drop_target(widget: Any, handle_drop: Callable[[Any], str]) -> bool:
    drop_target_register = getattr(widget, "drop_target_register", None)
    dnd_bind = getattr(widget, "dnd_bind", None)
    if not callable(drop_target_register) or not callable(dnd_bind):
        LOGGER.debug("widget does not expose tkdnd methods widget=%s", widget)
        return False
    try:
        drop_target_register(DND_FILES)
        dnd_bind("<<Drop>>", handle_drop)
        return True
    except Exception as exc:
        LOGGER.warning("could not register drop target widget=%s: %s", widget, exc)
        return False
