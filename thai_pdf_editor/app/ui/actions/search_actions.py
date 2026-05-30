# -*- coding: utf-8 -*-
"""Search-related window actions."""

from __future__ import annotations

from thai_pdf_editor.app.core.pdf_search import PdfSearchResult, next_search_index, previous_search_index, search_pdf_text
from thai_pdf_editor.app.ui.search_dialog import show_text_search_dialog


class SearchActionsMixin:
    """Actions for text-layer search and temporary preview highlighting."""

    def open_text_search(self) -> None:
        """Open a text-layer search dialog."""
        if not self.doc_state.has_document:
            self.status_bar.set_status("ยังไม่ได้เปิดไฟล์ PDF")
            return
        show_text_search_dialog(
            self,
            initial_query=self.search_query,
            on_search=self._search_text_layer,
            on_select=self._select_search_result,
            on_previous=self._previous_search_result,
            on_next=self._next_search_result,
            on_close=self.clear_search_highlight,
        )

    def _search_text_layer(self, query: str) -> list[PdfSearchResult]:
        self.search_query = query.strip()
        self.search_results = search_pdf_text(self.document.raw, self.search_query)
        self.search_current_index = 0
        self._go_to_search_result(0)
        return self.search_results

    def _select_search_result(self, result_index: int) -> None:
        self._go_to_search_result(result_index)

    def _previous_search_result(self) -> int:
        self.search_current_index = previous_search_index(self.search_current_index, len(self.search_results))
        self._go_to_search_result(self.search_current_index)
        return self.search_current_index

    def _next_search_result(self) -> int:
        self.search_current_index = next_search_index(self.search_current_index, len(self.search_results))
        self._go_to_search_result(self.search_current_index)
        return self.search_current_index

    def _go_to_search_result(self, result_index: int) -> None:
        if not 0 <= result_index < len(self.search_results):
            return
        self.search_current_index = result_index
        result = self.search_results[result_index]
        self.go_to_page(result.page_index)
        self.pdf_canvas.show_search_highlight(result.rect)
        self.status_bar.set_status(f"ผลค้นหา {result_index + 1}/{len(self.search_results)}: หน้า {result.page_index + 1}")

    def clear_search_highlight(self) -> None:
        """Clear temporary search highlighting."""
        self.pdf_canvas.clear_search_highlight()
