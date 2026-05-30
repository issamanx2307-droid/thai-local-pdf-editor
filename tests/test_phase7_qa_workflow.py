# -*- coding: utf-8 -*-
"""Tests for the repeatable Phase 7 QA workflow."""

from scripts.phase7_qa import run_phase7_qa


def test_phase7_qa_workflow_covers_real_pdf_flows(tmp_path) -> None:
    """Phase 7 QA covers Thai paths, edits, forms, JPG export, extract, and merge."""
    report = run_phase7_qa(tmp_path, include_gui=False)

    assert report["source_unchanged"] is True
    assert report["form_source_unchanged"] is True
    assert report["saved_page_count"] == 3
    assert report["thai_text_found"] is True
    assert report["secret_removed"] is True
    assert report["image_found"] is True
    assert report["jpg_export_count"] == 3
    assert report["jpg_images_valid"] is True
    assert report["output_unchanged_after_jpg_export"] is True
    assert report["form_dirty_after_update"] is True
    assert report["form_field_count"] == 2
    assert report["form_text_value_saved"] is True
    assert report["form_checkbox_value_saved"] is True
    assert report["extract_page_count"] == 1
    assert report["merge_page_count"] == 4
