# -*- coding: utf-8 -*-
"""Regression checks for desktop packaging configuration."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_installer_build_does_not_require_an_unavailable_updater_signing_key() -> None:
    """Release installers stay buildable until updater artifact signing is configured."""
    config_path = PROJECT_ROOT / "react_shell" / "src-tauri" / "tauri.conf.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["bundle"]["createUpdaterArtifacts"] is False
