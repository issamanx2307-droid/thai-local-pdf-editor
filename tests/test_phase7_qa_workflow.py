# -*- coding: utf-8 -*-
"""Tests for the repeatable Phase 7 QA workflow."""

from scripts.phase7_qa import run_phase7_qa


def test_phase7_qa_workflow_covers_real_pdf_flows(tmp_path) -> None:
    """Phase 7 QA covers Thai paths, edits, forms, JPG export, extract, merge, and bad inputs."""
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
    assert report["image_heavy_page_count"] == 2
    assert report["image_heavy_image_count"] == 4
    assert report["image_heavy_rendered"] is True
    assert report["large_pdf_page_count"] == 12
    assert report["large_pdf_last_page_rendered"] is True
    assert report["corrupt_pdf_rejected"] is True
    assert report["batch_jpg_total_sources"] == 4
    assert report["batch_jpg_succeeded"] == 3
    assert report["batch_jpg_failed"] == 1
    assert report["batch_jpg_output_count"] == 18
    assert report["batch_jpg_report_exists"] is True
    assert report["form_dirty_after_update"] is True
    assert report["form_field_count"] == 2
    assert report["form_text_value_saved"] is True
    assert report["form_checkbox_value_saved"] is True
    assert report["extract_page_count"] == 1
    assert report["merge_page_count"] == 4
