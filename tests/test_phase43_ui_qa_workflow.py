# -*- coding: utf-8 -*-
"""Tests for Phase 43 UI helper QA workflow."""

from scripts.phase43_ui_qa import run_phase43_ui_qa


def test_phase43_ui_qa_report_passes() -> None:
    """Phase 43 QA should cover search, recent files, preflight, and checklist helpers."""
    report = run_phase43_ui_qa()

    assert report["passed"] is True
    assert report["search_result_count"] == 1
    assert report["recent_after_clear_count"] == 0
    assert report["preflight_has_redaction_warning"] is True
