# -*- coding: utf-8 -*-
"""Tests for the React-ready local worker contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image

from thai_pdf_editor.app.core.form_operations import editable_form_fields
from thai_pdf_editor.app import worker as worker_module
from thai_pdf_editor.app.worker import PdfWorkerSession
from thai_pdf_editor.app.worker_contract import (
    COMMAND_ADD_HIGHLIGHT_OVERLAY,
    COMMAND_ADD_IMAGE_OVERLAY,
    COMMAND_ADD_REDACTION_OVERLAY,
    COMMAND_ADD_TEXT_OVERLAY,
    COMMAND_BATCH,
    COMMAND_BATCH_EXPORT_JPG,
    COMMAND_CLOSE_DOCUMENT,
    COMMAND_CROP_PAGE,
    COMMAND_CREATE_VISUAL_SIGNATURE,
    COMMAND_DELETE_PAGE,
    COMMAND_DRAW_RECTANGLE_OVERLAY,
    COMMAND_DUPLICATE_PAGE,
    COMMAND_EXPORT_JPG,
    COMMAND_EXTRACT_PAGE,
    COMMAND_GO_TO_PAGE,
    COMMAND_LIST_FORM_FIELDS,
    COMMAND_LIST_METADATA,
    COMMAND_LIST_PRINTERS,
    COMMAND_MERGE_PDFS,
    COMMAND_MOVE_PAGE,
    COMMAND_OPEN_PDF,
    COMMAND_PRINT_PDF,
    COMMAND_RENDER_PAGE,
    COMMAND_REDO_PENDING,
    COMMAND_REPLACE_TEXT,
    COMMAND_ROTATE_PAGE,
    COMMAND_SAVE_COPY,
    COMMAND_SEARCH_TEXT,
    COMMAND_UNDO_PENDING,
    COMMAND_UPDATE_FORM_FIELDS,
    COMMAND_UPDATE_METADATA,
)

from tests.fixtures.create_sample_pdfs import create_sample_pdf
from tests.test_form_operations import _create_form_pdf


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


def test_worker_rotate_page_updates_working_copy_and_keeps_source_safe(tmp_path) -> None:
    """Worker rotate should target the selected page and persist through save-copy."""
    source_path = create_sample_pdf(tmp_path / "rotate-source.pdf", pages=2)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "rotated.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        rotated = session.handle(
            {
                "command": COMMAND_ROTATE_PAGE,
                "payload": {"selected_page_index": 1, "degrees": 90},
            }
        )

        assert rotated["ok"] is True
        assert rotated["payload"]["page_index"] == 1
        assert rotated["payload"]["before_rotation"] == 0
        assert rotated["payload"]["after_rotation"] == 90
        assert rotated["state"]["current_page_index"] == 1
        assert rotated["state"]["selected_page_indices"] == [1]
        assert rotated["state"]["dirty"] is True

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 1, "zoom": 1.0}})
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

        with fitz.open(str(source_path)) as source_pdf:
            assert source_pdf[1].rotation == 0
        with fitz.open(str(output_path)) as saved_pdf:
            assert saved_pdf[1].rotation == 90
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


def test_worker_extract_page_creates_one_page_output_without_dirtying_source(tmp_path) -> None:
    """Worker extract should save one selected page without mutating the open document."""
    source_path = create_sample_pdf(tmp_path / "extract-source.pdf", pages=3)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "extracted.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        extracted = session.handle(
            {
                "command": COMMAND_EXTRACT_PAGE,
                "payload": {"selected_page_index": 1, "destination_path": str(output_path)},
            }
        )

        assert extracted["ok"] is True
        assert extracted["payload"]["page_index"] == 1
        assert extracted["payload"]["destination_path"] == str(output_path)
        assert extracted["state"]["dirty"] is False
        assert extracted["state"]["current_page_index"] == 1
        assert output_path.exists()
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash

        with fitz.open(str(output_path)) as pdf:
            assert pdf.page_count == 1
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


def test_worker_metadata_commands_update_and_save_copy(tmp_path) -> None:
    """Worker should expose metadata read/update for the React shell."""
    source_path = create_sample_pdf(tmp_path / "metadata-source.pdf", pages=1)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    output_path = tmp_path / "outputs" / "metadata-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        listed = session.handle({"command": COMMAND_LIST_METADATA})
        assert listed["ok"] is True
        assert set(listed["payload"]["metadata"]) == {"title", "author", "subject", "keywords"}

        updated = session.handle(
            {
                "command": COMMAND_UPDATE_METADATA,
                "payload": {
                    "updates": {
                        "title": "React metadata",
                        "author": "Local worker",
                    }
                },
            }
        )
        assert updated["ok"] is True
        assert updated["state"]["dirty"] is True
        assert updated["payload"]["metadata"]["title"] == "React metadata"

        saved = session.handle({"command": COMMAND_SAVE_COPY, "payload": {"destination_path": str(output_path)}})
        assert saved["ok"] is True
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
        with fitz.open(str(output_path)) as saved_pdf:
            assert saved_pdf.metadata["title"] == "React metadata"
            assert saved_pdf.metadata["author"] == "Local worker"
    finally:
        session.close()


def test_worker_form_commands_update_and_save_copy(tmp_path) -> None:
    """Worker should expose existing form fields for React editing."""
    source_path = _create_form_pdf(tmp_path / "form-source.pdf")
    output_path = tmp_path / "outputs" / "form-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        listed = session.handle({"command": COMMAND_LIST_FORM_FIELDS})
        assert listed["ok"] is True
        fields = listed["payload"]["fields"]
        assert [(field["name"], field["value"]) for field in fields] == [("customer_name", ""), ("accepted", False)]

        updated = session.handle(
            {
                "command": COMMAND_UPDATE_FORM_FIELDS,
                "payload": {
                    "updates": {
                        str(fields[0]["xref"]): "Somchai",
                        str(fields[1]["xref"]): True,
                    }
                },
            }
        )
        assert updated["ok"] is True
        assert updated["state"]["dirty"] is True
        assert [(field["name"], field["value"]) for field in updated["payload"]["fields"]] == [
            ("customer_name", "Somchai"),
            ("accepted", True),
        ]

        saved = session.handle({"command": COMMAND_SAVE_COPY, "payload": {"destination_path": str(output_path)}})
        assert saved["ok"] is True
        with fitz.open(str(output_path)) as saved_pdf:
            saved_fields = editable_form_fields(saved_pdf)
        assert [(field.name, field.value) for field in saved_fields] == [("customer_name", "Somchai"), ("accepted", True)]
    finally:
        session.close()


def test_worker_replace_text_command_previews_and_save_copy(tmp_path) -> None:
    """Worker replace-text command should create pending redaction operations."""
    source_path = create_sample_pdf(tmp_path / "replace-source.pdf", pages=1, text_prefix="OLD TEXT")
    output_path = tmp_path / "outputs" / "replace-output.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        replaced = session.handle(
            {
                "command": COMMAND_REPLACE_TEXT,
                "payload": {
                    "selected_page_index": 0,
                    "search_text": "OLD TEXT",
                    "replacement_text": "NEW TEXT",
                    "font_size": 14,
                    "color": "#111111",
                },
            }
        )
        assert replaced["ok"] is True
        assert replaced["payload"]["operation_count"] >= 1
        assert replaced["state"]["dirty"] is True

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()

        saved = session.handle({"command": COMMAND_SAVE_COPY, "payload": {"destination_path": str(output_path)}})
        assert saved["ok"] is True
        with fitz.open(str(output_path)) as saved_pdf:
            text = saved_pdf[0].get_text()
        assert "OLD TEXT" not in text
        assert "NEW TEXT" in text
    finally:
        session.close()


def test_worker_redaction_command_removes_text_on_save_copy(tmp_path) -> None:
    """Worker redaction command should persist as real PDF redaction on save."""
    source_path = tmp_path / "secret.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((50, 100), "SECRET DATA", fontsize=18)
    document.save(str(source_path))
    document.close()
    output_path = tmp_path / "outputs" / "redacted.pdf"
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        redacted = session.handle(
            {
                "command": COMMAND_ADD_REDACTION_OVERLAY,
                "payload": {
                    "selected_page_index": 0,
                    "x": 45,
                    "y": 82,
                    "width": 140,
                    "height": 36,
                },
            }
        )
        assert redacted["ok"] is True
        assert redacted["state"]["dirty"] is True

        saved = session.handle({"command": COMMAND_SAVE_COPY, "payload": {"destination_path": str(output_path)}})
        assert saved["ok"] is True
        with fitz.open(str(output_path)) as saved_pdf:
            assert "SECRET DATA" not in saved_pdf[0].get_text()
    finally:
        session.close()


def test_worker_export_jpg_command_exports_current_page(tmp_path) -> None:
    """Worker should export the current open document to JPG without batch automation."""
    source_path = create_sample_pdf(tmp_path / "jpg-source.pdf", pages=3)
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        assert session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})["ok"] is True
        assert session.handle({"command": COMMAND_GO_TO_PAGE, "payload": {"page_index": 1}})["ok"] is True
        exported = session.handle(
            {
                "command": COMMAND_EXPORT_JPG,
                "payload": {
                    "destination_dir": str(tmp_path / "jpg-output"),
                    "page_scope": "current",
                    "dpi": 72,
                    "quality": 80,
                },
            }
        )
        assert exported["ok"] is True
        assert exported["state"]["dirty"] is False
        assert exported["payload"]["count"] == 1
        output_path = Path(exported["payload"]["output_paths"][0])
        assert output_path.name == "jpg-source_page_0002.jpg"
        with Image.open(output_path) as image:
            assert image.format == "JPEG"
            assert image.width > 0
            assert image.height > 0
    finally:
        session.close()


def test_worker_batch_export_jpg_command_exports_multiple_pdfs(tmp_path) -> None:
    """Worker should expose approved local batch JPG export for multiple PDFs."""
    first_path = create_sample_pdf(tmp_path / "batch-first.pdf", pages=2)
    second_path = create_sample_pdf(tmp_path / "batch-second.pdf", pages=1)
    broken_path = tmp_path / "broken.pdf"
    broken_path.write_text("not a pdf", encoding="utf-8")
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        exported = session.handle(
            {
                "command": COMMAND_BATCH_EXPORT_JPG,
                "payload": {
                    "source_paths": [str(first_path), str(second_path), str(broken_path)],
                    "destination_dir": str(tmp_path / "batch-jpg-output"),
                    "dpi": 72,
                    "quality": 80,
                },
            }
        )

        assert exported["ok"] is True
        assert exported["state"]["has_document"] is False
        assert exported["payload"]["source_count"] == 3
        assert exported["payload"]["total_sources"] == 3
        assert exported["payload"]["succeeded"] == 2
        assert exported["payload"]["failed"] == 1
        assert exported["payload"]["count"] == 3
        assert Path(exported["payload"]["report_path"]).exists()
        output_paths = [Path(path) for path in exported["payload"]["output_paths"]]
        assert [path.name for path in output_paths] == [
            "batch-first_page_0001.jpg",
            "batch-first_page_0002.jpg",
            "batch-second_page_0001.jpg",
        ]
        with Image.open(output_paths[0]) as image:
            assert image.format == "JPEG"
            assert image.width > 0
            assert image.height > 0
        report = json.loads(Path(exported["payload"]["report_path"]).read_text(encoding="utf-8"))
        assert report["failed"] == 1
        assert report["items"][2]["status"] == "failed"
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


def test_worker_opens_selected_printer_queue(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The React worker exposes the Windows queue shortcut without a document."""
    calls: list[str] = []
    monkeypatch.setattr(worker_module, "open_printer_queue", lambda printer: calls.append(printer))
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        response = session.handle(
            {"command": "open_printer_queue", "payload": {"printer_name": "Printer A"}}
        )
        assert response["ok"] is True
        assert response["payload"]["printer_name"] == "Printer A"
        assert calls == ["Printer A"]
    finally:
        session.close()


def test_worker_print_pdf_dispatches_working_copy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Worker print should require an open document and dispatch the local working copy."""
    source_path = create_sample_pdf(tmp_path / "print-source.pdf", pages=1)
    calls: list[tuple[Path, str, int, str | None]] = []
    monkeypatch.setattr(
        worker_module,
        "print_pdf",
        lambda pdf_path, printer_name, *, copies, pages=None: calls.append(
            (Path(pdf_path), printer_name, copies, pages)
        ),
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
        assert calls == [(working_copy, "Printer A", 2, None)]
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


def test_worker_undo_and_redo_pending_overlay_refreshes_state(tmp_path) -> None:
    """Worker undo/redo commands should expose React-ready toolbar state."""
    source_path = create_sample_pdf(tmp_path / "undo-source.pdf", pages=1)
    session = PdfWorkerSession(preview_dir=tmp_path / "previews")

    try:
        opened = session.handle({"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}})
        assert opened["ok"] is True
        assert opened["state"]["can_undo"] is False
        assert opened["state"]["can_redo"] is False

        added = session.handle(
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
        assert added["ok"] is True
        assert added["state"]["can_undo"] is True
        assert added["state"]["can_redo"] is False
        assert len(session.state.pending_operations) == 1

        undone = session.handle({"command": COMMAND_UNDO_PENDING})
        assert undone["ok"] is True
        assert undone["payload"]["pending_count"] == 0
        assert undone["state"]["dirty"] is False
        assert undone["state"]["can_undo"] is False
        assert undone["state"]["can_redo"] is True
        assert len(session.state.pending_operations) == 0

        redone = session.handle({"command": COMMAND_REDO_PENDING})
        assert redone["ok"] is True
        assert redone["payload"]["pending_count"] == 1
        assert redone["state"]["dirty"] is True
        assert redone["state"]["can_undo"] is True
        assert redone["state"]["can_redo"] is False
        assert len(session.state.pending_operations) == 1

        rendered = session.handle({"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}})
        assert rendered["ok"] is True
        assert Path(rendered["payload"]["preview_path"]).exists()
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
