# -*- coding: utf-8 -*-
"""Verify the packaged React bridge recognizes its print-worker mode.

The probe intentionally uses a missing PDF path, so it never creates a real
printer job.  A return code of 1 proves the frozen executable reached the
print-worker validation path rather than starting the HTTP bridge.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIDECAR_PATH = PROJECT_ROOT / "react_shell" / "src-tauri" / "binaries" / "pdf-bridge-x86_64-pc-windows-msvc.exe"


def verify_sidecar_print_worker(sidecar_path: Path = SIDECAR_PATH) -> None:
    """Assert that a frozen bridge runs print-worker arguments, not HTTP mode."""
    if not sidecar_path.is_file():
        raise FileNotFoundError(f"ไม่พบไฟล์ sidecar ที่ build แล้ว: {sidecar_path}")

    probe = subprocess.run(
        [
            str(sidecar_path),
            "--print-worker",
            str(PROJECT_ROOT / "_print_worker_probe_missing.pdf"),
            "--printer",
            "QA printer",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if probe.returncode != 1:
        raise RuntimeError(
            "sidecar ไม่เข้าสู่โหมด print-worker ที่คาดไว้ "
            f"(exit code {probe.returncode})"
        )


def main() -> None:
    try:
        verify_sidecar_print_worker()
    except Exception as exc:  # noqa: BLE001
        print(f"React bridge sidecar QA failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("React bridge sidecar print-worker QA passed")


if __name__ == "__main__":
    main()
