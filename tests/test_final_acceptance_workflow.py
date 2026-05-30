# -*- coding: utf-8 -*-
"""Tests for the final acceptance workflow."""

from scripts.final_acceptance import run_final_acceptance


def test_final_acceptance_report_passes() -> None:
    """Final acceptance report should cover the local PDF workflow and source hygiene."""
    report = run_final_acceptance()

    assert report["passed"] is True
    assert report["preview_rendered"] is True
    assert report["source_unchanged"] is True
