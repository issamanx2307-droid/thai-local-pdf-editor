# -*- coding: utf-8 -*-
"""Overlay operations for text, images, rectangles, and highlights."""

import functools
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

from thai_pdf_editor.app.core.errors import FontError, ImageInsertError, InvalidOperationError
from thai_pdf_editor.app.models.geometry import PdfPoint, PdfRect
from thai_pdf_editor.app.models.operations import OperationType, PdfOperation
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font
from thai_pdf_editor.app.utils.image_utils import validate_image_path
from thai_pdf_editor.app.utils.validation import require_page_index

DEFAULT_TEXT_COLOR = "#111111"
DEFAULT_SHAPE_COLOR = "#d32f2f"
DEFAULT_HIGHLIGHT_COLOR = "#fff176"


def create_text_operation(
    *,
    page_index: int,
    point: PdfPoint,
    text: str,
    font_size: int,
    color: str,
    font_path: Path | None,
) -> PdfOperation:
    """Create a pending text overlay operation."""
    if not text.strip():
        raise InvalidOperationError("กรุณากรอกข้อความก่อนวางลง PDF")
    resolved_font = font_path or first_existing_thai_font()
    if resolved_font is None or not resolved_font.exists():
        raise FontError("ไม่พบฟอนต์ภาษาไทย กรุณาเลือกไฟล์ .ttf ก่อนเพิ่มข้อความ")
    return PdfOperation(
        type=OperationType.ADD_TEXT,
        page_index=page_index,
        payload={
            "x": point.x,
            "y": point.y,
            "text": text,
            "font_size": int(font_size),
            "color": color or DEFAULT_TEXT_COLOR,
            "font_path": str(resolved_font),
        },
    )


def create_image_operation(
    *,
    page_index: int,
    point: PdfPoint,
    image_path: Path,
    width: float,
) -> PdfOperation:
    """Create a pending image/signature overlay operation."""
    validate_image_path(image_path)
    with Image.open(image_path) as image:
        ratio = image.height / image.width
    height = max(1.0, width * ratio)
    return PdfOperation(
        type=OperationType.ADD_IMAGE,
        page_index=page_index,
        payload={
            "x": point.x,
            "y": point.y,
            "width": float(width),
            "height": float(height),
            "image_path": str(image_path),
        },
    )


def create_rectangle_operation(
    *,
    page_index: int,
    rect: PdfRect,
    color: str,
    line_width: float,
) -> PdfOperation:
    """Create a pending rectangle drawing operation."""
    _require_visible_rect(rect)
    return PdfOperation(
        type=OperationType.DRAW_RECTANGLE,
        page_index=page_index,
        payload={
            "rect": _rect_payload(rect),
            "color": color or DEFAULT_SHAPE_COLOR,
            "line_width": float(line_width),
        },
    )


def create_highlight_operation(*, page_index: int, rect: PdfRect, color: str) -> PdfOperation:
    """Create a pending translucent highlight operation."""
    _require_visible_rect(rect)
    return PdfOperation(
        type=OperationType.HIGHLIGHT,
        page_index=page_index,
        payload={"rect": _rect_payload(rect), "color": color or DEFAULT_HIGHLIGHT_COLOR, "opacity": 0.35},
    )


def create_redact_operation(*, page_index: int, rect: PdfRect) -> PdfOperation:
    """Create a pending real redaction operation."""
    _require_visible_rect(rect)
    return PdfOperation(
        type=OperationType.REDACT,
        page_index=page_index,
        payload={"rect": _rect_payload(rect), "fill": "#000000"},
        irreversible=True,
    )


def apply_overlay_operations(document: fitz.Document, operations: list[PdfOperation]) -> None:
    """Apply pending non-redaction overlay operations to a PyMuPDF document."""
    for operation in operations:
        if operation.type not in {
            OperationType.ADD_TEXT,
            OperationType.ADD_IMAGE,
            OperationType.DRAW_RECTANGLE,
            OperationType.HIGHLIGHT,
            OperationType.REPLACE_TEXT,
        }:
            continue
        operation.validate(document.page_count)
        page = document.load_page(operation.page_index)
        if operation.type == OperationType.ADD_TEXT:
            _apply_text(page, operation)
        elif operation.type == OperationType.ADD_IMAGE:
            _apply_image(page, operation)
        elif operation.type == OperationType.DRAW_RECTANGLE:
            _apply_rectangle(page, operation)
        elif operation.type == OperationType.HIGHLIGHT:
            _apply_highlight(page, operation)
        elif operation.type == OperationType.REPLACE_TEXT:
            _apply_replacement_text(page, operation)


def apply_redaction_operations(document: fitz.Document, operations: list[PdfOperation]) -> None:
    """Apply real PyMuPDF redactions grouped by page."""
    redact_operations = [
        operation for operation in operations if operation.type in {OperationType.REDACT, OperationType.REPLACE_TEXT}
    ]
    pages = sorted({operation.page_index for operation in redact_operations})
    for page_index in pages:
        require_page_index(page_index, document.page_count)
        page = document.load_page(page_index)
        for operation in redact_operations:
            if operation.page_index != page_index:
                continue
            rect = _fitz_rect(operation.payload["rect"])
            fill = _hex_to_rgb(str(operation.payload.get("fill", "#000000")))
            page.add_redact_annot(rect, fill=fill)
        page.apply_redactions()


def render_overlay_preview(
    image: Image.Image,
    operations: list[PdfOperation],
    *,
    page_index: int,
    zoom: float,
) -> Image.Image:
    """Render pending overlay operations onto a preview image."""
    preview = image.convert("RGBA")
    overlay_layer = Image.new("RGBA", preview.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_layer)
    for operation in operations:
        if operation.page_index != page_index:
            continue
        if operation.type == OperationType.ADD_TEXT:
            _preview_text(draw, operation, zoom)
        elif operation.type == OperationType.ADD_IMAGE:
            _preview_image(overlay_layer, operation, zoom)
        elif operation.type == OperationType.DRAW_RECTANGLE:
            _preview_rectangle(draw, operation, zoom)
        elif operation.type == OperationType.HIGHLIGHT:
            _preview_highlight(draw, operation, zoom)
        elif operation.type == OperationType.REDACT:
            _preview_redaction(draw, operation, zoom)
        elif operation.type == OperationType.REPLACE_TEXT:
            _preview_replacement_text(draw, operation, zoom)
    return Image.alpha_composite(preview, overlay_layer).convert("RGB")


def _apply_text(page: fitz.Page, operation: PdfOperation) -> None:
    payload = operation.payload
    font_path = Path(str(payload["font_path"]))
    if not font_path.exists():
        raise FontError("ไม่พบไฟล์ฟอนต์ที่เลือก")
    page.insert_text(
        fitz.Point(float(payload["x"]), float(payload["y"])),
        str(payload["text"]),
        fontsize=float(payload["font_size"]),
        fontname="thai_overlay_font",
        fontfile=str(font_path),
        color=_hex_to_rgb(str(payload["color"])),
    )


def _apply_replacement_text(page: fitz.Page, operation: PdfOperation) -> None:
    payload = operation.payload
    text = str(payload.get("text", ""))
    if not text.strip():
        return
    font_path = Path(str(payload["font_path"]))
    if not font_path.exists():
        raise FontError("ไม่พบไฟล์ฟอนต์ที่เลือก")
    rect = _fitz_rect(payload["rect"])
    spare = page.insert_textbox(
        rect,
        text,
        fontsize=float(payload["font_size"]),
        fontname="thai_replace_font",
        fontfile=str(font_path),
        color=_hex_to_rgb(str(payload["color"])),
    )
    if spare < 0:
        page.insert_text(
            fitz.Point(rect.x0, max(rect.y0 + float(payload["font_size"]), rect.y1 - 1)),
            text,
            fontsize=float(payload["font_size"]),
            fontname="thai_replace_font",
            fontfile=str(font_path),
            color=_hex_to_rgb(str(payload["color"])),
        )


def _apply_image(page: fitz.Page, operation: PdfOperation) -> None:
    payload = operation.payload
    image_path = Path(str(payload["image_path"]))
    if not image_path.exists():
        raise ImageInsertError("ไม่พบไฟล์รูปภาพที่เลือก")
    rect = fitz.Rect(
        float(payload["x"]),
        float(payload["y"]),
        float(payload["x"]) + float(payload["width"]),
        float(payload["y"]) + float(payload["height"]),
    )
    page.insert_image(rect, filename=str(image_path))


def _apply_rectangle(page: fitz.Page, operation: PdfOperation) -> None:
    payload = operation.payload
    page.draw_rect(
        _fitz_rect(payload["rect"]),
        color=_hex_to_rgb(str(payload["color"])),
        width=float(payload["line_width"]),
    )


def _apply_highlight(page: fitz.Page, operation: PdfOperation) -> None:
    payload = operation.payload
    page.draw_rect(
        _fitz_rect(payload["rect"]),
        color=None,
        fill=_hex_to_rgb(str(payload["color"])),
        fill_opacity=float(payload["opacity"]),
        overlay=True,
    )


@functools.lru_cache(maxsize=64)
def _load_preview_font(font_path_str: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load and cache a PIL font. Key: (path, size) — shared across all renders."""
    try:
        return ImageFont.truetype(font_path_str, font_size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


@functools.lru_cache(maxsize=32)
def _load_preview_image(image_path_str: str) -> Image.Image:
    """Load, convert to RGBA, and cache a preview image. Key: path string."""
    with Image.open(image_path_str) as source:
        return source.convert("RGBA").copy()  # .copy() detaches from the file handle


def _preview_text(draw: ImageDraw.ImageDraw, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    font_size = max(1, int(float(payload["font_size"]) * zoom))
    font = _load_preview_font(str(payload["font_path"]), font_size)
    draw.text(
        (float(payload["x"]) * zoom, float(payload["y"]) * zoom),
        str(payload["text"]),
        fill=_hex_to_rgba(str(payload["color"]), 255),
        font=font,
    )


def _preview_image(layer: Image.Image, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    image_path_str = str(payload["image_path"])
    if not Path(image_path_str).exists():
        return
    width = max(1, int(float(payload["width"]) * zoom))
    height = max(1, int(float(payload["height"]) * zoom))
    stamp = _load_preview_image(image_path_str).resize((width, height))
    layer.alpha_composite(stamp, (int(float(payload["x"]) * zoom), int(float(payload["y"]) * zoom)))


def _preview_rectangle(draw: ImageDraw.ImageDraw, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    rect = _scaled_rect(payload["rect"], zoom)
    line_width = max(1, int(float(payload["line_width"]) * zoom))
    draw.rectangle(rect, outline=_hex_to_rgba(str(payload["color"]), 255), width=line_width)


def _preview_highlight(draw: ImageDraw.ImageDraw, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    rect = _scaled_rect(payload["rect"], zoom)
    alpha = int(255 * float(payload["opacity"]))
    draw.rectangle(rect, fill=_hex_to_rgba(str(payload["color"]), alpha))


def _preview_redaction(draw: ImageDraw.ImageDraw, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    draw.rectangle(_scaled_rect(payload["rect"], zoom), fill=_hex_to_rgba("#000000", 210))


def _preview_replacement_text(draw: ImageDraw.ImageDraw, operation: PdfOperation, zoom: float) -> None:
    payload = operation.payload
    draw.rectangle(_scaled_rect(payload["rect"], zoom), fill=_hex_to_rgba(str(payload["fill"]), 255))
    text = str(payload.get("text", ""))
    if not text.strip():
        return
    font_size = max(1, int(float(payload["font_size"]) * zoom))
    font = _load_preview_font(str(payload["font_path"]), font_size)
    x0, y0, _x1, _y1 = payload["rect"]
    draw.text(
        (float(x0) * zoom, float(y0) * zoom),
        text,
        fill=_hex_to_rgba(str(payload["color"]), 255),
        font=font,
    )


def _require_visible_rect(rect: PdfRect) -> None:
    if rect.width < 2 or rect.height < 2:
        raise InvalidOperationError("กรุณาลากพื้นที่ให้มีขนาดชัดเจน")


def _rect_payload(rect: PdfRect) -> tuple[float, float, float, float]:
    return (rect.x0, rect.y0, rect.x1, rect.y1)


def _fitz_rect(payload: object) -> fitz.Rect:
    x0, y0, x1, y1 = payload
    return fitz.Rect(float(x0), float(y0), float(x1), float(y1))


def _scaled_rect(payload: object, zoom: float) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = payload
    return (
        int(float(x0) * zoom),
        int(float(y0) * zoom),
        int(float(x1) * zoom),
        int(float(y1) * zoom),
    )


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    red, green, blue = _hex_to_ints(value)
    return (red / 255, green / 255, blue / 255)


def _hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    red, green, blue = _hex_to_ints(value)
    return (red, green, blue, alpha)


def _hex_to_ints(value: str) -> tuple[int, int, int]:
    clean = value.strip().lstrip("#")
    if len(clean) != 6:
        clean = "111111"
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
