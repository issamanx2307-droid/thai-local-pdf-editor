# -*- coding: utf-8 -*-
"""Local recent-file storage for opened PDFs."""

from __future__ import annotations

import json
from pathlib import Path

from thai_pdf_editor.app.config import RECENT_FILES_PATH

MAX_RECENT_FILES = 10


def load_recent_files(path: Path = RECENT_FILES_PATH) -> list[Path]:
    """Load existing recent PDF paths, preserving Thai paths."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    paths: list[Path] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        candidate = Path(item)
        key = str(candidate).lower()
        if candidate.exists() and candidate.suffix.lower() == ".pdf" and key not in seen:
            paths.append(candidate)
            seen.add(key)
    return paths[:MAX_RECENT_FILES]


def add_recent_file(pdf_path: Path, path: Path = RECENT_FILES_PATH) -> list[Path]:
    """Add a PDF path to the local recent-file list."""
    resolved = Path(pdf_path).expanduser()
    recent = [candidate for candidate in load_recent_files(path) if _path_key(candidate) != _path_key(resolved)]
    recent.insert(0, resolved)
    recent = recent[:MAX_RECENT_FILES]
    save_recent_files(recent, path)
    return recent


def remove_recent_file(pdf_path: Path, path: Path = RECENT_FILES_PATH) -> list[Path]:
    """Remove one path from the local recent-file list."""
    target_key = _path_key(pdf_path)
    recent = [candidate for candidate in load_recent_files(path) if _path_key(candidate) != target_key]
    save_recent_files(recent, path)
    return recent


def clear_recent_files(path: Path = RECENT_FILES_PATH) -> None:
    """Clear the local recent-file list."""
    save_recent_files([], path)


def save_recent_files(paths: list[Path], path: Path = RECENT_FILES_PATH) -> None:
    """Persist recent files as UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_paths: list[str] = []
    seen: set[str] = set()
    for candidate in paths:
        key = _path_key(candidate)
        if key in seen:
            continue
        clean_paths.append(str(candidate))
        seen.add(key)
    path.write_text(json.dumps(clean_paths[:MAX_RECENT_FILES], ensure_ascii=False, indent=2), encoding="utf-8")


def _path_key(path: Path) -> str:
    return str(Path(path)).lower()
