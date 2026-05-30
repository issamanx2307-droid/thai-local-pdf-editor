# -*- coding: utf-8 -*-
"""Image validation helpers."""

from pathlib import Path

from PIL import Image

from thai_pdf_editor.app.core.errors import ImageInsertError


def validate_image_path(path: Path) -> None:
    """Validate that an image can be opened by Pillow."""
    if not path.exists() or not path.is_file():
        raise ImageInsertError("ไม่พบไฟล์รูปภาพที่เลือก")
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise ImageInsertError("ไฟล์รูปภาพไม่ถูกต้อง", detail=str(exc)) from exc
