# -*- coding: utf-8 -*-
"""Application error types with Thai user-facing messages."""


class AppError(Exception):
    """Base application error safe to show in Thai UI."""

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        super().__init__(detail or user_message)
        self.user_message = user_message
        self.detail = detail or user_message


class PdfOpenError(AppError):
    """Raised when a PDF cannot be opened."""


class PdfPasswordRequiredError(AppError):
    """Raised when a PDF is password-protected and needs a (correct) password."""


class PdfSaveError(AppError):
    """Raised when saving a PDF fails."""


class PdfRenderError(AppError):
    """Raised when preview rendering fails."""


class PdfExportError(AppError):
    """Raised when exporting a PDF to another format fails."""


class PdfPrintError(AppError):
    """Raised when sending a PDF to the printer fails."""


class InvalidOperationError(AppError):
    """Raised when a requested PDF operation is not valid."""


class FontError(AppError):
    """Raised when a font cannot be used."""


class ImageInsertError(AppError):
    """Raised when an image cannot be inserted."""
