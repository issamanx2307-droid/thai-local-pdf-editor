# -*- coding: utf-8 -*-
"""Document, navigation, zoom, and error-handling window actions."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from thai_pdf_editor.app.constants import DEFAULT_STATUS, MAX_ZOOM, MIN_ZOOM, ZOOM_STEP
from thai_pdf_editor.app.core.errors import AppError
from thai_pdf_editor.app.core.recent_files import add_recent_file, clear_recent_files, load_recent_files, remove_recent_file
from thai_pdf_editor.app.core.undo_redo import can_redo_pending, can_undo_pending
from thai_pdf_editor.app.ui.dialogs import ask_open_pdf_path, confirm, show_error, show_usage_guide_dialog
from thai_pdf_editor.app.ui.dirty_guard import can_discard_unsaved_changes
from thai_pdf_editor.app.ui.drag_drop import first_pdf_path
from thai_pdf_editor.app.ui.keyboard_shortcuts import NAVIGATION_SHORTCUTS, is_text_input_event
from thai_pdf_editor.app.ui.recent_files_dialog import show_recent_files_dialog

LOGGER = logging.getLogger("thai_pdf_editor.main_window")


class DocumentActionsMixin:
    """Actions for opening documents, navigation, rendering, and shared error handling."""

    def request_close(self) -> None:
        """Close the window after confirming unsaved changes."""
        if self._confirm_discard_unsaved_changes():
            self.destroy()

    def destroy(self) -> None:
        """Close the current PDF before destroying the window."""
        self.document.close()
        super().destroy()

    def open_pdf(self) -> None:
        """Open a PDF through a file dialog."""
        if not self._confirm_discard_unsaved_changes():
            return
        path_text = ask_open_pdf_path()
        if not path_text:
            return
        self._run_user_action(lambda: self._open_pdf_path(Path(path_text)))

    def open_pdf_from_path(self, file_path: str) -> None:
        """Open a PDF from a given file path (e.g. command-line argument or file association)."""
        path = Path(file_path)
        if not path.is_file():
            LOGGER.warning("file not found: %s", file_path)
            return
        self._run_user_action(lambda: self._open_pdf_path(path))

    def open_recent_files(self) -> None:
        """Open a recent local PDF file."""
        recent_paths = load_recent_files()

        def open_selected(path: Path) -> None:
            if not self._confirm_discard_unsaved_changes():
                return
            self._run_user_action(lambda: self._open_pdf_path(path))

        show_recent_files_dialog(
            self,
            recent_paths,
            on_open_path=open_selected,
            on_remove_path=remove_recent_file,
            on_clear=clear_recent_files,
        )

    def show_usage_guide(self) -> None:
        """Open the local usage guide dialog."""
        show_usage_guide_dialog(self)

    def open_dropped_paths(self, paths: list[Path]) -> None:
        """Open the first PDF path from a drag-and-drop event."""
        pdf_path = first_pdf_path(paths)
        if pdf_path is None:
            self.status_bar.set_status("กรุณาลากไฟล์ PDF มาวางเท่านั้น")
            show_error("กรุณาลากไฟล์ PDF มาวางเท่านั้น")
            return
        if not self._confirm_discard_unsaved_changes():
            return
        self._run_user_action(lambda: self._open_pdf_path(pdf_path))

    def _confirm_discard_unsaved_changes(self) -> bool:
        """Ask before losing unsaved working-copy changes."""
        return can_discard_unsaved_changes(self.doc_state.dirty, confirm)

    def _open_pdf_path(self, path: Path) -> None:
        self.status_bar.set_status("กำลังเปิดไฟล์...")
        self._fit_width_active = False
        self._fit_height_active = False
        self.document.open(path)
        self.page_panel.reset_page_cache()
        add_recent_file(path)
        self.search_results.clear()
        self.search_current_index = -1
        self.renderer.clear_cache()
        self.render_current_page()
        self.status_bar.set_status(f"เปิดไฟล์แล้ว: {path.name}")

    def render_current_page(self) -> None:
        """Render and show the current PDF page."""
        if not self.doc_state.has_document:
            return
        if self._fit_width_active:
            self.update_idletasks()
            self.doc_state.zoom_level = round(self._fit_width_zoom(), 2)
        elif self._fit_height_active:
            self.update_idletasks()
            self.doc_state.zoom_level = round(self._fit_height_zoom(), 2)
        rendered = self.renderer.render_page(
            self.document.raw,
            self.doc_state.working_copy_path,
            self.doc_state.current_page_index,
            self.doc_state.zoom_level,
            self.doc_state.dirty_version,
            self.doc_state.pending_operations,
        )
        self.pdf_canvas.show_image(rendered.image, zoom=self.doc_state.zoom_level)
        self.refresh_ui()
        self._prefetch_adjacent_pages()

    def _prefetch_adjacent_pages(self) -> None:
        """Start background threads to pre-render the pages before and after the current one."""
        if not self.doc_state.has_document or self.doc_state.working_copy_path is None:
            return
        path = self.doc_state.working_copy_path
        zoom = self.doc_state.zoom_level
        dirty_version = self.doc_state.dirty_version
        pending = self.doc_state.pending_operations or None
        current = self.doc_state.current_page_index
        total = self.doc_state.total_pages
        candidates = []
        if current + 1 < total:
            candidates.append(current + 1)
        if current - 1 >= 0:
            candidates.append(current - 1)
        for idx in candidates:
            threading.Thread(
                target=self.renderer.prefetch_page,
                args=(path, idx, zoom, dirty_version, pending),
                daemon=True,
            ).start()

    def refresh_ui(self) -> None:
        """Refresh toolbar, page list, and status-dependent widgets."""
        self.toolbar.set_document_state(
            self.doc_state.display_page_number,
            self.doc_state.total_pages,
            self.doc_state.zoom_level,
            can_undo=can_undo_pending(self.doc_state),
            can_redo=can_redo_pending(self.doc_state),
        )
        self.page_panel.refresh(self.doc_state.total_pages, self.doc_state.current_page_index)
        self.tool_panel.set_document_loaded(self.doc_state.has_document)
        self.status_bar.set_document_state(
            self.doc_state.display_page_number,
            self.doc_state.total_pages,
            self.doc_state.zoom_level,
        )

    def previous_page(self) -> None:
        """Move to the previous page."""
        if self.doc_state.current_page_index > 0:
            self.go_to_page(self.doc_state.current_page_index - 1)

    def next_page(self) -> None:
        """Move to the next page."""
        if self.doc_state.current_page_index < self.doc_state.total_pages - 1:
            self.go_to_page(self.doc_state.current_page_index + 1)

    def first_page(self) -> None:
        """Move to the first page."""
        self.go_to_page(0)

    def last_page(self) -> None:
        """Move to the last page."""
        if self.doc_state.total_pages:
            self.go_to_page(self.doc_state.total_pages - 1)

    def go_to_page(self, page_index: int) -> None:
        """Show a specific page."""
        if not 0 <= page_index < self.doc_state.total_pages:
            return
        self.doc_state.set_current_page(page_index)
        self._run_user_action(self.render_current_page)

    def _bind_navigation_shortcuts(self) -> None:
        """Bind page navigation shortcuts across the current Tk app."""
        self.bind_all(NAVIGATION_SHORTCUTS["previous_page"], self._shortcut_previous_page, add="+")
        self.bind_all(NAVIGATION_SHORTCUTS["next_page"], self._shortcut_next_page, add="+")
        self.bind_all(NAVIGATION_SHORTCUTS["first_page"], self._shortcut_first_page, add="+")
        self.bind_all(NAVIGATION_SHORTCUTS["last_page"], self._shortcut_last_page, add="+")

    def _shortcut_previous_page(self, event: object) -> str | None:
        return self._run_navigation_shortcut(event, self.previous_page)

    def _shortcut_next_page(self, event: object) -> str | None:
        return self._run_navigation_shortcut(event, self.next_page)

    def _shortcut_first_page(self, event: object) -> str | None:
        return self._run_navigation_shortcut(event, self.first_page)

    def _shortcut_last_page(self, event: object) -> str | None:
        return self._run_navigation_shortcut(event, self.last_page)

    def _run_navigation_shortcut(self, event: object, action: Callable[[], None]) -> str | None:
        if is_text_input_event(event) or not self.doc_state.has_document:
            return None
        action()
        return "break"

    def zoom_in(self) -> None:
        """Increase preview zoom."""
        self._set_zoom(min(MAX_ZOOM, self.doc_state.zoom_level + ZOOM_STEP))

    def zoom_out(self) -> None:
        """Decrease preview zoom."""
        self._set_zoom(max(MIN_ZOOM, self.doc_state.zoom_level - ZOOM_STEP))

    def fit_width(self) -> None:
        """Fit the current page preview to the canvas width."""
        if not self.doc_state.has_document:
            return
        self._fit_width_active = True
        self._fit_height_active = False
        self.update_idletasks()
        self._set_zoom(self._fit_width_zoom(), keep_fit_width=True)

    def _fit_width_zoom(self) -> float:
        page = self.document.get_page(self.doc_state.current_page_index)
        viewport_width = self.pdf_canvas.viewport_width()
        return max(MIN_ZOOM, min(MAX_ZOOM, viewport_width / page.rect.width))

    def fit_height(self) -> None:
        """Fit the current page preview to the canvas height."""
        if not self.doc_state.has_document:
            return
        self._fit_width_active = False
        self._fit_height_active = True
        self.update_idletasks()
        self._set_zoom(self._fit_height_zoom(), keep_fit_height=True)

    def _fit_height_zoom(self) -> float:
        page = self.document.get_page(self.doc_state.current_page_index)
        viewport_height = self.pdf_canvas.viewport_height()
        return max(MIN_ZOOM, min(MAX_ZOOM, viewport_height / page.rect.height))

    def _set_zoom(self, zoom: float, *, keep_fit_width: bool = False, keep_fit_height: bool = False) -> None:
        if not keep_fit_width:
            self._fit_width_active = False
        if not keep_fit_height:
            self._fit_height_active = False
        self.doc_state.zoom_level = round(zoom, 2)
        self._run_user_action(self.render_current_page)

    def _run_user_action(self, action: object) -> None:
        try:
            action()
        except AppError as exc:
            LOGGER.warning("user action failed: %s", exc.detail)
            self.status_bar.set_status(f"เกิดข้อผิดพลาด: {exc.user_message}")
            show_error(exc.user_message)
        except Exception:
            LOGGER.exception("unexpected user action failure")
            self.status_bar.set_status("เกิดข้อผิดพลาด: ไม่สามารถทำรายการได้")
            show_error("ไม่สามารถทำรายการได้ รายละเอียดถูกบันทึกไว้ใน log")
        finally:
            if not self.doc_state.has_document:
                self.status_bar.set_status(DEFAULT_STATUS)
