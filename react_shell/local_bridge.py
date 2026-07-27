# -*- coding: utf-8 -*-
"""Local-only HTTP bridge for the React migration shell.

This bridge is intentionally scoped to development and migration testing. The
current packaged desktop app remains the default Windows PDF handler.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import logging
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import uuid4

import fitz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from thai_pdf_editor.app.config import TEMP_DIR
from thai_pdf_editor.app.logging_config import setup_logging
from thai_pdf_editor.app.utils.image_utils import validate_image_path
from thai_pdf_editor.app.worker import PdfWorkerSession
from thai_pdf_editor.app.worker_contract import (
    COMMAND_BATCH,
    COMMAND_OPEN_PDF,
    COMMAND_RENDER_PAGE,
    state_payload,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5178
BRIDGE_NAME = "thai-pdf-react-bridge"
DEFAULT_DEV_ORIGIN = "http://127.0.0.1:5173"
MAX_UPLOAD_IMAGE_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_PDF_BYTES = 80 * 1024 * 1024
# A PDF upload is JSON with a base64 data URL, so its request body can be
# roughly 4/3 of the PDF limit. Keep one bound for every JSON endpoint.
MAX_JSON_REQUEST_BYTES = 120 * 1024 * 1024
MAX_CHUNK_HEADER_BYTES = 1024
UPLOAD_IMAGE_DIR = TEMP_DIR / "react_bridge_uploads"
UPLOAD_PDF_DIR = TEMP_DIR / "react_bridge_pdf_uploads"
ALLOWED_DEV_ORIGINS = {
    DEFAULT_DEV_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
    # Tauri v1 custom protocol
    "tauri://localhost",
    # Tauri v2 production WebView (Windows/Linux use https://tauri.localhost
    # per Tauri's docs, but the actual WebView2 origin observed on Windows
    # 11 is plain http://tauri.localhost — keep both so this doesn't regress
    # again if the scheme differs across WebView2 versions).
    "https://tauri.localhost",
    "http://tauri.localhost",
}

LOGGER = logging.getLogger("thai_pdf_editor.react_bridge")


class ReactBridgeServer(ThreadingHTTPServer):
    """Threaded localhost server that owns one PDF worker session."""

    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        preview_dir: Path,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.preview_dir = preview_dir
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.session = PdfWorkerSession(preview_dir=self.preview_dir)
        self.session_lock = threading.Lock()

    def server_close(self) -> None:
        """Close the worker session when the bridge stops."""
        try:
            self.session.close()
        finally:
            super().server_close()


class ReactBridgeHandler(BaseHTTPRequestHandler):
    """HTTP handler for React-to-worker commands and preview images."""

    server: ReactBridgeServer

    def do_OPTIONS(self) -> None:
        """Allow browser preflight requests from the local Vite dev server."""
        self._send_no_content()

    def do_GET(self) -> None:
        """Serve health, demo metadata, and rendered preview images."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "bridge": BRIDGE_NAME,
                    "state": state_payload(self.server.session.state),
                    # Portable per-user default (no hardcoded username), so
                    # the React UI never needs to guess a Windows path.
                    "default_downloads_dir": str(Path.home() / "Downloads"),
                }
            )
            return

        if parsed.path.startswith("/api/previews/"):
            self._send_preview(parsed.path.removeprefix("/api/previews/"))
            return

        self._send_error(HTTPStatus.NOT_FOUND, "route not found")

    def do_POST(self) -> None:
        """Handle JSON worker requests from React."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload-image":
            request = self._read_json()
            if request is not None:
                try:
                    self._send_json(_save_uploaded_image(request))
                except ValueError as exc:
                    self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if parsed.path == "/api/upload-pdf":
            request = self._read_json()
            if request is not None:
                try:
                    self._send_json(_save_uploaded_pdf(request))
                except ValueError as exc:
                    self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if parsed.path != "/api/worker":
            self._send_error(HTTPStatus.NOT_FOUND, "route not found")
            return

        request = self._read_json()
        if request is None:
            return

        with self.server.session_lock:
            response = self.server.session.handle(request)
        self._send_json(_with_preview_urls(response, self.server.preview_dir))

    def log_message(self, format: str, *args: object) -> None:
        """Keep test and dev output quiet unless the caller logs explicitly."""

    def _read_json(self) -> dict[str, Any] | None:
        length_text = self.headers.get("Content-Length", "")
        transfer_encoding = self.headers.get("Transfer-Encoding", "")
        LOGGER.info(
            "_read_json path=%s Content-Length=%r Transfer-Encoding=%r Origin=%r",
            self.path,
            length_text,
            transfer_encoding,
            self.headers.get("Origin"),
        )

        try:
            if length_text:
                length = int(length_text)
                if length < 0:
                    raise ValueError("negative content length")
                if length > MAX_JSON_REQUEST_BYTES:
                    self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
                    return None
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    raise ValueError("incomplete request body")
            elif any(item.strip().lower() == "chunked" for item in transfer_encoding.split(",")):
                raw_body = self._read_chunked_body()
            else:
                # There is no EOF marker for a keep-alive HTTP request. Reading
                # until EOF here would hang the UI when a WebView omits the
                # header, which was the cause of PDF open requests stalling.
                self._send_error(HTTPStatus.LENGTH_REQUIRED, "Content-Length or chunked transfer encoding is required")
                return None
            body = json.loads(raw_body.decode("utf-8"))
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid content length")
            return None
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid json body")
            return None

        if not isinstance(body, dict):
            self._send_error(HTTPStatus.BAD_REQUEST, "json body must be an object")
            return None
        return body

    def _read_chunked_body(self) -> bytes:
        """Read and validate a HTTP/1.1 chunked request body within our limit."""
        chunks: list[bytes] = []
        total_size = 0
        while True:
            size_line = self.rfile.readline(MAX_CHUNK_HEADER_BYTES + 1)
            if not size_line or len(size_line) > MAX_CHUNK_HEADER_BYTES or not size_line.endswith(b"\r\n"):
                raise ValueError("invalid chunk header")
            try:
                chunk_size = int(size_line[:-2].split(b";", 1)[0], 16)
            except ValueError as exc:
                raise ValueError("invalid chunk size") from exc
            if chunk_size < 0 or total_size + chunk_size > MAX_JSON_REQUEST_BYTES:
                raise ValueError("request body too large")
            if chunk_size == 0:
                # Consume optional trailer headers, ending at the empty line.
                while True:
                    trailer = self.rfile.readline(MAX_CHUNK_HEADER_BYTES + 1)
                    if not trailer or len(trailer) > MAX_CHUNK_HEADER_BYTES:
                        raise ValueError("invalid chunk trailer")
                    if trailer == b"\r\n":
                        return b"".join(chunks)
            chunk = self.rfile.read(chunk_size)
            if len(chunk) != chunk_size or self.rfile.read(2) != b"\r\n":
                raise ValueError("incomplete chunked body")
            chunks.append(chunk)
            total_size += chunk_size

    def _send_preview(self, raw_name: str) -> None:
        name = unquote(raw_name)
        if Path(name).name != name or not name.lower().endswith(".png"):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid preview name")
            return

        preview_path = self.server.preview_dir / name
        if not preview_path.exists() or not preview_path.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "preview not found")
            return

        data = preview_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._send_common_headers(content_type="image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_common_headers(content_type="application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_no_content(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_common_headers()
        self.end_headers()

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"ok": False, "error": {"message": message}}, status=status)

    def _send_common_headers(self, *, content_type: str | None = None) -> None:
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _allowed_origin(self) -> str:
        origin = self.headers.get("Origin")
        if origin in ALLOWED_DEV_ORIGINS:
            return origin
        # Do NOT fall back to "*". Binding to 127.0.0.1 does not stop a
        # malicious page open in the same browser from calling this
        # bridge (localhost is reachable from any tab on this machine);
        # a wildcard CORS origin would let that page also read the
        # response (file paths, exported content, etc). Unknown origins
        # get the default origin instead, same as before.
        return DEFAULT_DEV_ORIGIN


def create_bridge_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    preview_dir: Path | None = None,
) -> ReactBridgeServer:
    """Create a local-only bridge server without starting it."""
    if host not in {DEFAULT_HOST, "localhost"}:
        raise ValueError("React bridge must bind to 127.0.0.1 or localhost")
    resolved_host = DEFAULT_HOST if host == "localhost" else host
    ReactBridgeServer.allow_reuse_address = True
    last_error: Exception | None = None
    for attempt in range(10):
        try:
            return ReactBridgeServer(
                (resolved_host, port),
                ReactBridgeHandler,
                preview_dir=preview_dir or TEMP_DIR / "react_bridge_previews",
            )
        except OSError as exc:
            last_error = exc
            time.sleep(0.3)
    if last_error is not None:
        raise last_error
    raise OSError("could not bind to port")


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        pass


def run_bridge(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, preview_dir: Path | None = None) -> None:
    """Run the local bridge until interrupted."""
    setup_logging()
    server = create_bridge_server(host=host, port=port, preview_dir=preview_dir)
    try:
        _safe_print(f"{BRIDGE_NAME} listening on http://{host}:{port}")
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run the Thai PDF React local bridge")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--preview-dir")
    args = parser.parse_args(argv)
    run_bridge(
        host=args.host,
        port=args.port,
        preview_dir=Path(args.preview_dir) if args.preview_dir else None,
    )
    return 0


def _save_uploaded_image(request: dict[str, Any]) -> dict[str, Any]:
    file_name = str(request.get("file_name") or "uploaded-image").strip()
    data_url = str(request.get("data_url") or "")
    mime_type, payload = _split_data_url(data_url)
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("รองรับเฉพาะ PNG, JPG/JPEG หรือ WEBP")
    try:
        data = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("ข้อมูลรูปภาพไม่ถูกต้อง") from exc
    if not data or len(data) > MAX_UPLOAD_IMAGE_BYTES:
        raise ValueError("ไฟล์รูปภาพใหญ่เกินไป")

    UPLOAD_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = UPLOAD_IMAGE_DIR / _safe_upload_name(file_name, mime_type)
    output_path.write_bytes(data)
    validate_image_path(output_path)
    return {"ok": True, "path": str(output_path), "file_name": output_path.name}


def _save_uploaded_pdf(request: dict[str, Any]) -> dict[str, Any]:
    file_name = str(request.get("file_name") or "uploaded.pdf").strip()
    data_url = str(request.get("data_url") or "")
    mime_type, payload = _split_data_url(data_url)
    if mime_type not in {"", "application/octet-stream", "application/pdf", "application/x-pdf"}:
        raise ValueError("รองรับเฉพาะไฟล์ PDF")
    if Path(file_name).suffix.lower() != ".pdf":
        raise ValueError("รองรับเฉพาะไฟล์ PDF")
    try:
        data = base64.b64decode(payload, validate=True)
    except binascii.Error as exc:
        raise ValueError("ข้อมูลไฟล์ PDF ไม่ถูกต้อง") from exc
    if not data or len(data) > MAX_UPLOAD_PDF_BYTES:
        raise ValueError("ไฟล์ PDF ใหญ่เกินไป")

    UPLOAD_PDF_DIR.mkdir(parents=True, exist_ok=True)
    output_path = UPLOAD_PDF_DIR / _safe_pdf_upload_name(file_name)
    output_path.write_bytes(data)
    try:
        with fitz.open(str(output_path)) as document:
            page_count = document.page_count
        if page_count <= 0:
            raise ValueError("ไฟล์ PDF ไม่มีหน้า")
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError("ไฟล์ PDF ไม่ถูกต้อง") from exc
    return {"ok": True, "path": str(output_path), "file_name": output_path.name, "page_count": page_count}


def _split_data_url(data_url: str) -> tuple[str, str]:
    header, separator, payload = data_url.partition(",")
    if not separator or not header.startswith("data:") or ";base64" not in header:
        raise ValueError("ข้อมูลรูปภาพไม่ถูกต้อง")
    mime_type = header.removeprefix("data:").split(";", maxsplit=1)[0].lower()
    return mime_type, payload


def _safe_upload_name(file_name: str, mime_type: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
        }[mime_type]
    stem = Path(file_name).stem or "uploaded-image"
    safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48]
    return f"{safe_stem or 'uploaded-image'}_{uuid4().hex[:10]}{suffix}"


def _safe_pdf_upload_name(file_name: str) -> str:
    stem = Path(file_name).stem or "uploaded-pdf"
    safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)[:48]
    return f"{safe_stem or 'uploaded-pdf'}_{uuid4().hex[:10]}.pdf"


def _with_preview_urls(response: dict[str, Any], preview_dir: Path) -> dict[str, Any]:
    converted = dict(response)
    if converted.get("command") == COMMAND_BATCH:
        converted["responses"] = [
            _with_preview_urls(item, preview_dir) if isinstance(item, dict) else item
            for item in converted.get("responses", [])
        ]
        return converted

    payload = converted.get("payload")
    if not isinstance(payload, dict):
        return converted

    preview_path_text = payload.get("preview_path")
    if not preview_path_text:
        return converted

    preview_path = Path(str(preview_path_text)).resolve()
    if preview_path.parent == preview_dir.resolve():
        converted["payload"] = {
            **payload,
            "preview_url": f"/api/previews/{preview_path.name}",
        }
    return converted


if __name__ == "__main__":
    raise SystemExit(main())
