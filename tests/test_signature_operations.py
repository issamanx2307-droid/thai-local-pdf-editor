# -*- coding: utf-8 -*-
"""Tests for simple visual signature image creation."""

from pathlib import Path

import pytest
from PIL import Image

from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.core.signature_operations import create_visual_signature_image
from thai_pdf_editor.app.utils.font_utils import first_existing_thai_font


def test_create_visual_signature_image_writes_transparent_png(tmp_path: Path) -> None:
    """A simple visual signature should be a local PNG usable as an image overlay."""
    font_path = first_existing_thai_font()
    assert font_path is not None

    output_path = create_visual_signature_image(
        "สมชาย ใจดี",
        output_dir=tmp_path,
        font_path=font_path,
        width_px=480,
    )

    assert output_path.parent == tmp_path
    assert output_path.suffix.lower() == ".png"
    with Image.open(output_path) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"
        assert image.width == 480
        assert image.height >= 80
        assert image.getbbox() is not None


def test_create_visual_signature_image_requires_text(tmp_path: Path) -> None:
    """Blank signature text should not create an empty stamp."""
    with pytest.raises(InvalidOperationError, match="ลายเซ็นภาพ"):
        create_visual_signature_image("   ", output_dir=tmp_path)
