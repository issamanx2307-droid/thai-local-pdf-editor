# -*- coding: utf-8 -*-
"""Tests for page action button coordination."""

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.ui.actions.page_overlay_actions import PageOverlayActionsMixin


class _FakePagePanel:
    def __init__(self, selected_index: int | None) -> None:
        self._selected_index = selected_index

    def selected_page_index(self) -> int | None:
        return self._selected_index


class _FakePageOperations:
    def __init__(self, state: DocumentState) -> None:
        self.state = state
        self.moved_from: int | None = None

    def move_current_page(self, delta: int) -> None:
        self.moved_from = self.state.current_page_index
        self.state.set_current_page(self.state.current_page_index + delta)


class _FakeRenderer:
    def __init__(self) -> None:
        self.clear_count = 0

    def clear_cache(self) -> None:
        self.clear_count += 1


class _FakeStatusBar:
    def __init__(self) -> None:
        self.message = ""

    def set_status(self, message: str) -> None:
        self.message = message


class _FakeWindow(PageOverlayActionsMixin):
    def __init__(self) -> None:
        self.doc_state = DocumentState(total_pages=10, current_page_index=8)
        self.doc_state.selected_page_indices = [8]
        self.page_panel = _FakePagePanel(selected_index=6)
        self.page_operations = _FakePageOperations(self.doc_state)
        self.renderer = _FakeRenderer()
        self.status_bar = _FakeStatusBar()
        self.render_count = 0

    def render_current_page(self) -> None:
        self.render_count += 1

    def _run_user_action(self, action: object) -> None:
        action()


def test_move_up_uses_highlighted_page_list_row_when_state_lagged() -> None:
    """Page action buttons should target the highlighted row if UI state lagged."""
    window = _FakeWindow()

    window.move_page_up()

    assert window.page_operations.moved_from == 6
    assert window.doc_state.current_page_index == 5
    assert window.doc_state.selected_page_indices == [5]
    assert window.renderer.clear_count == 1
    assert window.render_count == 1
    assert window.status_bar.message == "ย้ายหน้าขึ้นแล้ว"
