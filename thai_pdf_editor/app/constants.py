# -*- coding: utf-8 -*-
"""Shared constants for the PDF editor."""

APP_NAME = "Thai Local PDF Editor"
APP_VERSION = "v1.0.0-local"
APP_TITLE = "โปรแกรมแก้ไข PDF ภาษาไทย"
CREATOR_CREDIT = "สร้างโดย อิสระพงษ์ id line iss2510"
APP_MIN_WIDTH = 1440
APP_MIN_HEIGHT = 760

DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 0.25

PREVIEW_CACHE_SIZE = 32
DEFAULT_STATUS = "พร้อมใช้งาน"
NO_FILE_MESSAGE = "ยังไม่ได้เปิดไฟล์ PDF"

PDF_FILE_TYPES = [("PDF files", "*.pdf")]
IMAGE_FILE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg"),
    ("PNG files", "*.png"),
    ("JPEG files", "*.jpg *.jpeg"),
]
FONT_FILE_TYPES = [("TrueType fonts", "*.ttf *.otf")]
