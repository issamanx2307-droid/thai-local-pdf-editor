# -*- coding: utf-8 -*-
"""Tests for the pending overlay edit QA workflow."""

from pathlib import Path

from scripts.overlay_edit_qa import run_overlay_edit_qa


def test_overlay_edit_qa_workflow_passes(tmp_path: Path) -> None:
    """Overlay QA should prove delete, move, resize, and safe Save As."""
    report = run_overlay_edit_qa(tmp_path / "overlay_edit_qa")

    assert report["passed"] is True
    assert report["source_unchanged"] is True
    assert report["pending_before"] == 5
    assert report["pending_after_edit"] == 4
    assert report["thai_text_found"] is True
    assert report["deleted_text_absent"] is True
    assert report["image_found"] is True
