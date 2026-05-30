# -*- coding: utf-8 -*-
"""Tests for the React-ready local worker contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from thai_pdf_editor.app.worker import PdfWorkerSession
from thai_pdf_editor.app.worker_contract import (
    COMMAND_BATCH,
    COMMAND_GO_TO_PAGE,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
)

from tests.fixtures.create_sample_pdfs import create_sample_pdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_worker_opens_renders_and_navigates_pdf(tmp_path) -> None:
    """Worker should expose document state and preview output without Tk widgets."""
    source_path = create_sample_pdf(tmp_path / "เอกสาร worker.pdf", pages=3)
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        opened = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        assert opened["ok"] is True
        assert opened["state"]["total_pages"] == 3
        assert opened["state"]["current_page_index"] == 0

        rendered = session.handle(
            {"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 2, "zoom": 1.25}}
        )
        preview_path = Path(rendered["payload"]["preview_path"])
        assert rendered["ok"] is True
        assert rendered["state"]["current_page_index"] == 2
        assert rendered["state"]["zoom_level"] == 1.25
        assert rendered["payload"]["image_width"] > 0
        assert rendered["payload"]["image_height"] > 0
        assert preview_path.exists()

        navigated = session.handle({"command": COMMAND_GO_TO_PAGE, "payload": {"page_index": 1}})
        assert navigated["ok"] is True
        assert navigated["state"]["display_page_number"] == 2
    finally:
        session.close()


def test_worker_move_page_uses_selected_page_index_when_state_lagged(tmp_path) -> None:
    """Page operation commands should target the highlighted page row from React."""
    source_path = create_sample_pdf(tmp_path / "move-source.pdf", pages=4)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        assert session.handle({"command": COMMAND_GO_TO_PAGE, "payload": {"page_index": 3}})["ok"] is True

        moved = session.handle(
            {
                "command": COMMAND_MOVE_PAGE,
                "payload": {"selected_page_index": 2, "delta": -1},
            }
        )

        assert moved["ok"] is True
        assert moved["payload"]["from_page_index"] == 2
        assert moved["payload"]["to_page_index"] == 1
        assert moved["state"]["current_page_index"] == 1
        assert moved["state"]["selected_page_indices"] == [1]
        assert moved["state"]["dirty"] is True
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    finally:
        session.close()


def test_worker_cli_batch_returns_json_state_and_preview(tmp_path) -> None:
    """CLI batch mode should keep one worker session across commands."""
    source_path = create_sample_pdf(tmp_path / "cli-source.pdf", pages=2)
    request_path = tmp_path / "request.json"
    preview_dir = tmp_path / "previews"
    request_path.write_text(
        json.dumps(
            {
                "command": COMMAND_BATCH,
                "commands": [
                    {"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}},
                    {"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 1, "zoom": 1.5}},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "thai_pdf_editor.app.worker",
            "--request-file",
            str(request_path),
            "--preview-dir",
            str(preview_dir),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    response = json.loads(completed.stdout)
    assert response["ok"] is True
    assert response["state"]["current_page_index"] == 1
    render_response = response["responses"][1]
    assert render_response["payload"]["image_width"] > 0
    assert render_response["payload"]["image_height"] > 0
    assert preview_dir.exists()
    assert list(preview_dir.glob("*.png"))
