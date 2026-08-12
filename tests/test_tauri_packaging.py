# -*- coding: utf-8 -*-
"""Regression checks for desktop packaging configuration."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_installer_build_creates_signed_updater_artifacts() -> None:
    """Release installers must produce signed updater artifacts.

    Updater signing keys are available locally at
    C:\\Users\\WINDOWS\\.thai-pdf-editor-keys\\ and are injected by
    scripts\\release.ps1 via TAURI_SIGNING_PRIVATE_KEY(_PASSWORD) before
    building, so createUpdaterArtifacts must stay enabled for the
    auto-updater (latest.json + .sig) to keep working.
    """
    config_path = PROJECT_ROOT / "react_shell" / "src-tauri" / "tauri.conf.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["bundle"]["createUpdaterArtifacts"] is True
