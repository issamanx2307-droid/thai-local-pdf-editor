# -*- coding: utf-8 -*-
"""Tests for the local React bridge used during migration."""

from __future__ import annotations

import base64
import http.client
import io
import json
import threading
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from react_shell.local_bridge import create_bridge_server
from thai_pdf_editor.app.worker_contract import (
    COMMAND_BATCH,
    COMMAND_BATCH_EXPORT_JPG,
    COMMAND_MERGE_PDFS,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
)
from tests.fixtures.create_sample_pdfs import create_sample_pdf


def test_react_bridge_handles_worker_batch_and_serves_preview(tmp_path) -> None:
    """Bridge should keep a session, render through worker, and expose a preview URL."""
    source_path = create_sample_pdf(tmp_path / "bridge-source.pdf", pages=2)
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        response = _json_request(
            port,
            "POST",
            "/api/worker",
            {
                "command": COMMAND_BATCH,
                "commands": [
                    {"command": COMMAND_OPEN_PDF, "payload": {"path": str(source_path)}},
                    {"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 1, "zoom": 1.1}},
                ],
            },
        )

        assert response["status"] == 200
        body = response["body"]
        assert body["ok"] is True
        assert body["state"]["total_pages"] == 2
        render_response = body["responses"][1]
        assert render_response["payload"]["image_width"] > 0
        assert render_response["payload"]["preview_url"].startswith("/api/previews/")

        preview = _raw_request(port, "GET", render_response["payload"]["preview_url"])
        assert preview["status"] == 200
        assert preview["content_type"] == "image/png"
        assert preview["body"].startswith(b"\x89PNG")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_health_reports_worker_state(tmp_path) -> None:
    """Health endpoint should be JSON and local-browser friendly."""
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        response = _json_request(port, "GET", "/api/health")

        assert response["status"] == 200
        assert response["body"]["ok"] is True
        assert response["body"]["bridge"] == "thai-pdf-react-bridge"
        assert response["body"]["state"]["has_document"] is False
        assert response["headers"]["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_upload_image_saves_valid_local_file(tmp_path) -> None:
    """Bridge should accept a local image upload and return a validated file path."""
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        png_data = _tiny_png_bytes()
        response = _json_request(
            port,
            "POST",
            "/api/upload-image",
            {
                "file_name": "signature.png",
                "data_url": f"data:image/png;base64,{base64.b64encode(png_data).decode('ascii')}",
            },
        )

        assert response["status"] == 200
        body = response["body"]
        assert body["ok"] is True
        image_path = Path(body["path"])
        assert image_path.exists()
        assert image_path.suffix.lower() == ".png"
        assert body["file_name"] == image_path.name
        assert response["headers"]["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_upload_pdf_opens_and_renders_single_document(tmp_path) -> None:
    """Bridge should support the React open-file flow for one selected local PDF."""
    source_path = create_sample_pdf(tmp_path / "single-open.pdf", pages=4)
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        upload_response = _json_request(
            port,
            "POST",
            "/api/upload-pdf",
            {
                "file_name": source_path.name,
                "data_url": f"data:application/pdf;base64,{base64.b64encode(source_path.read_bytes()).decode('ascii')}",
            },
        )
        assert upload_response["status"] == 200
        assert upload_response["body"]["ok"] is True
        uploaded_path = upload_response["body"]["path"]

        open_response = _json_request(
            port,
            "POST",
            "/api/worker",
            {
                "command": COMMAND_BATCH,
                "commands": [
                    {"command": COMMAND_OPEN_PDF, "payload": {"path": uploaded_path}},
                    {"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}},
                ],
            },
        )

        assert open_response["status"] == 200
        body = open_response["body"]
        assert body["ok"] is True
        assert body["state"]["total_pages"] == 4
        assert body["responses"][1]["payload"]["preview_url"].startswith("/api/previews/")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_upload_pdf_and_merge_through_worker(tmp_path) -> None:
    """Bridge should accept local PDF uploads and merge them through the worker session."""
    first = create_sample_pdf(tmp_path / "first.pdf", pages=2)
    second = create_sample_pdf(tmp_path / "second.pdf", pages=3)
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        uploaded_paths = []
        for source_path in (first, second):
            upload_response = _json_request(
                port,
                "POST",
                "/api/upload-pdf",
                {
                    "file_name": source_path.name,
                    "data_url": f"data:application/pdf;base64,{base64.b64encode(source_path.read_bytes()).decode('ascii')}",
                },
            )
            assert upload_response["status"] == 200
            assert upload_response["body"]["ok"] is True
            assert upload_response["body"]["page_count"] in {2, 3}
            uploaded_paths.append(upload_response["body"]["path"])

        merge_response = _json_request(
            port,
            "POST",
            "/api/worker",
            {
                "command": COMMAND_BATCH,
                "commands": [
                    {"command": COMMAND_MERGE_PDFS, "payload": {"source_paths": uploaded_paths}},
                    {"command": COMMAND_RENDER_PAGE, "payload": {"page_index": 0, "zoom": 1.0}},
                ],
            },
        )

        assert merge_response["status"] == 200
        body = merge_response["body"]
        assert body["ok"] is True
        assert body["state"]["total_pages"] == 5
        assert body["responses"][0]["payload"]["source_count"] == 2
        assert Path(body["responses"][0]["payload"]["destination_path"]).exists()
        assert body["responses"][1]["payload"]["preview_url"].startswith("/api/previews/")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_uploads_multiple_pdfs_and_batch_exports_jpg(tmp_path) -> None:
    """Bridge should support the React-approved multi-file Batch JPG flow."""
    first = create_sample_pdf(tmp_path / "batch-one.pdf", pages=2)
    second = create_sample_pdf(tmp_path / "batch-two.pdf", pages=1)
    server = create_bridge_server(port=0, preview_dir=tmp_path / "previews")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])
        uploaded_paths = []
        for source_path in (first, second):
            upload_response = _json_request(
                port,
                "POST",
                "/api/upload-pdf",
                {
                    "file_name": source_path.name,
                    "data_url": f"data:application/pdf;base64,{base64.b64encode(source_path.read_bytes()).decode('ascii')}",
                },
            )
            assert upload_response["status"] == 200
            assert upload_response["body"]["ok"] is True
            uploaded_paths.append(upload_response["body"]["path"])

        batch_response = _json_request(
            port,
            "POST",
            "/api/worker",
            {
                "command": COMMAND_BATCH_EXPORT_JPG,
                "payload": {
                    "source_paths": uploaded_paths,
                    "destination_dir": str(tmp_path / "bridge-batch-jpg"),
                    "dpi": 72,
                    "quality": 80,
                },
            },
        )

        assert batch_response["status"] == 200
        body = batch_response["body"]
        assert body["ok"] is True
        assert body["payload"]["source_count"] == 2
        assert body["payload"]["succeeded"] == 2
        assert body["payload"]["failed"] == 0
        assert body["payload"]["count"] == 3
        assert Path(body["payload"]["report_path"]).exists()
        assert all(Path(path).exists() for path in body["payload"]["output_paths"])
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_react_bridge_rejects_non_loopback_bind(tmp_path) -> None:
    """The migration bridge must never bind to all interfaces."""
    with pytest.raises(ValueError, match="127.0.0.1"):
        create_bridge_server(host="0.0.0.0", port=0, preview_dir=tmp_path / "previews")


def _tiny_png_bytes() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGBA", (16, 8), (21, 101, 192, 210))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _json_request(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = _raw_request(port, method, path, payload)
    return {
        **raw,
        "body": json.loads(raw["body"].decode("utf-8")),
    }


def _raw_request(port: int, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        return {
            "status": response.status,
            "headers": dict(response.getheaders()),
            "content_type": response.getheader("Content-Type"),
            "body": data,
        }
    finally:
        connection.close()
