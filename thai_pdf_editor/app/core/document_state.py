# -*- coding: utf-8 -*-
"""Central document state for UI and core coordination."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thai_pdf_editor.app.constants import DEFAULT_ZOOM


@dataclass
class DocumentState:
    """Single source of truth for the currently opened PDF."""

    current_file_path: Path | None = None
    working_copy_path: Path | None = None
    total_pages: int = 0
    current_page_index: int = 0
    zoom_level: float = DEFAULT_ZOOM
    dirty: bool = False
    pending_operations: list[Any] = field(default_factory=list)
    applied_operations: list[Any] = field(default_factory=list)
    undo_stack: list[Any] = field(default_factory=list)
    redo_stack: list[Any] = field(default_factory=list)
    selected_tool: str | None = None
    selected_page_indices: list[int] = field(default_factory=list)
    page_order: list[int] = field(default_factory=list)
    deleted_pages: set[int] = field(default_factory=set)
    rotation_map: dict[int, int] = field(default_factory=dict)
    dirty_version: int = 0

    @property
    def has_document(self) -> bool:
        """Return True when a PDF is loaded."""
        return self.current_file_path is not None and self.total_pages > 0

    @property
    def display_page_number(self) -> int:
        """Return one-based current page number for the UI."""
        return self.current_page_index + 1 if self.has_document else 0

    def load_document(self, source_path: Path, working_copy_path: Path, total_pages: int) -> None:
        """Reset state for a newly opened document."""
        self.current_file_path = source_path
        self.working_copy_path = working_copy_path
        self.total_pages = total_pages
        self.current_page_index = 0
        self.zoom_level = DEFAULT_ZOOM
        self.dirty = False
        self.pending_operations.clear()
        self.applied_operations.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.selected_tool = None
        self.selected_page_indices = [0] if total_pages else []
        self.page_order = list(range(total_pages))
        self.deleted_pages.clear()
        self.rotation_map.clear()
        self.bump_version()

    def reset(self) -> None:
        """Clear all document-specific state."""
        self.current_file_path = None
        self.working_copy_path = None
        self.total_pages = 0
        self.current_page_index = 0
        self.zoom_level = DEFAULT_ZOOM
        self.dirty = False
        self.pending_operations.clear()
        self.applied_operations.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.selected_tool = None
        self.selected_page_indices.clear()
        self.page_order.clear()
        self.deleted_pages.clear()
        self.rotation_map.clear()
        self.bump_version()

    def clamp_current_page(self) -> None:
        """Keep the current page index inside the document bounds."""
        if self.total_pages <= 0:
            self.current_page_index = 0
            self.selected_page_indices.clear()
            return
        self.current_page_index = max(0, min(self.current_page_index, self.total_pages - 1))
        self.selected_page_indices = [self.current_page_index]

    def set_current_page(self, page_index: int) -> None:
        """Set the current page and validate the page index."""
        if not 0 <= page_index < self.total_pages:
            return
        self.current_page_index = page_index
        self.selected_page_indices = [page_index]

    def mark_dirty(self) -> None:
        """Mark the document as modified and invalidate dependent previews."""
        self.dirty = True
        self.bump_version()

    def mark_saved(self) -> None:
        """Mark pending changes as saved."""
        self.dirty = False
        self.pending_operations.clear()
        self.applied_operations.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.bump_version()

    def record_operation(self, operation: Any, *, pending: bool = False) -> None:
        """Track a document operation for dirty state and basic undo history."""
        if pending:
            self.pending_operations.append(operation)
        else:
            self.applied_operations.append(operation)
        self.undo_stack.append(operation)
        self.redo_stack.clear()
        self.mark_dirty()

    def bump_version(self) -> None:
        """Increment the preview invalidation version."""
        self.dirty_version += 1
