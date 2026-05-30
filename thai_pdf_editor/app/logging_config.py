# -*- coding: utf-8 -*-
"""Logging setup for the desktop app."""

from logging import Formatter, Logger, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path

from thai_pdf_editor.app.config import APP_LOG_PATH, REQUIRED_DIRS

MAX_LOG_BYTES = 120_000
MAX_LOG_LINES = 900


def setup_logging() -> Logger:
    """Configure rotating UTF-8 file logging and return the app logger."""
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    _trim_log_file(APP_LOG_PATH)

    logger = getLogger("thai_pdf_editor")
    logger.setLevel("INFO")
    logger.propagate = False

    if not _has_log_file_handler(logger, APP_LOG_PATH):
        handler = RotatingFileHandler(
            APP_LOG_PATH,
            maxBytes=MAX_LOG_BYTES,
            backupCount=0,
            encoding="utf-8",
        )
        formatter = Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.info("application logging ready")
    return logger


def _trim_log_file(path: Path, *, max_lines: int = MAX_LOG_LINES) -> None:
    """Keep the active log readable and under the project line-count limit."""
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    if len(lines) <= max_lines:
        return
    try:
        path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except OSError:
        return


def _has_log_file_handler(logger: Logger, path: Path) -> bool:
    resolved = path.resolve()
    for handler in logger.handlers:
        filename = getattr(handler, "baseFilename", None)
        if filename and Path(filename).resolve() == resolved:
            return True
    return False
