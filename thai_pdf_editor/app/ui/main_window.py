# -*- coding: utf-8 -*-
"""Main CustomTkinter window."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from thai_pdf_editor.app.constants import APP_MIN_HEIGHT, APP_MIN_WIDTH, APP_TITLE, APP_VERSION
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.layout_settings import LayoutSettings
from thai_pdf_editor.app.core.page_operations import PageOperations
from thai_pdf_editor.app.core.pdf_document import PdfDocument
from thai_pdf_editor.app.core.pdf_renderer import PdfRenderer
from thai_pdf_editor.app.core.pdf_search import PdfSearchResult
from thai_pdf_editor.app.core.save_manager import SaveManager
from thai_pdf_editor.app.models.app_settings import AppSettings
from thai_pdf_editor.app.ui.actions.document_actions import DocumentActionsMixin
from thai_pdf_editor.app.ui.actions.document_edit_actions import DocumentEditActionsMixin
from thai_pdf_editor.app.ui.actions.page_overlay_actions import PageOverlayActionsMixin
from thai_pdf_editor.app.ui.actions.save_export_actions import SaveExportActionsMixin
from thai_pdf_editor.app.ui.actions.search_actions import SearchActionsMixin
from thai_pdf_editor.app.ui.drag_drop import enable_pdf_drop_target
from thai_pdf_editor.app.ui.fonts import configure_tk_default_fonts
from thai_pdf_editor.app.ui.page_panel import PagePanel
from thai_pdf_editor.app.ui.pdf_canvas import PdfCanvas
from thai_pdf_editor.app.ui.resize_handle import ResizeHandle
from thai_pdf_editor.app.ui.status_bar import StatusBar
from thai_pdf_editor.app.ui.theme import (
    COLORS,
    PAGE_PANEL_DEFAULT_WIDTH,
    TOOL_PANEL_DEFAULT_WIDTH,
    clamp_page_panel_width,
    clamp_tool_panel_width,
)
from thai_pdf_editor.app.ui.tool_panel import ToolPanel
from thai_pdf_editor.app.ui.toolbar import Toolbar
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font, preferred_ui_font


class MainWindow(
    DocumentActionsMixin,
    SearchActionsMixin,
    SaveExportActionsMixin,
    DocumentEditActionsMixin,
    PageOverlayActionsMixin,
    ctk.CTk,
):
    """Main desktop window for the local PDF editor."""

    def __init__(self, *, smoke_test: bool = False, open_file: str | None = None) -> None:
        super().__init__()
        self.doc_state = DocumentState()
        self.settings = AppSettings(ui_font_family=preferred_ui_font())
        self.document = PdfDocument(self.doc_state)
        self.renderer = PdfRenderer()
        self.page_operations = PageOperations(self.document, self.doc_state)
        self.save_manager = SaveManager()
        self.search_query = ""
        self.search_results: list[PdfSearchResult] = []
        self.search_current_index = -1
        self._layout_settings = LayoutSettings()
        self._page_panel_width = self._layout_settings.page_panel_width
        self._tool_panel_width = self._layout_settings.tool_panel_width
        self._page_panel_collapsed = False
        self._tool_panel_collapsed = False
        self._fit_width_active = False
        self._fit_height_active = False
        self._layout_sync_job: str | None = None

        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry(f"{APP_MIN_WIDTH}x{APP_MIN_HEIGHT}")
        self.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.05)
        configure_tk_default_fonts()
        self.configure(fg_color=COLORS["app_bg"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.toolbar = Toolbar(
            self,
            on_open=self.open_pdf,
            on_open_recent=self.open_recent_files,
            on_save_as=self.save_as,
            on_search=self.open_text_search,
            on_undo=self.undo_pending_operation,
            on_redo=self.redo_pending_operation,
            on_merge_pdfs=self.merge_pdf_files,
            on_edit_metadata=self.edit_metadata,
            on_prev=self.previous_page,
            on_next=self.next_page,
            on_zoom_in=self.zoom_in,
            on_zoom_out=self.zoom_out,
            on_fit_width=self.fit_width,
            on_fit_height=self.fit_height,
            on_go_to_page=self.go_to_page,
            on_usage_guide=self.show_usage_guide,
            on_reset_layout=self.reset_layout,
            on_print=self.print_current_pdf,
        )
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(4, 4))

        content = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["app_bg"])
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(2, weight=1, minsize=360)
        content.grid_columnconfigure(1, weight=0)
        content.grid_columnconfigure(3, weight=0)
        content.grid_columnconfigure(4, weight=0)

        self.page_panel = PagePanel(
            content,
            on_select_page=self.go_to_page,
            on_move_up=self.move_page_up,
            on_move_down=self.move_page_down,
            on_duplicate_page=self.duplicate_page,
            on_rotate_left=self.rotate_left,
            on_rotate_right=self.rotate_right,
            on_delete_page=self.delete_page,
            on_extract_page=self.extract_current_page,
            on_edit_form=self.edit_form_fields,
            on_replace_text=self.replace_existing_text,
            on_import_fonts=self.import_fonts_from_pdf,
            on_manage_pending_overlays=self.manage_pending_overlays,
            on_export_jpg=self.export_jpg_files,
            on_batch_jpg=self.batch_export_jpg_files,
            on_open_qa_checklist=self.open_qa_checklist,
        )
        self.page_panel.configure(width=self._page_panel_width)
        self.page_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        self.page_resize_handle = ResizeHandle(
            content,
            on_drag=self._resize_page_panel,
            on_toggle=self._toggle_page_panel,
            expanded_button_text="<",
            collapsed_button_text=">",
            expanded_grip_text="<>\n<>\n<>",
            collapsed_grip_text="<\n<\n<",
        )
        self.page_resize_handle.grid(row=0, column=1, sticky="ns", padx=(0, 8))

        self.pdf_canvas = PdfCanvas(content, on_open=self.open_pdf)
        self.pdf_canvas.set_interaction_handlers(on_click=self.handle_canvas_click, on_rect=self.handle_canvas_rect)
        self.pdf_canvas.grid(row=0, column=2, sticky="nsew")

        self.resize_handle = ResizeHandle(
            content,
            on_drag=self._resize_tool_panel,
            on_toggle=self._toggle_tool_panel,
        )
        self.resize_handle.grid(row=0, column=3, sticky="ns", padx=(8, 0))

        self.tool_panel = ToolPanel(
            content,
            on_choose_font=self.choose_font,
            on_choose_image=self.choose_image,
            on_create_signature=self.create_simple_signature,
            on_text_tool=lambda: self.activate_tool("text"),
            on_image_tool=lambda: self.activate_tool("image"),
            on_rectangle_tool=lambda: self.activate_tool("rectangle"),
            on_highlight_tool=lambda: self.activate_tool("highlight"),
            on_crop_tool=lambda: self.activate_tool("crop"),
            on_redact_tool=lambda: self.activate_tool("redact"),
            on_edit_metadata=self.edit_metadata,
        )
        self.tool_panel.configure(width=self._tool_panel_width)
        self.tool_panel.grid(row=0, column=4, sticky="ns", padx=(10, 0))
        default_pdf_font = first_existing_thai_font()
        if default_pdf_font is not None:
            self.tool_panel.set_font_path(default_pdf_font)

        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self._drag_drop_enabled = enable_pdf_drop_target(
            self,
            (self, self.pdf_canvas, self.pdf_canvas.canvas),
            self.open_dropped_paths,
        )
        self._bind_navigation_shortcuts()

        self.refresh_ui()
        if smoke_test:
            self.after(250, self.destroy)
        elif open_file:
            # Auto-open the PDF passed via command-line (e.g. Windows file association)
            self.after(100, lambda: self._auto_open_file(open_file))

    def _auto_open_file(self, file_path: str) -> None:
        """Auto-open a PDF file passed via command-line argument."""
        self.open_pdf_from_path(file_path)

    def destroy(self) -> None:
        """Close the app without carrying resized panels into the next run."""
        if self._layout_sync_job is not None:
            try:
                self.after_cancel(self._layout_sync_job)
            except (ValueError, tk.TclError):
                pass
            self._layout_sync_job = None
        self._sync_layout_settings()
        super().destroy()

    def _resize_page_panel(self, delta_x: int) -> None:
        """Resize the left page panel by dragging the divider."""
        if self._page_panel_collapsed:
            self._show_page_panel()
        self._page_panel_width = clamp_page_panel_width(self._page_panel_width + delta_x)
        self.page_panel.configure(width=self._page_panel_width)
        self._sync_layout_settings()
        self._schedule_viewer_layout_sync()

    def _toggle_page_panel(self) -> None:
        """Collapse or restore the left page list panel."""
        if self._page_panel_collapsed:
            self._show_page_panel()
        else:
            self.page_panel.grid_remove()
            self._page_panel_collapsed = True
            self.page_resize_handle.set_collapsed(True)
            self._sync_viewer_after_layout_change()

    def _show_page_panel(self) -> None:
        self._page_panel_width = clamp_page_panel_width(self._page_panel_width)
        self.page_panel.configure(width=self._page_panel_width)
        self.page_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        self._page_panel_collapsed = False
        self.page_resize_handle.set_collapsed(False)
        self._sync_viewer_after_layout_change()

    def _resize_tool_panel(self, delta_x: int) -> None:
        """Resize the right tool panel by dragging the divider."""
        if self._tool_panel_collapsed:
            self._show_tool_panel()
        self._tool_panel_width = clamp_tool_panel_width(self._tool_panel_width - delta_x)
        self.tool_panel.configure(width=self._tool_panel_width)
        self._sync_layout_settings()
        self._schedule_viewer_layout_sync()

    def _toggle_tool_panel(self) -> None:
        """Collapse or restore the right tool panel to expand the PDF reader."""
        if self._tool_panel_collapsed:
            self._show_tool_panel()
        else:
            self.tool_panel.grid_remove()
            self._tool_panel_collapsed = True
            self.resize_handle.set_collapsed(True)
            self._sync_viewer_after_layout_change()

    def _show_tool_panel(self) -> None:
        self._tool_panel_width = clamp_tool_panel_width(self._tool_panel_width)
        self.tool_panel.configure(width=self._tool_panel_width)
        self.tool_panel.grid(row=0, column=4, sticky="ns", padx=(10, 0))
        self._tool_panel_collapsed = False
        self.resize_handle.set_collapsed(False)
        self._sync_viewer_after_layout_change()

    def reset_layout(self) -> None:
        """Restore the default reader layout for the current session."""
        self._page_panel_width = PAGE_PANEL_DEFAULT_WIDTH
        self._tool_panel_width = TOOL_PANEL_DEFAULT_WIDTH
        self.page_panel.configure(width=self._page_panel_width)
        self.tool_panel.configure(width=self._tool_panel_width)
        self._show_page_panel()
        self._show_tool_panel()
        self._sync_layout_settings()
        self.status_bar.set_status("คืนค่าหน้าจอเริ่มต้นแล้ว")
        self._sync_viewer_after_layout_change()

    def _sync_layout_settings(self) -> None:
        """Keep in-memory layout values aligned without writing startup state."""
        self._layout_settings = LayoutSettings(
            tool_panel_width=self._tool_panel_width,
            page_panel_width=self._page_panel_width,
        )

    def _schedule_viewer_layout_sync(self) -> None:
        """Debounce expensive PDF re-rendering while a divider is being dragged."""
        if self._layout_sync_job is not None:
            try:
                self.after_cancel(self._layout_sync_job)
            except (ValueError, tk.TclError):
                pass
        self._layout_sync_job = self.after(90, self._sync_viewer_after_layout_change)

    def _sync_viewer_after_layout_change(self) -> None:
        """Keep the PDF viewport in sync with side panel width changes."""
        if self._layout_sync_job is not None:
            try:
                self.after_cancel(self._layout_sync_job)
            except (ValueError, tk.TclError):
                pass
        self._layout_sync_job = None
        self.update_idletasks()
        if self.doc_state.has_document and (self._fit_width_active or self._fit_height_active):
            self._run_user_action(self.render_current_page)
        self.pdf_canvas.clamp_scroll_to_content()
