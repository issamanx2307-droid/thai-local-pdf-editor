# -*- coding: utf-8 -*-
"""Tests for the React-ready local worker contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fitz

from thai_pdf_editor.app import worker as worker_module
from thai_pdf_editor.app.worker import PdfWorkerSession
from thai_pdf_editor.app.worker_contract import (
    COMMAND_ADD_HIGHLIGHT_OVERLAY,
    COMMAND_ADD_IMAGE_OVERLAY,
    COMMAND_ADD_TEXT_OVERLAY,
    COMMAND_BATCH,
    COMMAND_CLOSE_DOCUMENT,
    COMMAND_CROP_PAGE,
    COMMAND_CREATE_VISUAL_SIGNATURE,
    COMMAND_DELETE_PAGE,
    COMMAND_DRAW_RECTANGLE_OVERLAY,
    COMMAND_DUPLICATE_PAGE,
    COMMAND_GO_TO_PAGE,
    COMMAND_LIST_PRINTERS,
    COMMAND_MERGE_PDFS,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_PRINT_PDF,
    COMMAND_RENDER_PAGE,
    COMMAND_SAVE_COPY,
    COMMAND_SEARCH_TEXT,
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


def test_worker_close_document_clears_state_and_working_copy(tmp_path) -> None:
    """Worker close should reset document state and remove the local working copy."""
    source_path = create_sample_pdf(tmp_path / "close-source.pdf", pages=2)
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        opened = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        working_copy_path = Path(opened["state"]["working_copy_path"])
        assert opened["ok"] is True
        assert working_copy_path.exists()

        closed = session.handle({"command": COMMAND_CLOSE_DOCUMENT})

        assert closed["ok"] is True
        assert closed["state"]["has_document"] is False
        assert closed["state"]["current_file_path"] is None
        assert closed["state"]["working_copy_path"] is None
        assert closed["state"]["total_pages"] == 0
        assert closed["state"]["display_page_number"] == 0
        assert closed["state"]["dirty"] is False
        assert not working_copy_path.exists()
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


def test_worker_duplicate_and_delete_page_commands_keep_state_and_source_safe(tmp_path) -> None:
    """Worker should expose duplicate/delete page operations for the React shell."""
    source_path = create_sample_pdf(tmp_path / "page-action-source.pdf", pages=3)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True

        duplicated = session.handle(
            {
                "command": COMMAND_DUPLICATE_PAGE,
                "payload": {"selected_page_index": 1},
            }
        )

        assert duplicated["ok"] is True
        assert duplicated["payload"]["source_page_index"] == 1
        assert duplicated["payload"]["duplicated_page_index"] == 2
        assert duplicated["state"]["total_pages"] == 4
        assert duplicated["state"]["current_page_index"] == 2
        assert duplicated["state"]["selected_page_indices"] == [2]
        assert duplicated["state"]["dirty"] is True

        deleted = session.handle(
            {
                "command": COMMAND_DELETE_PAGE,
                "payload": {"selected_page_index": 2},
            }
        )

        assert deleted["ok"] is True
        assert deleted["payload"]["deleted_page_index"] == 2
        assert deleted["state"]["total_pages"] == 3
        assert deleted["state"]["current_page_index"] == 2
        assert deleted["state"]["selected_page_indices"] == [2]
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    finally:
        session.close()


def test_worker_crop_page_previews_and_saves_copy_without_changing_source(tmp_path) -> None:
    """Worker crop should mutate only the working copy and persist through save-copy."""
    source_path = create_sample_pdf(tmp_path / "crop-source.pdf", pages=1)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "crop-output.pdf"
    with fitz.open(str(source_path)) as source_pdf:
        original_cropbox = tuple(source_pdf[0].cropbox)
        original_width = source_pdf[0].cropbox.width
        original_height = source_pdf[0].cropbox.height

    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        cropped = session.handle(
            {
                "command": COMMAND_CROP_PAGE,
                "payload": {"selected_page_index": 0, "margin_percent": 10},
            }
        )

        assert cropped["ok"] is True
        assert cropped["payload"]["before_cropbox"] == list(original_cropbox)
        assert cropped["state"]["dirty"] is True
        assert cropped["state"]["current_page_index"] == 0
        assert cropped["payload"]["after_cropbox"][2] - cropped["payload"]["after_cropbox"][0] < original_width
        assert cropped["payload"]["after_cropbox"][3] - cropped["payload"]["after_cropbox"][1] < original_height

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()

        saved = session.handle(
            {
                "command": COMMAND_SAVE_COPY,
                "payload": {"destination_path": str(output_path)},
            }
        )
        assert saved["ok"] is True
        assert saved["state"]["dirty"] is False
        assert output_path.exists()
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

        with fitz.open(str(output_path)) as saved_pdf:
            assert saved_pdf[0].cropbox.width < original_width
            assert saved_pdf[0].cropbox.height < original_height
        with fitz.open(str(source_path)) as source_pdf:
            assert tuple(source_pdf[0].cropbox) == original_cropbox
    finally:
        session.close()


def test_worker_search_text_returns_results_and_selects_first_match(tmp_path) -> None:
    """Worker search should expose text-layer matches for the React shell."""
    source_path = create_sample_pdf(tmp_path / "search-source.pdf", pages=3, text_prefix="SearchTarget")
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        searched = session.handle({"command": COMMAND_SEARCH_TEXT, "payload": {"query": "SearchTarget"}})

        assert searched["ok"] is True
        assert searched["payload"]["query"] == "SearchTarget"
        assert searched["payload"]["count"] == 3
        assert searched["payload"]["results"][0]["page_index"] == 0
        assert searched["payload"]["results"][0]["match_index"] == 1
        assert searched["payload"]["results"][0]["rect"]
        assert searched["state"]["current_page_index"] == 0
        assert searched["state"]["dirty"] is False
    finally:
        session.close()


def test_worker_save_copy_writes_new_file_and_clears_dirty(tmp_path) -> None:
    """Worker save should persist a local copy without modifying the source PDF."""
    source_path = create_sample_pdf(tmp_path / "save-source.pdf", pages=3)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "save-copy.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        assert session.handle({"command": COMMAND_DUPLICATE_PAGE, "payload": {"selected_page_index": 1}})["ok"] is True
        saved = session.handle(
            {
                "command": COMMAND_SAVE_COPY,
                "payload": {"destination_path": str(output_path)},
            }
        )

        assert saved["ok"] is True
        assert saved["payload"]["destination_path"] == str(output_path)
        assert output_path.exists()
        assert saved["state"]["total_pages"] == 4
        assert saved["state"]["dirty"] is False
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    finally:
        session.close()


def test_worker_merge_pdfs_opens_merged_output_without_changing_sources(tmp_path) -> None:
    """Worker merge should create a local output and load it for preview."""
    first = create_sample_pdf(tmp_path / "merge-first.pdf", pages=2)
    second = create_sample_pdf(tmp_path / "merge-second.pdf", pages=3)
    first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
    second_hash = hashlib.sha256(second.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "merged.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        merged = session.handle(
            {
                "command": COMMAND_MERGE_PDFS,
                "payload": {
                    "source_paths": [str(first), str(second)],
                    "destination_path": str(output_path),
                },
            }
        )

        assert merged["ok"] is True
        assert merged["payload"]["source_count"] == 2
        assert merged["payload"]["destination_path"] == str(output_path)
        assert merged["state"]["total_pages"] == 5
        assert merged["state"]["current_page_index"] == 0
        assert output_path.exists()
        assert hashlib.sha256(first.read_bytes()).hexdigest() == first_hash
        assert hashlib.sha256(second.read_bytes()).hexdigest() == second_hash

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 4, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()
    finally:
        session.close()


def test_worker_lists_printers_for_react_dialog(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Worker printer discovery should be JSON-safe for the React print dialog."""
    monkeypatch.setattr(worker_module, "list_printers", lambda: ["Printer A", "Printer B"])
    monkeypatch.setattr(worker_module, "get_default_printer", lambda: "Printer B")
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        response = session.handle({"command": COMMAND_LIST_PRINTERS})

        assert response["ok"] is True
        assert response["payload"]["printers"] == ["Printer A", "Printer B"]
        assert response["payload"]["default_printer"] == "Printer B"
    finally:
        session.close()


def test_worker_print_pdf_dispatches_working_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Worker print should require an open document and dispatch the local working copy."""
    source_path = create_sample_pdf(tmp_path / "print-source.pdf", pages=1)
    calls: list[tuple[Path, str, int]] = []
    monkeypatch.setattr(
        worker_module,
        "print_pdf",
        lambda pdf_path, printer_name, *, copies: calls.append((Path(pdf_path), printer_name, copies)),
    )
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        opened = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        working_copy = Path(opened["state"]["working_copy_path"])
        printed = session.handle(
            {
                "command": COMMAND_PRINT_PDF,
                "payload": {"printer_name": "Printer A", "copies": 2},
            }
        )

        assert printed["ok"] is True
        assert printed["payload"]["printer_name"] == "Printer A"
        assert printed["payload"]["copies"] == 2
        assert calls == [(working_copy, "Printer A", 2)]
    finally:
        session.close()


def test_worker_add_text_overlay_previews_and_saves_copy(tmp_path) -> None:
    """Worker text overlay should preview as pending work and persist on save-copy."""
    source_path = create_sample_pdf(tmp_path / "text-overlay-source.pdf", pages=1)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "text-overlay-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        added = session.handle(
            {
                "command": COMMAND_ADD_TEXT_OVERLAY,
                "payload": {
                    "selected_page_index": 0,
                    "text": "React worker text",
                    "font_size": 18,
                    "color": "#111111",
                },
            }
        )

        assert added["ok"] is True
        assert added["payload"]["page_index"] == 0
        assert added["state"]["dirty"] is True
        assert len(session.state.pending_operations) == 1

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()

        saved = session.handle(
            {
                "command": COMMAND_SAVE_COPY,
                "payload": {"destination_path": str(output_path)},
            }
        )
        assert saved["ok"] is True
        assert saved["state"]["dirty"] is False
        assert output_path.exists()
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

        with fitz.open(str(output_path)) as saved_pdf:
            assert "React worker text" in saved_pdf[0].get_text()
    finally:
        session.close()


def test_worker_shape_overlays_preview_and_save_copy(tmp_path) -> None:
    """Worker shape overlays should preview as pending work and persist on save-copy."""
    source_path = create_sample_pdf(tmp_path / "shape-overlay-source.pdf", pages=1)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "shape-overlay-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        rectangle = session.handle(
            {
                "command": COMMAND_DRAW_RECTANGLE_OVERLAY,
                "payload": {
                    "selected_page_index": 0,
                    "x": 72,
                    "y": 144,
                    "width": 180,
                    "height": 72,
                    "color": "#d32f2f",
                    "line_width": 2,
                },
            }
        )
        highlight = session.handle(
            {
                "command": COMMAND_ADD_HIGHLIGHT_OVERLAY,
                "payload": {
                    "selected_page_index": 0,
                    "x": 80,
                    "y": 240,
                    "width": 190,
                    "height": 44,
                    "color": "#fff176",
                },
            }
        )

        assert rectangle["ok"] is True
        assert rectangle["payload"]["rect"] == [72.0, 144.0, 252.0, 216.0]
        assert highlight["ok"] is True
        assert highlight["state"]["dirty"] is True
        assert len(session.state.pending_operations) == 2

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()

        saved = session.handle(
            {
                "command": COMMAND_SAVE_COPY,
                "payload": {"destination_path": str(output_path)},
            }
        )
        assert saved["ok"] is True
        assert saved["state"]["dirty"] is False
        assert output_path.exists()
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

        with fitz.open(str(output_path)) as saved_pdf:
            assert saved_pdf.page_count == 1
            assert len(saved_pdf[0].get_drawings()) >= 2
    finally:
        session.close()


def test_worker_image_overlay_from_visual_signature_previews_and_save_copy(tmp_path) -> None:
    """Worker image overlay should accept a local visual signature image and persist it."""
    source_path = create_sample_pdf(tmp_path / "image-overlay-source.pdf", pages=1)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "image-overlay-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        signature = session.handle(
            {
                "command": COMMAND_CREATE_VISUAL_SIGNATURE,
                "payload": {"text": "React Signature", "width_px": 420, "color": "#1565c0"},
            }
        )

        assert signature["ok"] is True
        image_path = Path(signature["payload"]["image_path"])
        assert image_path.exists()
        assert image_path.suffix.lower() == ".png"

        added = session.handle(
            {
                "command": COMMAND_ADD_IMAGE_OVERLAY,
                "payload": {
                    "selected_page_index": 0,
                    "image_path": str(image_path),
                    "x": 72,
                    "y": 180,
                    "width": 120,
                },
            }
        )

        assert added["ok"] is True
        assert added["payload"]["page_index"] == 0
        assert added["payload"]["width"] == 120.0
        assert added["state"]["dirty"] is True
        assert len(session.state.pending_operations) == 1

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()

        saved = session.handle(
            {
                "command": COMMAND_SAVE_COPY,
                "payload": {"destination_path": str(output_path)},
            }
        )
        assert saved["ok"] is True
        assert saved["state"]["dirty"] is False
        assert output_path.exists()
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

        with fitz.open(str(output_path)) as saved_pdf:
            assert saved_pdf.page_count == 1
            assert saved_pdf[0].get_images(full=True)
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
