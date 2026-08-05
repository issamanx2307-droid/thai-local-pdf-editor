# -*- coding: utf-8 -*-
"""Tests for the packaged React bridge entrypoint."""

from __future__ import annotations

import run_react_bridge


def test_react_bridge_entrypoint_runs_print_worker(monkeypatch) -> None:
    """The frozen bridge executable must support the GDI print-worker switch."""
    calls: list[tuple[str, str, int, str | None]] = []

    def fake_worker(pdf_path: str, printer: str, *, copies: int, pages: str | None) -> int:
        calls.append((pdf_path, printer, copies, pages))
        return 0

    from thai_pdf_editor.app.core import print_operations

    monkeypatch.setattr(print_operations, "run_print_worker", fake_worker)

    assert run_react_bridge.main(
        ["--print-worker", "D:/เอกสาร/test.pdf", "--printer", "Printer A", "--copies", "2", "--pages", "1-3"]
    ) == 0
    assert calls == [("D:/เอกสาร/test.pdf", "Printer A", 2, "1-3")]


def test_react_bridge_entrypoint_forwards_normal_bridge_arguments(monkeypatch) -> None:
    """Normal sidecar startup still delegates to the HTTP bridge."""
    calls: list[list[str]] = []
    monkeypatch.setattr(run_react_bridge, "run_bridge", lambda argv: calls.append(argv) or 0)

    assert run_react_bridge.main(["--port", "5178"]) == 0
    assert calls == [["--port", "5178"]]
