# -*- coding: utf-8 -*-
"""Tests for app logging hygiene."""

from logging import getLogger

from thai_pdf_editor.app.config import APP_LOG_PATH
from thai_pdf_editor.app.logging_config import _trim_log_file, setup_logging


def test_trim_log_file_keeps_recent_lines_under_limit(tmp_path) -> None:
    """Large active logs are trimmed to a bounded recent tail."""
    log_path = tmp_path / "app.log"
    log_path.write_text("\n".join(f"line {index}" for index in range(1100)) + "\n", encoding="utf-8")

    _trim_log_file(log_path, max_lines=900)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 900
    assert lines[0] == "line 200"
    assert lines[-1] == "line 1099"


def test_logging_handler_avoids_windows_rename_rollover() -> None:
    """The active log should not use rename-based backup rollover on Windows."""
    logger = setup_logging()
    handlers = [
        handler
        for handler in getLogger("thai_pdf_editor").handlers
        if getattr(handler, "baseFilename", None) == str(APP_LOG_PATH)
    ]

    assert logger is getLogger("thai_pdf_editor")
    assert handlers
    assert all(getattr(handler, "backupCount", None) == 0 for handler in handlers)
