# -*- coding: utf-8 -*-
"""Create simple local visual signature images for PDF overlay use."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from thai_pdf_editor.app.config import SIGNATURE_DIR
from thai_pdf_editor.app.core.errors import FontError, InvalidOperationError
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font

DEFAULT_SIGNATURE_COLOR = "#1565c0"
DEFAULT_SIGNATURE_WIDTH_PX = 720
MIN_SIGNATURE_WIDTH_PX = 240
MAX_SIGNATURE_WIDTH_PX = 1600


def create_visual_signature_image(
    text: str,
    *,
    output_dir: Path = SIGNATURE_DIR,
    font_path: Path | None = None,
    width_px: int = DEFAULT_SIGNATURE_WIDTH_PX,
    color: str = DEFAULT_SIGNATURE_COLOR,
) -> Path:
    """Create a transparent PNG signature image from text."""
    clean_text = " ".join(str(text or "").split())
    if not clean_text:
        raise InvalidOperationError("กรุณากรอกข้อความสำหรับลายเซ็นภาพ")

    resolved_font = font_path or first_existing_thai_font()
    if resolved_font is None or not resolved_font.exists():
        raise FontError("ไม่พบฟอนต์ภาษาไทย กรุณาเลือกไฟล์ .ttf ก่อนสร้างลายเซ็นภาพ")

    width = max(MIN_SIGNATURE_WIDTH_PX, min(MAX_SIGNATURE_WIDTH_PX, int(width_px)))
    font = _fit_text_font(resolved_font, clean_text, width)
    text_bbox = _text_bbox(clean_text, font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    padding_x = max(24, width // 20)
    padding_y = max(22, width // 28)
    height = max(100, text_height + padding_y * 2 + 28)

    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    text_x = max(padding_x, (width - text_width) // 2)
    text_y = padding_y - text_bbox[1]
    rgba = _hex_to_rgba(color, 235)
    draw.text((text_x, text_y), clean_text, font=font, fill=rgba)
    underline_y = min(height - padding_y // 2, text_y + text_height + 12)
    draw.line(
        (padding_x, underline_y, width - padding_x, underline_y),
        fill=_hex_to_rgba(color, 155),
        width=max(2, width // 240),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"ลายเซ็นภาพ_{uuid4().hex[:10]}.png"
    image.save(output_path)
    return output_path


def _fit_text_font(font_path: Path, text: str, width_px: int) -> ImageFont.FreeTypeFont:
    max_width = width_px - max(48, width_px // 10)
    size = max(28, min(132, width_px // 6))
    while size > 18:
        font = ImageFont.truetype(str(font_path), size)
        bbox = _text_bbox(text, font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(str(font_path), 18)


def _text_bbox(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int, int]:
    probe = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    return ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)


def _hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    clean = value.strip().lstrip("#")
    if len(clean) != 6:
        clean = DEFAULT_SIGNATURE_COLOR.lstrip("#")
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), alpha)
