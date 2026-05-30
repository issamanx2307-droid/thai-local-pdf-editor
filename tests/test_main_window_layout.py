# -*- coding: utf-8 -*-
"""Tests for main-window layout startup behavior."""

import json
from pathlib import Path

from thai_pdf_editor.app.config import LAYOUT_SETTINGS_PATH
from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.ui.actions.document_actions import DocumentActionsMixin
from thai_pdf_editor.app.ui.main_window import MainWindow
from thai_pdf_editor.app.ui.theme import (
    PAGE_PANEL_DEFAULT_WIDTH,
    PAGE_PANEL_MIN_WIDTH,
    RIBBON_BUTTON_WIDTH,
    TOOL_PANEL_DEFAULT_WIDTH,
    TOOL_PANEL_MIN_WIDTH,
)


class _FakeRect:
    width = 300
    height = 420


class _FakePage:
    rect = _FakeRect()


class _FakeDocument:
    def get_page(self, _page_index: int) -> _FakePage:
        return _FakePage()


class _FakeCanvas:
    def viewport_height(self) -> int:
        return 210


class _FakeDocumentActions(DocumentActionsMixin):
    def __init__(self) -> None:
        self.doc_state = DocumentState(current_file_path=Path("source.pdf"), total_pages=1)
        self.document = _FakeDocument()
        self.pdf_canvas = _FakeCanvas()
        self._fit_width_active = True
        self._fit_height_active = False
        self.keep_fit_width: bool | None = None
        self.keep_fit_height: bool | None = None

    def update_idletasks(self) -> None:
        pass

    def _set_zoom(self, zoom: float, *, keep_fit_width: bool = False, keep_fit_height: bool = False) -> None:
        self.keep_fit_width = keep_fit_width
        self.keep_fit_height = keep_fit_height
        if not keep_fit_width:
            self._fit_width_active = False
        if not keep_fit_height:
            self._fit_height_active = False
        self.doc_state.zoom_level = round(zoom, 2)


def test_main_window_starts_with_default_layout_without_reusing_old_widths() -> None:
    """A fresh app launch should not reuse previous drag-resize widths."""
    original_text = LAYOUT_SETTINGS_PATH.read_text(encoding="utf-8") if LAYOUT_SETTINGS_PATH.exists() else None
    LAYOUT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_SETTINGS_PATH.write_text(
        json.dumps(
            {
                "tool_panel_width": TOOL_PANEL_MIN_WIDTH,
                "page_panel_width": PAGE_PANEL_MIN_WIDTH,
            }
        ),
        encoding="utf-8",
    )
    app = MainWindow()
    destroyed = False

    try:
        assert app._tool_panel_width == TOOL_PANEL_DEFAULT_WIDTH
        assert app._page_panel_width == PAGE_PANEL_DEFAULT_WIDTH
        app.update()
        app.update_idletasks()
        assert app.toolbar.winfo_reqheight() <= 120
        assert app.toolbar.open_button.winfo_height() >= 60
        assert app.pdf_canvas.bottom_scrollbar_frame.winfo_height() >= 42
        assert app.pdf_canvas.bottom_scrollbar.winfo_height() >= 28
        assert app.pdf_canvas.x_scroll == app.pdf_canvas.bottom_scrollbar
        assert app.pdf_canvas.x_scroll.master == app.pdf_canvas.bottom_scrollbar_frame
        app.pdf_canvas._set_horizontal_scrollbar(0.0, 1.0)
        assert app.pdf_canvas._bottom_scrollbar_is_scrollable() is False
        assert not app.pdf_canvas.bottom_scrollbar.find_withtag("thumb")
        x0, x1 = app.pdf_canvas._horizontal_scroll_bounds(content_width=500, view_width=1000)
        assert x0 < 0
        assert x1 - x0 > 1000
        app.pdf_canvas._page_image_size = (500, 700)
        app.pdf_canvas._align_content_left_on_next_region_update = True
        app.pdf_canvas._update_scroll_region()
        assert app.pdf_canvas._bottom_scrollbar_is_scrollable() is True
        app.pdf_canvas._set_horizontal_scrollbar(0.25, 0.75)
        assert app.pdf_canvas._x_scroll_first == 0.25
        assert app.pdf_canvas._x_scroll_last == 0.75
        assert app.pdf_canvas._bottom_scrollbar_is_scrollable() is True
        assert app.pdf_canvas.bottom_scrollbar.find_withtag("thumb")
        left_info = app.page_panel.rotate_left_button.grid_info()
        right_info = app.page_panel.rotate_right_button.grid_info()

        assert int(left_info["columnspan"]) == 3
        assert int(right_info["columnspan"]) == 3
        assert int(right_info["row"]) == int(left_info["row"]) + 1
        assert "↺" in app.page_panel.rotate_left_button.cget("text")
        assert "หมุนซ้าย" in app.page_panel.rotate_left_button.cget("text")
        assert "↻" in app.page_panel.rotate_right_button.cget("text")
        assert "หมุนขวา" in app.page_panel.rotate_right_button.cget("text")
        assert "พอดีกว้าง" in app.toolbar.fit_width_button.cget("text")
        assert "พอดีบน-ล่าง" in app.toolbar.fit_height_button.cget("text")
        assert app.toolbar.fit_width_button.cget("width") > RIBBON_BUTTON_WIDTH
        assert app.toolbar.fit_height_button.cget("width") > app.toolbar.fit_width_button.cget("width")
        app.page_panel.refresh(80, 55)
        app.update_idletasks()
        assert app.page_panel.listbox.curselection() == (55,)
        assert app.page_panel.listbox.yview()[0] > 0.0
        app.page_panel.listbox.yview_moveto(0.0)
        app.update_idletasks()
        app.page_panel.refresh(80, 55)
        app.update_idletasks()
        first_visible, last_visible = app.page_panel.listbox.yview()
        assert app.page_panel.listbox.curselection() == (55,)
        assert first_visible > 0.0
        assert first_visible < last_visible
        app.destroy()
        destroyed = True
        saved = json.loads(LAYOUT_SETTINGS_PATH.read_text(encoding="utf-8"))
        assert saved["tool_panel_width"] == TOOL_PANEL_MIN_WIDTH
        assert saved["page_panel_width"] == PAGE_PANEL_MIN_WIDTH
    finally:
        if not destroyed:
            app.destroy()
        if original_text is None:
            LAYOUT_SETTINGS_PATH.unlink(missing_ok=True)
        else:
            LAYOUT_SETTINGS_PATH.write_text(original_text, encoding="utf-8")


def test_fit_height_uses_viewport_height_and_clears_width_mode() -> None:
    """The top-bottom fit button should zoom from the PDF viewport height."""
    window = _FakeDocumentActions()

    window.fit_height()

    assert window.keep_fit_width is False
    assert window.keep_fit_height is True
    assert window._fit_height_active is True
    assert window._fit_width_active is False
    assert window.doc_state.zoom_level == 0.5
