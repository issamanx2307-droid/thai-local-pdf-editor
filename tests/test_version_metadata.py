# -*- coding: utf-8 -*-
"""Tests for release version metadata."""

import tomllib
from pathlib import Path

from thai_pdf_editor import __version__
from thai_pdf_editor.app.constants import APP_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_app_version_is_local_v1_release() -> None:
    """User-facing version metadata should identify the local v1 release."""
    assert __version__ == "v1.0.0-local"
    assert APP_VERSION == __version__


def test_project_metadata_uses_valid_local_version() -> None:
    """pyproject uses PEP 440 local-version syntax for packaging tools."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "1.0.0+local"
