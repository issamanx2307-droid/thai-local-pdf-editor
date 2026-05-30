# -*- coding: utf-8 -*-
"""Shared scrolling settings for desktop widgets."""

from __future__ import annotations

SCROLLBAR_WIDTH = 24
BOTTOM_SCROLLBAR_HEIGHT = 42
HORIZONTAL_SCROLLBAR_THICKNESS = 28
BOTTOM_SCROLLBAR_THUMB_MIN_WIDTH = 56
BOTTOM_SCROLLBAR_PAN_MIN_EXTRA = 180
BOTTOM_SCROLLBAR_PAN_VIEWPORT_FACTOR = 0.50
WHEEL_SCROLL_UNITS = 4
WHEEL_SCROLL_FINE_FACTOR = 0.70


def wheel_scroll_units(delta: int = 0, num: int | None = None) -> int:
    """Convert a Tk mouse-wheel event value to yview/xview scroll units."""
    units, _remainder = wheel_scroll_units_with_remainder(delta=delta, num=num, remainder=0.0)
    return units


def wheel_scroll_units_with_remainder(
    delta: int = 0,
    num: int | None = None,
    *,
    remainder: float = 0.0,
) -> tuple[int, float]:
    """Convert a Tk mouse-wheel event value, carrying fractional scroll units."""
    if num == 4:
        return _scaled_scroll_units(-WHEEL_SCROLL_UNITS, remainder)
    if num == 5:
        return _scaled_scroll_units(WHEEL_SCROLL_UNITS, remainder)
    if delta == 0:
        return 0, 0.0
    notches = max(1, abs(delta) // 120)
    direction = -1 if delta > 0 else 1
    return _scaled_scroll_units(direction * notches * WHEEL_SCROLL_UNITS, remainder)


def event_wheel_scroll_units(event: object) -> int:
    """Return scroll units from a Tk event object."""
    return wheel_scroll_units(
        delta=int(getattr(event, "delta", 0) or 0),
        num=getattr(event, "num", None),
    )


def event_wheel_scroll_units_with_remainder(event: object, *, remainder: float) -> tuple[int, float]:
    """Return scroll units from a Tk event object, carrying fractional scroll units."""
    return wheel_scroll_units_with_remainder(
        delta=int(getattr(event, "delta", 0) or 0),
        num=getattr(event, "num", None),
        remainder=remainder,
    )


def ctk_scroll_units_with_remainder(
    delta: int,
    *,
    platform_name: str,
    remainder: float = 0.0,
) -> tuple[int, float]:
    """Return finer wheel units for CustomTkinter scrollable frames."""
    if delta == 0:
        return 0, 0.0
    if platform_name.startswith("win"):
        raw_units = -int(delta / 6)
    else:
        raw_units = -delta
    return _scaled_scroll_units(raw_units, remainder)


def _scaled_scroll_units(raw_units: int, remainder: float) -> tuple[int, float]:
    if raw_units == 0:
        return 0, 0.0
    scaled = (raw_units * WHEEL_SCROLL_FINE_FACTOR) + remainder
    units = int(round(scaled))
    if units == 0:
        units = -1 if scaled < 0 else 1
    return units, scaled - units
