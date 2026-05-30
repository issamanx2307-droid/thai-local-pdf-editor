# -*- coding: utf-8 -*-
"""Tests for the release QA checklist script."""

from pathlib import Path

from scripts.release_qa import build_static_report, release_commands


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REQUIREMENTS = {"customtkinter", "pymupdf", "pillow", "tkinterdnd2"}


def test_release_qa_static_report_is_clean() -> None:
    """Release QA static checks must pass before runtime gates run."""
    report = build_static_report(PROJECT_ROOT)

    assert report["source_files_over_line_limit"] == []
    assert report["mojibake_files"] == []
    assert report["missing_required_paths"] == []
    assert report["checked_source_files"] > 0


def test_release_qa_command_plan_includes_required_gates() -> None:
    """The release QA command plan mirrors the project acceptance gate."""
    names = [command.name for command in release_commands(include_build=True)]

    assert names == [
        "stop_existing_app",
        "compileall",
        "pytest",
        "phase7_qa",
        "font_import_qa",
        "overlay_edit_qa",
        "phase43_ui_qa",
        "run_app_smoke",
        "start_bat_smoke",
        "stop_bat",
        "final_acceptance",
        "build_exe",
        "exe_smoke",
    ]


def test_runtime_requirements_are_kept_minimal() -> None:
    """Runtime install should not include test/build or removed PDF stacks."""
    requirement_lines = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    requirement_names = {
        line.split(">", maxsplit=1)[0].split("=", maxsplit=1)[0].strip().lower()
        for line in requirement_lines
        if line.strip() and not line.startswith("#")
    }

    assert requirement_names == RUNTIME_REQUIREMENTS
