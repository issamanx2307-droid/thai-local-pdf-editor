# -*- coding: utf-8 -*-
"""Tests for PDF drag-and-drop path handling."""

from pathlib import Path

from thai_pdf_editor.app.ui import drag_drop
from thai_pdf_editor.app.ui.drag_drop import first_pdf_path, parse_dropped_paths


def test_parse_dropped_paths_with_spaces_and_thai_text() -> None:
    """Dropped paths from tkdnd preserve spaces and Thai file names."""
    raw_data = r'{D:\เอกสารลูกค้า\ใบเสนอราคา 1.pdf} {D:\tmp\รูป.png}'

    paths = parse_dropped_paths(raw_data, lambda value: value.split("} {"))

    assert paths[0] == Path(r"D:\เอกสารลูกค้า\ใบเสนอราคา 1.pdf")
    assert paths[1] == Path(r"D:\tmp\รูป.png")


def test_first_pdf_path_chooses_first_pdf_only() -> None:
    """Only PDF files should be opened from a mixed drop set."""
    paths = [
        Path(r"D:\tmp\รูป.png"),
        Path(r"D:\เอกสาร\ไฟล์.pdf"),
        Path(r"D:\เอกสาร\อีกไฟล์.pdf"),
    ]

    assert first_pdf_path(paths) == Path(r"D:\เอกสาร\ไฟล์.pdf")


def test_parse_file_uri_drop_path() -> None:
    """File URI drops are converted to Windows paths."""
    paths = parse_dropped_paths("file:///D:/%E0%B9%84%E0%B8%9F%E0%B8%A5%E0%B9%8C.pdf", lambda value: [value])

    assert paths == [Path(r"D:\ไฟล์.pdf")]


def test_enable_pdf_drop_target_returns_true_when_any_widget_registers(monkeypatch) -> None:
    """CustomTk widgets without tkdnd methods should not block valid targets."""
    calls: list[object] = []

    class FakeTkinterDnD:
        @staticmethod
        def _require(_root: object) -> str:
            return "2.9"

    class FakeTk:
        @staticmethod
        def splitlist(value: str) -> list[str]:
            return [value]

    class FakeRoot:
        tk = FakeTk()

    class MissingDndMethods:
        pass

    class GoodWidget:
        def drop_target_register(self, dnd_type: str) -> None:
            calls.append(("register", dnd_type))

        def dnd_bind(self, sequence: str, callback: object) -> None:
            calls.append(("bind", sequence, callback))

    monkeypatch.setattr(drag_drop, "TkinterDnD", FakeTkinterDnD)

    enabled = drag_drop.enable_pdf_drop_target(FakeRoot(), [MissingDndMethods(), GoodWidget()], lambda _paths: None)

    assert enabled is True
    assert calls[0] == ("register", drag_drop.DND_FILES)
    assert calls[1][0:2] == ("bind", "<<Drop>>")


def test_enable_pdf_drop_target_returns_false_when_no_widget_registers(monkeypatch) -> None:
    """The feature should not report enabled when no drop target was bound."""

    class FakeTkinterDnD:
        @staticmethod
        def _require(_root: object) -> str:
            return "2.9"

    class FakeRoot:
        pass

    monkeypatch.setattr(drag_drop, "TkinterDnD", FakeTkinterDnD)
    monkeypatch.setattr(drag_drop.LOGGER, "warning", lambda *_args, **_kwargs: None)

    enabled = drag_drop.enable_pdf_drop_target(FakeRoot(), [object()], lambda _paths: None)

    assert enabled is False
