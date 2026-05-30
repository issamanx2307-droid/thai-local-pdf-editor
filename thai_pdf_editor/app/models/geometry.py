# -*- coding: utf-8 -*-
"""Geometry models in PDF point coordinates."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfPoint:
    """A point in PDF coordinate space."""

    x: float
    y: float


@dataclass(frozen=True)
class PdfRect:
    """A rectangle in PDF coordinate space."""

    x0: float
    y0: float
    x1: float
    y1: float

    @classmethod
    def from_points(cls, start: PdfPoint, end: PdfPoint) -> "PdfRect":
        """Build a normalized rectangle from two points."""
        return cls(
            x0=min(start.x, end.x),
            y0=min(start.y, end.y),
            x1=max(start.x, end.x),
            y1=max(start.y, end.y),
        )

    @property
    def width(self) -> float:
        """Return rectangle width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Return rectangle height."""
        return self.y1 - self.y0
