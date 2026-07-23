# -*- coding: utf-8 -*-
"""PDF print operations for Windows.

Strategy (tried in order):
1. SumatraPDF - reliable, supports specific printer + copies.
2. Internal Windows GDI print worker - renders PDF pages locally with PyMuPDF.
3. os.startfile 'print' verb - last-resort system PDF viewer handler.
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from ctypes import wintypes

from thai_pdf_editor.app.core.errors import PdfPrintError

_log = logging.getLogger(__name__)

_PRINT_UNAVAILABLE_MESSAGE = (
    "พิมพ์ PDF ไม่ได้บนเครื่องนี้: ไม่พบตัวพิมพ์ PDF ที่แอปเรียกใช้ได้ "
    "และ Windows ไม่มีคำสั่งพิมพ์สำหรับไฟล์ PDF"
)
_PRINT_WORKER_TIMEOUT_SECONDS = 600
_GDI_RENDER_DPI = 150

# Common SumatraPDF install locations
_SUMATRA_CANDIDATES = [
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    r"C:\Users\Public\SumatraPDF\SumatraPDF.exe",
]


# ---------------------------------------------------------------------------
# Printer discovery
# ---------------------------------------------------------------------------

def list_printers() -> list[str]:
    """Return installed printer names via WMI (no extra dependencies)."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NonInteractive", "-NoProfile", "-Command",
                "(Get-WmiObject Win32_Printer).Name",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            encoding="utf-8",
            errors="replace",
        )
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return names if names else []
    except Exception as exc:  # noqa: BLE001
        _log.warning("list_printers failed: %s", exc)
        return []


def get_default_printer() -> str:
    """Return the system default printer name, or '' if unavailable."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NonInteractive", "-NoProfile", "-Command",
                "(Get-WmiObject Win32_Printer | Where-Object {$_.Default -eq $True}).Name",
            ],
            capture_output=True,
            text=True,
            timeout=12,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        _log.warning("get_default_printer failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Page range parsing
# ---------------------------------------------------------------------------

def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse a 1-based page-range spec such as ``"1-3,5,8-9"`` into 0-based indices.

    Returns a sorted list of unique 0-based page indices. Raises
    :class:`PdfPrintError` for blank input, bad syntax, or pages outside
    ``1..total_pages``.
    """
    if total_pages <= 0:
        raise PdfPrintError("ไฟล์ PDF ไม่มีหน้าให้พิมพ์")

    indices: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            bounds = chunk.split("-")
            if len(bounds) != 2 or not all(b.strip().isdigit() for b in bounds):
                raise PdfPrintError(f"รูปแบบช่วงหน้าไม่ถูกต้อง: '{chunk}'")
            start, end = int(bounds[0]), int(bounds[1])
            if start < 1 or end < start:
                raise PdfPrintError(f"ช่วงหน้าไม่ถูกต้อง: '{chunk}'")
            if end > total_pages:
                raise PdfPrintError(f"หน้า {end} เกินจำนวนหน้าทั้งหมด ({total_pages} หน้า)")
            indices.update(range(start - 1, end))
        else:
            if not chunk.isdigit():
                raise PdfPrintError(f"รูปแบบเลขหน้าไม่ถูกต้อง: '{chunk}'")
            page = int(chunk)
            if page < 1 or page > total_pages:
                raise PdfPrintError(f"หน้า {page} เกินจำนวนหน้าทั้งหมด ({total_pages} หน้า)")
            indices.add(page - 1)

    if not indices:
        raise PdfPrintError("กรุณาระบุหน้าที่ต้องการพิมพ์")

    return sorted(indices)


def _format_page_ranges(indices: list[int]) -> str:
    """Collapse sorted 0-based indices into a compact 1-based range string."""
    if not indices:
        return ""
    ordered = sorted(set(indices))
    parts: list[str] = []
    start = prev = ordered[0]
    for idx in ordered[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        parts.append(str(start + 1) if start == prev else f"{start + 1}-{prev + 1}")
        start = prev = idx
    parts.append(str(start + 1) if start == prev else f"{start + 1}-{prev + 1}")
    return ",".join(parts)


def _get_page_count(pdf_path: Path) -> int:
    """Open *pdf_path* just long enough to read its page count."""
    try:
        import fitz
    except Exception as exc:  # noqa: BLE001
        raise PdfPrintError("ไม่สามารถเตรียมระบบพิมพ์ PDF ได้", detail=str(exc)) from exc
    try:
        with fitz.open(pdf_path) as document:
            return document.page_count
    except Exception as exc:  # noqa: BLE001
        raise PdfPrintError("ไม่สามารถอ่านไฟล์ PDF เพื่อตรวจสอบจำนวนหน้าได้", detail=str(exc)) from exc


def _normalize_page_spec(pdf_path: Path, pages: str | None) -> str | None:
    """Validate *pages* against the document and return a normalized spec.

    Returns ``None`` when *pages* is blank, meaning "print every page".
    """
    if pages is None or not pages.strip():
        return None
    total_pages = _get_page_count(pdf_path)
    indices = parse_page_range(pages, total_pages)
    return _format_page_ranges(indices)


# ---------------------------------------------------------------------------
# Print execution
# ---------------------------------------------------------------------------

def _find_sumatra() -> Path | None:
    """Locate SumatraPDF executable, or return None."""
    for candidate in _SUMATRA_CANDIDATES:
        p = Path(candidate)
        if p.exists():
            return p
    return None


def print_pdf(pdf_path: Path, printer_name: str, *, copies: int = 1, pages: str | None = None) -> None:
    """Send *pdf_path* to *printer_name*.

    *pages*, if given, is a 1-based page-range spec such as ``"1-3,5,8-9"``.
    Leave it blank (or ``None``) to print every page.

    Tries SumatraPDF first (supports printer selection + copy count);
    falls back to the Windows shell 'print' verb which opens the system
    default PDF viewer and triggers its print handler.
    """
    pdf_path = Path(pdf_path)
    _validate_print_request(pdf_path, printer_name, copies)
    page_spec = _normalize_page_spec(pdf_path, pages)

    sumatra = _find_sumatra()
    if sumatra:
        _log.info(
            "Printing via SumatraPDF: %s -> %s (x%d) pages=%s",
            pdf_path.name, printer_name, copies, page_spec or "all",
        )
        _print_via_sumatra(sumatra, pdf_path, printer_name, copies=copies, page_spec=page_spec)
        return

    if _is_windows():
        try:
            _spawn_gdi_print_worker(pdf_path, printer_name, copies=copies, page_spec=page_spec)
            return
        except Exception as exc:  # noqa: BLE001
            _log.warning("internal GDI print worker could not be started: %s", exc)

    _log.info("Falling back to shell print verb")
    try:
        _print_via_shell(pdf_path)
    except OSError as exc:
        raise PdfPrintError(_PRINT_UNAVAILABLE_MESSAGE, detail=str(exc)) from exc


def _print_via_sumatra(
    sumatra: Path,
    pdf_path: Path,
    printer_name: str,
    *,
    copies: int,
    page_spec: str | None = None,
) -> None:
    settings_parts = [page_spec] if page_spec else []
    settings_parts.append(f"ncopies={copies}")
    settings = ",".join(settings_parts)
    subprocess.Popen(
        [str(sumatra), "-print-to", printer_name, "-print-settings", settings, str(pdf_path)],
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


def _validate_print_request(pdf_path: Path, printer_name: str, copies: int) -> None:
    if not pdf_path.is_file():
        raise PdfPrintError("ไม่พบไฟล์ PDF ที่ต้องการพิมพ์", detail=f"file not found: {pdf_path}")
    if not printer_name.strip():
        raise PdfPrintError("กรุณาเลือกเครื่องพิมพ์ก่อนพิมพ์")
    if copies < 1:
        raise PdfPrintError("จำนวนชุดพิมพ์ต้องมากกว่า 0", detail=f"invalid copies: {copies}")


def _spawn_gdi_print_worker(
    pdf_path: Path,
    printer_name: str,
    *,
    copies: int,
    page_spec: str | None = None,
) -> None:
    command = _print_worker_command()
    if command is None:
        raise PdfPrintError("ไม่สามารถเริ่มตัวช่วยพิมพ์ PDF ได้")
    args = [
        *command,
        "--print-worker",
        str(pdf_path),
        "--printer",
        printer_name,
        "--copies",
        str(copies),
    ]
    if page_spec:
        args += ["--pages", page_spec]
    process = subprocess.Popen(
        args,
        creationflags=_creationflags_no_window(),
        close_fds=True,
    )
    _log.info(
        "Started internal PDF print worker pid=%s printer=%s copies=%d pages=%s",
        process.pid, printer_name, copies, page_spec or "all",
    )


def _print_worker_command() -> list[str] | None:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    project_root = Path(__file__).resolve().parents[3]
    entrypoint = project_root / "run_app.py"
    if entrypoint.exists():
        return [sys.executable, str(entrypoint)]
    return None


def _creationflags_no_window() -> int:
    if _is_windows() and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def _is_windows() -> bool:
    return os.name == "nt"


def _print_via_shell(pdf_path: Path) -> None:
    """Use the Windows shell 'print' verb on the PDF file."""
    os.startfile(str(pdf_path), "print")


def run_print_worker(pdf_path: str, printer_name: str, *, copies: int = 1, pages: str | None = None) -> int:
    """Run the hidden Windows GDI print worker process."""
    timer = threading.Timer(_PRINT_WORKER_TIMEOUT_SECONDS, _abort_timed_out_worker)
    timer.daemon = True
    timer.start()
    try:
        _print_via_windows_gdi(Path(pdf_path), printer_name, copies=copies, page_spec=pages)
    except Exception as exc:  # noqa: BLE001
        _log.exception("internal PDF print worker failed: %s", exc)
        return 1
    finally:
        timer.cancel()
    _log.info(
        "internal PDF print worker finished: %s -> %s (x%d) pages=%s",
        Path(pdf_path).name, printer_name, copies, pages or "all",
    )
    return 0


def _abort_timed_out_worker() -> None:
    _log.error("internal PDF print worker timed out after %d seconds", _PRINT_WORKER_TIMEOUT_SECONDS)
    os._exit(2)


def _print_via_windows_gdi(
    pdf_path: Path,
    printer_name: str,
    *,
    copies: int,
    page_spec: str | None = None,
    render_dpi: int = _GDI_RENDER_DPI,
) -> None:
    _validate_print_request(pdf_path, printer_name, copies)
    if not _is_windows():
        raise PdfPrintError(_PRINT_UNAVAILABLE_MESSAGE, detail="Windows GDI printing is unavailable")

    try:
        import fitz
        from PIL import Image, ImageWin
    except Exception as exc:  # noqa: BLE001
        raise PdfPrintError("ไม่สามารถเตรียมระบบพิมพ์ PDF ได้", detail=str(exc)) from exc

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    _configure_gdi32(gdi32)

    hdc = gdi32.CreateDCW("WINSPOOL", printer_name, None, None)
    if not hdc:
        raise PdfPrintError(
            "ไม่สามารถเชื่อมต่อเครื่องพิมพ์ที่เลือกได้",
            detail=_last_windows_error("CreateDCW"),
        )

    doc_started = False
    try:
        docinfo = _DOCINFOW(
            cbSize=ctypes.sizeof(_DOCINFOW),
            lpszDocName=f"Thai PDF Editor - {pdf_path.name}",
            lpszOutput=None,
            lpszDatatype=None,
            fwType=0,
        )
        if gdi32.StartDocW(hdc, ctypes.byref(docinfo)) <= 0:
            raise PdfPrintError("เริ่มงานพิมพ์ไม่ได้", detail=_last_windows_error("StartDocW"))
        doc_started = True

        printable_width = max(gdi32.GetDeviceCaps(hdc, _HORZRES), 1)
        printable_height = max(gdi32.GetDeviceCaps(hdc, _VERTRES), 1)

        with fitz.open(pdf_path) as document:
            page_indices = (
                parse_page_range(page_spec, document.page_count)
                if page_spec
                else list(range(document.page_count))
            )
            for _copy_index in range(copies):
                for page_index in page_indices:
                    page = document.load_page(page_index)
                    _print_gdi_page(
                        gdi32,
                        hdc,
                        page,
                        Image,
                        ImageWin,
                        printable_width=printable_width,
                        printable_height=printable_height,
                        render_dpi=render_dpi,
                    )

        if gdi32.EndDoc(hdc) <= 0:
            raise PdfPrintError("ปิดงานพิมพ์ไม่ได้", detail=_last_windows_error("EndDoc"))
        doc_started = False
    except Exception:
        if doc_started:
            gdi32.AbortDoc(hdc)
        raise
    finally:
        gdi32.DeleteDC(hdc)


def _print_gdi_page(
    gdi32: Any,
    hdc: int,
    page: Any,
    image_module: Any,
    image_win_module: Any,
    *,
    printable_width: int,
    printable_height: int,
    render_dpi: int,
) -> None:
    if gdi32.StartPage(hdc) <= 0:
        raise PdfPrintError("เริ่มหน้าพิมพ์ไม่ได้", detail=_last_windows_error("StartPage"))

    page_started = True
    try:
        image = _render_pdf_page_to_image(page, image_module, render_dpi=render_dpi)
        target_box = _fit_image_to_printable_area(
            image.width,
            image.height,
            printable_width,
            printable_height,
        )
        image_win_module.Dib(image).draw(int(hdc), target_box)
    except Exception:
        if page_started:
            gdi32.EndPage(hdc)
        raise

    if gdi32.EndPage(hdc) <= 0:
        raise PdfPrintError("ปิดหน้าพิมพ์ไม่ได้", detail=_last_windows_error("EndPage"))


def _render_pdf_page_to_image(page: Any, image_module: Any, *, render_dpi: int) -> Any:
    import fitz

    scale = render_dpi / 72
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return image_module.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def _fit_image_to_printable_area(
    image_width: int,
    image_height: int,
    printable_width: int,
    printable_height: int,
) -> tuple[int, int, int, int]:
    if image_width <= 0 or image_height <= 0 or printable_width <= 0 or printable_height <= 0:
        return (0, 0, max(printable_width, 1), max(printable_height, 1))

    image_ratio = image_width / image_height
    printable_ratio = printable_width / printable_height
    if image_ratio > printable_ratio:
        target_width = printable_width
        target_height = max(1, int(printable_width / image_ratio))
    else:
        target_height = printable_height
        target_width = max(1, int(printable_height * image_ratio))

    left = max(0, (printable_width - target_width) // 2)
    top = max(0, (printable_height - target_height) // 2)
    return (left, top, left + target_width, top + target_height)


class _DOCINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_int),
        ("lpszDocName", wintypes.LPCWSTR),
        ("lpszOutput", wintypes.LPCWSTR),
        ("lpszDatatype", wintypes.LPCWSTR),
        ("fwType", wintypes.DWORD),
    ]


_HORZRES = 8
_VERTRES = 10


def _configure_gdi32(gdi32: Any) -> None:
    gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID]
    gdi32.CreateDCW.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.GetDeviceCaps.restype = ctypes.c_int
    gdi32.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(_DOCINFOW)]
    gdi32.StartDocW.restype = ctypes.c_int
    gdi32.EndDoc.argtypes = [wintypes.HDC]
    gdi32.EndDoc.restype = ctypes.c_int
    gdi32.AbortDoc.argtypes = [wintypes.HDC]
    gdi32.AbortDoc.restype = ctypes.c_int
    gdi32.StartPage.argtypes = [wintypes.HDC]
    gdi32.StartPage.restype = ctypes.c_int
    gdi32.EndPage.argtypes = [wintypes.HDC]
    gdi32.EndPage.restype = ctypes.c_int


def _last_windows_error(operation: str) -> str:
    error_code = ctypes.get_last_error()
    if error_code:
        return f"{operation} failed with Windows error {error_code}: {ctypes.FormatError(error_code)}"
    return f"{operation} failed"
