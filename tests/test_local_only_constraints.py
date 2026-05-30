# -*- coding: utf-8 -*-
"""Regression tests for local-only desktop constraints."""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATHS = [
    PROJECT_ROOT / "run_app.py",
    PROJECT_ROOT / "start.bat",
    PROJECT_ROOT / "stop.bat",
    PROJECT_ROOT / "requirements.txt",
    PROJECT_ROOT / "requirements-build.txt",
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "thai_pdf_editor",
    PROJECT_ROOT / "scripts",
]
FORBIDDEN_PORT = "80" + "00"
FORBIDDEN_WEB_DEPENDENCIES = {
    "fastapi",
    "flask",
    "django",
    "uvicorn",
    "gunicorn",
}
FORBIDDEN_OCR_DEPENDENCIES = {
    "easyocr",
    "ocrmypdf",
    "paddleocr",
    "pytesseract",
    "tesseract",
}
FORBIDDEN_WORD_EXPORT_DEPENDENCIES = {
    "docx2pdf",
    "mammoth",
    "python-docx",
    "pypdf",
}
FORBIDDEN_CERT_SIGNATURE_DEPENDENCIES = {
    "endesive",
    "pyhanko",
}
FORBIDDEN_SERVER_IMPORTS = {
    "http.server",
    "socketserver",
    "wsgiref",
    "uvicorn",
}
FORBIDDEN_MOJIBAKE_MARKERS = {
    chr(0x00E0) + chr(0x00B8),
    chr(0x00E0) + chr(0x00B9),
    "\ufffd",
}


def _production_files() -> list[Path]:
    files: list[Path] = []
    for path in PRODUCTION_PATHS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(file for file in path.rglob("*.py") if "__pycache__" not in file.parts)
            files.extend(file for file in path.rglob("*.ps1") if "__pycache__" not in file.parts)
    return files


def test_production_code_does_not_reference_forbidden_port() -> None:
    """Production code must not reference port 8000."""
    offenders = []
    for path in _production_files():
        text = path.read_text(encoding="utf-8").lower()
        if FORBIDDEN_PORT in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_no_web_server_dependencies_are_declared() -> None:
    """Desktop app dependencies must not include web server frameworks."""
    dependency_text = "\n".join(
        [
            (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        ]
    ).lower()

    offenders = []
    for dependency_name in FORBIDDEN_WEB_DEPENDENCIES:
        pattern = rf"(^|[\s\"',\[]){re.escape(dependency_name)}([<>=!~\s\"',\]]|$)"
        if re.search(pattern, dependency_text):
            offenders.append(dependency_name)

    assert offenders == []


def test_no_ocr_dependencies_are_declared() -> None:
    """OCR is intentionally excluded from this project."""
    dependency_text = "\n".join(
        [
            (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        ]
    ).lower()

    offenders = []
    for dependency_name in FORBIDDEN_OCR_DEPENDENCIES:
        pattern = rf"(^|[\s\"',\[]){re.escape(dependency_name)}([<>=!~\s\"',\]]|$)"
        if re.search(pattern, dependency_text):
            offenders.append(dependency_name)

    assert offenders == []


def test_no_pdf_to_word_dependencies_are_declared() -> None:
    """PDF-to-Word conversion remains outside this editor."""
    dependency_text = "\n".join(
        [
            (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        ]
    ).lower()

    offenders = []
    for dependency_name in FORBIDDEN_WORD_EXPORT_DEPENDENCIES:
        pattern = rf"(^|[\s\"',\[]){re.escape(dependency_name)}([<>=!~\s\"',\]]|$)"
        if re.search(pattern, dependency_text):
            offenders.append(dependency_name)

    assert offenders == []


def test_no_certificate_signature_dependencies_are_declared() -> None:
    """Certificate/PKI signing is not implemented in this editor yet."""
    dependency_text = "\n".join(
        [
            (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        ]
    ).lower()

    offenders = []
    for dependency_name in FORBIDDEN_CERT_SIGNATURE_DEPENDENCIES:
        pattern = rf"(^|[\s\"',\[]){re.escape(dependency_name)}([<>=!~\s\"',\]]|$)"
        if re.search(pattern, dependency_text):
            offenders.append(dependency_name)

    assert offenders == []


def test_excluded_scopes_are_documented_and_not_listed_as_backlog() -> None:
    """Plugin, cloud, user-account, and AI work is intentionally out of scope."""
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    roadmap_text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()
    remaining_section = readme_text.split("## ฟีเจอร์ที่ยังไม่ทำใน v1", maxsplit=1)[1]

    assert "plugin system: ตัดออกจาก scope" in readme_text
    assert "cloud sync / cloud storage: ตัดออกจาก scope" in readme_text
    assert "user account / login: ตัดออกจาก scope" in readme_text
    assert "ai integration: ตัดออกจาก scope" in readme_text
    assert "pdf to word แบบ ocr/layout reconstruction" in readme_text
    assert "digital signature certificate/pki" in readme_text
    assert "plugin, cloud, and user account features: intentionally excluded" in roadmap_text
    assert "ai integration: intentionally excluded" in roadmap_text
    assert "pdf to word ocr/layout reconstruction: intentionally kept" in roadmap_text
    assert "large batch automation beyond local sequential batch jpg: ask before implementation" in roadmap_text
    assert "plugin system" not in remaining_section
    assert "cloud sync" not in remaining_section
    assert "user account" not in remaining_section
    assert "ai integration" not in remaining_section


def test_visual_signature_is_not_presented_as_certificate_signature() -> None:
    """The UI and docs must call the current feature a visual signature only."""
    ui_text = "\n".join(
        [
            (PROJECT_ROOT / "thai_pdf_editor" / "app" / "ui" / "tool_panel.py").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "thai_pdf_editor" / "app" / "ui" / "dialogs.py").read_text(encoding="utf-8"),
            (PROJECT_ROOT / "thai_pdf_editor" / "app" / "ui" / "main_window.py").read_text(encoding="utf-8"),
        ]
    )
    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    roadmap_text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()

    assert "ลายเซ็นภาพ" in ui_text
    assert "ลายเซ็นภาพ" in readme_text
    assert "image overlay" in readme_text
    assert "certificate/PKI digital signatures require a separate design".lower() in roadmap_text
    assert "digital signature" not in ui_text.lower()


def test_production_code_does_not_import_server_modules() -> None:
    """Production code must remain a desktop app, not a local server."""
    offenders = []
    for path in _production_files():
        text = path.read_text(encoding="utf-8").lower()
        for forbidden_import in FORBIDDEN_SERVER_IMPORTS:
            if forbidden_import in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{forbidden_import}")

    assert offenders == []


def test_production_text_has_no_mojibake_markers() -> None:
    """Thai UI/error text must stay readable and not be double-decoded."""
    offenders = []
    for path in _production_files():
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in FORBIDDEN_MOJIBAKE_MARKERS):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
            continue
        if any("\x80" <= char <= "\x9f" for char in text):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_windows_launchers_exist_and_track_pid() -> None:
    """Root launchers must exist and use PID tracking instead of ports."""
    start_text = (PROJECT_ROOT / "start.bat").read_text(encoding="utf-8")
    stop_text = (PROJECT_ROOT / "stop.bat").read_text(encoding="utf-8")
    stop_script_text = (PROJECT_ROOT / "scripts" / "stop_app.ps1").read_text(encoding="utf-8")

    assert "run_app.py" in start_text
    assert "THAI_PDF_EDITOR_ARGS" in start_text
    assert "data\\temp\\app.pid" in start_text
    assert "scripts\\stop_app.ps1" in stop_text
    assert "data\\temp\\app.pid" in stop_script_text
    assert "run_app.py" in stop_script_text
    assert "ThaiLocalPdfEditor.exe" in stop_script_text
    assert "Stop-Process" in stop_script_text


def test_packaging_script_exists_for_pyinstaller_build() -> None:
    """Packaging uses the repo entrypoint and keeps the app local-only."""
    script_text = (PROJECT_ROOT / "scripts" / "build_exe.bat").read_text(encoding="utf-8")

    assert "PyInstaller" in script_text
    assert "run_app.py" in script_text
    assert "ThaiLocalPdfEditor" in script_text


def test_packaging_excludes_dev_and_heavy_optional_modules() -> None:
    """The packaged app should not drag dev/test or unused optional analysis stacks."""
    script_text = (PROJECT_ROOT / "scripts" / "build_exe.bat").read_text(encoding="utf-8")
    excluded_modules = {
        "pytest",
        "_pytest",
        "pandas",
        "matplotlib",
        "openpyxl",
        "lxml",
        "numpy",
        "cryptography",
        "OpenSSL",
        "twisted",
    }

    for module_name in excluded_modules:
        assert f"--exclude-module {module_name}" in script_text


def test_roadmap_exists_with_next_phases() -> None:
    """Roadmap tracks remaining manual QA and packaging work."""
    roadmap_text = (PROJECT_ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    assert "Phase 6: UX Readiness" in roadmap_text
    assert "Phase 7: Manual GUI QA" in roadmap_text
    assert "Phase 8: Packaging" in roadmap_text
    assert "python -m pytest" in roadmap_text
    assert "python scripts/phase7_qa.py --include-gui" in roadmap_text
    assert "cmd /c scripts\\build_exe.bat" in roadmap_text
    assert "dist\\ThaiLocalPdfEditor\\ThaiLocalPdfEditor.exe" in roadmap_text
