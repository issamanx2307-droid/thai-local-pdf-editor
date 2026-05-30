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
