# -*- coding: utf-8 -*-
"""Tests for local recent PDF files."""

from pathlib import Path

from thai_pdf_editor.app.core.recent_files import (
    MAX_RECENT_FILES,
    add_recent_file,
    clear_recent_files,
    load_recent_files,
    remove_recent_file,
    save_recent_files,
)


def test_add_recent_file_keeps_latest_first_and_deduplicates(tmp_path: Path) -> None:
    """Recent files should be UTF-8 local JSON with newest file first."""
    settings_path = tmp_path / "recent_files.json"
    first = tmp_path / "เอกสารหนึ่ง.pdf"
    second = tmp_path / "เอกสารสอง.pdf"
    first.write_bytes(b"%PDF-1.7\n")
    second.write_bytes(b"%PDF-1.7\n")

    add_recent_file(first, settings_path)
    recent = add_recent_file(second, settings_path)
    recent = add_recent_file(first, settings_path)

    assert recent == [first, second]
    assert load_recent_files(settings_path) == [first, second]
    assert "เอกสารหนึ่ง.pdf" in settings_path.read_text(encoding="utf-8")


def test_load_recent_files_ignores_missing_non_pdf_and_limits(tmp_path: Path) -> None:
    """Only existing PDFs should be returned and the list should be bounded."""
    settings_path = tmp_path / "recent_files.json"
    paths = []
    for index in range(MAX_RECENT_FILES + 2):
        path = tmp_path / f"file_{index}.pdf"
        path.write_bytes(b"%PDF-1.7\n")
        paths.append(path)
    missing = tmp_path / "missing.pdf"
    text_file = tmp_path / "note.txt"
    text_file.write_text("not pdf", encoding="utf-8")
    save_recent_files(paths + [missing, text_file], settings_path)

    loaded = load_recent_files(settings_path)

    assert len(loaded) == MAX_RECENT_FILES
    assert all(path.suffix.lower() == ".pdf" for path in loaded)


def test_remove_and_clear_recent_files(tmp_path: Path) -> None:
    """Recent files can be removed or cleared from the local JSON list."""
    settings_path = tmp_path / "recent_files.json"
    first = tmp_path / "หนึ่ง.pdf"
    second = tmp_path / "สอง.pdf"
    first.write_bytes(b"%PDF-1.7\n")
    second.write_bytes(b"%PDF-1.7\n")
    save_recent_files([first, second], settings_path)

    assert remove_recent_file(first, settings_path) == [second]
    clear_recent_files(settings_path)

    assert load_recent_files(settings_path) == []
