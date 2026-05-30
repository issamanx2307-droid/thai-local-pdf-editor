# -*- coding: utf-8 -*-
"""Create small sample PDFs for tests."""

from pathlib import Path

import fitz


def create_sample_pdf(path: Path, *, pages: int = 2, text_prefix: str = "ทดสอบ") -> Path:
    """Create a small PDF with Thai-capable metadata and simple page text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    for page_number in range(1, pages + 1):
        page = document.new_page(width=300, height=420)
        page.insert_text((36, 64), f"{text_prefix} {page_number}", fontsize=14)
    document.save(str(path))
    document.close()
    return path
