# -*- coding: utf-8 -*-
"""Export PDF pages to raster image files."""

import logging
import shutil
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

import fitz
from PIL import Image

from thai_pdf_editor.app.core.document_state import DocumentState
from thai_pdf_editor.app.core.errors import InvalidOperationError, PdfExportError
from thai_pdf_editor.app.core.overlay_operations import apply_overlay_operations, apply_redaction_operations
from thai_pdf_editor.app.utils.path_utils import make_temp_output_path
from thai_pdf_editor.app.utils.validation import require_page_index
from thai_pdf_editor.app.utils.validation import require_pdf_path

LOGGER = logging.getLogger("thai_pdf_editor.export_operations")

DEFAULT_JPG_DPI = 300
DEFAULT_JPG_QUALITY = 100
MIN_JPG_DPI = 72
MAX_JPG_DPI = 600
MIN_JPG_QUALITY = 1
MAX_JPG_QUALITY = 100
JPG_EXPORT_SCOPE_ALL = "all"
JPG_EXPORT_SCOPE_CURRENT = "current"
BATCH_JPG_REPORT_NAME = "batch_jpg_report.json"


def export_pdf_as_jpg(
    document: fitz.Document,
    state: DocumentState,
    destination_dir: Path,
    *,
    page_indices: Sequence[int] | None = None,
    dpi: int = DEFAULT_JPG_DPI,
    quality: int = DEFAULT_JPG_QUALITY,
) -> list[Path]:
    """Export selected PDF pages to JPG files without modifying the document."""
    if not state.has_document:
        raise PdfExportError("ยังไม่ได้เปิดไฟล์ PDF")
    _validate_export_options(dpi=dpi, quality=quality)
    destination_dir = destination_dir.expanduser()
    destination_dir.mkdir(parents=True, exist_ok=True)

    export_document = fitz.open()
    temp_paths: list[Path] = []
    try:
        export_document.insert_pdf(document)
        _apply_pending_operations_for_export(export_document, state)
        resolved_indices = _resolve_page_indices(page_indices, export_document.page_count)
        stem = _export_stem(state)
        output_paths: list[Path] = []
        matrix = fitz.Matrix(dpi / 72, dpi / 72)

        for page_index in resolved_indices:
            page = export_document.load_page(page_index)
            output_path = _unique_jpg_path(destination_dir, stem, page_index)
            temp_path = make_temp_output_path(output_path)
            temp_paths.append(temp_path)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pixmap.save(str(temp_path), jpg_quality=quality)
            _verify_jpg(temp_path)
            shutil.copy2(temp_path, output_path)
            output_paths.append(output_path)

    except Exception as exc:
        LOGGER.exception("export jpg failed destination=%s", destination_dir)
        if isinstance(exc, (InvalidOperationError, PdfExportError)):
            raise
        raise PdfExportError("ส่งออก JPG ไม่สำเร็จ", detail=str(exc)) from exc
    finally:
        export_document.close()
        for temp_path in temp_paths:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    LOGGER.info("exported jpg pages=%s destination=%s", len(output_paths), destination_dir)
    return output_paths


def batch_export_pdfs_as_jpg(
    source_paths: Sequence[Path],
    destination_dir: Path,
    *,
    dpi: int = DEFAULT_JPG_DPI,
    quality: int = DEFAULT_JPG_QUALITY,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, object]:
    """Export multiple PDFs to JPG sequentially and write a JSON report.

    *progress_callback*, if provided, is called as ``progress_callback(completed, total)``
    after each source PDF finishes (from the calling thread).
    """
    if not source_paths:
        raise InvalidOperationError("กรุณาเลือก PDF อย่างน้อย 1 ไฟล์")
    _validate_export_options(dpi=dpi, quality=quality)
    destination_dir = destination_dir.expanduser()
    destination_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, object]] = []
    for source_path in source_paths:
        item: dict[str, object] = {
            "source_path": str(source_path),
            "status": "failed",
            "output_paths": [],
            "error": "",
        }
        try:
            require_pdf_path(source_path)
            state = DocumentState()
            with fitz.open(str(source_path)) as document:
                if document.page_count <= 0:
                    raise PdfExportError("ไฟล์ PDF ไม่มีหน้าให้ส่งออก")
                state.load_document(source_path, source_path, document.page_count)
                output_paths = export_pdf_as_jpg(document, state, destination_dir, dpi=dpi, quality=quality)
            item["status"] = "succeeded"
            item["output_paths"] = [str(path) for path in output_paths]
        except Exception as exc:
            user_message = getattr(exc, "user_message", None)
            item["error"] = user_message if user_message else f"ส่งออก JPG ไม่สำเร็จ: {exc}"
            LOGGER.warning("batch jpg item failed source=%s error=%s", source_path, item["error"])
        items.append(item)
        if progress_callback is not None:
            try:
                progress_callback(len(items), len(source_paths))
            except Exception:  # noqa: BLE001
                pass

    succeeded = sum(1 for item in items if item["status"] == "succeeded")
    failed = len(items) - succeeded
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "destination_dir": str(destination_dir),
        "dpi": dpi,
        "quality": quality,
        "total_sources": len(items),
        "succeeded": succeeded,
        "failed": failed,
        "items": items,
    }
    report_path = destination_dir / BATCH_JPG_REPORT_NAME
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    LOGGER.info("batch exported jpg sources=%s succeeded=%s failed=%s", len(items), succeeded, failed)
    return report


def _validate_export_options(*, dpi: int, quality: int) -> None:
    if not MIN_JPG_DPI <= dpi <= MAX_JPG_DPI:
        raise InvalidOperationError(f"ค่า DPI ต้องอยู่ระหว่าง {MIN_JPG_DPI}-{MAX_JPG_DPI}")
    if not MIN_JPG_QUALITY <= quality <= MAX_JPG_QUALITY:
        raise InvalidOperationError(f"คุณภาพ JPG ต้องอยู่ระหว่าง {MIN_JPG_QUALITY}-{MAX_JPG_QUALITY}")


def resolve_jpg_page_indices(page_scope: str, current_page_index: int, total_pages: int) -> list[int] | None:
    """Resolve a user-facing JPG export scope to page indices."""
    if page_scope == JPG_EXPORT_SCOPE_ALL:
        return None
    if page_scope == JPG_EXPORT_SCOPE_CURRENT:
        require_page_index(current_page_index, total_pages)
        return [current_page_index]
    raise InvalidOperationError("ตัวเลือกหน้าสำหรับส่งออก JPG ไม่ถูกต้อง")


def _apply_pending_operations_for_export(document: fitz.Document, state: DocumentState) -> None:
    if not state.pending_operations:
        return
    apply_redaction_operations(document, state.pending_operations)
    apply_overlay_operations(document, state.pending_operations)


def _resolve_page_indices(page_indices: Sequence[int] | None, total_pages: int) -> list[int]:
    if total_pages <= 0:
        raise PdfExportError("ไฟล์ PDF ไม่มีหน้าให้ส่งออก")
    if page_indices is None:
        return list(range(total_pages))
    resolved = list(page_indices)
    if not resolved:
        raise InvalidOperationError("กรุณาเลือกหน้าอย่างน้อย 1 หน้า")
    for page_index in resolved:
        require_page_index(page_index, total_pages)
    return resolved


def _export_stem(state: DocumentState) -> str:
    if state.current_file_path is None:
        return "export"
    return state.current_file_path.stem


def _unique_jpg_path(destination_dir: Path, stem: str, page_index: int) -> Path:
    page_number = page_index + 1
    candidate = destination_dir / f"{stem}_page_{page_number:04d}.jpg"
    counter = 2
    while candidate.exists():
        candidate = destination_dir / f"{stem}_page_{page_number:04d}_{counter}.jpg"
        counter += 1
    return candidate


def _verify_jpg(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
            if image.width <= 0 or image.height <= 0:
                raise PdfExportError("ไฟล์ JPG ที่สร้างไม่มีขนาดภาพ")
    except PdfExportError:
        raise
    except Exception as exc:
        raise PdfExportError("ตรวจสอบไฟล์ JPG ที่สร้างไม่สำเร็จ", detail=str(exc)) from exc
