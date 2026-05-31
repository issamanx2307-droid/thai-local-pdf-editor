# -*- coding: utf-8 -*-
"""Run repeatable release QA checks for the local PDF editor."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "data" / "logs"
REPORT_PATH = LOG_DIR / "release_qa_report.json"

SOURCE_EXTENSIONS = {".py", ".md", ".bat", ".ps1", ".toml", ".txt"}
EXCLUDED_DIRS = {"build", "dist", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
MAX_SOURCE_LINES = 1000
MOJIBAKE_MARKERS = {
    chr(0x00E0) + chr(0x00B8),
    chr(0x00E0) + chr(0x00B9),
    "\ufffd",
}
FATAL_STDERR_MARKERS = {
    "--- Logging error ---",
    "Traceback (most recent call last)",
}

REQUIRED_PATHS = [
    "run_app.py",
    "start.bat",
    "stop.bat",
    "README.md",
    "RELEASE_NOTES.md",
    "ROADMAP.md",
    "V1_ACCEPTANCE_CHECKLIST.md",
    "requirements.txt",
    "thai_pdf_editor/app/main.py",
    "thai_pdf_editor/app/ui/main_window.py",
    "scripts/phase7_qa.py",
    "scripts/font_import_qa.py",
    "scripts/overlay_edit_qa.py",
    "scripts/phase43_ui_qa.py",
    "scripts/final_acceptance.py",
]


@dataclass(frozen=True)
class QaCommand:
    """One release QA command."""

    name: str
    command: list[str]


def release_commands(*, include_build: bool) -> list[QaCommand]:
    """Return the release QA commands in execution order."""
    commands = [
        QaCommand("stop_existing_app", ["cmd", "/c", "stop.bat"]),
        QaCommand("compileall", [sys.executable, "-m", "compileall", "thai_pdf_editor", "scripts", "run_app.py", "tests"]),
        QaCommand("pytest", [sys.executable, "-m", "pytest"]),
        QaCommand("phase7_qa", [sys.executable, "scripts/phase7_qa.py"]),
        QaCommand("font_import_qa", [sys.executable, "scripts/font_import_qa.py"]),
        QaCommand("overlay_edit_qa", [sys.executable, "scripts/overlay_edit_qa.py"]),
        QaCommand("phase43_ui_qa", [sys.executable, "scripts/phase43_ui_qa.py"]),
        QaCommand("run_app_smoke", [sys.executable, "run_app.py", "--smoke-test"]),
        QaCommand("start_bat_smoke", ["cmd", "/c", "start.bat", "--smoke-test"]),
        QaCommand("stop_bat", ["cmd", "/c", "stop.bat"]),
        QaCommand("final_acceptance", [sys.executable, "scripts/final_acceptance.py"]),
    ]
    if include_build:
        commands.extend(
            [
                QaCommand("build_exe", ["cmd", "/c", "scripts\\build_exe.bat"]),
                QaCommand("exe_smoke", ["dist\\ThaiLocalPdfEditor\\ThaiLocalPdfEditor.exe", "--smoke-test"]),
            ]
        )
    return commands


def build_static_report(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Check source hygiene that does not require launching the app."""
    source_files = list(_source_files(root))
    over_line_limit: list[dict[str, object]] = []
    mojibake_files: list[str] = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        if line_count > MAX_SOURCE_LINES:
            over_line_limit.append({"path": _relative(path, root), "lines": line_count})
        if any(marker in text for marker in MOJIBAKE_MARKERS) or any("\x80" <= char <= "\x9f" for char in text):
            mojibake_files.append(_relative(path, root))

    missing_paths = [_relative(root / path, root) for path in REQUIRED_PATHS if not (root / path).exists()]
    return {
        "checked_source_files": len(source_files),
        "source_files_over_line_limit": over_line_limit,
        "mojibake_files": mojibake_files,
        "missing_required_paths": missing_paths,
    }


def run_release_qa(*, include_build: bool = False) -> dict[str, Any]:
    """Run release QA commands and write a structured report."""
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "include_build": include_build,
        "static": build_static_report(PROJECT_ROOT),
        "commands": [],
        "passed": False,
    }
    for qa_command in release_commands(include_build=include_build):
        result = _run_command(qa_command)
        report["commands"].append(result)
        if result["returncode"] != 0 or result["stderr_blocker"]:
            _write_report(report)
            raise SystemExit(result["returncode"] or 1)
    report["passed"] = _report_passed(report)
    _write_report(report)
    if not report["passed"]:
        raise SystemExit(1)
    return report


def _run_command(qa_command: QaCommand) -> dict[str, Any]:
    completed = subprocess.run(
        qa_command.command,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return {
        "name": qa_command.name,
        "command": qa_command.command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "stderr_blocker": _has_fatal_stderr(completed.stderr),
    }


def _report_passed(report: dict[str, Any]) -> bool:
    static = report["static"]
    commands = report["commands"]
    return (
        not static["source_files_over_line_limit"]
        and not static["mojibake_files"]
        and not static["missing_required_paths"]
        and all(command["returncode"] == 0 and not command["stderr_blocker"] for command in commands)
    )


def _has_fatal_stderr(stderr: str) -> bool:
    return any(marker in stderr for marker in FATAL_STDERR_MARKERS)


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("/", "\\")


def _write_report(report: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Thai Local PDF Editor release QA")
    parser.add_argument("--include-build", action="store_true", help="also build and smoke-test the packaged exe")
    args = parser.parse_args()
    report = run_release_qa(include_build=args.include_build)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
