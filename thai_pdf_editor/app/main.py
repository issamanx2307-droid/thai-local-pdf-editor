# -*- coding: utf-8 -*-
"""Application entrypoint."""

from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.ui.main_window import MainWindow
from thai_pdf_editor.app.utils.path_utils import cleanup_temp_files, ensure_app_dirs


def create_app(*, smoke_test: bool = False, open_file: str | None = None) -> MainWindow:
    """Create the desktop app window."""
    ensure_app_dirs()
    setup_logging()
    cleanup_temp_files()
    return MainWindow(smoke_test=smoke_test, open_file=open_file)


def run(*, smoke_test: bool = False, open_file: str | None = None) -> None:
    """Run the desktop app."""
    app = create_app(smoke_test=smoke_test, open_file=open_file)
    app.mainloop()
