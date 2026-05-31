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
