# -*- coding: utf-8 -*-
"""Inspect PDF fonts and import matching local or downloadable fonts."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

import fitz

from thai_pdf_editor.app.config import FONT_DIR, IMPORTED_FONT_DIR
from thai_pdf_editor.app.core.errors import InvalidOperationError
from thai_pdf_editor.app.utils.font_utils import PREFERRED_THAI_FONT_PATH, WINDOWS_FONT_DIR

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
DEFAULT_FONT_SEARCH_DIRS = (
    IMPORTED_FONT_DIR,
    FONT_DIR,
    PREFERRED_THAI_FONT_PATH.parent,
    WINDOWS_FONT_DIR,
)
MAX_IMPORT_ATTEMPTS = 8
DOWNLOAD_TIMEOUT_SECONDS = 30

GOOGLE_FONT_DOWNLOADS = {
    "sarabun": (
        "Sarabun",
        "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf",
        "Sarabun-Regular.ttf",
    ),
    "notosansthai": (
        "Noto Sans Thai",
        "https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai%5Bwdth,wght%5D.ttf",
        "NotoSansThai.ttf",
    ),
    "notoserifthai": (
        "Noto Serif Thai",
        "https://github.com/google/fonts/raw/main/ofl/notoserifthai/NotoSerifThai%5Bwdth,wght%5D.ttf",
        "NotoSerifThai.ttf",
    ),
    "kanit": (
        "Kanit",
        "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Regular.ttf",
        "Kanit-Regular.ttf",
    ),
    "prompt": (
        "Prompt",
        "https://github.com/google/fonts/raw/main/ofl/prompt/Prompt-Regular.ttf",
        "Prompt-Regular.ttf",
    ),
}

SIMILAR_FONT_KEYS = {
    "thsarabunnew": "sarabun",
    "thsarabunpsk": "sarabun",
    "sarabunnew": "sarabun",
    "angsanaitalic": "notoserifthai",
    "angsananew": "notoserifthai",
    "angsanaupcregular": "notoserifthai",
    "cordianew": "notosansthai",
    "cordiaupc": "notosansthai",
    "browallianew": "notosansthai",
    "browalliaupc": "notosansthai",
    "tahoma": "notosansthai",
    "arial": "notosansthai",
    "arialmt": "notosansthai",
    "helvetica": "notosansthai",
    "timesnewroman": "notoserifthai",
}

LOCAL_FONT_ALIASES = {
    "thsarabunnew": ("THSarabunNew.ttf",),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf"),
    "arialmt": ("arial.ttf",),
    "helvetica": ("arial.ttf",),
    "timesnewroman": ("times.ttf", "timesbd.ttf"),
    "calibri": ("calibri.ttf", "calibrib.ttf"),
    "cordianew": ("cordia.ttf", "cordiab.ttf"),
    "angsananew": ("angsa.ttf", "angsab.ttf"),
    "browallianew": ("browa.ttf", "browab.ttf"),
    "sarabun": ("Sarabun-Regular.ttf",),
    "notosansthai": ("NotoSansThai.ttf", "NotoSansThai-Regular.ttf"),
    "notoserifthai": ("NotoSerifThai.ttf", "NotoSerifThai-Regular.ttf"),
}

STATUS_LABELS = {
    "local_exact": "พบฟอนต์ตรงกันในเครื่อง",
    "local_similar": "พบฟอนต์ใกล้เคียงในเครื่อง",
    "downloaded_exact": "ดาวน์โหลดฟอนต์ตรงกัน",
    "downloaded_similar": "ดาวน์โหลดฟอนต์ใกล้เคียง",
    "download_failed": "ดาวน์โหลดไม่สำเร็จ",
    "unresolved": "ไม่พบฟอนต์ที่ใช้ได้",
}


@dataclass(frozen=True)
class PdfFontUsage:
    """Font use detected from PDF text spans or page resources."""

    pdf_name: str
    normalized_name: str
    pages: tuple[int, ...]
    spans: int
    characters: int
    from_text_layer: bool


@dataclass(frozen=True)
class FontImportResult:
    """Result of matching or importing one PDF font."""

    pdf_font_name: str
    status: str
    resolved_family: str | None = None
    imported_path: Path | None = None
    source_path: Path | None = None
    source_url: str | None = None
    message: str = ""

    @property
    def resolved(self) -> bool:
        return self.imported_path is not None


@dataclass(frozen=True)
class FontImportSummary:
    """Import summary for an opened PDF document."""

    usages: tuple[PdfFontUsage, ...]
    results: tuple[FontImportResult, ...]
    selected_font_path: Path


@dataclass
class _FontAccumulator:
    pdf_name: str
    pages: set[int] = field(default_factory=set)
    spans: int = 0
    characters: int = 0
    from_text_layer: bool = False


def import_fonts_for_document(
    document: fitz.Document,
    *,
    allow_download: bool = True,
    imported_dir: Path = IMPORTED_FONT_DIR,
    search_dirs: tuple[Path, ...] = DEFAULT_FONT_SEARCH_DIRS,
) -> FontImportSummary:
    """Import fonts detected in the PDF or raise a clear Thai error."""
    usages = scan_pdf_font_usage(document)
    if not usages:
        raise InvalidOperationError("ไม่สามารถหาข้อมูลได้: PDF ไม่มี text layer หรือข้อมูลฟอนต์ให้ตรวจ")

    results: list[FontImportResult] = []
    for usage in usages[:MAX_IMPORT_ATTEMPTS]:
        results.append(
            resolve_and_import_font(
                usage.pdf_name,
                allow_download=allow_download,
                imported_dir=imported_dir,
                search_dirs=search_dirs,
            )
        )

    resolved_results = [result for result in results if result.resolved]
    if not resolved_results:
        raise InvalidOperationError("ไม่สามารถหาข้อมูลได้: ไม่พบฟอนต์จริงหรือฟอนต์ใกล้เคียงให้ใช้งาน")

    return FontImportSummary(
        usages=tuple(usages),
        results=tuple(results),
        selected_font_path=resolved_results[0].imported_path,
    )


def format_font_import_summary(summary: FontImportSummary, *, max_results: int = 12) -> str:
    """Format a readable Thai report for the font import dialog."""
    resolved_count = sum(1 for result in summary.results if result.resolved)
    unresolved_count = len(summary.results) - resolved_count
    lines = [
        "นำเข้าฟอนต์สำเร็จ",
        f"ฟอนต์ที่ใช้แก้ข้อความ: {summary.selected_font_path.name}",
        f"พบฟอนต์ใน PDF: {len(summary.usages)} รายการ",
        f"นำเข้าได้: {resolved_count} รายการ",
    ]
    if unresolved_count:
        lines.append(f"ยังหาหรือโหลดไม่ได้: {unresolved_count} รายการ")

    lines.append("")
    lines.append("รายละเอียดฟอนต์ที่พบ")
    usage_by_name = {usage.normalized_name: usage for usage in summary.usages}
    for index, result in enumerate(summary.results[:max_results], start=1):
        usage = usage_by_name.get(normalize_font_name(result.pdf_font_name))
        lines.extend(_format_font_import_result(index, result, usage))
    if len(summary.results) > max_results:
        lines.append(f"...แสดง {max_results} จาก {len(summary.results)} รายการ")
    return "\n".join(lines)


def scan_pdf_font_usage(document: fitz.Document) -> list[PdfFontUsage]:
    """Read font names from PDF text spans, falling back to page font resources."""
    text_accumulators: dict[str, _FontAccumulator] = {}
    resource_accumulators: dict[str, _FontAccumulator] = {}

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        for font_name, text in _iter_span_fonts(page):
            _record_font(text_accumulators, font_name, page_index, characters=len(text), from_text_layer=True)
        for font_name in _iter_resource_fonts(page):
            _record_font(resource_accumulators, font_name, page_index, characters=0, from_text_layer=False)

    source = text_accumulators if text_accumulators else resource_accumulators
    usages = [_to_usage(accumulator) for accumulator in source.values()]
    return sorted(usages, key=lambda usage: (usage.from_text_layer, usage.characters, usage.spans), reverse=True)


def resolve_and_import_font(
    pdf_font_name: str,
    *,
    allow_download: bool = True,
    imported_dir: Path = IMPORTED_FONT_DIR,
    search_dirs: tuple[Path, ...] = DEFAULT_FONT_SEARCH_DIRS,
) -> FontImportResult:
    """Resolve one PDF font name to an imported local file."""
    normalized = normalize_font_name(pdf_font_name)
    if not normalized:
        return FontImportResult(pdf_font_name=pdf_font_name, status="unresolved", message="ชื่อฟอนต์ว่าง")

    local_path = find_local_font(normalized, search_dirs)
    if local_path is not None:
        imported_path = copy_font_to_imported(local_path, imported_dir)
        return FontImportResult(
            pdf_font_name=pdf_font_name,
            status="local_exact",
            resolved_family=display_font_name(pdf_font_name),
            imported_path=imported_path,
            source_path=local_path,
            message="พบฟอนต์ตรงกันในเครื่อง",
        )

    similar_key = SIMILAR_FONT_KEYS.get(normalized)
    if similar_key:
        local_path = find_local_font(similar_key, search_dirs)
        if local_path is not None:
            imported_path = copy_font_to_imported(local_path, imported_dir)
            return FontImportResult(
                pdf_font_name=pdf_font_name,
                status="local_similar",
                resolved_family=GOOGLE_FONT_DOWNLOADS.get(similar_key, (similar_key, "", ""))[0],
                imported_path=imported_path,
                source_path=local_path,
                message="พบฟอนต์ใกล้เคียงในเครื่อง",
            )

    if allow_download:
        download_key = normalized if normalized in GOOGLE_FONT_DOWNLOADS else similar_key
        if download_key in GOOGLE_FONT_DOWNLOADS:
            family, url, filename = GOOGLE_FONT_DOWNLOADS[download_key]
            try:
                imported_path = download_font(url, imported_dir / filename)
            except Exception as exc:
                return FontImportResult(
                    pdf_font_name=pdf_font_name,
                    status="download_failed",
                    resolved_family=family,
                    source_url=url,
                    message=f"ดาวน์โหลดฟอนต์ไม่สำเร็จ: {exc}",
                )
            else:
                return FontImportResult(
                    pdf_font_name=pdf_font_name,
                    status="downloaded_exact" if download_key == normalized else "downloaded_similar",
                    resolved_family=family,
                    imported_path=imported_path,
                    source_url=url,
                    message="ดาวน์โหลดฟอนต์ฟรีจาก Google Fonts แล้ว",
                )

    return FontImportResult(
        pdf_font_name=pdf_font_name,
        status="unresolved",
        message="ไม่พบฟอนต์ตรงกันหรือฟอนต์ใกล้เคียง",
    )


def normalize_font_name(font_name: str) -> str:
    """Normalize PDF font names for matching."""
    clean = str(font_name or "").strip()
    clean = re.sub(r"^[A-Z]{6}\+", "", clean)
    clean = clean.split(",")[0]
    clean = re.sub(r"(?i)(bold|italic|regular|medium|light|psmt|mt|cidfont\+f\d+)$", "", clean)
    return re.sub(r"[^0-9a-z]+", "", clean.lower())


def display_font_name(font_name: str) -> str:
    """Return a readable PDF font name without subset prefixes."""
    return re.sub(r"^[A-Z]{6}\+", "", str(font_name or "").strip()) or "Unknown"


def find_local_font(font_key: str, search_dirs: tuple[Path, ...] = DEFAULT_FONT_SEARCH_DIRS) -> Path | None:
    """Find a local font file by normalized family key or known filename alias."""
    aliases = LOCAL_FONT_ALIASES.get(font_key, ())
    for directory in search_dirs:
        if not directory.exists():
            continue
        for filename in aliases:
            candidate = directory / filename
            if candidate.exists():
                return candidate

    for directory in search_dirs:
        if not directory.exists():
            continue
        for candidate in directory.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in FONT_EXTENSIONS:
                continue
            if normalize_font_name(candidate.stem) == font_key:
                return candidate
    return None


def copy_font_to_imported(source_path: Path, imported_dir: Path = IMPORTED_FONT_DIR) -> Path:
    """Copy a resolved local font into the app imported-font directory."""
    imported_dir.mkdir(parents=True, exist_ok=True)
    destination = imported_dir / source_path.name
    if source_path.resolve() == destination.resolve():
        return destination
    shutil.copy2(source_path, destination)
    return destination


def download_font(url: str, destination_path: Path) -> Path:
    """Download a known free font file into the app imported-font directory."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists() and destination_path.stat().st_size > 0:
        return destination_path

    request = Request(url, headers={"User-Agent": "ThaiLocalPdfEditor/1.0"})
    with urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        data = response.read()
    if not _looks_like_font(data):
        raise InvalidOperationError("ดาวน์โหลดฟอนต์ไม่สำเร็จ: ไฟล์ที่ได้ไม่ใช่ฟอนต์ที่รองรับ")

    temp_path = destination_path.with_suffix(destination_path.suffix + ".tmp")
    temp_path.write_bytes(data)
    temp_path.replace(destination_path)
    return destination_path


def _iter_span_fonts(page: fitz.Page) -> list[tuple[str, str]]:
    text_dict = page.get_text("dict")
    spans: list[tuple[str, str]] = []
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_name = str(span.get("font") or "").strip()
                text = str(span.get("text") or "")
                if font_name and text.strip():
                    spans.append((font_name, text))
    return spans


def _iter_resource_fonts(page: fitz.Page) -> list[str]:
    names: list[str] = []
    for item in page.get_fonts(full=True):
        for value in item[3:5]:
            font_name = str(value or "").strip()
            if font_name:
                names.append(font_name)
                break
    return names


def _record_font(
    accumulators: dict[str, _FontAccumulator],
    font_name: str,
    page_index: int,
    *,
    characters: int,
    from_text_layer: bool,
) -> None:
    normalized = normalize_font_name(font_name)
    if not normalized:
        return
    accumulator = accumulators.setdefault(
        normalized,
        _FontAccumulator(pdf_name=display_font_name(font_name), from_text_layer=from_text_layer),
    )
    accumulator.pages.add(page_index + 1)
    accumulator.spans += 1
    accumulator.characters += characters


def _to_usage(accumulator: _FontAccumulator) -> PdfFontUsage:
    return PdfFontUsage(
        pdf_name=accumulator.pdf_name,
        normalized_name=normalize_font_name(accumulator.pdf_name),
        pages=tuple(sorted(accumulator.pages)),
        spans=accumulator.spans,
        characters=accumulator.characters,
        from_text_layer=accumulator.from_text_layer,
    )


def _format_font_import_result(
    index: int,
    result: FontImportResult,
    usage: PdfFontUsage | None,
) -> list[str]:
    status = STATUS_LABELS.get(result.status, result.status)
    selected_name = result.imported_path.name if result.imported_path is not None else "-"
    family = result.resolved_family or "-"
    lines = [
        f"{index}. ชื่อฟอนต์ใน PDF: {display_font_name(result.pdf_font_name)}",
        f"   สถานะ: {status}",
        f"   ฟอนต์ที่ระบบเลือก: {family}",
        f"   ไฟล์ที่ใช้: {selected_name}",
    ]
    if usage is not None:
        page_text = ", ".join(str(page) for page in usage.pages)
        source = "text layer" if usage.from_text_layer else "font resource"
        lines.append(
            f"   ข้อมูลจาก PDF: หน้า {page_text}, {usage.spans} spans, {usage.characters} ตัวอักษร, {source}"
        )
    if result.source_url:
        lines.append(f"   แหล่งดาวน์โหลด: {result.source_url}")
    if not result.resolved and result.message:
        lines.append(f"   เหตุผล: {result.message}")
    return lines


def _looks_like_font(data: bytes) -> bool:
    return data.startswith((b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"true")) and len(data) > 1024
