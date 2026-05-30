# -*- coding: utf-8 -*-
"""Tests for readable Thai UI font and layout configuration."""

from thai_pdf_editor.app.constants import APP_MIN_HEIGHT, APP_MIN_WIDTH, CREATOR_CREDIT
from thai_pdf_editor.app.ui.fonts import (
    BUTTON_FONT,
    BUTTON_HEIGHT,
    CANVAS_MESSAGE_FONT,
    ENTRY_FONT,
    ENTRY_HEIGHT,
    LABEL_FONT,
    PAGE_LIST_MIN_HEIGHT,
    PAGE_PANEL_WIDTH,
    TOOLBAR_HEIGHT,
    TOOL_PANEL_WIDTH,
    UI_FONT_FAMILY,
    readable_button_width,
)
from thai_pdf_editor.app.ui.keyboard_shortcuts import NAVIGATION_SHORTCUTS
from thai_pdf_editor.app.ui.scrolling import (
    BOTTOM_SCROLLBAR_HEIGHT,
    BOTTOM_SCROLLBAR_PAN_MIN_EXTRA,
    BOTTOM_SCROLLBAR_PAN_VIEWPORT_FACTOR,
    BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH,
    HORIZONTAL_SCROLLBAR_THICKNESS,
    SCROLLBAR_WIDTH,
    WHEEL_SCROLL_FINE_FACTOR,
    WHEEL_SCROLL_UNITS,
    ctk_scroll_units_with_remainder,
    wheel_scroll_units,
    wheel_scroll_units_with_remainder,
)
from thai_pdf_editor.app.ui.theme import (
    COLORS,
    PAGE_PANEL_DEFAULT_WIDTH,
    PAGE_PANEL_MAX_WIDTH,
    PAGE_PANEL_MIN_WIDTH,
    RESIZER_WIDTH,
    RIBBON_BUTTON_HEIGHT,
    TOOL_PANEL_DEFAULT_WIDTH,
    TOOL_PANEL_MAX_WIDTH,
    TOOL_PANEL_MIN_WIDTH,
    button_depth_palette,
    button_style,
    clamp_page_panel_width,
    clamp_tool_panel_width,
)
from thai_pdf_editor.app.utils.font_utils import preferred_ui_font


def test_ui_font_family_uses_thai_capable_font() -> None:
    """UI widgets use the Thai-capable font family helper."""
    assert UI_FONT_FAMILY == preferred_ui_font()
    assert UI_FONT_FAMILY in {"Tahoma", "Leelawadee UI", "Segoe UI"}


def test_primary_ui_fonts_are_large_enough_to_read() -> None:
    """Thai text should not fall back to tiny default widget fonts."""
    for font in (BUTTON_FONT, CANVAS_MESSAGE_FONT, ENTRY_FONT, LABEL_FONT):
        assert font[0] == UI_FONT_FAMILY
        assert font[1] >= 14


def test_primary_controls_are_sized_for_thai_text() -> None:
    """Common Thai controls should have stable readable dimensions."""
    assert APP_MIN_WIDTH >= 1440
    assert APP_MIN_HEIGHT >= 760
    assert TOOL_PANEL_WIDTH >= 320
    assert PAGE_PANEL_WIDTH >= 250
    assert TOOLBAR_HEIGHT == 1
    assert PAGE_LIST_MIN_HEIGHT >= 220
    assert BUTTON_HEIGHT >= 38
    assert ENTRY_HEIGHT >= 36
    assert SCROLLBAR_WIDTH >= 24
    assert BOTTOM_SCROLLBAR_HEIGHT >= 42
    assert HORIZONTAL_SCROLLBAR_THICKNESS >= 28
    assert BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH >= 56
    assert BOTTOM_SCROLLBAR_PAN_MIN_EXTRA >= 180
    assert BOTTOM_SCROLLBAR_PAN_VIEWPORT_FACTOR >= 0.50
    assert RIBBON_BUTTON_HEIGHT >= 60
    assert RESIZER_WIDTH >= 14

    labels = [
        "บันทึกเป็น",
        "ล่าสุด",
        "ค้นหา",
        "เปิดไฟล์ที่เลือก",
        "ล้างทั้งหมด",
        "บันทึกต่อ",
        "ปิดหน้าต่าง",
        "ยกเลิกและกลับไปแก้",
        "ตรวจงาน",
        "ข้อมูลไฟล์",
        "พอดีกว้าง",
        "พอดีบน-ล่าง",
        "เลือกรูป/ลายเซ็นภาพ",
        "สร้างลายเซ็นภาพ",
        "ลบ/ปิดทับข้อมูลถาวร",
        "แก้ข้อความเดิม",
        "หา/โหลดฟอนต์",
        "รายการที่วางแล้ว",
        "ลบรายการ",
    ]
    for label in labels:
        assert readable_button_width(label) >= 96
        assert readable_button_width(label) >= 36 + len(label) * 9


def test_polished_ui_tokens_include_credit_and_contrast_colors() -> None:
    """The refreshed UI keeps the requested credit and shared visual tokens."""
    assert CREATOR_CREDIT == "สร้างโดย อิสระพงษ์ id line iss2510"
    assert COLORS["surface"] == "#ffffff"
    assert COLORS["primary"].startswith("#")
    assert COLORS["danger"].startswith("#")


def test_buttons_have_raised_and_pressed_visual_depth_tokens() -> None:
    """Shared button tokens should make controls look raised and depress on click."""
    secondary_style = button_style("secondary")
    secondary_depth = button_depth_palette("secondary")
    primary_depth = button_depth_palette("primary")

    assert secondary_style["border_width"] >= 2
    assert secondary_style["border_color"] == secondary_depth["border_color"]
    assert secondary_style["fg_color"] != secondary_depth["pressed_fg_color"]
    assert secondary_depth["pressed_border_width"] < secondary_depth["border_width"]
    assert primary_depth["pressed_fg_color"] != primary_depth["fg_color"]


def test_tool_panel_resize_range_keeps_reader_usable() -> None:
    """The PDF reader dividers keep side panels in stable width ranges."""
    assert TOOL_PANEL_MIN_WIDTH <= TOOL_PANEL_DEFAULT_WIDTH <= TOOL_PANEL_MAX_WIDTH
    assert clamp_tool_panel_width(1) == TOOL_PANEL_MIN_WIDTH
    assert clamp_tool_panel_width(TOOL_PANEL_DEFAULT_WIDTH) == TOOL_PANEL_DEFAULT_WIDTH
    assert clamp_tool_panel_width(9999) == TOOL_PANEL_MAX_WIDTH
    assert PAGE_PANEL_MIN_WIDTH <= PAGE_PANEL_DEFAULT_WIDTH <= PAGE_PANEL_MAX_WIDTH
    assert clamp_page_panel_width(1) == PAGE_PANEL_MIN_WIDTH
    assert clamp_page_panel_width(PAGE_PANEL_DEFAULT_WIDTH) == PAGE_PANEL_DEFAULT_WIDTH
    assert clamp_page_panel_width(9999) == PAGE_PANEL_MAX_WIDTH


def test_mouse_wheel_scroll_units_are_large_enough_to_control() -> None:
    """Mouse-wheel scrolling should be 30% finer while keeping visible steps."""
    assert WHEEL_SCROLL_UNITS >= 4
    assert WHEEL_SCROLL_FINE_FACTOR == 0.70
    assert wheel_scroll_units(delta=120) == -3
    assert wheel_scroll_units(delta=-120) == 3
    assert wheel_scroll_units(delta=240) == -6
    assert wheel_scroll_units(num=4) == -3
    assert wheel_scroll_units(num=5) == 3
    assert wheel_scroll_units() == 0


def test_mouse_wheel_scroll_remainder_keeps_thirty_percent_finer_average() -> None:
    """Fractional scroll units are carried so repeated wheel steps average exactly."""
    remainder = 0.0
    total_units = 0
    for _ in range(5):
        units, remainder = wheel_scroll_units_with_remainder(delta=120, remainder=remainder)
        total_units += units

    assert total_units == -14
    assert round(remainder, 8) == 0


def test_customtkinter_panel_scroll_is_thirty_percent_finer_on_windows() -> None:
    """Scrollable side panels use the same 30% finer wheel behavior."""
    units, remainder = ctk_scroll_units_with_remainder(120, platform_name="win32", remainder=0.0)

    assert units == -14
    assert round(remainder, 8) == 0


def test_navigation_shortcuts_are_available_for_long_documents() -> None:
    """Long document navigation should have keyboard shortcuts."""
    assert NAVIGATION_SHORTCUTS["previous_page"] == "<Prior>"
    assert NAVIGATION_SHORTCUTS["next_page"] == "<Next>"
    assert NAVIGATION_SHORTCUTS["first_page"] == "<Home>"
    assert NAVIGATION_SHORTCUTS["last_page"] == "<End>"
