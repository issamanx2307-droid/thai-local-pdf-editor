# -*- coding: utf-8 -*-
"""Static contract checks for React-only viewer behavior."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_react_viewer_fullscreen_and_scrollbar_are_wired() -> None:
    """Viewer expansion and bottom scrollbar sync should not regress silently."""
    app_source = (PROJECT_ROOT / "react_shell" / "src" / "App.tsx").read_text(encoding="utf-8")
    app_css = (PROJECT_ROOT / "react_shell" / "src" / "App.css").read_text(encoding="utf-8")

    assert "requestFullscreen" in app_source
    assert "document.exitFullscreen" in app_source
    assert "is-viewer-expanded" in app_source
    assert "bottom-scrollbar" in app_source
    assert "stage.scrollLeft" in app_source
    assert "bottomScroll.scrollLeft = stage.scrollLeft" in app_source
    assert ".app-shell.is-viewer-expanded" in app_css
    assert ".bottom-scrollbar" in app_css


def test_open_batch_activates_the_native_pdf_viewer() -> None:
    """Opening a PDF uses a batch, so it must still enable the PDF.js viewer."""
    app_source = (PROJECT_ROOT / "react_shell" / "src" / "App.tsx").read_text(encoding="utf-8")
    worker_api_source = (PROJECT_ROOT / "react_shell" / "src" / "workerApi.ts").read_text(encoding="utf-8")

    assert "responseHasCommand(response, 'open_pdf')" in app_source
    assert "function responseHasCommand" in worker_api_source
