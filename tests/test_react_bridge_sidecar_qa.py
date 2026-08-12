# -*- coding: utf-8 -*-
"""Unit checks for the frozen React bridge QA probe."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import react_bridge_sidecar_qa


def test_verify_sidecar_print_worker_rejects_missing_sidecar(tmp_path: Path) -> None:
    """QA must fail clearly when packaging did not create the sidecar."""
    with pytest.raises(FileNotFoundError, match="ไม่พบไฟล์ sidecar"):
        react_bridge_sidecar_qa.verify_sidecar_print_worker(tmp_path / "missing.exe")
